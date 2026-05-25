from .admin import is_admin
from .config import APP_VERSION, UPDATE_OPTIONAL_SERVICES, UPDATE_SERVICES
from .defender import check_defender
from .service_ops import get_service_info, update_service_optional_ok, update_service_required_ok
from .state import STATE
from .update_controls import is_windows_update_policy_disabled


def check_update_controls():
    services = [get_service_info(service) for service in UPDATE_SERVICES]
    optional_services = [get_service_info(service) for service in UPDATE_OPTIONAL_SERVICES]

    services_ok = all(update_service_required_ok(svc) for svc in services)
    optional_ok = all(update_service_optional_ok(svc) for svc in optional_services)
    policy_ok = is_windows_update_policy_disabled()

    return {
        "ok": bool(services_ok and optional_ok and policy_ok),
        "services": services,
        "optional_services": optional_services,
        "policy_disabled": policy_ok,
        "guard_enabled": STATE.update_guard_enabled,
    }


def _interval_parts(total_seconds):
    total = max(1, int(total_seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return {
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }


def check_status():
    with STATE.status_lock:
        updates = check_update_controls()
        defender = check_defender()
        interval_seconds = max(1, int(STATE.update_guard_interval_seconds))

        return {
            "services": updates["ok"],
            "defender": None if STATE.ignore_defender else defender["ok"],
            "details": {
                "updates": updates,
                "defender": defender,
                "ignore_defender": STATE.ignore_defender,
                "admin": is_admin(),
                "version": APP_VERSION,
                "guard_interval_seconds": interval_seconds,
                "guard_interval_parts": _interval_parts(interval_seconds),
            },
        }
