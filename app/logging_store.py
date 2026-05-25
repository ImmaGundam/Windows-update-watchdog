import time

from .config import MAX_LOG_LINES
from .state import STATE


def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"

    with STATE.activity_lock:
        STATE.activity_log.append(line)
        if len(STATE.activity_log) > MAX_LOG_LINES:
            del STATE.activity_log[:-MAX_LOG_LINES]


def set_current_action(action):
    with STATE.activity_lock:
        STATE.current_action = action


def get_activity_snapshot():
    with STATE.activity_lock:
        return {
            "current_action": STATE.current_action,
            "lines": list(STATE.activity_log[-MAX_LOG_LINES:]),
        }


def log_service_change(prefix, item):
    service = item.get("service", "unknown")

    if item.get("skipped"):
        add_log(f"{prefix}: {service} skipped ({item.get('reason', 'not applicable')})")
        return

    before = item.get("before") or {}
    after = item.get("after") or {}
    before_text = f"{before.get('state', '?')}/{before.get('start_type', '?')}"
    after_text = f"{after.get('state', '?')}/{after.get('start_type', '?')}"
    result = "OK" if item.get("ok") else "CHECK"
    add_log(f"{prefix}: {service} {before_text} -> {after_text} [{result}]")


def log_update_results(prefix, results):
    for item in results.get("services", []):
        log_service_change(prefix, item)
    for item in results.get("optional_services", []):
        log_service_change(prefix + " optional", item)

    policy = results.get("policy")
    if isinstance(policy, dict):
        add_log(f"{prefix}: update policy {'OK' if policy.get('ok') else 'CHECK'}")

    tasks = results.get("tasks")
    if isinstance(tasks, dict):
        add_log(f"{prefix}: UpdateOrchestrator tasks {'OK' if tasks.get('ok') else 'CHECK'}")

    metered = results.get("metered_ethernet")
    if isinstance(metered, dict):
        add_log(f"{prefix}: Ethernet metered setting {'OK' if metered.get('ok') else 'CHECK'}")


def log_defender_results(prefix, results):
    for item in results.get("services", []):
        log_service_change(prefix, item)

    removed = results.get("removed_policies", [])
    removed_count = sum(1 for item in removed if item.get("removed"))
    add_log(f"{prefix}: Defender policy cleanup removed {removed_count} value(s)")

    sig = results.get("signature_updates")
    if isinstance(sig, dict):
        add_log(f"{prefix}: Defender signature fallback {'OK' if sig.get('ok') else 'CHECK'}")

    add_log(f"{prefix}: Defender status {'OK' if results.get('ok') else 'CHECK'}")
