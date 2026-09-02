"""Background workers so logo detection does not freeze the UI."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from pokiwrap.catalog import CatalogGame
from pokiwrap.engine.artwork import fetch_logo_bytes, fetch_page_artwork
from pokiwrap.engine.generator import generate_app, game_slug_from_url
from pokiwrap.paths import catalog_cache_dir


def slugify_cache(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "game"


class GenerateWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, name: str, url: str, accent: str, parent=None) -> None:
        super().__init__(parent)
        self._name = name
        self._url = url
        self._accent = accent

    def run(self) -> None:
        try:
            app = generate_app(self._name, self._url, self._accent)
            self.succeeded.emit(app)
        except Exception as exc:
            self.failed.emit(str(exc))


class PagePreviewWorker(QThread):
    ready = pyqtSignal(str, str, bytes)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        title = ""
        logo = b""
        try:
            artwork = fetch_page_artwork(self._url)
            title = artwork.title
            if artwork.logo_url:
                logo = fetch_logo_bytes(artwork.logo_url, self._url) or b""
        except Exception:
            slug = game_slug_from_url(self._url)
            title = slug.replace("-", " ").replace("_", " ").title()
        self.ready.emit(self._url, title, logo)


class CatalogLogoWorker(QThread):
    logo_ready = pyqtSignal(str, bytes)

    def __init__(self, games: tuple[CatalogGame, ...], parent=None) -> None:
        super().__init__(parent)
        self._games = games

    def run(self) -> None:
        cache = catalog_cache_dir()
        for game in self._games:
            cached = cache / f"{slugify_cache(game.title)}.img"
            if cached.exists() and cached.stat().st_size > 0:
                self.logo_ready.emit(game.url, cached.read_bytes())
                continue
            try:
                artwork = fetch_page_artwork(game.url)
                if not artwork.logo_url:
                    continue
                data = fetch_logo_bytes(artwork.logo_url, game.url)
                if not data:
                    continue
                cached.write_bytes(data)
                self.logo_ready.emit(game.url, data)
            except Exception:
                continue
