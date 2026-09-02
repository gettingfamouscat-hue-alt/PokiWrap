"""Dark theme stylesheet and palette helpers."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

BG = "#0F1117"
SURFACE = "#161922"
CARD = "#1C2030"
CARD_HOVER = "#242A3D"
BORDER = "#2A3148"
TEXT = "#E8EAED"
MUTED = "#8B90A0"
ACCENT = "#7C5CFF"
ACCENT_HOVER = "#9174FF"
DANGER = "#F43F5E"
SUCCESS = "#34D399"


def apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(CARD))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(CARD))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(CARD))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    app.setPalette(palette)


STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", "SF Pro Display", "Inter", sans-serif;
    font-size: 13px;
}}
QMainWindow {{
    background: {BG};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QLineEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px 14px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    border: none;
    border-radius: 10px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton#primaryButton {{
    background: {ACCENT};
    color: #FFFFFF;
}}
QPushButton#primaryButton:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton#primaryButton:pressed {{
    background: #6A48F0;
}}
QPushButton#ghostButton {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QPushButton#ghostButton:hover {{
    background: {CARD_HOVER};
}}
QPushButton#dangerButton {{
    background: rgba(244, 63, 94, 0.14);
    color: #FF6B85;
    border: 1px solid rgba(244, 63, 94, 0.28);
}}
QPushButton#dangerButton:hover {{
    background: rgba(244, 63, 94, 0.24);
}}
QPushButton#navButton {{
    background: transparent;
    color: {MUTED};
    text-align: left;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#navButton:hover {{
    background: {CARD};
    color: {TEXT};
}}
QPushButton#navButton[active="true"] {{
    background: rgba(124, 92, 255, 0.16);
    color: #FFFFFF;
}}
QLabel#muted {{
    color: {MUTED};
}}
QLabel#title {{
    font-size: 22px;
    font-weight: 700;
}}
QLabel#subtitle {{
    color: {MUTED};
    font-size: 13px;
}}
QFrame#sidebar {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#card:hover {{
    border: 1px solid #3A4464;
}}
QStatusBar {{
    background: {SURFACE};
    color: {MUTED};
    border-top: 1px solid {BORDER};
}}
QCheckBox {{
    color: {TEXT};
    spacing: 10px;
    font-weight: 600;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {BORDER};
    background: {CARD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QMessageBox {{
    background: {SURFACE};
}}
"""
