"""uBlock-style network ad blocking lists for game and login WebViews."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from pokiwrap.paths import adblock_domains_path, settings_path

LIST_URLS = (
    "https://easylist.to/easylist/easylist.txt",
    "https://easylist.to/easylist/easyprivacy.txt",
)

SEED_DOMAINS = """
ads.poki.com
doubleclick.net
googleadservices.com
googlesyndication.com
googletagservices.com
googletagmanager.com
google-analytics.com
googleanalytics.com
adservice.google.com
pagead2.googlesyndication.com
tpc.googlesyndication.com
fundingchoicesmessages.google.com
imasdk.googleapis.com
2mdn.net
adsafeprotected.com
moatads.com
amazon-adsystem.com
adnxs.com
adsrvr.org
advertising.com
adform.net
adroll.com
adition.com
appnexus.com
casalemedia.com
contextweb.com
criteo.com
criteo.net
indexww.com
media.net
openx.net
outbrain.com
prebid.org
pubmatic.com
rubiconproject.com
scorecardresearch.com
smartadserver.com
spotxchange.com
taboola.com
yieldmo.com
bidswitch.net
bluekai.com
exelator.com
krxd.net
rlcdn.com
agkn.com
quantserve.com
hotjar.com
hotjar.io
facebook.net
connect.facebook.net
ads-twitter.com
analytics.twitter.com
ads.youtube.com
addthis.com
sharethrough.com
serving-sys.com
ay.delivery
onetag-sys.com
adtrafficquality.google
""".strip()

PROTECTED = {
    "poki.com",
    "www.poki.com",
    "a.poki.com",
    "games.poki.com",
    "game-cdn.poki.com",
    "poki-cdn.com",
    "img.poki-cdn.com",
    "poki-gdn.com",
    "poki.io",
    "t.poki.io",
    "geo.poki.io",
    "auds.poki.io",
    "api.poki.io",
    "poki-user-content.com",
    "user-vault.poki.com",
    "api.poki.com",
    "auth.poki.com",
    "account.poki.com",
    "accounts.poki.com",
    "google.com",
    "www.google.com",
    "googleapis.com",
    "identitytoolkit.googleapis.com",
    "securetoken.googleapis.com",
    "firebaseio.com",
    "firebaseapp.com",
    "firebase.com",
    "gstatic.com",
    "microsoft.com",
    "live.com",
    "apple.com",
    "crazygames.com",
    "www.crazygames.com",
    "games.crazygames.com",
    "imgs.crazygames.com",
    "files.crazygames.com",
    "game-files.crazygames.com",
}

def _is_protected(host: str) -> bool:
    if host == "ads.poki.com" or host.endswith(".ads.poki.com"):
        return False
    if host == "ads.crazygames.com" or host.endswith(".ads.crazygames.com"):
        return False
    if host in PROTECTED:
        return True
    return any(host.endswith("." + allowed) for allowed in PROTECTED)


_HOST = re.compile(r"^\|\|([a-zA-Z0-9.-]+)(?:[\^/$?]|$)")


def adblock_enabled() -> bool:
    path = settings_path()
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return data.get("adblock", True) is not False


def set_adblock_enabled(enabled: bool) -> None:
    path = settings_path()
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    data["adblock"] = bool(enabled)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_filter_list(text: str) -> set[str]:
    domains: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("!") or line.startswith("[") or line.startswith("@@"):
            continue
        match = _HOST.match(line)
        if not match:
            continue
        host = match.group(1).lower().rstrip(".")
        if "*" in host or host.count(".") < 1 or _is_protected(host):
            continue
        domains.add(host)
    return domains


def _write_domains(domains: set[str]) -> Path:
    path = adblock_domains_path()
    lines = sorted(domains)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def ensure_adblock_list() -> Path:
    path = adblock_domains_path()
    seed = {line.strip() for line in SEED_DOMAINS.splitlines() if line.strip()}
    if path.exists():
        try:
            seed.update(
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            )
        except OSError:
            pass
    _write_domains({host for host in seed if host and not _is_protected(host)})
    return path


def update_adblock_list() -> Path:
    path = ensure_adblock_list()
    domains = {line.strip() for line in SEED_DOMAINS.splitlines() if line.strip()}
    try:
        existing = {
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        domains.update(existing)
    except OSError:
        pass
    for url in LIST_URLS:
        try:
            request = Request(url, headers={"User-Agent": "PokiWrap/1.0"})
            with urlopen(request, timeout=20) as response:
                text = response.read().decode("utf-8", "replace")
            domains.update(_parse_filter_list(text))
        except Exception:
            continue
    domains = {host for host in domains if host and not _is_protected(host)}
    _write_domains(domains)
    stamp = path.with_suffix(".updated")
    stamp.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return path
