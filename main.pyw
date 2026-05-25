import threading

import webview

from app.api import API
from app.config import APP_NAME, APP_VERSION, STATUS_WINDOW_TITLE
from app.guard import update_guard_loop
from app.logging_store import add_log
from app.state import STATE
from app.tray import on_closing, on_status_closing, run_tray
from app.windows import apply_native_window_icons, resource_path, set_windows_app_id


def main():
    set_windows_app_id()
    add_log(f"{APP_NAME} v{APP_VERSION} started")
    STATE.api_instance = API()

    threading.Thread(target=run_tray, daemon=True).start()
    threading.Thread(target=update_guard_loop, daemon=True).start()

    STATE.window = webview.create_window(
        APP_NAME,
        resource_path("ui/main.html"),
        js_api=STATE.api_instance,
        width=200,
        height=135,
        hidden=False,
        resizable=False,
    )

    STATE.status_window = webview.create_window(
        STATUS_WINDOW_TITLE,
        resource_path("ui/status.html"),
        js_api=STATE.api_instance,
        width=715,
        height=600,
        hidden=True,
        resizable=False,
    )

    STATE.window.events.loaded += apply_native_window_icons
    STATE.status_window.events.loaded += apply_native_window_icons
    STATE.window.events.closing += on_closing
    STATE.status_window.events.closing += on_status_closing
    webview.start()


if __name__ == "__main__":
    main()
