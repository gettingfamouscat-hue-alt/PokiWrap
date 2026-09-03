"""Write wrapper scripts, metadata, and a game logo icon."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pokiwrap.engine.artwork import fetch_logo_bytes, fetch_page_artwork
from pokiwrap.engine.exe import build_game_exe, publish_desktop_exe
from pokiwrap.engine.icons import render_fallback_icon, save_square_logo
from pokiwrap.engine.shortcut import create_desktop_shortcut
from pokiwrap.engine.template import AD_SKIP_JS, CHROME_HIDE_JS, WRAPPER_TEMPLATE
from pokiwrap.paths import generated_app_roots, generated_apps_dir


@dataclass
class GeneratedApp:
    slug: str
    name: str
    url: str
    folder: Path
    script_path: Path
    shortcut_path: str | None
    created: str
    accent: str
    exe_path: str | None = None

    @property
    def icon_path(self) -> Path:
        ico = self.folder / "icon.ico"
        png = self.folder / "icon.png"
        return ico if ico.exists() else png

    @property
    def executable(self) -> Path:
        if self.exe_path and Path(self.exe_path).exists():
            return Path(self.exe_path)
        local = self.folder / f"{self.name}.exe"
        if local.exists():
            return local
        return self.script_path


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip()).strip("_").lower()
    return slug or "poki_game"


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _unique_folder(base: Path, slug: str) -> Path:
    candidate = base / slug
    index = 2
    while candidate.exists():
        candidate = base / f"{slug}_{index}"
        index += 1
    return candidate


def _initials(name: str) -> str:
    parts = [part for part in re.split(r"\s+", name.strip()) if part]
    if not parts:
        return "PW"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def game_slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")
    if "g" in path:
        index = path.index("g")
        if index + 1 < len(path):
            return path[index + 1]
    return slugify(url)


def write_wrapper_script(script_path: Path, name: str, url: str) -> None:
    slug = game_slug_from_url(url)
    js = CHROME_HIDE_JS.replace("__TARGET_SLUG__", slug)
    script_path.write_text(
        WRAPPER_TEMPLATE.replace("__APP_NAME_TEXT__", name)
        .replace("__APP_NAME__", repr(name))
        .replace("__GAME_URL__", repr(url))
        .replace("__PROFILE_NAME__", repr(f"pokiwrap_{slug.replace('-', '_')}"))
        .replace("__CHROME_HIDE_JS__", repr(js))
        .replace("__AD_SKIP_JS__", repr(AD_SKIP_JS))
        .replace("__TARGET_SLUG__", repr(slug)),
        encoding="utf-8",
        newline="\n",
    )


def rewrite_existing_wrappers() -> int:
    count = 0
    folders: list[Path] = []
    seen: set[Path] = set()
    for root in generated_app_roots():
        try:
            for folder in root.iterdir():
                if folder.is_dir():
                    resolved = folder.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        folders.append(folder)
        except OSError:
            continue
    for folder in folders:
        if not folder.is_dir():
            continue
        script_path = folder / "app.py"
        meta_path = folder / "metadata.json"
        if not script_path.exists() or not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = data.get("name") or folder.name
        url = data.get("url")
        if not url:
            continue
        write_wrapper_script(script_path, name, url)
        play_url = data.get("play_url") or url
        if not data.get("play_url"):
            try:
                play_url = fetch_page_artwork(url).play_url or url
            except Exception:
                play_url = url
        icon = folder / "icon.ico"
        if not icon.exists():
            icon = folder / "icon.png"
        try:
            exe_path = build_game_exe(name, folder, icon if icon.exists() else None, play_url, url)
            if exe_path:
                desktop = publish_desktop_exe(exe_path, name)
                data["exe"] = str(exe_path)
                data["play_url"] = play_url
                data["shortcut"] = str(desktop)
                meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        count += 1
    return count


def _write_icon(folder: Path, name: str, accent: str, logo_bytes: bytes | None) -> Path:
    if logo_bytes:
        saved = save_square_logo(logo_bytes, folder)
        if saved is not None:
            return saved
    return render_fallback_icon(folder, accent, _initials(name))


def generate_app(name: str, url: str, accent: str = "#7C5CFF") -> GeneratedApp:
    clean_url = url.strip()
    if not is_valid_http_url(clean_url):
        raise ValueError("Enter a valid http(s) game URL.")

    artwork = None
    logo_bytes = None
    try:
        artwork = fetch_page_artwork(clean_url)
        if artwork.logo_url:
            logo_bytes = fetch_logo_bytes(artwork.logo_url, clean_url)
    except Exception:
        artwork = None

    clean_name = " ".join(name.strip().split())
    if not clean_name:
        clean_name = artwork.title if artwork and artwork.title else ""
    if not clean_name:
        raise ValueError("Enter an app name, or use a Poki URL so the title can be detected.")

    folder = _unique_folder(generated_apps_dir(), slugify(clean_name))
    folder.mkdir(parents=True, exist_ok=True)

    script_path = folder / "app.py"
    write_wrapper_script(script_path, clean_name, clean_url)

    icon_path = _write_icon(folder, clean_name, accent, logo_bytes)
    play_url = (artwork.play_url if artwork else None) or clean_url
    exe_path = None
    try:
        exe_path = build_game_exe(clean_name, folder, icon_path, play_url, clean_url)
    except Exception:
        exe_path = None
    if exe_path is not None:
        shortcut = publish_desktop_exe(exe_path, clean_name)
    else:
        shortcut = create_desktop_shortcut(clean_name, script_path, icon_path)

    created = datetime.now(timezone.utc).isoformat()
    metadata = {
        "name": clean_name,
        "url": clean_url,
        "play_url": play_url,
        "slug": folder.name,
        "script": script_path.name,
        "exe": str(exe_path) if exe_path else None,
        "shortcut": str(shortcut) if shortcut else None,
        "created": created,
        "accent": accent,
        "logo_url": artwork.logo_url if artwork else None,
    }
    (folder / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    return GeneratedApp(
        slug=folder.name,
        name=clean_name,
        url=clean_url,
        folder=folder,
        script_path=script_path,
        shortcut_path=str(shortcut) if shortcut else None,
        created=created,
        accent=accent,
        exe_path=str(exe_path) if exe_path else None,
    )
