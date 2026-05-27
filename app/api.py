from .defender import fix_defender_logic
from .config import MAX_GUARD_INTERVAL_SECONDS
from .logging_store import add_log, get_activity_snapshot, log_defender_results, log_update_results, set_current_action
from .state import STATE
from .status import check_status
from .update_controls import disable_update_controls, restore_update_controls
from .windows import apply_native_window_icons


class API:
    def get_status(self):
        return check_status()

    def get_activity_log(self):
        return get_activity_snapshot()

    def open_status_window(self):
        try:
            if STATE.status_window is not None:
                STATE.status_window.show()
                apply_native_window_icons()
                add_log("Status window opened")
                return {"ok": True, "opened": True}
        except Exception as exc:
            add_log(f"Status window failed: {exc}")
            return {"ok": False, "error": str(exc)}

        return {"ok": False, "error": "Status window is not available"}

    def open_settings_window(self):
        return self.open_status_window()

    def run_all(self):
        from .admin import require_admin

        set_current_action("Start")
        add_log("Start requested")

        try:
            if not require_admin():
                add_log("Start stopped: admin required")
                return check_status()

            update_results = disable_update_controls()
            log_update_results("Start", update_results)

            STATE.update_guard_enabled = True
            add_log("Update guard enabled")

            defender_results = fix_defender_logic(check_admin=False)
            log_defender_results("Start Defender", defender_results)

            status = check_status()
            add_log("Start completed")
            return status
        finally:
            set_current_action("Idle")

    def stop_watchdog(self):
        set_current_action("Stop")
        add_log("Stop requested")

        try:
            if STATE.update_guard_enabled:
                STATE.update_guard_enabled = False
                add_log("Update guard disabled")
            else:
                add_log("Update guard already off")

            add_log("Stop completed")
            return check_status()
        finally:
            set_current_action("Idle")

    def fix_defender(self):
        set_current_action("Fix Defender")
        add_log("Fix Defender started")

        try:
            results = fix_defender_logic(check_admin=True)
            if results.get("admin") is False:
                add_log("Fix Defender stopped: admin required")
            else:
                log_defender_results("Fix Defender", results)
                add_log("Fix Defender completed")
            return check_status()
        finally:
            set_current_action("Idle")

    def restore_all(self):
        from .admin import require_admin

        set_current_action("Restore")
        add_log("Restore started")

        try:
            if not require_admin():
                add_log("Restore stopped: admin required")
                return check_status()

            STATE.update_guard_enabled = False
            add_log("Update guard disabled")

            results = restore_update_controls()
            log_update_results("Restore", results)
            add_log("Restore completed")
            return check_status()
        finally:
            set_current_action("Idle")

    def toggle_ignore(self, value):
        STATE.ignore_defender = bool(value)
        add_log(f"Ignore Defender set to {STATE.ignore_defender}")
        return check_status()

    def set_guard_interval(self, value=0, unit="seconds"):
        try:
            value = max(0, int(value))
        except Exception:
            value = 0

        unit = (unit or "seconds").lower()

        if unit == "hours":
            total = value * 3600
        elif unit == "minutes":
            total = value * 60
        else:
            unit = "seconds"
            total = value

        total = min(MAX_GUARD_INTERVAL_SECONDS, max(1, total))
        STATE.update_guard_interval_seconds = total
        STATE.guard_interval_changed.set()
        add_log(f"Watch interval set to {value} {unit} [{total} second(s)]")
        return check_status()
