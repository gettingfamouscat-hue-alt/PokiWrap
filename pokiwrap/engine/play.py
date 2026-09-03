"""Launch a generated game inside the frozen PokiWrap app (macOS)."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def configure_webengine_env() -> None:
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    extra = (
        "--no-sandbox --disable-gpu-sandbox --autoplay-policy=no-user-gesture-required "
        "--ignore-gpu-blocklist --enable-webgl"
    )
    current = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{current} {extra}".strip()
    if sys.platform == "darwin":
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
    if not getattr(sys, "frozen", False):
        return
    exe = Path(sys.executable).resolve()
    roots = [Path(getattr(sys, "_MEIPASS", exe.parent)), exe.parent]
    for parent in exe.parents:
        roots.append(parent)
        if parent.name.endswith(".app"):
            break
    names = (
        Path("QtWebEngineProcess"),
        Path("Helpers") / "QtWebEngineProcess.app" / "Contents" / "MacOS" / "QtWebEngineProcess",
        Path("QtWebEngineCore.framework") / "Helpers" / "QtWebEngineProcess.app" / "Contents" / "MacOS" / "QtWebEngineProcess",
        Path("PyQt6") / "Qt6" / "lib" / "QtWebEngineCore.framework" / "Helpers" / "QtWebEngineProcess.app" / "Contents" / "MacOS" / "QtWebEngineProcess",
    )
    for root in roots:
        for name in names:
            path = root / name
            if path.is_file():
                os.environ["QTWEBENGINEPROCESS_PATH"] = str(path)
                return
        helper = root / "Frameworks" / "QtWebEngineCore.framework" / "Helpers" / "QtWebEngineProcess.app" / "Contents" / "MacOS" / "QtWebEngineProcess"
        if helper.is_file():
            os.environ["QTWEBENGINEPROCESS_PATH"] = str(helper)
            return


def play_target_from_argv(argv: list[str]) -> Path | None:
    args = [item for item in argv[1:] if not item.startswith("-psn")]
    if not args:
        return None
    if args[0] == "--play" and len(args) >= 2:
        folder = Path(args[1]).expanduser()
        return folder if folder.exists() else None
    candidate = Path(args[0]).expanduser()
    if candidate.is_file() and candidate.name == "app.py":
        return candidate.parent
    if candidate.is_dir() and (candidate / "app.py").exists():
        return candidate
    return None


def play_game(folder: Path) -> int:
    script = folder / "app.py"
    if not script.exists():
        raise FileNotFoundError(f"No game wrapper in {folder}")
    configure_webengine_env()
    os.chdir(folder)
    sys.argv = [str(script)]
    runpy.run_path(str(script), run_name="__main__")
    return 0
