from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from pokiwrap.catalog import CatalogGame


class GameCard(QFrame):
    download_requested = pyqtSignal(object)

    def __init__(self, game: CatalogGame, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.setObjectName("card")
        self.setFixedSize(210, 236)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self.icon = QLabel()
        self.icon.setFixedSize(64, 64)
        self.icon.setPixmap(_placeholder_icon(game.accent, game.title))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(game.title)
        title.setObjectName("cardTitle")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent; border: none; color: #E8EAED;")

        tagline = QLabel(game.tagline)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("color: #8B90A0; background: transparent; border: none;")

        button = QPushButton("Download App")
        button.setObjectName("primaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.download_requested.emit(self.game))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(4)
        layout.addWidget(title)
        layout.addWidget(tagline)
        layout.addStretch()
        layout.addWidget(button)

    def set_logo(self, data: bytes) -> None:
        pixmap = rounded_logo(data, 64, 16)
        if not pixmap.isNull():
            self.icon.setPixmap(pixmap)


def rounded_logo(data: bytes, size: int, radius: int) -> QPixmap:
    image = QImage()
    if not image.loadFromData(data):
        return QPixmap()
    scaled = QPixmap.fromImage(image).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return out


def _placeholder_icon(accent: str, title: str) -> QPixmap:
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(accent))
    painter.drawRoundedRect(0, 0, size, size, 16, 16)

    parts = title.split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else parts[0][1:2])).upper()
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    return pixmap
