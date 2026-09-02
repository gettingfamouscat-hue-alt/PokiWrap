"""Detect Poki (or generic) page titles and download game logos."""

from __future__ import annotations

import json
import re
import ssl
import sys
from dataclasses import dataclass
from html import unescape
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
)
MAC_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

POKI_IMG_CDN = (
    "https://img.poki-cdn.com/cdn-cgi/image/"
    "q=78,scq=50,width=512,height=512,fit=cover,f=png/"
)

_META_CONTENT = re.compile(
    r"<meta\b[^>]*?(?:property|name)=['\"]([^'\"]+)['\"][^>]*?content=['\"]([^'\"]+)['\"][^>]*?>"
    r"|<meta\b[^>]*?content=['\"]([^'\"]+)['\"][^>]*?(?:property|name)=['\"]([^'\"]+)['\"][^>]*?>",
    re.I,
)
_LINK_ICON = re.compile(
    r"<link\b[^>]*?rel=['\"][^'\"]*icon[^'\"]*['\"][^>]*?href=['\"]([^'\"]+)['\"]",
    re.I,
)
_JSONLD = re.compile(
    r"<script[^>]*type=['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
    re.I | re.S,
)
_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_IMAGE_URL_FIELD = re.compile(r'"imageUrl"\s*:\s*"([^"]+)"')
_FILE_CONTENT = re.compile(
    r'"file"\s*:\s*\{[^}]{0,800}?"content"\s*:\s*"(https:[^"]+)"',
    re.I,
)
_GAMES_POKI = re.compile(
    r"https:(?:\\u002F|/)+(?:games\.poki\.com|[-a-z0-9.]+\.poki-gdn\.com)(?:\\u002F|/)[-A-Za-z0-9_./]+",
    re.I,
)


@dataclass
class PageArtwork:
    title: str
    logo_url: str | None
    play_url: str | None = None


def _headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": MAC_UA if sys.platform == "darwin" else CHROME_UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _ssl_context(unverified: bool = False):
    if unverified:
        return ssl._create_unverified_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch_bytes(url: str, timeout: float = 12.0, referer: str | None = None) -> bytes:
    request = Request(url, headers=_headers(referer))
    try:
        with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            return response.read()
    except (ssl.SSLError, URLError) as exc:
        text = str(exc).lower()
        if not isinstance(exc, ssl.SSLError) and "ssl" not in text and "certificate" not in text:
            raise
        with urlopen(request, timeout=timeout, context=_ssl_context(True)) as response:
            return response.read()


def fetch_text(url: str, timeout: float = 12.0) -> str:
    return fetch_bytes(url, timeout=timeout).decode("utf-8", "replace")


def clean_title(title: str) -> str:
    text = unescape(re.sub(r"\s+", " ", title)).strip()
    text = re.sub(r"\s*[-–|]\s*Play Online.*$", "", text, flags=re.I)
    text = re.sub(r"\s*[-–|]\s*.*\bPoki\b.*$", "", text, flags=re.I)
    return text.strip(" -|") or "Poki Game"


def _absolute(page_url: str, maybe: str | None) -> str | None:
    if not maybe:
        return None
    value = unescape(maybe.strip()).replace("\\u002F", "/")
    if not value:
        return None
    return urljoin(page_url, value)


def _walk_json(node: object) -> tuple[str | None, str | None]:
    title = None
    image = None
    if isinstance(node, list):
        for item in node:
            found_title, found_image = _walk_json(item)
            title = title or found_title
            image = image or found_image
        return title, image
    if not isinstance(node, dict):
        return None, None
    if isinstance(node.get("name"), str):
        title = node["name"]
    image_node = node.get("primaryImageOfPage") or node.get("image") or node.get("thumbnailUrl")
    if isinstance(image_node, str):
        image = image_node
    elif isinstance(image_node, dict):
        image = image_node.get("url") or image_node.get("contentUrl") or image_node.get("thumbnailUrl")
    elif isinstance(image_node, list) and image_node:
        image = image_node[0] if isinstance(image_node[0], str) else None
    nested = node.get("@graph")
    if nested:
        nested_title, nested_image = _walk_json(nested)
        title = title or nested_title
        image = image or nested_image
    return title, image


def _poki_cdn_logo(image_url_field: str) -> str:
    path = image_url_field.replace("\\u002F", "/").lstrip("/")
    if path.startswith("http"):
        return path
    return POKI_IMG_CDN + path


def extract_artwork(html: str, page_url: str) -> PageArtwork:
    title: str | None = None
    logo: str | None = None

    for match in _JSONLD.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        found_title, found_image = _walk_json(payload)
        title = title or found_title
        logo = logo or found_image

    props: dict[str, str] = {}
    for match in _META_CONTENT.finditer(html):
        if match.group(1):
            props[match.group(1).lower()] = unescape(match.group(2))
        else:
            props[match.group(4).lower()] = unescape(match.group(3))
    title = title or props.get("og:title") or props.get("twitter:title")
    logo = (
        logo
        or props.get("og:image")
        or props.get("og:image:url")
        or props.get("twitter:image")
        or props.get("twitter:image:src")
    )

    slug = ""
    parsed = urlparse(page_url)
    parts = [part for part in parsed.path.split("/") if part]
    if "g" in parts:
        idx = parts.index("g")
        if idx + 1 < len(parts):
            slug = parts[idx + 1]
    if slug:
        for image_field in _IMAGE_URL_FIELD.findall(html):
            decoded = image_field.replace("\\u002F", "/")
            if slug.replace("_", "-") in decoded.lower() or slug in decoded.lower():
                logo = logo or _poki_cdn_logo(decoded)
                break

    if not logo:
        icon = _LINK_ICON.search(html)
        if icon:
            logo = icon.group(1)

    if not title:
        tagged = _TITLE_TAG.search(html)
        if tagged:
            title = re.sub(r"<[^>]+>", "", tagged.group(1))

    return PageArtwork(
        title=clean_title(title or ""),
        logo_url=_absolute(page_url, logo),
        play_url=extract_play_url(html),
    )


def extract_play_url(html: str) -> str | None:
    match = _FILE_CONTENT.search(html)
    if match:
        return unescape(match.group(1)).replace("\\u002F", "/")
    found = _GAMES_POKI.findall(html)
    if found:
        return unescape(found[0]).replace("\\u002F", "/")
    return None


def fetch_page_artwork(page_url: str) -> PageArtwork:
    html = fetch_text(page_url)
    artwork = extract_artwork(html, page_url)
    if not artwork.title:
        artwork.title = "Poki Game"
    return artwork


def fetch_logo_bytes(logo_url: str, page_url: str) -> bytes | None:
    try:
        data = fetch_bytes(logo_url, referer=page_url)
    except (URLError, TimeoutError, OSError, ValueError):
        return None
    return data if data else None
