"""Qt WebEngine Poki sign-in (macOS, and Windows fallback)."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pokiwrap.engine.account import load_account
from pokiwrap.paths import account_profile_dir, account_state_path, assets_dir

FIND_USER_JS = r"""
(function () {
  var name = "";
  function fromText(value) {
    if (!value) return;
    var text = String(value);
    var match = text.match(/"username"\s*:\s*"([^"]{2,64})"/);
    if (match && match[1] && match[1] !== "TestUser") name = match[1];
    match = text.match(/"displayName"\s*:\s*"([^"]{2,64})"/);
    if (match && match[1]) name = match[1];
  }
  try {
    for (var i = 0; i < localStorage.length; i++) fromText(localStorage.getItem(localStorage.key(i)));
  } catch (e) {}
  try { fromText(document.documentElement.innerHTML); } catch (e) {}
  var loggedIn = !!name;
  var nodes = document.querySelectorAll("button, a, [role='button']");
  for (var i = 0; i < nodes.length; i++) {
    var t = (nodes[i].textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (t === "log out" || t === "sign out" || t === "logout") loggedIn = true;
  }
  return JSON.stringify({ username: name, loggedIn: loggedIn });
})();
"""


def _write_account(connected: bool, username: str) -> None:
    path = account_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"connected": connected, "username": username}), encoding="utf-8")


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
    profile.setHttpUserAgent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
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
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0F1117"))
        self.setPalette(palette)

        bar = QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet("background: #161922;")
        self.status = QLabel(
            "Sign in to Poki with Google, Apple, Microsoft, or a passkey, then click Done."
        )
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #E8EAED; font-size: 14px;")
        done = QPushButton("Done")
        done.setFixedSize(110, 36)
        done.setStyleSheet(
            "background: #7C5CFF; color: white; border: 0; border-radius: 8px; font-weight: 700;"
        )
        done.clicked.connect(self._finish)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 8, 16, 8)
        bar_layout.addWidget(self.status, 1)
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

    def _poll(self) -> None:
        self.view.page().runJavaScript(FIND_USER_JS, self._on_user)

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
                f"Signed in as {self._username}. Click Done to save."
                if self._username
                else "Signed in. Click Done to save this account to PokiWrap."
            )

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
