"""Force one game to fill the wrapper window and block other Poki titles."""

from __future__ import annotations

CHROME_HIDE_JS = r"""
(function () {
  try { if (window.top !== window.self) return; } catch (err) { return; }
  var TARGET_SLUG = "__TARGET_SLUG__";

  function frameSrc(frame) {
    return [frame.src, frame.getAttribute("src"), frame.getAttribute("data-src"), frame.getAttribute("data-iframe-src")].join(" ");
  }

    function isAuthFrame(iframe) {
      return /accounts\.google|appleid\.apple|login\.live|login\.microsoftonline|firebaseapp|identitytoolkit|securetoken|user-vault|poki\.io/i.test(frameSrc(iframe));
    }

    function isAdFrame(iframe) {
      return /ads\.poki|\/ads\/|housead|doubleclick|googlesyndication|imasdk|adnxs|prebid|amazon-adsystem|ay\.delivery|onetag-sys|youtube\.com\/embed/i.test(frameSrc(iframe));
    }

    function isGameFrame(iframe) {
    return /games\.poki\.com|poki-gdn\.com|gdn\.poki\.com|game-cdn\.poki|poki-cdn\.com\/game|games\.crazygames\.com|game-files\.crazygames\.com|files\.crazygames\.com|crazygames\.com\/embed/i.test(frameSrc(iframe));
  }

  function isProbeFrame(iframe) {
    if (!iframe) return true;
    if (iframe.srcdoc && String(iframe.srcdoc).length < 32) return true;
    var src = frameSrc(iframe);
    if (/srcdoc/i.test(src) && !isGameFrame(iframe)) return true;
    var w = Math.max(iframe.clientWidth || 0, iframe.offsetWidth || 0);
    var h = Math.max(iframe.clientHeight || 0, iframe.offsetHeight || 0);
    if (w * h > 0 && w * h < 10000) return true;
    return false;
  }

  function ancestorText(iframe) {
    var text = "";
    var el = iframe;
    for (var i = 0; i < 10 && el; i++) {
      var cls = "";
      try {
        cls = el.className && el.className.baseVal != null ? el.className.baseVal : String(el.className || "");
      } catch (err) {}
      text += " " + cls + " " + (el.id || "");
      try { text += " " + (el.getAttribute("data-testid") || ""); } catch (err2) {}
      el = el.parentElement;
    }
    return text;
  }

  function isPlayerShell(iframe) {
    if (!iframe || isAdFrame(iframe) || isWrongGame(iframe) || isAuthFrame(iframe)) return false;
    if ((iframe.id || "") === "game-element") return true;
    return /GamePlayer|game-player|game-element|GameFrame|game-container|GameIframe|game-iframe|gameFrame/i.test(ancestorText(iframe));
  }

  function looksLikePlayer(iframe) {
    if (!iframe || isAdFrame(iframe) || isWrongGame(iframe) || isAuthFrame(iframe)) return false;
    if (isGameFrame(iframe) || isPlayerShell(iframe)) return true;
    if (isProbeFrame(iframe)) return false;
    var allow = (iframe.getAttribute("allow") || "") + (iframe.allowFullscreen ? " fullscreen" : "");
    var area = Math.max(iframe.clientWidth || 0, 0) * Math.max(iframe.clientHeight || 0, 0);
    return /fullscreen/i.test(allow) && area >= 40000;
  }

  function isHelperFrame(iframe) {
    if (isAdFrame(iframe) || isWrongGame(iframe)) return false;
    if (isAuthFrame(iframe) || isGameFrame(iframe)) return true;
    var src = frameSrc(iframe).trim();
    if (!src || /about:blank|javascript:/i.test(src)) return false;
    if (/\/ads\/|housead|\/vast/i.test(src)) return false;
    return /poki\.com|poki\.io|poki-cdn|poki-gdn|poki-user-content|crazygames\.com|googleapis|gstatic|google|apple|microsoft|live\.com/i.test(src);
  }

  function isWrongGame(iframe) {
    var src = frameSrc(iframe);
    var match = src.match(/poki\.com\/[^/]+\/g\/([^/?#]+)/i);
    if (match && TARGET_SLUG && match[1].toLowerCase() !== TARGET_SLUG.toLowerCase()) return true;
    match = src.match(/crazygames\.[^/]+\/(?:[a-z]{2}\/)?game\/([^/?#]+)/i);
    if (match && TARGET_SLUG && match[1].toLowerCase() !== TARGET_SLUG.toLowerCase()) return true;
    return false;
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
    var byId = document.getElementById("game-element");
    if (byId && (byId.tagName || "").toUpperCase() === "IFRAME" && !isAdFrame(byId) && !isWrongGame(byId)) return byId;
    var box = document.getElementById("game-player") || document.getElementById("game-container");
    if (box && box.querySelector) {
      var inner = box.querySelector("iframe");
      if (inner && !isAdFrame(inner) && !isWrongGame(inner)) return inner;
    }
    var frames = allIframes(document);
    var i;
    for (i = 0; i < frames.length; i++) {
      if (isWrongGame(frames[i]) || isAdFrame(frames[i]) || isProbeFrame(frames[i])) continue;
      if (isGameFrame(frames[i])) return frames[i];
    }
    for (i = 0; i < frames.length; i++) {
      if (isPlayerShell(frames[i])) return frames[i];
    }
    var named = document.querySelector(
      "#game-element, #game-player iframe, #game-container iframe, [class*='GamePlayer'] iframe, [class*='game-player'] iframe, [class*='GameFrame'] iframe, [id*='game-container'] iframe, [data-testid*='game'] iframe, #game-iframe, iframe#game, [class*='GameIframe'] iframe"
    );
    if (named && looksLikePlayer(named)) return named;
    var best = null;
    var bestArea = 0;
    for (i = 0; i < frames.length; i++) {
      if (!looksLikePlayer(frames[i])) continue;
      var area = Math.max(frames[i].clientWidth, 0) * Math.max(frames[i].clientHeight, 0);
      if (area > bestArea) {
        bestArea = area;
        best = frames[i];
      }
    }
    return best;
  }

  function pickPlayerBox() {
    return (
      document.getElementById("game-player") ||
      document.getElementById("game-container") ||
      document.querySelector("[class*='GamePlayer'], [class*='game-player'], [class*='gamePlayer'], [id*='game-container'], [class*='GameFrame']")
    );
  }

  function unfillOthers(game) {
    var frames = allIframes(document);
    for (var i = 0; i < frames.length; i++) {
      if (frames[i] === game) continue;
      frames[i].classList.remove("pokiwrap-game");
    }
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
      "header,nav,footer,[role='banner'],[role='navigation'],[class*='PageHeader'],[class*='page-header'],[class*='NavBar'],[class*='Navbar'],[class*='TopBar'],[class*='top-bar'],[class*='GamesBar'],[class*='GameBar']:not([class*='GamePlayer']):not([class*='gamePlayer']),[class*='BottomBar'],[class*='Sidebar'],[class*='RightRail'],[class*='Advertisement']{display:none!important;visibility:hidden!important;pointer-events:none!important;}",
      "#game-container,#game-player,#game-element,iframe#game-element,.pokiwrap-game-box{position:fixed!important;inset:0!important;left:0!important;top:0!important;width:100vw!important;height:100vh!important;min-width:100%!important;min-height:100%!important;max-width:none!important;max-height:none!important;margin:0!important;padding:0!important;border:0!important;z-index:2147483646!important;background:transparent!important;display:block!important;visibility:visible!important;overflow:hidden!important;}",
      "iframe.pokiwrap-game,iframe#game-element{position:fixed!important;inset:0!important;left:0!important;top:0!important;width:100vw!important;height:100vh!important;min-width:100vw!important;min-height:100vh!important;max-width:none!important;max-height:none!important;border:0!important;margin:0!important;padding:0!important;z-index:2147483647!important;background:transparent!important;display:block!important;visibility:visible!important;opacity:1!important;transform:none!important;clip:auto!important;clip-path:none!important;}",
      "iframe[srcdoc],iframe[src*='doubleclick'],iframe[src*='googlesyndication'],iframe[src*='ads.poki'],iframe[src*='/ads/'],iframe[src*='housead'],iframe[src*='imasdk'],iframe[src*='amazon-adsystem'],ins.adsbygoogle,[id*='google_ads'],[class*='ad-slot'],[class*='AdSlot'],[class*='HouseAd'],[class*='CommercialBreak']{display:none!important;visibility:hidden!important;pointer-events:none!important;width:0!important;height:0!important;}"
    ].join("");
  }

  function hideSiblings(game) {
    var node = game;
    while (node && node.parentElement) {
      var parent = node.parentElement;
      for (var i = 0; i < parent.children.length; i++) {
        var sibling = parent.children[i];
        if (sibling !== node && sibling.id !== "pokiwrap-chrome-hide") {
          var tag = (sibling.tagName || "").toUpperCase();
          if (tag === "SCRIPT" || tag === "STYLE" || tag === "LINK" || tag === "META" || tag === "NOSCRIPT") continue;
          if (tag === "IFRAME" && isHelperFrame(sibling)) continue;
          if (sibling.querySelectorAll) {
            var nested = sibling.querySelectorAll("iframe");
            var keep = false;
            for (var f = 0; f < nested.length; f++) {
              if (isHelperFrame(nested[f])) { keep = true; break; }
            }
            if (keep) continue;
          }
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

    function fillBox(box) {
    if (!box) return;
    box.classList.add("pokiwrap-game-box");
    var props = {
      position: "fixed",
      left: "0",
      top: "0",
      right: "0",
      bottom: "0",
      width: "100vw",
      height: "100vh",
      "max-width": "none",
      "max-height": "none",
      margin: "0",
      padding: "0",
      overflow: "hidden",
      "z-index": "2147483646",
      background: "transparent"
    };
    for (var key in props) {
      if (props.hasOwnProperty(key)) box.style.setProperty(key, props[key], "important");
    }
  }

    function fill(el) {
    if (!el) return false;
    if (!looksLikePlayer(el) && (el.id || "") !== "game-element") return false;
    unfillOthers(el);
    el.classList.add("pokiwrap-game");
    el.setAttribute("name", "gameFrame");
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
      background: "transparent",
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

  function hidePromo() {
    var nodes = document.querySelectorAll("a, button, [role='button']");
    for (var i = 0; i < nodes.length; i++) {
      var t = (nodes[i].textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
      if (t.indexOf("play it on poki") >= 0 || t === "play on poki") {
        var wrap = nodes[i].closest("[class*='Ad'], [class*='Overlay'], [class*='Modal'], [class*='Splash'], [class*='Promo']") || nodes[i];
        wrap.style.setProperty("display", "none", "important");
        wrap.style.setProperty("visibility", "hidden", "important");
        wrap.style.setProperty("pointer-events", "none", "important");
      }
    }
  }

  function clickContinue() {
    if (window.__pokiwrapTapped) return;
    var btn = document.querySelector("#game-player button, [class*='tapForFullscreen'], [class*='tap-to']");
    if (!btn) return;
    var t = (btn.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (t.indexOf("tap") >= 0 || t.indexOf("continue") >= 0 || t.indexOf("fullscreen") >= 0 || t === "") {
      window.__pokiwrapTapped = true;
      try { btn.click(); } catch (err) {}
    }
  }

  function tick() {
    try {
      ensureStyle();
      clickAccept();
      hidePromo();
      clickContinue();
      fillBox(pickPlayerBox());
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
      match = href.match(/crazygames\.[^/]+\/(?:[a-z]{2}\/)?game\/([^/?#]+)/i);
      if (match && TARGET_SLUG && match[1].toLowerCase() !== TARGET_SLUG.toLowerCase()) {
        event.preventDefault();
        event.stopPropagation();
      }
      var label = (link.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
      if (label.indexOf("play it on poki") >= 0) {
        event.preventDefault();
        event.stopPropagation();
      }
    }, true);
    setInterval(tick, 400);
    var n = 0;
    var fast = setInterval(function () {
      tick();
      if (++n > 50) clearInterval(fast);
    }, 80);
    try {
      new MutationObserver(tick).observe(document.documentElement, { childList: true, subtree: true });
    } catch (err) {}
  }
})();
"""

AD_SKIP_JS = r"""
(function () {
  function stubSdk() {
    var sdk = window.PokiSDK;
    if (!sdk) return;
    sdk.commercialBreak = function (cb) {
      try { if (typeof cb === "function") cb(); } catch (e) {}
      return Promise.resolve();
    };
    sdk.rewardedBreak = function () { return Promise.resolve(false); };
    sdk.displayAd = function () {};
    sdk.destroyAd = function () {};
    sdk.isAdBlocked = function () { return true; };
  }
  function stubCrazy() {
    try {
      window.CrazyGames = window.CrazyGames || {};
      window.CrazyGames.SDK = window.CrazyGames.SDK || {};
      var ad = window.CrazyGames.SDK.ad || {};
      ad.requestAd = function (type, callbacks) {
        try { if (callbacks && typeof callbacks.adFinished === "function") callbacks.adFinished(); } catch (e) {}
      };
      ad.happytime = function () {};
      ad.hasAdblock = function (cb) { try { if (typeof cb === "function") cb(true); } catch (e) {} };
      window.CrazyGames.SDK.ad = ad;
    } catch (e) {}
  }
  function hidePromo() {
    var nodes = document.querySelectorAll("a, button, [role='button']");
    for (var i = 0; i < nodes.length; i++) {
      var t = (nodes[i].textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
      if (t.indexOf("play it on poki") >= 0 || t === "play on poki") {
        var wrap = nodes[i].closest("div") || nodes[i];
        wrap.style.setProperty("display", "none", "important");
        wrap.style.setProperty("pointer-events", "none", "important");
      }
    }
  }
  function tick() {
    try { stubSdk(); stubCrazy(); hidePromo(); } catch (e) {}
  }
  document.addEventListener("click", function (event) {
    var t = ((event.target && event.target.textContent) || "").toLowerCase();
    if (t.indexOf("play it on poki") >= 0) {
      event.preventDefault();
      event.stopPropagation();
    }
  }, true);
  tick();
  setInterval(tick, 400);
})();
"""

FS_KEY_JS = r"""
(function () {
  if (window.__pokiwrapFsKeys) return;
  window.__pokiwrapFsKeys = true;
  window.addEventListener("keydown", function (event) {
    if (event.key !== "F11" && event.key !== "Escape") return;
    if (event.key === "F11") {
      event.preventDefault();
      event.stopPropagation();
    }
    try {
      if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
        window.chrome.webview.postMessage(event.key === "F11" ? "f11" : "esc");
      }
    } catch (err) {}
  }, true);
})();
"""

WRAPPER_TEMPLATE = r'''#!/usr/bin/env python3
"""PokiWrap generated desktop wrapper — __APP_NAME_TEXT__."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --disable-features=AudioServiceOutOfProcess "
    "--ignore-gpu-blocklist --enable-webgl",
)

from PyQt6.QtCore import QEvent, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

GAME_URL = __GAME_URL__
APP_NAME = __APP_NAME__
TARGET_SLUG = __TARGET_SLUG__
PROFILE_NAME = __PROFILE_NAME__
CHROME_HIDE_JS = __CHROME_HIDE_JS__
AD_SKIP_JS = __AD_SKIP_JS__
FS_KEY_JS = __FS_KEY_JS__


def _shared_pokiwrap_profile() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "PokiWrap"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "PokiWrap"
    else:
        base = Path.home() / ".local" / "share" / "PokiWrap"
    path = base / "account_webview"
    (path / "storage").mkdir(parents=True, exist_ok=True)
    (path / "cache").mkdir(parents=True, exist_ok=True)
    return path


def _pokiwrap_data_dir() -> Path:
    return _shared_pokiwrap_profile().parent


def _adblock_enabled() -> bool:
    path = _pokiwrap_data_dir() / "settings.json"
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return data.get("adblock", True) is not False


def _host_is(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _allowed_host(host: str) -> bool:
    if _host_is(host, "ads.poki.com"):
        return False
    if _host_is(host, "ads.crazygames.com"):
        return False
    if any(
        _host_is(host, domain)
        for domain in (
            "poki.com",
            "poki.io",
            "poki-cdn.com",
            "poki-gdn.com",
            "poki-user-content.com",
            "crazygames.com",
            "gstatic.com",
            "googleapis.com",
        )
    ):
        return True
    if "firebase" in host:
        return True
    return host in {
        "identitytoolkit.googleapis.com",
        "securetoken.googleapis.com",
        "accounts.google.com",
        "appleid.apple.com",
        "login.microsoftonline.com",
        "login.live.com",
    }


def _is_ad_request(url: QUrl, blocked: set[str]) -> bool:
    host = (url.host() or "").lower()
    path = (url.path() or "").lower()
    text = url.toString().lower()
    if _host_is(host, "ads.poki.com") or _host_is(host, "ads.crazygames.com") or _host_is(host, "ay.delivery") or _host_is(host, "onetag-sys.com"):
        return True
    if "/ads/" in path or "housead" in path or "housead" in text:
        return True
    if "/vast" in path or path.endswith(".vast") or "ima3.js" in path or "prebid" in path:
        return True
    if _allowed_host(host):
        return False
    current = host
    while current:
        if current in blocked:
            return True
        if "." not in current:
            break
        current = current.split(".", 1)[1]
    return False


class AdInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hosts: set[str] = {
            "ads.poki.com",
            "doubleclick.net",
            "googlesyndication.com",
            "googleadservices.com",
            "googletagmanager.com",
            "google-analytics.com",
            "imasdk.googleapis.com",
            "amazon-adsystem.com",
            "adnxs.com",
            "ay.delivery",
            "onetag-sys.com",
        }
        path = _pokiwrap_data_dir() / "adblock_domains.txt"
        try:
            if path.exists():
                self._hosts.update(
                    line.strip().lower()
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")
                )
        except OSError:
            pass

    def interceptRequest(self, info) -> None:
        try:
            url = info.requestUrl()
            host = (url.host() or "").lower()
            if any(
                _host_is(host, domain)
                for domain in (
                    "games.poki.com",
                    "poki-gdn.com",
                    "gdn.poki.com",
                    "game-cdn.poki.com",
                    "games.crazygames.com",
                    "game-files.crazygames.com",
                    "files.crazygames.com",
                )
            ):
                referer = b"https://www.crazygames.com/" if "crazygames" in host else b"https://poki.com/"
                info.setHttpHeader(b"Referer", referer)
        except Exception:
            pass
        if not _adblock_enabled():
            return
        try:
            if _is_ad_request(info.requestUrl(), self._hosts):
                info.block(True)
        except Exception:
            return


def chrome_user_agent() -> str:
    try:
        raw = QWebEngineProfile.defaultProfile().httpUserAgent()
        cleaned = re.sub(r"\s*QtWebEngine/[^\s]+", "", raw).strip()
        if "Chrome/" in cleaned:
            return cleaned
    except Exception:
        pass
    if sys.platform == "darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
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

    def createWindow(self, _wintype):
        holder = QWebEnginePage(self.profile(), self)

        def follow(url: QUrl) -> None:
            if url.isEmpty() or url.scheme() in {"about", "blob", "javascript"}:
                return
            text = url.toString().lower()
            if any(token in text for token in ("doubleclick", "googlesyndication", "imasdk", "amazon-adsystem", "/ads/", "housead", "ads.poki")):
                return
            host = (url.host() or "").lower()
            path = url.path() or ""
            if "poki.com" in host and TARGET_SLUG and "/g/" in path:
                slug = path.rstrip("/").split("/")[-1].lower()
                if slug != TARGET_SLUG.lower():
                    return
            if "crazygames" in host and TARGET_SLUG and "/game/" in path.lower():
                slug = path.rstrip("/").split("/")[-1].lower()
                if slug != TARGET_SLUG.lower():
                    return
            if any(token in text for token in ("accounts.google", "appleid.apple", "login.live", "login.microsoftonline", "firebaseapp")):
                self.setUrl(url)
                return
            if "poki.com" in host or "poki-gdn.com" in host or "poki-cdn.com" in host or "crazygames.com" in host:
                return
            self.setUrl(url)

        holder.urlChanged.connect(follow)
        return holder

    def acceptNavigationRequest(self, url, nav_type, is_main_frame) -> bool:
        text = url.toString().lower()
        if "/ads/" in text or "housead" in text or "ads.poki" in text:
            return False
        if not is_main_frame:
            if TARGET_SLUG and "poki.com" in (url.host() or "").lower() and "/g/" in (url.path() or ""):
                slug = url.path().rstrip("/").split("/")[-1].lower()
                if slug != TARGET_SLUG.lower():
                    return False
            if TARGET_SLUG and "crazygames" in (url.host() or "").lower() and "/game/" in (url.path() or "").lower():
                slug = url.path().rstrip("/").split("/")[-1].lower()
                if slug != TARGET_SLUG.lower():
                    return False
            return True
        host = (url.host() or "").lower()
        path = url.path() or ""
        if "poki.com" in host and TARGET_SLUG and "/g/" in path:
            slug = path.rstrip("/").split("/")[-1].lower()
            if slug != TARGET_SLUG.lower():
                return False
        if "crazygames" in host and TARGET_SLUG and "/game/" in path.lower():
            slug = path.rstrip("/").split("/")[-1].lower()
            if slug != TARGET_SLUG.lower():
                return False
        return True


class GameView(QWebEngineView):
    def event(self, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            key = event.key()
            if key in (Qt.Key.Key_F11, Qt.Key.Key_Escape):
                event.ignore()
                return False
        return super().event(event)


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

        storage = _shared_pokiwrap_profile()
        storage.mkdir(parents=True, exist_ok=True)

        self._profile = QWebEngineProfile("pokiwrap_account", self)
        self._profile.setPersistentStoragePath(str(storage / "storage"))
        self._profile.setCachePath(str(storage / "cache"))
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self._profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self._profile.setHttpUserAgent(chrome_user_agent())
        apply_browser_settings(self._profile.settings())
        self._blocker = AdInterceptor(self)
        self._profile.setUrlRequestInterceptor(self._blocker)

        hide = QWebEngineScript()
        hide.setName("pokiwrap-hide-chrome")
        hide.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        hide.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        hide.setRunsOnSubFrames(False)
        hide.setSourceCode(CHROME_HIDE_JS)
        self._profile.scripts().insert(hide)

        skip = QWebEngineScript()
        skip.setName("pokiwrap-skip-ads")
        skip.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        skip.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        skip.setRunsOnSubFrames(True)
        skip.setSourceCode(AD_SKIP_JS)
        self._profile.scripts().insert(skip)

        stealth = QWebEngineScript()
        stealth.setName("pokiwrap-stealth")
        stealth.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        stealth.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        stealth.setRunsOnSubFrames(True)
        stealth.setSourceCode(
            "(function(){try{Object.defineProperty(navigator,'webdriver',{get:function(){return undefined;}});}catch(e){}"
            "try{window.chrome=window.chrome||{runtime:{}};}catch(e){}})();"
        )
        self._profile.scripts().insert(stealth)

        keys = QWebEngineScript()
        keys.setName("pokiwrap-fs-keys")
        keys.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        keys.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        keys.setRunsOnSubFrames(True)
        keys.setSourceCode(FS_KEY_JS)
        self._profile.scripts().insert(keys)

        self.view = GameView(self)
        page = GamePage(self._profile, self.view)
        self.view.setPage(page)
        page.fullScreenRequested.connect(self._on_fullscreen)
        page.loadFinished.connect(self._on_loaded)
        self.view.setUrl(QUrl(GAME_URL))
        self.setCentralWidget(self.view)
        self._center_on_screen()
        self._fullscreen = False
        f11 = QShortcut(QKeySequence("F11"), self)
        f11.setContext(Qt.ShortcutContext.ApplicationShortcut)
        f11.activated.connect(self._toggle_fullscreen)
        if sys.platform == "darwin":
            mac = QShortcut(QKeySequence("Ctrl+Meta+F"), self)
            mac.setContext(Qt.ShortcutContext.ApplicationShortcut)
            mac.activated.connect(self._toggle_fullscreen)

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
        if sys.platform == "darwin" and not self.isFullScreen() and not getattr(self, "_fullscreen", False):
            self.view.update()
            QTimer.singleShot(50, self.view.repaint)

    def _on_fullscreen(self, request) -> None:
        on = True
        try:
            on = bool(request.toggleOn())
        except Exception:
            on = not self.isFullScreen()
        request.accept()
        if on:
            self.showFullScreen()
            self._fullscreen = True
        else:
            self.showNormal()
            self._fullscreen = False

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen() or self._fullscreen:
            self.showNormal()
            self._fullscreen = False
            return
        self.showFullScreen()
        self._fullscreen = True

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen() or self._fullscreen:
                self.showNormal()
                self._fullscreen = False
                return
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
