"""Qt WebEngine Poki sign-in (macOS, and Windows fallback)."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from PyQt6.QtCore import QDateTime, QTimer, QUrl, Qt
from PyQt6.QtGui import QColor, QDesktopServices, QPalette
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pokiwrap.engine.account import FIND_USER_JS, load_account
from pokiwrap.engine.browser_cookies import (
    chrome_profile_exists,
    export_browser_cookies,
    parse_cookie_file,
    session_hosts,
)
from pokiwrap.paths import account_profile_dir, account_state_path, assets_dir

STEALTH_JS = r"""
(function () {
  try { Object.defineProperty(navigator, "webdriver", { get: function () { return undefined; } }); } catch (e) {}
  try { window.chrome = window.chrome || { runtime: {}, loadTimes: function () {}, csi: function () {} }; } catch (e) {}
})();
"""

GOOGLE_BLOCK_JS = r"""
(function () {
  var text = ((document.body && document.body.innerText) || "") + " " + (document.title || "");
  text = text.toLowerCase();
  return text.indexOf("may not be secure") >= 0 || text.indexOf("couldn't sign you in") >= 0
    || text.indexOf("couldnt sign you in") >= 0;
})();
"""


def qt_chrome_user_agent() -> str:
    raw = QWebEngineProfile.defaultProfile().httpUserAgent()
    cleaned = re.sub(r"\s*QtWebEngine/[^\s]+", "", raw).strip()
    return cleaned or (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )


def _write_account(connected: bool, username: str) -> None:
    path = account_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"connected": connected, "username": username}), encoding="utf-8")


def _inject_browser_cookies(profile: QWebEngineProfile) -> int:
    try:
        export_browser_cookies()
    except Exception:
        pass
    records = parse_cookie_file()
    store = profile.cookieStore()
    count = 0
    same_enum = getattr(QNetworkCookie, "SameSite", None)
    same_none = None
    if same_enum is not None:
        same_none = getattr(same_enum, "None_", None) or getattr(same_enum, "None", None)
    for record in records:
        bare = (record.host or "").lstrip(".")
        domains = [record.host, bare, "." + bare if bare else ""]
        seen: set[str] = set()
        applied = False
        for domain in domains:
            if not domain or domain in seen:
                continue
            seen.add(domain)
            cookie = QNetworkCookie(record.name.encode("utf-8"), record.value.encode("utf-8"))
            cookie.setDomain(domain)
            cookie.setPath(record.path or "/")
            cookie.setSecure(True)
            cookie.setHttpOnly(record.http_only)
            if same_none is not None:
                try:
                    cookie.setSameSitePolicy(same_none)
                except Exception:
                    pass
            if not record.session and record.expires > 0:
                cookie.setExpirationDate(QDateTime.fromSecsSinceEpoch(int(record.expires)))
            for origin in (f"https://{bare}/", f"https://www.{bare}/"):
                try:
                    store.setCookie(cookie, QUrl(origin))
                    applied = True
                except Exception:
                    continue
        if applied:
            count += 1
    return count


def _shared_profile(parent=None) -> QWebEngineProfile:
    storage = account_profile_dir()
    (storage / "storage").mkdir(parents=True, exist_ok=True)
    (storage / "cache").mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile("pokiwrap_account", parent)
    profile.setPersistentStoragePath(str(storage / "storage"))
    profile.setCachePath(str(storage / "cache"))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setHttpUserAgent(qt_chrome_user_agent())
    settings = profile.settings()
    for name in (
        "JavascriptEnabled",
        "LocalStorageEnabled",
        "LocalContentCanAccessRemoteUrls",
        "AllowRunningInsecureContent",
        "JavascriptCanAccessClipboard",
        "PlaybackRequiresUserGesture",
    ):
        attr = getattr(QWebEngineSettings.WebAttribute, name, None)
        if attr is not None:
            settings.setAttribute(attr, name != "PlaybackRequiresUserGesture")
    stealth = QWebEngineScript()
    stealth.setName("pokiwrap-stealth")
    stealth.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    stealth.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    stealth.setRunsOnSubFrames(True)
    stealth.setSourceCode(STEALTH_JS)
    profile.scripts().insert(stealth)
    return profile


class _LoginPage(QWebEnginePage):
    def createWindow(self, _wintype: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        holder = QWebEnginePage(self.profile(), self)

        def follow(url: QUrl) -> None:
            if url.isEmpty() or url.scheme() in {"about", "blob", "javascript"}:
                return
            self.setUrl(url)

        holder.urlChanged.connect(follow)
        return holder

    def javaScriptConsoleMessage(self, level, message, line, source) -> None:
        return


class LoginDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect Poki account")
        self.resize(1100, 760)
        self.setMinimumSize(800, 560)
        self._username = ""
        self._logged_in = False
        self._auto_done = False
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0F1117"))
        self.setPalette(palette)

        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet("background: #161922;")
        self.status = QLabel(
            "Sign in to Poki. If Google blocks this window, open Poki in Chrome, sign in there, then click Import."
        )
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #E8EAED; font-size: 13px;")

        chrome_btn = QPushButton("Open in Chrome")
        chrome_btn.setFixedHeight(36)
        chrome_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chrome_btn.setStyleSheet(
            "background: #1C2030; color: #E8EAED; border: 1px solid #2A3148; border-radius: 8px; font-weight: 700; padding: 0 12px;"
        )
        chrome_btn.clicked.connect(self._open_system_browser)

        import_btn = QPushButton("Import from Chrome")
        import_btn.setFixedHeight(36)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(
            "background: #1C2030; color: #E8EAED; border: 1px solid #2A3148; border-radius: 8px; font-weight: 700; padding: 0 12px;"
        )
        import_btn.clicked.connect(self._import_chrome)

        done = QPushButton("Done")
        done.setFixedSize(110, 36)
        done.setStyleSheet(
            "background: #7C5CFF; color: white; border: 0; border-radius: 8px; font-weight: 700;"
        )
        done.clicked.connect(self._finish)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 8, 16, 8)
        bar_layout.addWidget(self.status, 1)
        if sys.platform == "darwin":
            bar_layout.addWidget(chrome_btn)
            bar_layout.addWidget(import_btn)
        bar_layout.addWidget(done)

        self._profile = _shared_profile(self)
        self.view = QWebEngineView(self)
        page = _LoginPage(self._profile, self.view)
        self.view.setPage(page)
        icon = assets_dir() / "pokiwrap.ico"
        if icon.exists():
            from PyQt6.QtGui import QIcon

            self.setWindowIcon(QIcon(str(icon)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(bar)
        layout.addWidget(self.view, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1200)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self.view.setUrl(QUrl("https://poki.com/en"))

    def _open_system_browser(self) -> None:
        url = "https://poki.com/en"
        opened = False
        if sys.platform == "darwin":
            for app in ("Google Chrome", "Microsoft Edge", "Safari"):
                try:
                    completed = subprocess.run(
                        ["open", "-a", app, url],
                        check=False,
                        capture_output=True,
                    )
                    if completed.returncode == 0:
                        opened = True
                        break
                except OSError:
                    continue
        if not opened:
            QDesktopServices.openUrl(QUrl(url))
        self.status.setText(
            "Chrome opened. Sign in to Poki with Google there, then click Import from Chrome. macOS may ask to allow Keychain access."
        )

    def _import_chrome(self) -> None:
        self.status.setText("Reading Chrome cookies…")
        count = _inject_browser_cookies(self._profile)
        poki_n, google_n = session_hosts()
        QTimer.singleShot(400, lambda: self.view.setUrl(QUrl("https://poki.com/en")))
        if poki_n:
            self._logged_in = True
            if not self._username:
                self._username = "Poki"
            self.status.setText(
                f"Imported {count} cookies ({poki_n} Poki). Reloading Poki to pick up the session…"
            )
            QTimer.singleShot(4000, self._finish_if_imported)
            return
        if count or google_n:
            self.status.setText(
                "Imported Google cookies, but no Poki session yet. Sign in to poki.com in Chrome (not only Google), quit Chrome, then Import again."
            )
            return
        if chrome_profile_exists():
            self.status.setText(
                "Chrome is installed, but cookies could not be read. Quit Chrome completely, click Import again, and allow Keychain access if macOS asks."
            )
            return
        self.status.setText(
            "No Chrome profile found. Open Chrome, sign in to poki.com, then click Import from Chrome."
        )

    def _finish_if_imported(self) -> None:
        if self._logged_in or self._username:
            self._finish()

    def _poll(self) -> None:
        self.view.page().runJavaScript(FIND_USER_JS, self._on_user)
        self.view.page().runJavaScript(GOOGLE_BLOCK_JS, self._on_google_block)

    def _on_google_block(self, blocked: object) -> None:
        if blocked is True or str(blocked).lower() in {"true", "1"}:
            self.status.setText(
                "Google blocked this in-app browser. Click Open in Chrome, sign in to Poki there, then Import from Chrome."
            )

    def _on_user(self, raw: object) -> None:
        if not raw:
            return
        try:
            data = json.loads(str(raw))
        except (TypeError, json.JSONDecodeError):
            return
        if data.get("username"):
            self._username = str(data["username"])
        if data.get("loggedIn"):
            self._logged_in = True
            self.status.setText(
                f"Signed in as {self._username}. Saving…"
                if self._username
                else "Signed in. Saving this account to PokiWrap…"
            )
            if not self._auto_done:
                self._auto_done = True
                QTimer.singleShot(500, self._finish)

    def _finish(self) -> None:
        self._timer.stop()
        connected = self._logged_in or bool(self._username)
        _write_account(connected, self._username)
        self.accept() if connected else self.reject()

    def reject(self) -> None:
        self._timer.stop()
        if self._logged_in or self._username:
            _write_account(True, self._username)
            super().accept()
            return
        _write_account(False, "")
        super().reject()


def run_login_dialog(parent: QWidget | None = None) -> dict:
    dialog = LoginDialog(parent)
    dialog.exec()
    return load_account()
