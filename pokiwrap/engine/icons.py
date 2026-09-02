"""Turn downloaded image bytes into square PNG/ICO logos."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath


def save_square_logo(data: bytes, dest: Path, size: int = 256) -> Path | None:
    image = QImage()
    if not image.loadFromData(data):
        return None
    scaled = image.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    dest.mkdir(parents=True, exist_ok=True)
    png_path = dest / "icon.png"
    ico_path = dest / "icon.ico"
    cropped.save(str(png_path), "PNG")
    cropped.save(str(ico_path), "ICO")
    if ico_path.exists():
        return ico_path
    if png_path.exists():
        return png_path
    return None


def render_fallback_icon(dest: Path, accent: str, initials: str, size: int = 256) -> Path:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#1A1F33"))
    painter.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    painter.setBrush(QColor(accent))
    inset = int(size * 0.08)
    painter.drawRoundedRect(
        inset, inset, size - inset * 2, size - inset * 2, size * 0.18, size * 0.18
    )
    play = QPainterPath()
    cx, cy = size * 0.46, size * 0.50
    play.moveTo(cx - size * 0.10, cy - size * 0.16)
    play.lineTo(cx + size * 0.18, cy)
    play.lineTo(cx - size * 0.10, cy + size * 0.16)
    play.closeSubpath()
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawPath(play)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", int(size * 0.10), QFont.Weight.Bold))
    painter.drawText(
        0,
        int(size * 0.72),
        size,
        int(size * 0.20),
        Qt.AlignmentFlag.AlignHCenter,
        initials,
    )
    painter.end()
    dest.mkdir(parents=True, exist_ok=True)
    png_path = dest / "icon.png"
    ico_path = dest / "icon.ico"
    image.save(str(png_path), "PNG")
    image.save(str(ico_path), "ICO")
    return ico_path if ico_path.exists() else png_path
