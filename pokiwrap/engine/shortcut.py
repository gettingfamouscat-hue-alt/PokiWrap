"""Create OS desktop shortcuts that launch generated wrappers."""

from __future__ import annotations

import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path

from pokiwrap.paths import desktop_dir, is_frozen, python_executable


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
        return _create_macos_game_app(desktop, app_name, script_path, icon_path)
    return _create_linux_desktop(desktop, app_name, python_exe, script_path, icon_path)


def remove_shortcut(shortcut_path: str | None) -> None:
    if not shortcut_path:
        return
    path = Path(shortcut_path)
    try:
        if path.exists():
            if path.is_dir():
                import shutil

                shutil.rmtree(path, ignore_errors=True)
            else:
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


def _png_to_icns(png: Path, icns: Path) -> None:
    from PIL import Image

    image = Image.open(png)
    image.save(icns, format="ICNS")


def _create_macos_game_app(
    desktop: Path,
    app_name: str,
    script_path: Path,
    icon_path: Path | None,
) -> Path:
    safe = _safe_shortcut_name(app_name)
    bundle = desktop / f"{safe}.app"
    if bundle.exists():
        import shutil

        shutil.rmtree(bundle)
    macos_dir = bundle / "Contents" / "MacOS"
    resources = bundle / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources.mkdir(parents=True)
    game_dir = script_path.parent
    if is_frozen():
        binary = sys.executable
        script = (
            "#!/bin/bash\n"
            f'DIR="{game_dir}"\n'
            f'BIN="{binary}"\n'
            'xattr -cr "$DIR" 2>/dev/null || true\n'
            'exec "$BIN" --play "$DIR"\n'
        )
    else:
        python_exe = python_executable()
        script = (
            "#!/bin/bash\n"
            f'cd "{game_dir}"\n'
            f'exec "{python_exe}" "{script_path}"\n'
        )
    launcher = macos_dir / "launcher"
    launcher.write_text(script, encoding="utf-8", newline="\n")
    os.chmod(launcher, 0o755)
    png = None
    if icon_path and icon_path.exists():
        png = icon_path if icon_path.suffix.lower() == ".png" else icon_path.with_suffix(".png")
        if not png.exists() and icon_path.suffix.lower() != ".png":
            png = script_path.parent / "icon.png"
    else:
        png = script_path.parent / "icon.png"
    icns = resources / "app.icns"
    if png and png.exists():
        try:
            _png_to_icns(png, icns)
        except Exception:
            pass
    slug = re.sub(r"[^a-z0-9]+", "-", app_name.lower()).strip("-") or "game"
    info = {
        "CFBundleName": app_name,
        "CFBundleDisplayName": app_name,
        "CFBundleIdentifier": f"app.pokiwrap.game.{slug}",
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        "CFBundleExecutable": "launcher",
        "CFBundlePackageType": "APPL",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    }
    if icns.exists():
        info["CFBundleIconFile"] = "app"
    with (bundle / "Contents" / "Info.plist").open("wb") as handle:
        plistlib.dump(info, handle)
    subprocess.run(["xattr", "-cr", str(bundle)], check=False)
    return bundle


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
