#!/usr/bin/env python3
"""PokiWrap — custom Web App Wrapper Generator for Poki games."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from pathlib import Path


def _launch_log_path() -> Path:
    if sys.platform == "darwin":
        folder = Path.home() / "Library" / "Logs" / "PokiWrap"
    elif sys.platform == "win32":
        folder = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "PokiWrap"
    else:
        folder = Path.home() / ".local" / "share" / "PokiWrap"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "launch.log"


def _install_logging() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    path = _launch_log_path()
    handle = path.open("w", encoding="utf-8")
    sys.stdout = handle
    sys.stderr = handle
    return path


def _report_crash(exc: BaseException) -> None:
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    try:
        sys.stderr.flush()
    except Exception:
        pass
    if sys.platform == "darwin":
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display dialog "PokiWrap failed to open. Details: ~/Library/Logs/PokiWrap/launch.log" with title "PokiWrap" buttons {"OK"} default button 1',
                ],
                check=False,
            )
        except Exception:
            pass


if __name__ == "__main__":
    _install_logging()
    try:
        try:
            import certifi

            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        except Exception:
            pass
        from pokiwrap.engine.play import play_game, play_target_from_argv

        target = play_target_from_argv(sys.argv)
        if target is not None:
            raise SystemExit(play_game(target))
        from pokiwrap.app import run

        raise SystemExit(run())
    except Exception as exc:
        _report_crash(exc)
        raise SystemExit(1)
