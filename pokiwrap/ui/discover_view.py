from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pokiwrap.catalog import GAMES
from pokiwrap.engine.generator import is_valid_http_url
from pokiwrap.engine.workers import CatalogLogoWorker, PagePreviewWorker
from pokiwrap.ui.flow_layout import FlowLayout
from pokiwrap.ui.game_card import GameCard, rounded_logo


class _CatalogGrid(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._flow = FlowLayout(self, spacing=16)

    def add_card(self, card: GameCard) -> None:
        self._flow.addWidget(card)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._flow.heightForWidth(width)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.setMinimumHeight(self.heightForWidth(max(self.width(), 1)))


class DiscoverView(QWidget):
    generate_requested = pyqtSignal(str, str, str)
    catalog_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, GameCard] = {}
        self._preview_worker: PagePreviewWorker | None = None
        self._logo_worker: CatalogLogoWorker | None = None

        title = QLabel("Discover Games")
        title.setObjectName("title")
        subtitle = QLabel("Wrap any Poki title as a lightweight desktop app. Games stream from Poki — no files are downloaded.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(40, 40)
        self.logo_preview.setStyleSheet(
            "background: #1C2030; border: 1px solid #2A3148; border-radius: 10px;"
        )
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setText("★")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste any Poki game URL…  e.g. https://poki.com/en/g/subway-surfers")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("App name (auto-detected)")
        self.name_input.setFixedWidth(200)

        self.generate_btn = QPushButton("Generate App Shortcut")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._emit_manual)

        self.url_input.returnPressed.connect(self._emit_manual)
        self.name_input.returnPressed.connect(self._emit_manual)

        self._url_timer = QTimer(self)
        self._url_timer.setSingleShot(True)
        self._url_timer.setInterval(650)
        self._url_timer.timeout.connect(self._preview_from_url)
        self.url_input.textChanged.connect(lambda: self._url_timer.start())

        form = QFrame()
        form.setObjectName("card")
        form_layout = QHBoxLayout(form)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)
        form_layout.addWidget(self.logo_preview)
        form_layout.addWidget(self.url_input, 1)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.generate_btn)

        catalog_label = QLabel("Popular on Poki")
        catalog_label.setStyleSheet("font-size: 15px; font-weight: 700; padding-top: 8px;")

        cards = _CatalogGrid()
        for game in GAMES:
            card = GameCard(game)
            card.download_requested.connect(self.catalog_requested.emit)
            cards.add_card(card)
            self._cards[game.url] = card

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(cards)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        cards.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 24, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(form)
        layout.addWidget(catalog_label)
        layout.addWidget(scroll, 1)

        self._logo_worker = CatalogLogoWorker(GAMES, self)
        self._logo_worker.logo_ready.connect(self._on_catalog_logo)
        self._logo_worker.start()

    def _emit_manual(self) -> None:
        self.generate_requested.emit(self.name_input.text(), self.url_input.text(), "#7C5CFF")

    def clear_manual_form(self) -> None:
        self.url_input.clear()
        self.name_input.clear()
        self.logo_preview.clear()
        self.logo_preview.setText("★")

    def set_busy(self, busy: bool) -> None:
        self.generate_btn.setEnabled(not busy)
        self.generate_btn.setText("Detecting logo…" if busy else "Generate App Shortcut")

    def _preview_from_url(self) -> None:
        url = self.url_input.text().strip()
        if not is_valid_http_url(url):
            return
        worker = PagePreviewWorker(url, self)
        worker.ready.connect(self._on_preview)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._preview_worker = worker

    def _on_preview(self, url: str, title: str, logo: bytes) -> None:
        if url.strip() != self.url_input.text().strip():
            return
        if title and not self.name_input.text().strip():
            self.name_input.setText(title)
        if logo:
            pixmap = rounded_logo(logo, 40, 10)
            if not pixmap.isNull():
                self.logo_preview.setText("")
                self.logo_preview.setPixmap(pixmap)

    def _on_catalog_logo(self, url: str, data: bytes) -> None:
        card = self._cards.get(url)
        if card is not None:
            card.set_logo(data)
