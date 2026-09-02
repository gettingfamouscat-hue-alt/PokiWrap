"""Connect a Poki account so wrapped games can load cloud progress."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from pokiwrap.paths import account_cookies_path, account_profile_dir, account_state_path


def load_account() -> dict:
    path = account_state_path()
    cookies = account_cookies_path()
    profile = account_profile_dir() / "storage"
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
    has_session = (cookies.exists() and cookies.stat().st_size > 0) or (
        profile.exists() and any(profile.iterdir())
    )
    if connected and not has_session:
        connected = False
    return {"connected": connected, "username": username}


def _refresh_wrappers() -> None:
    try:
        from pokiwrap.engine.generator import rewrite_existing_wrappers

        rewrite_existing_wrappers()
    except Exception:
        return


def connect_account(parent=None) -> dict:
    if sys.platform == "win32":
        from pokiwrap.engine.exe import ensure_login_exe

        exe = ensure_login_exe()
        subprocess.run([str(exe)], check=False)
        _refresh_wrappers()
        return load_account()
    from pokiwrap.engine.account_qt import run_login_dialog

    state = run_login_dialog(parent)
    _refresh_wrappers()
    return state


def sign_out_account() -> dict:
    if sys.platform == "win32":
        from pokiwrap.engine.exe import ensure_login_exe

        exe = ensure_login_exe()
        completed = subprocess.run([str(exe), "--signout"], check=False)
        if completed.returncode != 0:
            _forget_local_account()
        return load_account()
    shutil.rmtree(account_profile_dir(), ignore_errors=True)
    account_profile_dir()
    _forget_local_account()
    return load_account()


def _forget_local_account() -> None:
    for path in (account_state_path(), account_cookies_path()):
        try:
            path.unlink()
        except OSError:
            pass
