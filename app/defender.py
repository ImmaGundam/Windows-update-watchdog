import json
import time

from .admin import require_admin
from .commands import run_powershell
from .config import DEFENDER_CORE_SERVICE, DEFENDER_OPTIONAL_SERVICES, DEFENDER_SUPPORT_SERVICES
from .registry_ops import delete_value_hklm, set_string_hklm
from .service_ops import enable_service, get_service_info
from .state import STATE


def remove_known_defender_policy_blocks():
    targets = {
        r"SOFTWARE\Policies\Microsoft\Windows Defender": [
            "DisableAntiSpyware",
            "DisableAntiVirus",
            "DisableSpecialRunningModes",
            "ServiceKeepAlive",
        ],
        r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection": [
            "DisableRealtimeMonitoring",
            "DisableBehaviorMonitoring",
            "DisableOnAccessProtection",
            "DisableScanOnRealtimeEnable",
            "DisableIOAVProtection",
        ],
        r"SOFTWARE\Policies\Microsoft\Windows Defender\Spynet": [
            "DisableBlockAtFirstSeen",
        ],
    }

    results = []
    for path, names in targets.items():
        for name in names:
            results.append(delete_value_hklm(path, name))
    return results


def enable_defender_signature_updates():
    return set_string_hklm(
        r"SOFTWARE\Policies\Microsoft\Windows Defender\Signature Updates",
        "FallbackOrder",
        "MMPC",
    )


def get_defender_mp_status_cached(max_age_seconds=30):
    now = time.time()
    cache = STATE.defender_cache
    if cache.status is not None and now - cache.checked_at < max_age_seconds:
        return cache.status

    script = r"""
    try {
        $s = Get-MpComputerStatus -ErrorAction Stop
        [PSCustomObject]@{
            AMServiceEnabled = $s.AMServiceEnabled
            AntivirusEnabled = $s.AntivirusEnabled
            RealTimeProtectionEnabled = $s.RealTimeProtectionEnabled
            BehaviorMonitorEnabled = $s.BehaviorMonitorEnabled
            IoavProtectionEnabled = $s.IoavProtectionEnabled
            NISEnabled = $s.NISEnabled
            IsTamperProtected = $s.IsTamperProtected
        } | ConvertTo-Json -Compress
    } catch {
        [PSCustomObject]@{
            Error = $_.Exception.Message
        } | ConvertTo-Json -Compress
    }
    """

    result = run_powershell(script, timeout=12)
    status = {"ok": False, "source": "Get-MpComputerStatus", "raw": result}

    if result["ok"] and result["stdout"]:
        try:
            data = json.loads(result["stdout"].splitlines()[-1])
            if data.get("Error"):
                status = {"ok": False, "source": "Get-MpComputerStatus", "data": data, "raw": result}
            else:
                protection_ok = (
                    data.get("AMServiceEnabled") is True
                    and data.get("AntivirusEnabled") is True
                    and data.get("RealTimeProtectionEnabled") is True
                )
                status = {
                    "ok": protection_ok,
                    "source": "Get-MpComputerStatus",
                    "data": data,
                    "raw": result,
                }
        except Exception as exc:
            status = {"ok": False, "source": "Get-MpComputerStatus", "error": str(exc), "raw": result}

    cache.checked_at = now
    cache.status = status
    return status


def check_defender():
    core = get_service_info(DEFENDER_CORE_SERVICE)
    support = [get_service_info(service) for service in DEFENDER_SUPPORT_SERVICES]
    optional = [get_service_info(service) for service in DEFENDER_OPTIONAL_SERVICES]

    core_ok = core["exists"] and core["state"] == "Running" and core["start_type"] != "Disabled"
    support_ok = all((not svc["exists"]) or svc["start_type"] != "Disabled" for svc in support)

    mp_status = get_defender_mp_status_cached()
    protection_ok = mp_status["ok"] if mp_status.get("raw", {}).get("ok") else core_ok
    ok = bool(core_ok and support_ok and protection_ok)

    return {
        "ok": ok,
        "core": core,
        "support": support,
        "optional": optional,
        "mp_status": mp_status,
    }


def fix_defender_logic(check_admin=True):
    if check_admin and not require_admin():
        return {"ok": False, "admin": False}

    results = {
        "admin": True,
        "removed_policies": remove_known_defender_policy_blocks(),
        "services": [],
        "signature_updates": enable_defender_signature_updates(),
    }

    results["services"].append(enable_service(DEFENDER_CORE_SERVICE, start_type="auto", should_start=True))

    for service in DEFENDER_SUPPORT_SERVICES:
        results["services"].append(enable_service(service, start_type="demand", should_start=True))

    for service in DEFENDER_OPTIONAL_SERVICES:
        info = get_service_info(service)
        if info["exists"]:
            results["services"].append(enable_service(service, start_type="demand", should_start=True))

    STATE.defender_cache.checked_at = 0.0
    STATE.defender_cache.status = None
    results["after"] = check_defender()
    results["ok"] = results["after"]["ok"]
    return results
