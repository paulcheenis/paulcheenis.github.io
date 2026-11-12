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
**Instagram** product and choose **Instagram API with Instagram login**. No
Facebook Page is needed.

### 3. Get a long-lived token

In the app dashboard, under Instagram → API setup with Instagram login:

1. Add @paid4winrar to **Instagram testers** (App roles).
2. Accept the tester invite in the Instagram app: Settings → Website permissions →
   Apps and websites.
3. Generate an access token. That one lasts an hour, so exchange it for a
   long-lived one on your own machine:

```bash
curl "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=APP_SECRET&access_token=SHORT_LIVED_TOKEN"
```

The reply has `access_token` and `expires_in`: 5184000 seconds, 60 days.

### 4. Put it in the repo secrets

GitHub → the repo → Settings → Secrets and variables → Actions → New repository
secret, name it exactly **IG_TOKEN**, paste the long-lived token.

Optionally add a second secret, **GH_SECRETS_PAT**: a fine-grained personal
access token for this repository with *Secrets: read and write*. With it, each
run refreshes the Instagram token and stores the new one, so the 60 days never
run out. Without it, you re-do step 3 every couple of months.

Then: Actions → **instagram sync** → Run workflow. First run puts everything up.

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
