"""Create OS desktop shortcuts that launch generated wrappers."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from pokiwrap.paths import desktop_dir, python_executable


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _safe_shortcut_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    return cleaned or "Poki Game"


def create_desktop_shortcut(
    app_name: str,
    script_path: Path,
    icon_path: Path | None = None,
) -> Path | None:
    desktop = desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    python_exe = python_executable()

    if sys.platform == "win32":
        return _create_windows_lnk(desktop, app_name, python_exe, script_path, icon_path)
    if sys.platform == "darwin":
        return _create_macos_command(desktop, app_name, python_exe, script_path)
    return _create_linux_desktop(desktop, app_name, python_exe, script_path, icon_path)


def remove_shortcut(shortcut_path: str | None) -> None:
    if not shortcut_path:
        return
    path = Path(shortcut_path)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _create_windows_lnk(
    desktop: Path,
    app_name: str,
    python_exe: str,
    script_path: Path,
    icon_path: Path | None,
) -> Path:
    lnk = desktop / f"{_safe_shortcut_name(app_name)}.lnk"
    icon = str(icon_path) if icon_path and icon_path.exists() else ""
    command = (
        f"$s = New-Object -ComObject WScript.Shell; "
        f"$sc = $s.CreateShortcut({_ps_quote(str(lnk))}); "
        f"$sc.TargetPath = {_ps_quote(python_exe)}; "
        f"$sc.Arguments = {_ps_quote(f'\"{script_path}\"')}; "
        f"$sc.WorkingDirectory = {_ps_quote(str(script_path.parent))}; "
        f"$sc.WindowStyle = 1; "
        f"$sc.Description = {_ps_quote(f'PokiWrap — {app_name}')}; "
    )
    if icon:
        command += f"$sc.IconLocation = {_ps_quote(icon)}; "
    command += "$sc.Save();"
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )
    return lnk


def _create_macos_command(
    desktop: Path,
    app_name: str,
    python_exe: str,
    script_path: Path,
) -> Path:
    path = desktop / f"{_safe_shortcut_name(app_name)}.command"
    path.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                f'cd "{script_path.parent}"',
                f'exec "{python_exe}" "{script_path}"',
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    os.chmod(path, 0o755)
    return path


def _create_linux_desktop(
    desktop: Path,
    app_name: str,
    python_exe: str,
    script_path: Path,
    icon_path: Path | None,
) -> Path:
    path = desktop / f"{_safe_shortcut_name(app_name)}.desktop"
    icon = str(icon_path) if icon_path and icon_path.exists() else "applications-games"
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={app_name}",
                f'Exec="{python_exe}" "{script_path}"',
                f"Path={script_path.parent}",
                f"Icon={icon}",
                "Terminal=false",
                "Categories=Game;",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    os.chmod(path, 0o755)
    return path
