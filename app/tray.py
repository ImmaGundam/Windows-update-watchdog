import os
import threading

import pystray
import webview
from PIL import Image, ImageDraw

from .config import APP_NAME
from .logging_store import add_log
from .state import STATE
from .status import check_status
from .windows import apply_native_window_icons


def create_icon(color):
    img = Image.new("RGB", (16, 16), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, 14, 14), fill=color)
    return img


def update_tray():
    while not STATE.shutdown_requested.is_set():
        try:
            status = check_status()
            if STATE.icon is not None:
                if status["services"] and (status["defender"] or status["defender"] is None):
                    STATE.icon.icon = create_icon("green")
                else:
                    STATE.icon.icon = create_icon("red")
        except Exception:
            if STATE.icon is not None:
                STATE.icon.icon = create_icon("gray")

        STATE.shutdown_requested.wait(10)


def open_panel(_icon_obj=None, _item=None):
    try:
        if STATE.window is not None:
            STATE.window.show()
            apply_native_window_icons()
            add_log("Main window opened from tray")
            return

        if webview.windows:
            webview.windows[0].show()
            apply_native_window_icons()
            add_log("Main window opened from tray")
    except Exception as exc:
        add_log(f"Open from tray failed: {exc}")


def exit_app(icon_obj=None, _item=None):
    STATE.shutdown_requested.set()

    tray_icon = icon_obj or STATE.icon
    if tray_icon is not None:
        try:
            tray_icon.stop()
        except Exception:
            pass

    for item in list(webview.windows):
        try:
            item.destroy()
        except Exception:
            pass

    os._exit(0)


def on_status_closing():
    if STATE.status_window is not None and not STATE.shutdown_requested.is_set():
        try:
            STATE.status_window.hide()
            add_log("Status window hidden")
            return False
        except Exception:
            pass
    return True


def on_closing():
    if STATE.shutdown_requested.is_set():
        return True

    try:
        if STATE.window is not None:
            STATE.window.hide()
        add_log("Main window hidden to system tray")
        return False
    except Exception as exc:
        add_log(f"Hide to tray failed: {exc}")
        return False


def run_tray():
    STATE.icon = pystray.Icon(
        "Watchdog",
        create_icon("gray"),
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem("Open", open_panel),
            pystray.MenuItem("Exit", exit_app),
        ),
    )

    threading.Thread(target=update_tray, daemon=True).start()
    STATE.icon.run()
