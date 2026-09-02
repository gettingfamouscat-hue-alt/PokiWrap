"""Download Microsoft Edge WebView2 assemblies used by native game .exes."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from pokiwrap.paths import runtime_dir

NUGET_URL = "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/1.0.2903.40"

NEEDED = (
    "Microsoft.Web.WebView2.Core.dll",
    "Microsoft.Web.WebView2.WinForms.dll",
    "WebView2Loader.dll",
)


def webview2_dir() -> Path:
    path = runtime_dir() / "webview2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def webview2_ready() -> bool:
    folder = webview2_dir()
    return all((folder / name).exists() for name in NEEDED)


def ensure_webview2() -> Path:
    folder = webview2_dir()
    if webview2_ready():
        return folder

    from pokiwrap.paths import is_frozen, project_root

    if is_frozen():
        bundled = project_root() / "runtime" / "webview2"
        if bundled.exists():
            folder.mkdir(parents=True, exist_ok=True)
            for name in NEEDED:
                src = bundled / name
                dest = folder / name
                if src.exists() and not dest.exists():
                    dest.write_bytes(src.read_bytes())
            if webview2_ready():
                return folder

    request = Request(
        NUGET_URL,
        headers={"User-Agent": "PokiWrap/1.0", "Accept": "*/*"},
    )
    with urlopen(request, timeout=60) as response:
        payload = BytesIO(response.read())

    with zipfile.ZipFile(payload) as archive:
        mapping = {
            "lib/net462/Microsoft.Web.WebView2.Core.dll": "Microsoft.Web.WebView2.Core.dll",
            "lib/net462/Microsoft.Web.WebView2.WinForms.dll": "Microsoft.Web.WebView2.WinForms.dll",
            "runtimes/win-x64/native/WebView2Loader.dll": "WebView2Loader.dll",
        }
        for inner, dest_name in mapping.items():
            try:
                data = archive.read(inner)
            except KeyError:
                continue
            (folder / dest_name).write_bytes(data)

    if not webview2_ready():
        raise RuntimeError("Could not install Microsoft Edge WebView2 libraries.")
    return folder
