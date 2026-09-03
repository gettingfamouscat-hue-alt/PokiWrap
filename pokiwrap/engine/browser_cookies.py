"""Copy Poki/Google session cookies from installed Chrome, Edge, or Brave."""

from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from hashlib import pbkdf2_hmac
from pathlib import Path

from pokiwrap.paths import account_cookies_path

HOST_MARKERS = (
    "poki.com",
    "poki.io",
    "poki-cdn.com",
    "poki-gdn.com",
    "poki-user-content.com",
    "accounts.google.com",
    ".google.com",
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "firebase",
    "identitytoolkit",
    "appleid.apple.com",
    "login.live.com",
    "login.microsoftonline.com",
    "live.com",
)

HOST_DENY = (
    "ads.poki.com",
    "doubleclick.",
    "googlesyndication",
    "googleadservices",
    "googletagmanager",
    "google-analytics",
)


@dataclass
class CookieRecord:
    name: str
    host: str
    path: str
    value: str
    http_only: bool
    secure: bool
    expires: float
    session: bool


def _wanted_host(host: str) -> bool:
    text = (host or "").lower()
    if not text:
        return False
    if any(token in text for token in HOST_DENY):
        return False
    return any(token in text for token in HOST_MARKERS)


def _browser_roots() -> list[tuple[Path, tuple[str, str] | None]]:
    if sys.platform == "darwin":
        support = Path.home() / "Library" / "Application Support"
        return [
            (support / "Google" / "Chrome", ("Chrome Safe Storage", "Chrome")),
            (support / "Google" / "Chrome", ("Chrome Safe Storage", None)),
            (support / "Google" / "Chrome Beta", ("Chrome Safe Storage", "Chrome")),
            (support / "Microsoft Edge", ("Microsoft Edge Safe Storage", "Microsoft Edge")),
            (support / "Microsoft Edge", ("Microsoft Edge Safe Storage", None)),
            (support / "BraveSoftware" / "Brave-Browser", ("Brave Safe Storage", "Brave")),
            (support / "Chromium", ("Chromium Safe Storage", "Chromium")),
        ]
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return [
        (local / "Google" / "Chrome" / "User Data", None),
        (local / "Microsoft" / "Edge" / "User Data", None),
        (local / "BraveSoftware" / "Brave-Browser" / "User Data", None),
        (local / "Chromium" / "User Data", None),
    ]


def _profile_dirs(root: Path) -> list[Path]:
    names = ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4"]
    found = [root / name for name in names if (root / name).is_dir()]
    return found or ([root] if root.is_dir() else [])


def _cookie_db(profile: Path) -> Path | None:
    for relative in (Path("Network") / "Cookies", Path("Cookies")):
        path = profile / relative
        if path.exists():
            return path
    return None


def _copy_db(src: Path) -> Path | None:
    tmp = Path(tempfile.mkdtemp(prefix="pokiwrap-cookies-"))
    dest = tmp / "Cookies"
    try:
        shutil.copy2(src, dest)
        for suffix in ("-wal", "-shm"):
            extra = Path(str(src) + suffix)
            if extra.exists():
                shutil.copy2(extra, tmp / extra.name)
        return dest
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
        return None


def _dpapi_decrypt(blob: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(blob, len(blob))
    blob_in = DATA_BLOB(len(blob), buffer)
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ) == 0:
        raise OSError("DPAPI decrypt failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _windows_master_key(root: Path) -> bytes | None:
    state = root / "Local State"
    if not state.exists():
        return None
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
        encrypted = base64.b64decode(payload["os_crypt"]["encrypted_key"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None
    if encrypted.startswith(b"DPAPI"):
        encrypted = encrypted[5:]
    elif encrypted.startswith(b"APPB"):
        return None
    try:
        return _dpapi_decrypt(encrypted)
    except OSError:
        return None


def _mac_master_key(service: str, account: str | None) -> bytes | None:
    commands = []
    if account:
        commands.append(["security", "find-generic-password", "-w", "-s", service, "-a", account])
    commands.append(["security", "find-generic-password", "-w", "-s", service])
    for command in commands:
        try:
            raw = subprocess.check_output(command, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            continue
        password = raw.decode("utf-8", "replace").strip("\r\n")
        if password:
            return pbkdf2_hmac("sha1", password.encode("utf-8"), b"saltysalt", 1003, 16)
    return None


def _decrypt_value(raw: bytes, key: bytes | None) -> str:
    if not raw:
        return ""
    if raw.startswith((b"v10", b"v11")) and key:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            return AESGCM(key).decrypt(raw[3:15], raw[15:], None).decode("utf-8", "replace")
        except Exception:
            pass
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.padding import PKCS7

            cipher = Cipher(algorithms.AES(key), modes.CBC(b" " * 16))
            decryptor = cipher.decryptor()
            padded = decryptor.update(raw[3:]) + decryptor.finalize()
            unpadder = PKCS7(128).unpadder()
            return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8", "replace")
        except Exception:
            return ""
    if raw.startswith(b"v20"):
        return ""
    if sys.platform == "win32":
        try:
            return _dpapi_decrypt(raw).decode("utf-8", "replace")
        except Exception:
            pass
    try:
        return raw.decode("utf-8", "replace")
    except Exception:
        return ""


def _chrome_expiry_to_unix(value: int) -> float:
    if not value or value < 1:
        return 0
    return max(0.0, value / 1_000_000 - 11_644_473_600)


def _read_profile(root: Path, profile: Path, key: bytes | None) -> dict[str, str]:
    db_path = _cookie_db(profile)
    if db_path is None:
        return {}
    copied = _copy_db(db_path)
    if copied is None:
        return {}
    seen: dict[str, str] = {}
    try:
        connection = sqlite3.connect(str(copied))
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT host_key, name, value, encrypted_value, path, is_secure, "
                "is_httponly, expires_utc FROM cookies"
            )
            for row in rows:
                host = str(row["host_key"] or "")
                name = str(row["name"] or "")
                if not name or not _wanted_host(host):
                    continue
                value = str(row["value"] or "")
                if not value:
                    encrypted = row["encrypted_value"] or b""
                    if not isinstance(encrypted, (bytes, bytearray)):
                        encrypted = bytes(encrypted)
                    value = _decrypt_value(bytes(encrypted), key)
                if not value:
                    continue
                path = str(row["path"] or "/") or "/"
                secure = "1" if int(row["is_secure"] or 0) else "0"
                http_only = "1" if int(row["is_httponly"] or 0) else "0"
                expires = _chrome_expiry_to_unix(int(row["expires_utc"] or 0))
                session = "1" if expires <= 0 else "0"
                encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
                line_key = f"{name}\n{host}\n{path}"
                seen[line_key] = (
                    f"{name}\t{host}\t{path}\t{http_only}\t{secure}\t{session}\t"
                    f"{expires}\t{encoded}\r\n"
                )
        except sqlite3.Error:
            return {}
        finally:
            connection.close()
    finally:
        try:
            shutil.rmtree(copied.parent, ignore_errors=True)
        except OSError:
            pass
    return seen


def parse_cookie_file(path: Path | None = None) -> list[CookieRecord]:
    file_path = path or account_cookies_path()
    if not file_path.exists():
        return []
    records: list[CookieRecord] = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        try:
            value = base64.b64decode(parts[7]).decode("utf-8", "replace")
        except Exception:
            value = parts[7]
        records.append(
            CookieRecord(
                name=parts[0],
                host=parts[1],
                path=parts[2] or "/",
                value=value,
                http_only=parts[3] == "1",
                secure=parts[4] == "1",
                expires=float(parts[6] or 0),
                session=parts[5] == "1",
            )
        )
    return records


def session_hosts(records: list[CookieRecord] | None = None) -> tuple[int, int]:
    items = records if records is not None else parse_cookie_file()
    poki = sum(1 for item in items if "poki" in item.host.lower())
    google = sum(1 for item in items if "google" in item.host.lower())
    return poki, google


def chrome_profile_exists() -> bool:
    for root, _keychain in _browser_roots():
        if (root / "Default").is_dir() or (root / "Local State").exists():
            return True
    return False


def export_browser_cookies() -> int:
    if sys.platform not in {"win32", "darwin"}:
        return 0
    collected: dict[str, str] = {}
    for root, keychain in _browser_roots():
        if not root.is_dir():
            continue
        if sys.platform == "darwin" and keychain:
            key = _mac_master_key(keychain[0], keychain[1])
        elif sys.platform == "win32":
            key = _windows_master_key(root)
        else:
            key = None
        for profile in _profile_dirs(root):
            collected.update(_read_profile(root, profile, key))
    path = account_cookies_path()
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8", errors="replace")
            for line in existing.splitlines():
                parts = line.split("\t")
                if len(parts) >= 3:
                    collected.setdefault(f"{parts[0]}\n{parts[1]}\n{parts[2]}", line.rstrip("\r") + "\r\n")
        except OSError:
            pass
    if not collected:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(collected.values()), encoding="utf-8")
    return len(collected)
