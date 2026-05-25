import ctypes
import os
import subprocess
import sys

from .logging_store import add_log
from .state import STATE


def is_admin():
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    if getattr(sys, "frozen", False):
        file_to_run = sys.executable
        params = ""
    else:
        file_to_run = sys.executable
        params = subprocess.list2cmdline(sys.argv)

    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        file_to_run,
        params,
        None,
        1,
    )


def require_admin():
    if is_admin():
        return True

    add_log("Administrator elevation requested")

    result = ctypes.windll.user32.MessageBoxW(
        0,
        "This action requires Administrator privileges.\n\nClick YES to restart as Administrator.",
        "Administrator Required",
        0x04 | 0x20,
    )

    if result == 6:
        if STATE.icon is not None:
            try:
                STATE.icon.stop()
            except Exception:
                pass
        elevate()
        os._exit(0)

    add_log("Administrator elevation declined")
    return False
