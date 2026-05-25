import ctypes
import ctypes.wintypes
import os
import sys

from .config import APP_ICON_RELATIVE_PATH, APP_ID, APP_NAME, STATUS_WINDOW_TITLE


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


def app_icon_path():
    return resource_path(APP_ICON_RELATIVE_PATH)


def set_windows_app_id():
    if os.name != "nt":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def apply_native_window_icons(*_args):
    if os.name != "nt":
        return

    icon_file = app_icon_path()
    if not os.path.exists(icon_file):
        return

    try:
        user32 = ctypes.windll.user32

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCLP_HICON = -14
        GCLP_HICONSM = -34

        hicon_big = user32.LoadImageW(None, icon_file, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        hicon_small = user32.LoadImageW(None, icon_file, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if not hicon_big:
            return

        current_pid = os.getpid()
        target_titles = {APP_NAME, STATUS_WINDOW_TITLE}

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_callback(hwnd, _lparam):
            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            if pid.value != current_pid:
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            if title in target_titles or title.startswith(APP_NAME):
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small or hicon_big)

                if hasattr(user32, "SetClassLongPtrW"):
                    user32.SetClassLongPtrW(hwnd, GCLP_HICON, hicon_big)
                    user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon_small or hicon_big)
                else:
                    user32.SetClassLongW(hwnd, GCLP_HICON, hicon_big)
                    user32.SetClassLongW(hwnd, GCLP_HICONSM, hicon_small or hicon_big)

            return True

        user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
    except Exception:
        pass
