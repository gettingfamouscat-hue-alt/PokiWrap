"""Live Poki catalog plus a CrazyGames set, with a local cache."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

from pokiwrap.paths import catalog_cache_dir

ACCENTS = (
    "#F97316",
    "#D97706",
    "#EF4444",
    "#22D3EE",
    "#A78BFA",
    "#F43F5E",
    "#34D399",
    "#60A5FA",
    "#818CF8",
    "#FB7185",
    "#FBBF24",
    "#F87171",
    "#4ADE80",
    "#F59E0B",
    "#2DD4BF",
    "#C084FC",
)

POKI_SITEMAP = "https://poki.com/en/sitemaps/games.xml"
CRAZY_SITEMAP = "https://www.crazygames.com/en/sitemap"

_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_IMAGE_LOC = re.compile(r"<image:loc>\s*([^<\s]+)\s*</image:loc>", re.I)
_POKI_SLUG = re.compile(r"/g/([^/?#]+)", re.I)

FEATURED_POKI = (
    "subway-surfers",
    "temple-run-2",
    "moto-x3m",
    "slope",
    "stickman-hook",
    "drive-mad",
    "smash-karts",
    "paper-io-2",
    "run-3",
    "vex-7",
    "basketball-stars",
    "superhot",
    "fireboy-and-watergirl-the-forest-temple",
    "2048",
    "crossy-road",
    "hole-io",
    "cluster-rush",
    "getaway-shootout",
    "retro-bowl",
    "drift-boss",
    "tag",
    "gobattle2",
    "minefun-io",
    "master-chess",
)

FEATURED_CRAZY = (
    "smash-karts",
    "shell-shockers",
    "krunker-io",
    "1v1-lol",
    "slope",
    "drift-hunters",
    "rooftop-snipers",
    "getaway-shootout",
    "paper-io-2",
    "hole-io",
    "snake-io",
    "slither-io",
    "agar-io",
    "moto-x3m",
    "stickman-hook",
    "basketball-stars",
    "retro-bowl",
    "friday-night-funkin",
    "subway-surfers",
    "temple-run-2",
    "crossy-road",
    "2048",
    "cookie-clicker",
    "happy-wheels",
    "run-3",
    "cluster-rush",
    "vex-4",
    "geometry-dash",
    "pacman",
    "space-invaders",
    "age-of-war",
    "gold-miner",
    "line-rider",
    "wordle",
    "solitaire",
    "chess",
    "mahjong",
    "tetris",
    "flappy-bird",
    "doodle-jump",
    "cubefield",
    "ovo",
    "iron-snout",
    "little-alchemy-2",
)


@dataclass(frozen=True)
class CatalogGame:
    title: str
    url: str
    tagline: str
    accent: str
    source: str = "poki"
    logo_url: str | None = None


def _accent_for(slug: str) -> str:
    total = 0
    for char in slug.lower():
        total = (total * 33 + ord(char)) & 0xFFFFFFFF
    return ACCENTS[total % len(ACCENTS)]


def title_from_slug(slug: str) -> str:
    text = unquote(slug or "").strip().replace("_", "-")
    text = re.sub(r"-io(?=-|$)", ".io", text, flags=re.I)
    parts = [part for part in text.split("-") if part]
    pretty: list[str] = []
    special = {"3d": "3D", "2d": "2D", "fps": "FPS", "1v1": "1v1", "io": ".io", "lol": "LOL"}
    for part in parts:
        key = part.lower()
        if key in special:
            pretty.append(special[key])
        elif part[:1].isalpha():
            pretty.append(part[:1].upper() + part[1:])
        else:
            pretty.append(part)
    return " ".join(pretty).replace(" .io", ".io") or slug


def _poki_game(slug: str) -> CatalogGame:
    return CatalogGame(
        title=title_from_slug(slug),
        url=f"https://poki.com/en/g/{slug}",
        tagline="Poki",
        accent=_accent_for(slug),
        source="poki",
    )


def _crazy_game(slug: str, logo_url: str | None = None) -> CatalogGame:
    return CatalogGame(
        title=title_from_slug(slug),
        url=f"https://www.crazygames.com/game/{slug}",
        tagline="CrazyGames",
        accent=_accent_for("crazy-" + slug),
        source="crazygames",
        logo_url=logo_url,
    )


GAMES: tuple[CatalogGame, ...] = tuple(_poki_game(slug) for slug in FEATURED_POKI) + tuple(
    _crazy_game(slug) for slug in FEATURED_CRAZY[:16]
)


def _cache_path():
    return catalog_cache_dir() / "games.json"


def load_cached_catalog() -> list[CatalogGame]:
    path = _cache_path()
    if not path.exists():
        return list(GAMES)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        games = [_from_dict(item) for item in payload.get("games") or []]
        return games or list(GAMES)
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return list(GAMES)


def catalog_cache_is_fresh(max_hours: float = 24.0) -> bool:
    path = _cache_path()
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(str(payload.get("fetched") or ""))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - stamp
        games = payload.get("games") or []
        return age.total_seconds() < max_hours * 3600 and len(games) > 200
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False


def save_cached_catalog(games: list[CatalogGame]) -> None:
    path = _cache_path()
    payload = {
        "fetched": datetime.now(timezone.utc).isoformat(),
        "games": [asdict(game) for game in games],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _from_dict(item: dict) -> CatalogGame:
    return CatalogGame(
        title=str(item.get("title") or title_from_slug(str(item.get("url") or "game"))),
        url=str(item.get("url") or ""),
        tagline=str(item.get("tagline") or "Poki"),
        accent=str(item.get("accent") or ACCENTS[0]),
        source=str(item.get("source") or "poki"),
        logo_url=item.get("logo_url") or None,
    )


def _fetch_poki_games() -> list[CatalogGame]:
    from pokiwrap.engine.artwork import fetch_text

    xml = fetch_text(POKI_SITEMAP, timeout=20)
    seen: set[str] = set()
    games: list[CatalogGame] = []
    for loc in _LOC.findall(xml):
        match = _POKI_SLUG.search(loc)
        if not match:
            continue
        slug = unquote(match.group(1)).strip().lower()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        games.append(_poki_game(slug))
    return games


_CRAZY_ENTRY = re.compile(
    r"<loc>\s*(https://www\.crazygames\.com/game/([^<\s]+))\s*</loc>(.{0,500})",
    re.I | re.S,
)


def _fetch_crazy_games() -> list[CatalogGame]:
    from pokiwrap.engine.artwork import fetch_text

    xml = fetch_text(CRAZY_SITEMAP, timeout=45)
    by_slug: dict[str, CatalogGame] = {}
    for match in _CRAZY_ENTRY.finditer(xml):
        slug = unquote(match.group(2)).strip().lower()
        if not slug or "/" in slug or "?" in slug:
            continue
        image = None
        img_match = _IMAGE_LOC.search(match.group(3))
        if img_match:
            image = unquote(img_match.group(1).replace("&amp;", "&"))
        if slug not in by_slug or (image and not by_slug[slug].logo_url):
            by_slug[slug] = _crazy_game(slug, image)
    return list(by_slug.values())


def _order_games(poki: list[CatalogGame], crazy: list[CatalogGame]) -> list[CatalogGame]:
    poki_map = {urlparse(game.url).path.rstrip("/").split("/")[-1]: game for game in poki}
    crazy_map = {urlparse(game.url).path.rstrip("/").split("/")[-1]: game for game in crazy}
    ordered: list[CatalogGame] = []
    seen: set[str] = set()

    def add(game: CatalogGame) -> None:
        if game.url in seen:
            return
        seen.add(game.url)
        ordered.append(game)

    for slug in FEATURED_POKI:
        if slug in poki_map:
            add(poki_map[slug])
        else:
            add(_poki_game(slug))
    for slug in FEATURED_CRAZY:
        if slug in crazy_map:
            add(crazy_map[slug])
        else:
            add(_crazy_game(slug))
    for game in sorted(poki, key=lambda item: item.title.lower()):
        add(game)
    for game in sorted(crazy, key=lambda item: item.title.lower()):
        add(game)
    return ordered


def fetch_remote_catalog() -> list[CatalogGame]:
    poki: list[CatalogGame] = []
    crazy: list[CatalogGame] = []
    try:
        poki = _fetch_poki_games()
    except Exception:
        poki = [_poki_game(slug) for slug in FEATURED_POKI]
    try:
        crazy = _fetch_crazy_games()
    except Exception:
        crazy = [_crazy_game(slug) for slug in FEATURED_CRAZY]
    if not poki:
        poki = [_poki_game(slug) for slug in FEATURED_POKI]
    if not crazy:
        crazy = [_crazy_game(slug) for slug in FEATURED_CRAZY]
    games = _order_games(poki, crazy)
    try:
        save_cached_catalog(games)
    except OSError:
        pass
    return games


def filter_catalog(
    games: list[CatalogGame],
    query: str = "",
    source: str = "all",
    limit: int = 72,
) -> list[CatalogGame]:
    needle = " ".join(query.lower().split())
    source_key = source.strip().lower()
    matched: list[CatalogGame] = []
    for game in games:
        if source_key not in {"", "all"} and game.source != source_key:
            continue
        if needle:
            hay = f"{game.title} {game.url} {game.tagline}".lower()
            if needle not in hay:
                continue
        matched.append(game)
        if len(matched) >= limit:
            break
    return matched


def catalog_counts(games: list[CatalogGame]) -> tuple[int, int]:
    poki = sum(1 for game in games if game.source == "poki")
    crazy = sum(1 for game in games if game.source == "crazygames")
    return poki, crazy
