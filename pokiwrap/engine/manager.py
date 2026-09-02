"""Scan, launch, and delete generated wrappers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from pokiwrap.engine.generator import GeneratedApp
from pokiwrap.engine.shortcut import remove_shortcut
from pokiwrap.paths import desktop_dir, generated_app_roots, python_executable


def _load_app(folder: Path) -> GeneratedApp | None:
    meta_path = folder / "metadata.json"
    script_path = folder / "app.py"
    exe_files = list(folder.glob("*.exe"))
    if not meta_path.exists() and not script_path.exists() and not exe_files:
        return None

    name = folder.name.replace("_", " ").title()
    url = ""
    shortcut = None
    created = ""
    accent = "#7C5CFF"
    exe_path = None
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        name = data.get("name", name)
        url = data.get("url", "")
        shortcut = data.get("shortcut")
        created = data.get("created", "")
        accent = data.get("accent", accent)
        exe_path = data.get("exe")

    return GeneratedApp(
        slug=folder.name,
        name=name,
        url=url,
        folder=folder,
        script_path=script_path,
        shortcut_path=shortcut,
        created=created,
        accent=accent,
        exe_path=exe_path,
    )


def list_apps() -> list[GeneratedApp]:
    apps: list[GeneratedApp] = []
    seen: set[str] = set()
    folders: list[Path] = []
    for root in generated_app_roots():
        try:
            folders.extend(path for path in root.iterdir() if path.is_dir())
        except OSError:
            continue
    folders.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for folder in folders:
        key = folder.name.lower()
        if key in seen:
            continue
        app = _load_app(folder)
        if app:
            seen.add(key)
            apps.append(app)
    return apps


def launch_app(app: GeneratedApp) -> None:
    if sys.platform == "darwin":
        from pokiwrap.paths import is_frozen

        if is_frozen():
            args = [sys.executable, "--play", str(app.folder)]
        else:
            args = [python_executable(), str(app.script_path)]
        subprocess.Popen(
            args,
            cwd=str(app.folder),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        return
    target = app.executable
    if target.suffix.lower() != ".exe" or not target.exists():
        matches = list(app.folder.glob("*.exe"))
        if matches:
            target = matches[0]
    desktop_copy = desktop_dir() / f"{app.name}.exe"
    if (target.suffix.lower() != ".exe" or not target.exists()) and desktop_copy.exists():
        target = desktop_copy
    if not target.exists():
        raise FileNotFoundError(f"Could not find {app.name}.exe.")
    if target.suffix.lower() == ".exe":
        args = [str(target)]
    else:
        args = [python_executable(), str(target)]
    kwargs: dict = {
        "args": args,
        "cwd": str(app.folder),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(**kwargs)


def delete_app(app: GeneratedApp) -> None:
    remove_shortcut(app.shortcut_path)
    shutil.rmtree(app.folder, ignore_errors=True)
