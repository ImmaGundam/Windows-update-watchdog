import winreg


def open_or_create_hklm_key(path, access):
    return winreg.CreateKeyEx(
        winreg.HKEY_LOCAL_MACHINE,
        path,
        0,
        access | winreg.KEY_WOW64_64KEY,
    )


def set_dword_hklm(path, name, value):
    try:
        with open_or_create_hklm_key(path, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))
        return {"ok": True, "path": path, "name": name, "value": value}
    except Exception as exc:
        return {"ok": False, "path": path, "name": name, "error": str(exc)}


def set_string_hklm(path, name, value):
    try:
        with open_or_create_hklm_key(path, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
        return {"ok": True, "path": path, "name": name, "value": value}
    except Exception as exc:
        return {"ok": False, "path": path, "name": name, "error": str(exc)}


def read_value_hklm(path, name):
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            path,
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, value_type = winreg.QueryValueEx(key, name)
        return {"exists": True, "value": value, "type": value_type}
    except FileNotFoundError:
        return {"exists": False, "value": None, "type": None}
    except Exception as exc:
        return {"exists": False, "value": None, "type": None, "error": str(exc)}


def delete_value_hklm(path, name):
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
        ) as key:
            winreg.DeleteValue(key, name)
        return {"ok": True, "path": path, "name": name, "removed": True}
    except FileNotFoundError:
        return {"ok": True, "path": path, "name": name, "removed": False, "reason": "not found"}
    except Exception as exc:
        return {"ok": False, "path": path, "name": name, "error": str(exc)}
