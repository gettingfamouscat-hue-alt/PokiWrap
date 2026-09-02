"""Filesystem locations used by the generator and dashboard."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_root() -> Path:
    """Folder containing PokiWrap.exe, or the source project."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """Stable project folder — never the PyInstaller unpack directory."""
    if not is_frozen():
        return Path(__file__).resolve().parent.parent

    exe_dir = install_root()
    known = Path.home() / "Desktop" / "PokiWrap"
    candidates = [
        exe_dir,
        exe_dir / "PokiWrap",
        known,
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if (candidate / "generated_apps").is_dir() or (candidate / "main.py").exists():
            return candidate
    if known.exists():
        return known
    return exe_dir


def generated_apps_dir() -> Path:
    path = project_root() / "generated_apps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generated_app_roots() -> list[Path]:
    """All folders that may contain generated games (frozen exe + project)."""
    seen: set[Path] = set()
    roots: list[Path] = []
    candidates = [
        generated_apps_dir(),
        Path.home() / "Desktop" / "PokiWrap" / "generated_apps",
        app_data_dir() / "generated_apps",
        install_root() / "generated_apps",
        install_root() / "PokiWrap" / "generated_apps",
    ]
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_dir():
            roots.append(path)
    return roots


def assets_dir() -> Path:
    if is_frozen():
        meipass = Path(getattr(sys, "_MEIPASS", install_root()))
        bundled = meipass / "assets"
        if bundled.exists():
            return bundled
    path = project_root() / "assets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def desktop_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / "Desktop"
    if sys.platform == "darwin":
        return Path.home() / "Desktop"
    xdg = Path.home() / "Desktop"
    xdg.mkdir(parents=True, exist_ok=True)
    return xdg


def app_data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    path = root / "PokiWrap"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir() -> Path:
    path = app_data_dir() / "runtime" if is_frozen() else project_root() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def account_profile_dir() -> Path:
    path = app_data_dir() / "account_webview"
    path.mkdir(parents=True, exist_ok=True)
    return path


def account_state_path() -> Path:
    return app_data_dir() / "account.json"


def account_cookies_path() -> Path:
    return app_data_dir() / "poki_cookies.txt"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def adblock_domains_path() -> Path:
    return app_data_dir() / "adblock_domains.txt"


def python_executable() -> str:
    """Prefer a windowed interpreter on Windows so wrappers skip the console."""
    exe = Path(sys.executable)
    if sys.platform == "win32":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(exe)
