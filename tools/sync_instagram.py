"""Copy the newest posts from Instagram into the site.

    py tools/sync_instagram.py                 # normal run (needs IG_TOKEN)
    py tools/sync_instagram.py --fixture x.json  # offline test, no token

What it does, in order:

1. takes the long-lived Instagram token from $IG_TOKEN (or .env)
2. refreshes it against Meta (a refresh resets the 60 day clock)
3. asks graph.instagram.com for the account's newest media
4. downloads the images it does not already have into Assets/ig/
5. rewrites tools/instagram.json
6. reruns tools/build_pages.py so pictures.html and index.html pick them up
7. when GH_SECRETS_PAT is set (GitHub Actions only) it stores the refreshed
   token back in the repo secret so the 60 day window never closes

Posts are keyed by Instagram's own media id, so a post that was already
downloaded is never fetched twice and older posts stay on the site even after
they scroll out of the API window.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "ig"
STORE = ROOT / "tools" / "instagram.json"
API = "https://graph.instagram.com/v23.0"
FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_url,media_type}"
MAX_PAGES = 4
UA = "paulcheenis-site-sync/1.0 (+https://paidforwinrar.com)"


# ------------------------------------------------------------------ plumbing
def die(msg: str) -> None:
    print("instagram sync:", msg, file=sys.stderr)
    raise SystemExit(1)


def http(url: str, *, headers: dict | None = None, data: bytes | None = None,
         method: str | None = None, tries: int = 3):
    """GET/PUT with a couple of retries on the errors that are worth retrying."""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("User-Agent", UA)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:400].decode("utf-8", "replace")
            last = f"HTTP {e.code} {url.split('?')[0]}: {body}"
            if e.code in (429, 500, 502, 503, 504) and attempt + 1 < tries:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"instagram sync: {last}")
        except urllib.error.URLError as e:
            last = f"{e.reason} for {url.split('?')[0]}"
            if attempt + 1 < tries:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"instagram sync: {last}")
    raise SystemExit(f"instagram sync: {last}")


def get_json(url: str, headers: dict | None = None) -> dict:
    return json.loads(http(url, headers=headers).decode("utf-8"))


def token_from_env() -> str:
    tok = os.environ.get("IG_TOKEN", "").strip()
    if tok:
        return tok
    env = ROOT.parent.parent / ".env"
    for candidate in (Path.home() / "AppData/Local/hermes/.env", env):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("IG_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


# ------------------------------------------------------------------ tokens
def refresh_token(token: str) -> tuple[str, int]:
    """Reset the 60 day clock. Returns (token, seconds left). Never fatal."""
    url = (f"https://graph.instagram.com/refresh_access_token"
           f"?grant_type=ig_refresh_token&access_token={urllib.parse.quote(token)}")
    try:
        r = json.loads(http(url, tries=2).decode("utf-8"))
    except (SystemExit, json.JSONDecodeError) as e:
        print(f"token refresh skipped ({e}); using the token as it is")
        return token, 0
    return r.get("access_token", token), int(r.get("expires_in", 0))


def store_secret(name: str, value: str) -> None:
    """Put a refreshed token back into the repo secrets, if we were given a PAT."""
    pat = os.environ.get("GH_SECRETS_PAT", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not pat or not repo:
        print("no GH_SECRETS_PAT, so the refreshed token is used once and not stored")
        return
    try:
        import base64
        from nacl import public  # type: ignore
    except ImportError:
        print("PyNaCl missing, cannot store the secret (pip install pynacl)")
        return
    hdrs = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}
    key = get_json(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", hdrs)
    sealed = public.SealedBox(public.PublicKey(base64.b64decode(key["key"])))
    body = json.dumps({
        "encrypted_value": base64.b64encode(sealed.encrypt(value.encode())).decode(),
        "key_id": key["key_id"],
    }).encode()
    http(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=hdrs,
         data=body, method="PUT", tries=2)
    print(f"stored a refreshed token in the {name} secret")


# ------------------------------------------------------------------ media
def fetch_media(base: str, target: str, token: str) -> list[dict]:
    out: list[dict] = []
    url = (f"{base}/{target}/media?fields={urllib.parse.quote(FIELDS)}"
           f"&limit=50&access_token={urllib.parse.quote(token)}")
    for _ in range(MAX_PAGES):
        page = get_json(url)
        out.extend(page.get("data", []))
        url = page.get("paging", {}).get("next", "")
        if not url:
            break
    return out


def try_get(url: str, token: str) -> tuple[int, str]:
    sep = "&" if "?" in url else "?"
    try:
        raw = http(f"{url}{sep}access_token={urllib.parse.quote(token)}", tries=1)
        return 200, raw.decode("utf-8", "replace")
    except SystemExit as e:
        return 0, str(e)


def resolve_target(token: str) -> tuple[str, str]:
    """Find the Graph host and the account id this token can read.

    A token minted by 'API setup with Unified login' is a Facebook system user
    token: graph.instagram.com will not parse it. Older Instagram-login tokens
    only work on graph.instagram.com. Try both, then look for the business
    account behind the system user.
    """
    base = "https://graph.facebook.com/v23.0"
    notes: list[str] = []

    for host in ("https://graph.instagram.com/v23.0", base):
        status, body = try_get(f"{host}/me?fields=id,username", token)
        if status == 200:
            data = json.loads(body)
            if data.get("username"):
                print(f"token reads {host} as @{data['username']}")
                return host, data["id"]
        notes.append(f"{host}/me -> {status} {body[:160]}")

    business_id = os.environ.get("IG_BUSINESS_ID", "1767727650988025").strip()
    for path in ("/me/accounts?fields=instagram_business_account{id,username}",
                 f"/{business_id}/instagram_accounts?fields=id,username",
                 "/me/assigned_instagram_accounts?fields=id,username"):
        status, body = try_get(base + path, token)
        notes.append(f"{base}{path} -> {status} {body[:160]}")
        if status != 200:
            continue
        data = json.loads(body).get("data", [])
        for row in data:
            ig = row.get("instagram_business_account") or row
            if ig.get("id"):
                print(f"token reads {base} as Instagram account {ig.get('username') or ig['id']}")
                return base, ig["id"]

    die("could not find an Instagram account with this token:\n  " + "\n  ".join(notes))
    raise SystemExit(1)


def pick_image(item: dict) -> tuple[str, str] | None:
    """(media_url, kind) for the picture that represents this post."""
    kind = item.get("media_type", "IMAGE")
    if kind == "CAROUSEL_ALBUM":
        for child in item.get("children", {}).get("data", []):
            if child.get("media_type") == "IMAGE" and child.get("media_url"):
                return child["media_url"], "image"
        kids = [c for c in item.get("children", {}).get("data", []) if c.get("media_url")]
        if kids:
            return kids[0]["media_url"], "image"
        return None
    if kind == "VIDEO":
        if item.get("thumbnail_url"):
            return item["thumbnail_url"], "video"
        return None
    if item.get("media_url"):
        return item["media_url"], "image"
    if item.get("thumbnail_url"):
        return item["thumbnail_url"], "video"
    return None


def image_size(data: bytes) -> tuple[int, int]:
    """Width and height without pulling in Pillow. (0, 0) when unknown."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:4] == b"GIF8":
            return struct.unpack("<HH", data[6:10])
        if data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except (struct.error, IndexError):
        pass
    return 0, 0


def ext_for(data: bytes, url: str) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"GIF8":
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    guess = urllib.parse.urlparse(url).path.rsplit(".", 1)[-1].lower()
    return guess if guess in ("jpg", "jpeg", "png", "webp", "gif") else "jpg"


def download(url: str) -> bytes:
    if url.startswith("file:"):
        raw = urllib.parse.unquote(url[len("file:///"):])
        if re.match(r"^[A-Za-z]:", raw):
            return Path(raw).read_bytes()
        return Path("/" + raw).read_bytes()
    return http(url)


def read_store() -> dict:
    if not STORE.exists():
        return {"updated": None, "posts": []}
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("instagram.json was not valid JSON, starting a fresh one")
        return {"updated": None, "posts": []}


def sync(items: list[dict], stored: dict, *, offline: bool = False) -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    known = {p["id"]: p for p in stored.get("posts", [])}
    new = 0
    for item in items:
        mid = item.get("id")
        if not mid or mid in known:
            continue
        chosen = pick_image(item)
        if not chosen:
            print(f"  {mid}: nothing to download, skipped")
            continue
        media_url, kind = chosen
        try:
            data = download(media_url) if offline else download(media_url)
        except SystemExit as e:
            print(f"  {mid}: download failed ({e}), skipped")
            continue
        ext = ext_for(data, media_url)
        name = f"{mid}.{ext}"
        (ASSETS / name).write_bytes(data)
        w, h = image_size(data)
        post = {
            "id": mid,
            "shortcode": item.get("shortcode")
            or (item.get("permalink", "").rstrip("/").rsplit("/", 1)[-1]),
            "permalink": item.get("permalink", ""),
            "caption": (item.get("caption") or "").strip(),
            "timestamp": item.get("timestamp", ""),
            "kind": kind,
            "file": f"ig/{name}",
            "width": w,
            "height": h,
        }
        known[mid] = post
        new += 1
        print(f"  {mid}: saved {name} ({w}x{h}, {kind})")

    posts = sorted(known.values(), key=lambda p: p.get("timestamp", ""), reverse=True)
    STORE.write_text(json.dumps({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "posts": posts}, indent=2) + "\n", encoding="utf-8")
    print(f"{new} new, {len(posts)} posts in tools/instagram.json")
    return new


def rebuild() -> None:
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_pages.py")],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"build_pages.py failed:\n{r.stdout}\n{r.stderr}")
    print(r.stdout.strip())


def main() -> None:
    offline = "--fixture" in sys.argv
    if offline:
        fixture = Path(sys.argv[sys.argv.index("--fixture") + 1])
        items = json.loads(fixture.read_text(encoding="utf-8"))
        print(f"offline run from {fixture.name}: {len(items)} items")
        sync(items, read_store(), offline=True)
        rebuild()
        return

    token = token_from_env()
    if not token:
        print("No IG_TOKEN set, so there is nothing to sync yet.\n"
              "INSTAGRAM.md has the four steps that create one; the site is untouched.")
        return

    base, target = resolve_target(token)

    if "graph.instagram.com" in base:
        token, seconds = refresh_token(token)
        if seconds:
            print(f"token refreshed, {seconds / 86400:.0f} days left on it")
    else:
        seconds = 0

    items = fetch_media(base, target, token)
    print(f"{len(items)} posts from Instagram")
    new = sync(items, read_store())
    rebuild()

    if new and seconds:
        try:
            store_secret("IG_TOKEN", token)
        except SystemExit as e:
            print(f"could not store the refreshed token: {e}")


if __name__ == "__main__":
    main()
