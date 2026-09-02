from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class Sidebar(QFrame):
    view_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(228)

        brand = QLabel("PokiWrap")
        brand.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.2px;")
        tagline = QLabel("Desktop wrappers for\nPoki games")
        tagline.setStyleSheet("color: #8B90A0; padding-bottom: 18px;")

        self.discover_btn = QPushButton("  Discover Games")
        self.apps_btn = QPushButton("  My Apps")
        self.account_btn = QPushButton("  Poki Account")
        for button in (self.discover_btn, self.apps_btn, self.account_btn):
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self.discover_btn, 0)
        self._group.addButton(self.apps_btn, 1)
        self._group.addButton(self.account_btn, 2)
        self._group.idClicked.connect(self._on_clicked)

        hint = QLabel("Wrappers load games live\nfrom Poki — nothing is\nscraped or downloaded.")
        hint.setStyleSheet("color: #6E7384; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(6)
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(8)
        layout.addWidget(self.discover_btn)
        layout.addWidget(self.apps_btn)
        layout.addWidget(self.account_btn)
        layout.addStretch()
        layout.addWidget(hint)

        self.set_active(0)

    def _on_clicked(self, view_id: int) -> None:
        self.set_active(view_id)
        self.view_changed.emit(view_id)

    def set_active(self, view_id: int) -> None:
        self.discover_btn.setChecked(view_id == 0)
        self.apps_btn.setChecked(view_id == 1)
        self.account_btn.setChecked(view_id == 2)
        self.discover_btn.setProperty("active", "true" if view_id == 0 else "false")
        self.apps_btn.setProperty("active", "true" if view_id == 1 else "false")
        self.account_btn.setProperty("active", "true" if view_id == 2 else "false")
        for button in (self.discover_btn, self.apps_btn, self.account_btn):
            button.style().unpolish(button)
            button.style().polish(button)
