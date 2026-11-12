"""Read-only tour of what this token can actually fetch.

    python tools/explore_api.py

Nothing is written. Every call prints its status and a trimmed body, so a
permission that is missing shows up as an error message instead of a crash.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("IG_TOKEN", "").strip()
FB = "https://graph.facebook.com/v23.0"
BUSINESS_ID = os.environ.get("IG_BUSINESS_ID", "1767727650988025").strip()


def call(label: str, path: str, **params) -> dict | None:
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
        body = e.read().decode("utf-8", "replace")
        print(f"\n{label} [{e.code}]\n{body[:400]}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"\n{label} [fail] {e!r}")
        return None


if not TOKEN:
    raise SystemExit("IG_TOKEN missing")

me = call("1 profile", f"{FB}/me",
          fields="id,username,name,biography,followers_count,follows_count,media_count,website,profile_picture_url")
account = (me or {}).get("id", "")

media = call("2 media + engagement fields", f"{FB}/me/media",
             fields="id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
             limit=3)
first_media = ""
if media and media.get("data"):
    first_media = media["data"][0]["id"]

call("3 account insights (day)", f"{FB}/me/insights", metric="reach,profile_views,website_clicks", period="day")
call("4 audience demographics", f"{FB}/me/insights", metric="audience_city,audience_country,audience_gender_age", period="lifetime")
call("5 stories", f"{FB}/me/stories", fields="id,media_type,permalink,timestamp")
call("6 tags", f"{FB}/me/tags", fields="id,caption,permalink", limit=3)
call("7 publishing quota", f"{FB}/me/content_publishing_limit", fields="config,quota_usage")
call("8 comments on newest post", f"{FB}/{first_media}/comments",
     fields="id,text,username,timestamp,like_count", limit=5) if first_media else None
call("9 media insights", f"{FB}/{first_media}/insights",
     metric="impressions,reach,saved,engagement") if first_media else None

if account:
    tags = call("10 hashtag search: sketch", f"{FB}/ig_hashtag_search", user_id=account, q="sketch")
    if tags and tags.get("data"):
        hashtag = tags["data"][0]["id"]
        call("11 hashtag top media", f"{FB}/{hashtag}/top_media",
             user_id=account, fields="id,caption,like_count,comments_count,permalink", limit=3)
    call("12 business discovery: another account", f"{FB}/{account}",
         fields="business_discovery.username(instagram){username,followers_count,media_count}")

call("13 portfolio assets", f"{FB}/{BUSINESS_ID}/owned_instagram_accounts", fields="id,username")
