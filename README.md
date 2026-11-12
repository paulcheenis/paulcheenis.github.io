# paulcheenis.github.io

My personal site: comics, sketches and random pictures. Static HTML on GitHub
Pages, served at **paidforwinrar.com** (see `CNAME`).

```
index.html        home — hero, newest comic, a few recent ones, picture strip
comics.html       all comics, newest first, click to zoom
pictures.html     everything that isn't a comic
sketch.html       sketches and gifs
about.html        the usual
suggestions.html  suggestion box (a plain GET form → thankyou.html)
projects.html     still empty, on purpose
404.html          shown for unknown URLs by GitHub Pages
style.css         one stylesheet, light + dark from prefers-color-scheme
script.js         lightbox (arrow keys, Esc) — the only JavaScript on the site
Assets/           every image, unchanged file names
tools/build_pages.py  regenerates the HTML from the lists at the top
tools/sync_instagram.py  mirrors the newest instagram posts (see INSTAGRAM.md)
.github/workflows/instagram-sync.yml  runs that every six hours
```

No framework, no build step at serve time, no cookies, no tracking.

## Instagram

Pictures posted to [@paid4winrar](https://www.instagram.com/paid4winrar/) copy
themselves onto the site every six hours: pencil and ink pages onto `sketch.html`,
digital work onto `pictures.html`. `INSTAGRAM.md` has the setup and the one file
that decides which page a post goes to.

## Adding a comic

1. Drop the image in `Assets/` (e.g. `12152026.png`).
2. Open `tools/build_pages.py` and add a row at the **top** of `COMICS`:

   ```python
   ("comic14", "12/15/2026", "12152026.png", "your-title.png", "", 600, 600),
   ```
   The tuple is `(anchor, date, image, title card, note, width, height)`. Keeping
   the anchor means old links like `comics.html#comic14` still land somewhere.
   `note` is optional and renders in handwriting under the card.
3. `py tools/build_pages.py`

## Adding a picture

Same file, the `PICTURES` list — `(file, title, caption, shape)` — then re-run the
script. Tiles letterbox images rather than crop them, so mixed aspect ratios
(600×250 wordmarks next to 2000×2000 comics) all look deliberate.

## Previewing locally

```bash
py -m http.server 8800
# then open http://127.0.0.1:8800/
```

## Backup

The pre-makeover site is archived two ways: a zip outside the repo
(`..\_backups\`), and a git tag.

```bash
git tag -l "backup/*"
git checkout backup/pre-makeover-2026-11-07_1703
```

## Deploying

Push to `main`. GitHub Pages publishes the repo root and `CNAME` points it at
`paidforwinrar.com`. The old paths (`sketch.html`, `projects.html`,
`thankyou.html`) were kept, so existing links still resolve.
