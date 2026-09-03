"""Connect a Poki account so wrapped games can load cloud progress."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from pokiwrap.paths import account_cookies_path, account_profile_dir, account_state_path

FIND_USER_JS = r"""
(function () {
  var name = "";
  var loggedIn = false;
  function takeName(value) {
    if (!value) return;
    var text = String(value);
    if (text === "TestUser" || text === "null" || text === "undefined") return;
    if (text.length < 2 || text.length > 64) return;
    if (!/^[A-Za-z0-9._\- ]+$/.test(text)) return;
    name = text;
    loggedIn = true;
  }
  function fromText(value) {
    if (!value) return;
    var text = String(value);
    var patterns = [
      /"username"\s*:\s*"([^"]{2,64})"/,
      /"displayName"\s*:\s*"([^"]{2,64})"/,
      /"userName"\s*:\s*"([^"]{2,64})"/,
      /"nickname"\s*:\s*"([^"]{2,64})"/
    ];
    for (var k = 0; k < patterns.length; k++) {
      var match = text.match(patterns[k]);
      if (match) takeName(match[1]);
    }
    if (/"status"\s*:\s*"authenticated"/i.test(text)) loggedIn = true;
    if (/"isLoggedIn"\s*:\s*true/.test(text) || /"loggedIn"\s*:\s*true/.test(text)) loggedIn = true;
  }
  try {
    for (var i = 0; i < localStorage.length; i++) {
      var key = localStorage.key(i) || "";
      fromText(key);
      fromText(localStorage.getItem(key));
      if (/firebase|idToken|refreshToken|user-vault|poki_uid|sb-access|supabase/i.test(key))
        loggedIn = true;
    }
  } catch (e) {}
  try { fromText(document.documentElement.innerHTML); } catch (e) {}
  var nodes = document.querySelectorAll("button, a, [role='button'], [aria-label]");
  for (var n = 0; n < nodes.length; n++) {
    var t = ((nodes[n].textContent || "") + " " + (nodes[n].getAttribute("aria-label") || ""))
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
    if (t === "log out" || t === "sign out" || t === "logout" || t.indexOf("log out") >= 0)
      loggedIn = true;
  }
    if (name) loggedIn = true;
    return JSON.stringify({ username: name, loggedIn: loggedIn });
})();
"""


def _profile_has_files() -> bool:
    profile = account_profile_dir()
    markers = (
        profile / "storage",
        profile / "EBWebView",
        profile / "Default",
    )
    for path in markers:
        try:
            if path.is_dir() and any(path.iterdir()):
                return True
        except OSError:
            continue
    return False


def _has_session() -> bool:
    cookies = account_cookies_path()
    try:
        if cookies.exists() and cookies.stat().st_size > 0:
            return True
    except OSError:
        pass
    return _profile_has_files()


def load_account() -> dict:
    path = account_state_path()
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
    if connected and not _has_session():
        connected = False
    return {"connected": connected, "username": username}


def _refresh_wrappers() -> None:
    try:
        from pokiwrap.engine.generator import rewrite_existing_wrappers

        rewrite_existing_wrappers()
    except Exception:
        return


def connect_account(parent=None) -> dict:
    try:
        from pokiwrap.engine.browser_cookies import export_browser_cookies

        export_browser_cookies()
    except Exception:
        pass
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
        subprocess.run([str(exe), "--signout"], check=False)
    shutil.rmtree(account_profile_dir(), ignore_errors=True)
    try:
        account_profile_dir()
    except OSError:
        pass
    _forget_local_account()
    return load_account()


def _forget_local_account() -> None:
    for path in (account_state_path(), account_cookies_path()):
        try:
            path.unlink()
        except OSError:
            pass
