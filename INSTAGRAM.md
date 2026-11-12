# Instagram → pictures page

Every six hours a GitHub Action asks Instagram for the newest media on
@paid4winrar, downloads anything new into `Assets/ig/`, and rebuilds the pages.
Pictures land at the top of `pictures.html` and the first six also sit on the
home page. Each one links back to the post on Instagram.

Nothing is pushed anywhere else, and no third-party script, widget or cookie
touches the site. GitHub copies the files once; visitors only ever load your own
domain.

## What only you can do

Four things, about ten minutes, all inside Meta and GitHub. The token never goes
in chat and never goes in the repo.

### 1. Make the account a Creator account

Instagram app → Settings → **Account type and tools** → Switch to professional
account → Creator. Free, and Meta's read API only serves Business and Creator
accounts. The old personal-account API was switched off in December 2024.

### 2. Create the Meta app

developer.facebook.com → My Apps → Create app. Pick **Other**, then add the
**Instagram** use case (Meta calls it "Instagram API"). No Facebook Page is needed.

### 3. Get a token

Newer apps get **API setup with Unified login**, not "with Instagram login",
which Meta no longer offers to new apps. In the App Dashboard:

1. **Use cases → Instagram API → API setup with Unified login.**
2. A **business portfolio** is mandatory here. Create or link one, then reload
   the page (a one-time thing, done for this app already).
3. **1. Configure your app** → **Create new configuration** → keep the template
   ("Instagram API (Unified Login)") → **Create from template**. The token becomes
   a system-user token that **never expires**.
4. Section 2 → **Add account**, or add the account by hand: **App roles → Roles →
   Instagram testers → Add people** with the username, then accept the invite in
   the Instagram app (Settings → Website permissions → Apps and websites).
5. **Generate token** next to the account. That string is `IG_TOKEN`.

### 4. Put it in the repo secrets

GitHub → the repo → Settings → Secrets and variables → Actions → New repository
secret, name it exactly **IG_TOKEN**, paste the token.

A system-user token never expires, so there is nothing to refresh and
`GH_SECRETS_PAT` is not needed. The script calls the refresh endpoint anyway,
gets an error, prints "token refresh skipped" and carries on with the token.

Then: Actions → **instagram sync** → Run workflow. First run puts everything up.

## Where a post lands

`tools/instagram_medium.json` decides that, and it is the only file to edit:

```json
{
  "sketch": ["17924915496205795", "17925620208428310"],
  "digital": ["18013443776989984"]
}
```

Sketch means paper: pencil, ballpoint, ink, photographed notebook pages. Those go
to `sketch.html`. Digital goes to `pictures.html`. A post that is in neither list
is treated as a sketch, since that is most of the account.

Every mirrored post is in there already. To move one, move its id between the two
lists and rerun `py tools/build_pages.py`.

## What the sync does

`tools/sync_instagram.py`:

1. reads `IG_TOKEN`
2. refreshes it against Meta (resets the 60 day clock)
3. pulls `/me/media` with paging, up to 200 posts
4. downloads each picture once, keyed by Instagram's media id, into `Assets/ig/`
5. writes `tools/instagram.json`
6. reruns `tools/build_pages.py`
7. stores the refreshed token back in the secret, if you gave it a PAT

Instagram's image URLs are signed and expire within days, which is why the files
are copied into the repo instead of hot-linked.

Carousels use their first image. Reels and videos use their poster frame, with a
short "video" note saved in the JSON. Posts that scroll out of the API window
stay on the site, because the JSON keeps them.

`build_pages.py` reads `tools/instagram.json` if it is there and puts those
tiles first. Delete the file and the site goes back to the four hand-added
pictures.

## Running it by hand

```bash
IG_TOKEN=... py tools/sync_instagram.py      # sync now
py tools/sync_instagram.py --fixture x.json  # offline test, no token needed
```

## Two things that will bite eventually

- **GitHub disables scheduled workflows** in a public repo after 60 days with no
  repository activity. Quiet months on Instagram means no commits, which means
  the schedule can switch itself off. Re-enable it from the Actions tab, or push
  anything at all.
- **Meta can change terms.** If the workflow starts failing with `HTTP 400` on
  `/me/media`, check the app is still in live mode and the token still has
  `instagram_business_basic`.
