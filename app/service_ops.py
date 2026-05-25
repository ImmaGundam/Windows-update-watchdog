import re

from .commands import run_cmd, run_powershell
from .registry_ops import set_dword_hklm


def get_service_info(service):
    query = run_cmd(["sc", "query", service], timeout=8)
    qc = run_cmd(["sc", "qc", service], timeout=8)

    if not query["ok"] and not qc["ok"]:
        return {
            "name": service,
            "exists": False,
            "state": "Missing",
            "start_type": "Missing",
            "query": query,
            "qc": qc,
        }

    state = "Unknown"
    state_match = re.search(r"STATE\s*:\s*\d+\s+(\w+)", query["stdout"])
    if state_match:
        raw_state = state_match.group(1).upper()
        if raw_state == "RUNNING":
            state = "Running"
        elif raw_state == "STOPPED":
            state = "Stopped"
        else:
            state = raw_state.title()

    start_type = "Unknown"
    start_match = re.search(r"START_TYPE\s*:\s*\d+\s+(\w+)", qc["stdout"])
    if start_match:
        raw_start = start_match.group(1).upper()
        if raw_start == "DISABLED":
            start_type = "Disabled"
        elif raw_start in ("DEMAND_START", "DEMAND"):
            start_type = "Manual"
        elif raw_start in ("AUTO_START", "AUTO"):
            start_type = "Automatic"
        elif raw_start == "BOOT_START":
            start_type = "Boot"
        elif raw_start == "SYSTEM_START":
            start_type = "System"
        else:
            start_type = raw_start.title()

    return {
        "name": service,
        "exists": True,
        "state": state,
        "start_type": start_type,
        "query": query,
        "qc": qc,
    }


def stop_service(service):
    return run_cmd(["sc", "stop", service], timeout=15)


def start_service(service):
    return run_cmd(["sc", "start", service], timeout=15)


def set_service_start_type(service, start_type):
    return run_cmd(["sc", "config", service, "start=", start_type], timeout=15)


def set_service_registry_start(service, value):
    return set_dword_hklm(rf"SYSTEM\CurrentControlSet\Services\{service}", "Start", value)


def powershell_stop_and_disable_service(service):
    script = rf'''
    try {{
        Stop-Service -Name "{service}" -Force -ErrorAction SilentlyContinue
        Set-Service -Name "{service}" -StartupType Disabled -ErrorAction SilentlyContinue
        "ok"
    }} catch {{
        "error: $($_.Exception.Message)"
    }}
    '''
    return run_powershell(script, timeout=20)


def update_service_required_ok(svc):
    if not svc or not svc.get("exists"):
        return True
    return svc.get("state") != "Running" and svc.get("start_type") == "Disabled"


def update_service_optional_ok(svc):
    if not svc or not svc.get("exists"):
        return True
    return svc.get("state") != "Running"


def stop_and_disable_service(service):
    before = get_service_info(service)
    results = []

    if not before["exists"]:
        return {"service": service, "ok": True, "skipped": True, "reason": "missing", "before": before}

    if before["state"] == "Running":
        results.append(stop_service(service))
        results.append(powershell_stop_and_disable_service(service))

    results.append(set_service_start_type(service, "disabled"))
    results.append(set_service_registry_start(service, 4))

    after_first = get_service_info(service)
    if after_first["state"] == "Running":
        results.append(stop_service(service))
        results.append(powershell_stop_and_disable_service(service))

    after = get_service_info(service)

    return {
        "service": service,
        "ok": update_service_required_ok(after),
        "before": before,
        "after": after,
        "results": results,
    }


def enable_service(service, start_type="demand", should_start=True):
    before = get_service_info(service)
    results = []

    if not before["exists"]:
        return {"service": service, "ok": True, "skipped": True, "reason": "missing", "before": before}

    start_value = 2 if start_type == "auto" else 3
    results.append(set_service_registry_start(service, start_value))
    results.append(set_service_start_type(service, start_type))
    if should_start:
        results.append(start_service(service))

    after = get_service_info(service)
    return {
        "service": service,
        "ok": after["exists"] and after["start_type"] != "Disabled",
        "before": before,
        "after": after,
        "results": results,
    }
