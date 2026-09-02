from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pokiwrap.engine.generator import GeneratedApp
from pokiwrap.ui.game_card import rounded_logo


class AppRow(QFrame):
    launch_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, app: GeneratedApp, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app = app
        self.setObjectName("card")

        icon = QLabel()
        icon.setFixedSize(44, 44)
        icon_path = app.icon_path
        if icon_path.exists():
            pixmap = rounded_logo(icon_path.read_bytes(), 44, 12)
            if pixmap.isNull():
                pixmap = QPixmap(str(icon_path)).scaled(
                    44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            icon.setPixmap(pixmap)
        else:
            icon.setPixmap(_badge(app.accent, app.name))

        title = QLabel(app.name)
        title.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent; border: none;")
        subtitle = QLabel(app.url or "Poki wrapper")
        subtitle.setStyleSheet("color: #8B90A0; background: transparent; border: none;")
        subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        text.addWidget(title)
        text.addWidget(subtitle)

        launch = QPushButton("Launch")
        launch.setObjectName("primaryButton")
        launch.setCursor(Qt.CursorShape.PointingHandCursor)
        launch.clicked.connect(lambda: self.launch_requested.emit(self.app))

        delete = QPushButton("Delete")
        delete.setObjectName("dangerButton")
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete.clicked.connect(lambda: self.delete_requested.emit(self.app))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(icon)
        layout.addLayout(text, 1)
        layout.addWidget(launch)
        layout.addWidget(delete)


class MyAppsView(QWidget):
    launch_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title = QLabel("My Apps")
        title.setObjectName("title")
        subtitle = QLabel("Launch or remove wrappers saved in generated_apps/.")
        subtitle.setObjectName("subtitle")

        self.empty = QLabel("No apps yet.\nGenerate a shortcut from Discover Games.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("color: #8B90A0; font-size: 14px; padding: 48px;")

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.list_host)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 24, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.empty)
        layout.addWidget(scroll, 1)
        self._scroll = scroll

    def refresh(self, apps: list[GeneratedApp]) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.empty.setVisible(not apps)
        self._scroll.setVisible(bool(apps))

        for app in apps:
            row = AppRow(app)
            row.launch_requested.connect(self.launch_requested.emit)
            row.delete_requested.connect(self.delete_requested.emit)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)


def _badge(accent: str, name: str) -> QPixmap:
    pixmap = QPixmap(44, 44)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(accent))
    painter.drawRoundedRect(0, 0, 44, 44, 12, 12)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, name[:1].upper())
    painter.end()
    return pixmap
