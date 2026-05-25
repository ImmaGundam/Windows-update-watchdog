import os
import subprocess


CREATE_NO_WINDOW = 0x08000000


def subprocess_kwargs(timeout=15):
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if os.name == "nt":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def run_cmd(args, timeout=15):
    try:
        result = subprocess.run(args, **subprocess_kwargs(timeout=timeout))
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "cmd": " ".join(args),
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": str(exc),
            "cmd": " ".join(args),
        }


def run_powershell(script, timeout=25):
    return run_cmd(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout=timeout,
    )
