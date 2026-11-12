"""Read-only tour of what this token can actually fetch.

    python tools/explore_api.py

A system-user token's /me is the system user, not the Instagram account, so the
account id is resolved first and every call after that is addressed to it.
Nothing is written; a missing permission shows up as an error line.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("IG_TOKEN", "").strip()
FB = "https://graph.facebook.com/v23.0"
BUSINESS_ID = os.environ.get("IG_BUSINESS_ID", "1767727650988025").strip()


def call(label: str, path: str, **params):
    params = {k: v for k, v in params.items() if v is not None}
    params["access_token"] = TOKEN
    url = f"{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            raw = r.read().decode("utf-8", "replace")
            print(f"\n{label} [200]\n{raw[:700]}")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
    except urllib.error.HTTPError as e:
        print(f"\n{label} [{e.code}]\n{e.read().decode('utf-8', 'replace')[:300]}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"\n{label} [fail] {e!r}")
        return None


def resolve() -> str:
    for path in (f"/{BUSINESS_ID}/instagram_accounts", "/me/accounts", "/me/assigned_instagram_accounts"):
        data = call(f"resolve {path}", FB + path, fields="id,username")
        for row in (data or {}).get("data", []):
            ig = row.get("instagram_business_account") or row
            if ig.get("id"):
                return ig["id"]
    return os.environ.get("IG_USER_ID", "").strip()


if not TOKEN:
    raise SystemExit("IG_TOKEN missing")

ig = resolve()
print(f"\n>>> instagram account id: {ig or 'not found'}")
if not ig:
    raise SystemExit("no account id")

call("1 profile", f"{FB}/{ig}",
     fields="id,username,name,followers_count,follows_count,media_count,website,profile_picture_url")

media = call("2 media + engagement", f"{FB}/{ig}/media",
             fields="id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
             limit=3)
first = media["data"][0]["id"] if media and media.get("data") else ""

call("3 account insights", f"{FB}/{ig}/insights", metric="reach,profile_views,website_clicks", period="day")
call("4 audience demographics", f"{FB}/{ig}/insights",
     metric="audience_city,audience_country,audience_gender_age", period="lifetime")
call("5 stories", f"{FB}/{ig}/stories", fields="id,media_type,permalink,timestamp")
call("6 tags", f"{FB}/{ig}/tags", fields="id,caption,permalink", limit=3)
call("7 publishing quota", f"{FB}/{ig}/content_publishing_limit", fields="config,quota_usage")
if first:
    call("8 comments on newest", f"{FB}/{first}/comments",
         fields="id,text,username,timestamp,like_count", limit=5)
    call("9 media insights", f"{FB}/{first}/insights", metric="impressions,reach,saved,engagement")

tags = call("10 hashtag search: sketch", f"{FB}/ig_hashtag_search", user_id=ig, q="sketch")
if tags and tags.get("data"):
    hashed = tags["data"][0]["id"]
    call("11 hashtag recent media", f"{FB}/{hashed}/recent_media",
         user_id=ig, fields="id,caption,like_count,comments_count,permalink", limit=3)

call("12 business discovery", f"{FB}/{ig}",
     fields="business_discovery.username(instagram){username,followers_count,media_count}")
