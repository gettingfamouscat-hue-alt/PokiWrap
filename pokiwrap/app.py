"""Application bootstrap."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import QApplication

from pokiwrap.paths import assets_dir, generated_apps_dir
from pokiwrap.theme import STYLESHEET, apply_dark_palette
from pokiwrap.ui.main_window import MainWindow


class _RewriteThread(QThread):
    def run(self) -> None:
        try:
            from pokiwrap.engine.browser_cookies import export_browser_cookies

            export_browser_cookies()
        except Exception:
            pass
        try:
            from pokiwrap.engine.generator import rewrite_existing_wrappers

            rewrite_existing_wrappers()
        except Exception:
            return


class _AdblockUpdateThread(QThread):
    def run(self) -> None:
        try:
            from pokiwrap.engine.adblock import update_adblock_list

            update_adblock_list()
        except Exception:
            return


def _set_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PokiWrap.App")
    except Exception:
        return


def _prepare_qt() -> None:
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    if sys.platform == "darwin":
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        for relative in (
            Path("PyQt6") / "Qt6" / "plugins",
            Path("PyQt6") / "Qt" / "plugins",
        ):
            plugins = meipass / relative
            if (plugins / "platforms").exists():
                os.environ.setdefault("QT_PLUGIN_PATH", str(plugins))
                break


def run() -> int:
    _prepare_qt()
    try:
        generated_apps_dir()
    except OSError:
        pass
    try:
        from pokiwrap.engine.adblock import ensure_adblock_list

        ensure_adblock_list()
    except Exception:
        pass
    _set_app_id()
    if sys.platform == "darwin":
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("PokiWrap")
    app.setOrganizationName("PokiWrap")
    icon = assets_dir() / "pokiwrap.ico"
    if icon.exists():
        from PyQt6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon)))
    apply_dark_palette(app)
    app.setStyleSheet(STYLESHEET)
    updater = _AdblockUpdateThread(app)
    rewriter = _RewriteThread(app)
    app.setProperty("adblockUpdater", "1")
    window = MainWindow()
    window._adblock_updater = updater
    window._wrapper_rewriter = rewriter
    updater.start()
    rewriter.start()
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
