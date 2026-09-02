"""Force one game to fill the wrapper window and block other Poki titles."""

from __future__ import annotations

CHROME_HIDE_JS = r"""
(function () {
  var TARGET_SLUG = "__TARGET_SLUG__";

  function frameSrc(frame) {
    return [frame.src, frame.getAttribute("src"), frame.getAttribute("data-src"), frame.getAttribute("data-iframe-src")].join(" ");
  }

  function isAdFrame(iframe) {
    return /ads\.poki|doubleclick|googlesyndication|imasdk|adnxs|prebid|facebook\.com|youtube\.com\/embed/i.test(frameSrc(iframe));
  }

  function isGameFrame(iframe) {
    return /games\.poki\.com|poki-gdn\.com|gdn\.poki\.com|game-cdn\.poki|poki-cdn\.com\/game/i.test(frameSrc(iframe));
  }

  function allIframes(root) {
    var out = [];
    if (!root) return out;
    var list = root.querySelectorAll ? root.querySelectorAll("iframe") : [];
    for (var i = 0; i < list.length; i++) out.push(list[i]);
    var nodes = root.querySelectorAll ? root.querySelectorAll("*") : [];
    for (var j = 0; j < nodes.length; j++) {
      if (nodes[j].shadowRoot) out = out.concat(allIframes(nodes[j].shadowRoot));
    }
    return out;
  }

  function pickGame() {
    var frames = allIframes(document);
    var i;
    for (i = 0; i < frames.length; i++) {
      if (isGameFrame(frames[i]) && !isAdFrame(frames[i])) return frames[i];
    }
    var named = document.querySelector(
      "[class*='GamePlayer'] iframe, [class*='game-player'] iframe, [class*='GameFrame'] iframe, [id*='game-container'] iframe, [data-testid*='game'] iframe"
    );
    if (named && !isAdFrame(named)) return named;
    var best = null;
    var bestArea = 0;
    for (i = 0; i < frames.length; i++) {
      if (isAdFrame(frames[i])) continue;
      var area = Math.max(frames[i].clientWidth, 0) * Math.max(frames[i].clientHeight, 0);
      if (area > bestArea) {
        bestArea = area;
        best = frames[i];
      }
    }
    if (best && bestArea >= 20000) return best;
    return null;
  }

  function ensureStyle() {
    var style = document.getElementById("pokiwrap-chrome-hide");
    if (!style) {
      style = document.createElement("style");
      style.id = "pokiwrap-chrome-hide";
      (document.head || document.documentElement).appendChild(style);
    }
    style.textContent = [
      "html,body{margin:0!important;padding:0!important;overflow:hidden!important;width:100%!important;height:100%!important;background:#000!important;}",
      "iframe.pokiwrap-game{position:fixed!important;inset:0!important;left:0!important;top:0!important;width:100vw!important;height:100vh!important;min-width:100vw!important;min-height:100vh!important;max-width:none!important;max-height:none!important;border:0!important;margin:0!important;padding:0!important;z-index:2147483647!important;background:#000!important;display:block!important;visibility:visible!important;opacity:1!important;transform:none!important;clip:auto!important;clip-path:none!important;}",
      "iframe[src*='doubleclick'],iframe[src*='googlesyndication'],iframe[src*='ads.poki'],iframe[src*='imasdk'],iframe[src*='amazon-adsystem'],ins.adsbygoogle,[id*='google_ads'],[class*='Advertisement'],[class*='ad-slot'],[class*='AdSlot']{display:none!important;visibility:hidden!important;pointer-events:none!important;width:0!important;height:0!important;}"
    ].join("");
  }

  function hideSiblings(game) {
    var node = game;
    while (node && node.parentElement) {
      var parent = node.parentElement;
      for (var i = 0; i < parent.children.length; i++) {
        var sibling = parent.children[i];
        if (sibling !== node && sibling.id !== "pokiwrap-chrome-hide") {
          sibling.style.setProperty("display", "none", "important");
          sibling.style.setProperty("visibility", "hidden", "important");
          sibling.style.setProperty("pointer-events", "none", "important");
        }
      }
      parent.style.setProperty("position", "fixed", "important");
      parent.style.setProperty("inset", "0", "important");
      parent.style.setProperty("width", "100%", "important");
      parent.style.setProperty("height", "100%", "important");
      parent.style.setProperty("max-width", "none", "important");
      parent.style.setProperty("max-height", "none", "important");
      parent.style.setProperty("overflow", "hidden", "important");
      parent.style.setProperty("transform", "none", "important");
      parent.style.setProperty("margin", "0", "important");
      parent.style.setProperty("padding", "0", "important");
      parent.style.setProperty("background", "#000", "important");
      if (parent === document.body || parent === document.documentElement) break;
      node = parent;
    }
  }

  function fill(el) {
    if (!el) return false;
    el.classList.add("pokiwrap-game");
    el.setAttribute("allowfullscreen", "true");
    el.setAttribute("allow", "autoplay; fullscreen; gamepad; clipboard-read; clipboard-write");
    hideSiblings(el);
    var props = {
      position: "fixed",
      left: "0",
      top: "0",
      right: "0",
      bottom: "0",
      width: "100vw",
      height: "100vh",
      "min-width": "100vw",
      "min-height": "100vh",
      "max-width": "none",
      "max-height": "none",
      border: "none",
      margin: "0",
      padding: "0",
      "z-index": "2147483647",
      background: "#000",
      display: "block",
      visibility: "visible",
      opacity: "1",
      transform: "none"
    };
    for (var key in props) {
      if (props.hasOwnProperty(key)) el.style.setProperty(key, props[key], "important");
    }
    return true;
  }

  function clickAccept() {
    var ot = document.getElementById("onetrust-accept-btn-handler");
    if (ot) ot.click();
  }

  function tick() {
    try {
      ensureStyle();
      clickAccept();
      var game = pickGame();
      if (!fill(game)) return;
      if (!window.__pokiwrapReady) {
        window.__pokiwrapReady = true;
        try { window.chrome.webview.postMessage("ready"); } catch (err) {}
      }
    } catch (err) {}
  }

  tick();
  if (!window.__pokiwrapChrome) {
    window.__pokiwrapChrome = true;
    document.addEventListener("click", function (event) {
      var link = event.target && event.target.closest ? event.target.closest("a") : null;
      if (!link) return;
      var href = link.href || "";
      var match = href.match(/poki\.com\/[^/]+\/g\/([^/?#]+)/i);
      if (match && TARGET_SLUG && match[1].toLowerCase() !== TARGET_SLUG.toLowerCase()) {
        event.preventDefault();
        event.stopPropagation();
      }
    }, true);
    setInterval(tick, 400);
    try {
      new MutationObserver(tick).observe(document.documentElement, { childList: true, subtree: true });
    } catch (err) {}
  }
})();
"""

WRAPPER_TEMPLATE = r'''#!/usr/bin/env python3
"""PokiWrap generated desktop wrapper — __APP_NAME_TEXT__."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --disable-features=AudioServiceOutOfProcess",
)

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

GAME_URL = __GAME_URL__
APP_NAME = __APP_NAME__
TARGET_SLUG = __TARGET_SLUG__
PROFILE_NAME = __PROFILE_NAME__
CHROME_HIDE_JS = __CHROME_HIDE_JS__


def chrome_user_agent() -> str:
    if sys.platform == "darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
    if sys.platform == "win32":
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )


def apply_browser_settings(settings: QWebEngineSettings) -> None:
    enabled = {
        "JavascriptEnabled": True,
        "LocalStorageEnabled": True,
        "PluginsEnabled": True,
        "WebGLEnabled": True,
        "Accelerated2dCanvasEnabled": True,
        "AutoLoadImages": True,
        "FullScreenSupportEnabled": True,
        "JavascriptCanAccessClipboard": True,
        "AllowRunningInsecureContent": True,
        "FocusOnNavigationEnabled": True,
        "PlaybackRequiresUserGesture": False,
        "WebRTCPublicInterfacesOnly": False,
    }
    for name, value in enabled.items():
        attr = getattr(QWebEngineSettings.WebAttribute, name, None)
        if attr is not None:
            settings.setAttribute(attr, value)


class GamePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source) -> None:
        return

    def acceptNavigationRequest(self, url, nav_type, is_main_frame) -> bool:
        if not is_main_frame:
            return True
        host = (url.host() or "").lower()
        path = url.path() or ""
        if "poki.com" in host and TARGET_SLUG and "/g/" in path:
            slug = path.rstrip("/").split("/")[-1].lower()
            if slug != TARGET_SLUG.lower():
                return False
        return True


class GameWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setMinimumSize(800, 500)

        root = Path(__file__).resolve().parent
        icon_png = root / "icon.png"
        if icon_png.exists():
            self.setWindowIcon(QIcon(str(icon_png)))

        storage = root / "profile"
        storage.mkdir(parents=True, exist_ok=True)

        self._profile = QWebEngineProfile(PROFILE_NAME, self)
        self._profile.setPersistentStoragePath(str(storage / "storage"))
        self._profile.setCachePath(str(storage / "cache"))
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self._profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self._profile.setHttpUserAgent(chrome_user_agent())
        apply_browser_settings(self._profile.settings())

        hide = QWebEngineScript()
        hide.setName("pokiwrap-hide-chrome")
        hide.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        hide.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        hide.setRunsOnSubFrames(False)
        hide.setSourceCode(CHROME_HIDE_JS)
        self._profile.scripts().insert(hide)

        self.view = QWebEngineView(self)
        page = GamePage(self._profile, self.view)
        self.view.setPage(page)
        page.fullScreenRequested.connect(self._on_fullscreen)
        page.loadFinished.connect(self._on_loaded)
        self.view.setUrl(QUrl(GAME_URL))
        self.setCentralWidget(self.view)
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(geo.center())
        self.move(frame.topLeft())

    def _on_loaded(self, ok: bool) -> None:
        if ok:
            self.view.page().runJavaScript(CHROME_HIDE_JS)

    def _on_fullscreen(self, request) -> None:
        request.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


def main() -> None:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    root = Path(__file__).resolve().parent
    icon_png = root / "icon.png"
    if icon_png.exists():
        app.setWindowIcon(QIcon(str(icon_png)))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0F1117"))
    app.setPalette(palette)
    window = GameWindow()
    window.showNormal()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
'''
