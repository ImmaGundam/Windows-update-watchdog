import time

from .config import MAX_GUARD_INTERVAL_SECONDS
from .defender import check_defender, fix_defender_logic
from .logging_store import add_log, log_defender_results, log_update_results, set_current_action
from .service_ops import update_service_optional_ok, update_service_required_ok
from .state import STATE
from .status import check_update_controls
from .update_controls import disable_update_controls


def wait_for_guard_interval():
    started_at = time.monotonic()

    while not STATE.shutdown_requested.is_set():
        interval = min(MAX_GUARD_INTERVAL_SECONDS, max(1, int(STATE.update_guard_interval_seconds)))
        remaining = interval - (time.monotonic() - started_at)

        if remaining <= 0:
            return True

        if STATE.shutdown_requested.wait(min(remaining, 0.25)):
            return False

        if STATE.guard_interval_changed.is_set():
            STATE.guard_interval_changed.clear()
            started_at = time.monotonic()

    return False


def update_guard_loop():
    while not STATE.shutdown_requested.is_set():
        if not wait_for_guard_interval():
            break

        if not STATE.update_guard_enabled:
            continue

        try:
            updates = check_update_controls()

            bad_services = [
                svc["name"]
                for svc in updates.get("services", [])
                if svc.get("exists") and not update_service_required_ok(svc)
            ]

            bad_optional = [
                svc["name"]
                for svc in updates.get("optional_services", [])
                if svc.get("exists") and not update_service_optional_ok(svc)
            ]

            bad_policy = not updates.get("policy_disabled")

            if bad_services or bad_optional or bad_policy:
                problems = bad_services + bad_optional
                if bad_policy:
                    problems.append("NoAutoUpdate policy")

                set_current_action("Update Guard")
                add_log("Guard detected re-enabled update control: " + ", ".join(problems))

                results = disable_update_controls()
                log_update_results("Guard", results)

                if not STATE.ignore_defender:
                    defender = check_defender()
                    if not defender.get("ok"):
                        add_log("Guard detected Defender check; repair started")
                        defender_results = fix_defender_logic(check_admin=False)
                        log_defender_results("Guard Defender", defender_results)

                add_log("Guard pass completed")
                set_current_action("Idle")
        except Exception as exc:
            add_log(f"Guard error: {exc}")
            set_current_action("Idle")
