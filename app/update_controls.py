from .config import UPDATE_OPTIONAL_SERVICES, UPDATE_SERVICES
from .commands import run_powershell
from .registry_ops import delete_value_hklm, read_value_hklm, set_dword_hklm
from .service_ops import enable_service, stop_and_disable_service, update_service_optional_ok


def set_windows_update_policy_disabled():
    return set_dword_hklm(
        r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
        "NoAutoUpdate",
        1,
    )


def remove_windows_update_policy_disabled():
    return delete_value_hklm(
        r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
        "NoAutoUpdate",
    )


def is_windows_update_policy_disabled():
    value = read_value_hklm(
        r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
        "NoAutoUpdate",
    )
    return value.get("exists") and int(value.get("value") or 0) == 1


def disable_update_orchestrator_tasks():
    script = r"""
    Get-ScheduledTask | Where-Object {
        $_.TaskPath -like '\Microsoft\Windows\UpdateOrchestrator*'
    } | ForEach-Object {
        Disable-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath -ErrorAction SilentlyContinue | Out-Null
    }
    "ok"
    """
    return run_powershell(script, timeout=30)


def enable_update_orchestrator_tasks():
    script = r"""
    Get-ScheduledTask | Where-Object {
        $_.TaskPath -like '\Microsoft\Windows\UpdateOrchestrator*'
    } | ForEach-Object {
        Enable-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath -ErrorAction SilentlyContinue | Out-Null
    }
    "ok"
    """
    return run_powershell(script, timeout=30)


def set_ethernet_metered(enabled):
    value = 2 if enabled else 1
    return set_dword_hklm(
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\DefaultMediaCost",
        "Ethernet",
        value,
    )


def disable_update_controls():
    results = {
        "services": [],
        "optional_services": [],
        "policy": None,
        "tasks": None,
        "metered_ethernet": None,
    }

    for service in UPDATE_SERVICES:
        results["services"].append(stop_and_disable_service(service))

    for service in UPDATE_OPTIONAL_SERVICES:
        item = stop_and_disable_service(service)
        after = item.get("after") or item.get("before")
        item["ok"] = update_service_optional_ok(after)
        results["optional_services"].append(item)

    results["policy"] = set_windows_update_policy_disabled()
    results["tasks"] = disable_update_orchestrator_tasks()
    results["metered_ethernet"] = set_ethernet_metered(True)
    return results


def restore_update_controls():
    results = {
        "services": [],
        "optional_services": [],
        "policy": None,
        "tasks": None,
        "metered_ethernet": None,
        "defender_signature_policy": None,
    }

    for service in UPDATE_SERVICES:
        results["services"].append(enable_service(service, start_type="demand", should_start=True))

    for service in UPDATE_OPTIONAL_SERVICES:
        results["optional_services"].append(enable_service(service, start_type="demand", should_start=True))

    results["policy"] = remove_windows_update_policy_disabled()
    results["tasks"] = enable_update_orchestrator_tasks()
    results["metered_ethernet"] = set_ethernet_metered(False)
    results["defender_signature_policy"] = delete_value_hklm(
        r"SOFTWARE\Policies\Microsoft\Windows Defender\Signature Updates",
        "FallbackOrder",
    )
    return results
