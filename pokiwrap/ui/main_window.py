from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from pokiwrap.catalog import CatalogGame
from pokiwrap.engine.workers import GenerateWorker
from pokiwrap.engine.manager import delete_app, launch_app, list_apps
from pokiwrap.ui.account_view import AccountView
from pokiwrap.ui.discover_view import DiscoverView
from pokiwrap.ui.my_apps_view import MyAppsView
from pokiwrap.ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PokiWrap")
        self.resize(1120, 740)
        self.setMinimumSize(960, 600)
        self._worker: GenerateWorker | None = None

        self.sidebar = Sidebar()
        self.discover = DiscoverView()
        self.my_apps = MyAppsView()
        self.account = AccountView()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.discover)
        self.stack.addWidget(self.my_apps)
        self.stack.addWidget(self.account)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.showMessage("Ready — wrap Poki and CrazyGames titles as isolated desktop apps.")
        self.setStatusBar(status)

        self.sidebar.view_changed.connect(self._show_view)
        self.discover.generate_requested.connect(self._generate_manual)
        self.discover.catalog_requested.connect(self._generate_catalog)
        self.my_apps.launch_requested.connect(self._launch)
        self.my_apps.delete_requested.connect(self._delete)

        self.refresh_apps()

    def _show_view(self, view_id: int) -> None:
        self.stack.setCurrentIndex(view_id)
        if view_id == 1:
            self.refresh_apps()
        elif view_id == 2:
            self.account.refresh()

    def _generate_manual(self, name: str, url: str, accent: str) -> None:
        self._generate(name, url, accent, clear_form=True)

    def _generate_catalog(self, game: CatalogGame) -> None:
        self._generate(game.title, game.url, game.accent, clear_form=False)

    def _generate(self, name: str, url: str, accent: str, clear_form: bool) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._clear_form = clear_form
        self.discover.set_busy(True)
        self.statusBar().showMessage("Detecting game logo and creating shortcut…")
        self._worker = GenerateWorker(name, url, accent, self)
        self._worker.succeeded.connect(self._on_generated)
        self._worker.failed.connect(self._on_generate_failed)
        self._worker.finished.connect(lambda: self.discover.set_busy(False))
        self._worker.start()

    def _on_generated(self, app) -> None:
        if self._clear_form:
            self.discover.clear_manual_form()
        shortcut_note = " Desktop shortcut created." if app.shortcut_path else ""
        self.statusBar().showMessage(f"Created {app.name}.{shortcut_note}", 6000)
        self.refresh_apps()
        if sys.platform == "darwin":
            detail = f"{app.name} is on your Desktop. Open it to play — the game fills the window."
        else:
            detail = f"{app.name} is a native .exe on your Desktop with the game logo. The game fills the window."
        QMessageBox.information(self, "App ready", detail)

    def _on_generate_failed(self, message: str) -> None:
        self.statusBar().showMessage("Generation failed.", 5000)
        QMessageBox.warning(self, "Cannot generate app", message)

    def _launch(self, app) -> None:
        try:
            launch_app(app)
            self.statusBar().showMessage(f"Launching {app.name}…", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Launch failed", str(exc))

    def _delete(self, app) -> None:
        confirm = QMessageBox.question(
            self,
            "Delete app",
            f"Remove {app.name} and its desktop shortcut?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        delete_app(app)
        self.refresh_apps()
        self.statusBar().showMessage(f"Deleted {app.name}.", 4000)

    def refresh_apps(self) -> None:
        self.my_apps.refresh(list_apps())
