"""Application bootstrap."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from pokiwrap.paths import assets_dir, generated_apps_dir
from pokiwrap.theme import STYLESHEET, apply_dark_palette
from pokiwrap.ui.main_window import MainWindow


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


def run() -> int:
    generated_apps_dir()
    try:
        from pokiwrap.engine.adblock import ensure_adblock_list

        ensure_adblock_list()
    except Exception:
        pass
    _set_app_id()
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
    app.setProperty("adblockUpdater", "1")
    window = MainWindow()
    window._adblock_updater = updater
    updater.start()
    window.show()
    return app.exec()
