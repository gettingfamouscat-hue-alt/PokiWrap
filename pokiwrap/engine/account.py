"""Connect a Poki account so wrapped games can load cloud progress."""

from __future__ import annotations

import json
import subprocess

from pokiwrap.paths import account_cookies_path, account_state_path


def load_account() -> dict:
    path = account_state_path()
    cookies = account_cookies_path()
    if not path.exists():
        return {"connected": False, "username": ""}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"connected": False, "username": ""}
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return {"connected": False, "username": ""}
        connected = bool(data.get("connected"))
        username = str(data.get("username") or "").strip()
    else:
        lines = text.splitlines()
        connected = bool(lines) and lines[0].strip() == "1"
        username = lines[1].strip() if len(lines) > 1 else ""
    if connected and (not cookies.exists() or cookies.stat().st_size == 0):
        connected = False
    return {"connected": connected, "username": username}


def connect_account() -> dict:
    from pokiwrap.engine.exe import ensure_login_exe

    exe = ensure_login_exe()
    subprocess.run([str(exe)], check=False)
    return load_account()


def sign_out_account() -> dict:
    from pokiwrap.engine.exe import ensure_login_exe

    exe = ensure_login_exe()
    completed = subprocess.run([str(exe), "--signout"], check=False)
    if completed.returncode != 0:
        _forget_local_account()
    return load_account()


def _forget_local_account() -> None:
    for path in (account_state_path(), account_cookies_path()):
        try:
            path.unlink()
        except OSError:
            pass
