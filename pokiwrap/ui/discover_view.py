from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pokiwrap.catalog import GAMES, catalog_counts, filter_catalog, load_cached_catalog
from pokiwrap.engine.generator import game_slug_from_url, is_valid_http_url, normalize_game_url
from pokiwrap.engine.workers import CatalogFetchWorker, CatalogLogoWorker, PagePreviewWorker
from pokiwrap.ui.game_card import GameCard, rounded_logo

MAX_VISIBLE = 72


class _CatalogGrid(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._cards: list[GameCard] = []
        self._columns = 0

    def set_cards(self, cards: list[GameCard]) -> None:
        self.clear_cards()
        self._cards = cards
        self._place_cards()

    def clear_cards(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cards = []

    def _place_cards(self) -> None:
        width = max(self.width(), self.parentWidget().width() if self.parentWidget() else 800)
        columns = max(1, width // 226)
        self._columns = columns
        for index, card in enumerate(self._cards):
            self._grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._cards:
            return
        width = max(self.width(), 1)
        columns = max(1, width // 226)
        if columns != getattr(self, "_columns", 0):
            widgets = list(self._cards)
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item is not None and item.widget() is not None:
                    self._grid.removeWidget(item.widget())
            self._columns = columns
            for index, card in enumerate(widgets):
                self._grid.addWidget(card, index // columns, index % columns)


class DiscoverView(QWidget):
    generate_requested = pyqtSignal(str, str, str)
    catalog_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, GameCard] = {}
        self._games = list(load_cached_catalog() or GAMES)
        self._source = "all"
        self._preview_worker: PagePreviewWorker | None = None
        self._logo_worker: CatalogLogoWorker | None = None
        self._catalog_worker: CatalogFetchWorker | None = None

        title = QLabel("Discover Games")
        title.setObjectName("title")
        subtitle = QLabel(
            "Wrap Poki and CrazyGames titles as desktop apps. Games stream from the site — no files are downloaded."
        )
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
        self.url_input.setPlaceholderText(
            "Paste a Poki or CrazyGames URL…  e.g. https://www.crazygames.com/game/shell-shockers"
        )
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

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search all games…")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self._render_catalog)
        self.search_input.textChanged.connect(lambda: self._search_timer.start())

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self._source_group = QButtonGroup(self)
        self._source_group.setExclusive(True)
        for key, label in (("all", "All"), ("poki", "Poki"), ("crazygames", "CrazyGames")):
            button = QPushButton(label)
            button.setObjectName("chipButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("source", key)
            if key == "all":
                button.setChecked(True)
            self._source_group.addButton(button)
            filters.addWidget(button)
        filters.addStretch()
        self._source_group.buttonClicked.connect(self._on_source_clicked)

        self.catalog_label = QLabel()
        self.catalog_label.setStyleSheet("font-size: 15px; font-weight: 700; padding-top: 8px;")
        self.catalog_meta = QLabel()
        self.catalog_meta.setObjectName("subtitle")
        self.catalog_meta.setWordWrap(True)

        self._cards_grid = _CatalogGrid()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._cards_grid)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self._cards_grid.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 24, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(form)
        layout.addWidget(self.search_input)
        layout.addLayout(filters)
        layout.addWidget(self.catalog_label)
        layout.addWidget(self.catalog_meta)
        layout.addWidget(scroll, 1)

        self._render_catalog()
        self._catalog_worker = CatalogFetchWorker(self)
        self._catalog_worker.ready.connect(self._on_catalog_ready)
        self._catalog_worker.start()

    def _on_source_clicked(self, button: QPushButton) -> None:
        self._source = str(button.property("source") or "all")
        self._render_catalog()

    def _on_catalog_ready(self, games) -> None:
        if not games:
            return
        self._games = list(games)
        self._render_catalog()

    def _render_catalog(self) -> None:
        query = self.search_input.text().strip()
        visible = filter_catalog(self._games, query, self._source, MAX_VISIBLE)
        poki_count, crazy_count = catalog_counts(self._games)
        source_total = {
            "poki": poki_count,
            "crazygames": crazy_count,
            "all": poki_count + crazy_count,
        }.get(self._source, poki_count + crazy_count)
        if self._source == "crazygames":
            heading = "CrazyGames"
        elif self._source == "poki":
            heading = "Poki"
        else:
            heading = "Poki + CrazyGames"
        self.catalog_label.setText(heading)
        if query:
            self.catalog_meta.setText(
                f"Showing {len(visible)} match{'es' if len(visible) != 1 else ''} — {poki_count:,} Poki · {crazy_count:,} CrazyGames in the catalog."
            )
        else:
            extra = ""
            if source_total > len(visible):
                extra = f" Showing {len(visible)} of {source_total:,}. Search to find any title."
            self.catalog_meta.setText(
                f"{poki_count:,} Poki games · {crazy_count:,} CrazyGames.{extra}"
            )

        self._cards_grid.clear_cards()
        self._cards = {}
        cards: list[GameCard] = []
        for game in visible:
            card = GameCard(game)
            card.download_requested.connect(self.catalog_requested.emit)
            cards.append(card)
            self._cards[game.url] = card
        self._cards_grid.set_cards(cards)
        if self._logo_worker is not None:
            self._logo_worker.requestInterruption()
        self._logo_worker = CatalogLogoWorker(visible, self)
        self._logo_worker.logo_ready.connect(self._on_catalog_logo)
        self._logo_worker.start()

    def _emit_manual(self) -> None:
        url = normalize_game_url(self.url_input.text())
        self.generate_requested.emit(self.name_input.text(), url, "#7C5CFF")

    def clear_manual_form(self) -> None:
        self.url_input.clear()
        self.name_input.clear()
        self.logo_preview.clear()
        self.logo_preview.setText("★")

    def set_busy(self, busy: bool) -> None:
        self.generate_btn.setEnabled(not busy)
        self.generate_btn.setText("Detecting logo…" if busy else "Generate App Shortcut")

    def _preview_from_url(self) -> None:
        url = normalize_game_url(self.url_input.text())
        if not is_valid_http_url(url):
            return
        if not self.name_input.text().strip():
            slug = game_slug_from_url(url)
            if slug and slug not in {"poki_game"}:
                pretty = slug.replace("-", " ").replace("_", " ").title()
                self.name_input.setText(pretty)
        worker = PagePreviewWorker(url, self)
        worker.ready.connect(self._on_preview)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._preview_worker = worker

    def _on_preview(self, url: str, title: str, logo: bytes) -> None:
        current = normalize_game_url(self.url_input.text())
        if url.strip() != current.strip():
            return
        if title:
            typed = self.name_input.text().strip()
            slug_guess = game_slug_from_url(url).replace("-", " ").replace("_", " ").title()
            if not typed or typed == slug_guess:
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
