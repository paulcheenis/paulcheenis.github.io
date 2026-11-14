"""Generate the static pages for paulcheenis.github.io.

Everything written here is plain HTML with no build step at serve time — this
script only exists so adding a comic or a picture is a one-line edit instead of
a copy-paste job across seven files.

    py tools/build_pages.py

Add a comic: append to COMICS (newest first) with the image you dropped in
Assets/, then run the script again.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "paidforwinrar.com"

NAV = [
    ("index.html", "home"),
    ("comics.html", "comics"),
    ("pictures.html", "pictures"),
    ("sketch.html", "sketches"),
    ("about.html", "about"),
    ("suggestions.html", "suggestions"),
]

# (anchor, date shown, comic image, title image, note, width, height)
COMICS = [
    ("comic13", "12/03/2024", "12032024.png", "chatgpt.png", "", 2000, 2000),
    ("comic12", "11/26/2024", "11262024.png", "mustard.png", "", 600, 600),
    ("comic11", "11/22/2024", "11222024.png", "just a game 2.png", "", 600, 600),
    ("comic10", "11/21/2024", "11212024.png", "yawning.png", "", 600, 600),
    ("comic9", "11/15/2024", "11152024.png", "breakfast.png", "", 600, 600),
    ("comic8", "11/14/2024", "11142024.png", "cupid you fool.png", "", 600, 600),
    ("comic7", "11/13/2024", "11132024.png", "just a game.png", "", 600, 600),
    ("comic6", "11/12/2024", "11122024.png", "indirect fire.png",
     "read this one right to left", 600, 900),
    ("comic5", "11/11/2024", "11112024.png", "mirada.png", "", 600, 600),
    ("comic4", "11/10/2024", "11102024.png", "punch.png", "", 600, 600),
    ("comic3", "11/09/2024", "11092024.png", "bidenblast.png", "", 600, 600),
    ("comic2", "11/08/2024", "11082024.png", "sniff.png", "", 600, 600),
    ("comic1", "11/07/2024", "11072024.png", "first.png", "the first one", 625, 360),
]

# (file, title, caption, shape)
PICTURES = [
    ("sketch1.png", "Pencil portrait", "Drawn by hand, photographed badly. 2025.", "square"),
    ("danke.gif", "danke", "An animated thank-you.", "square"),
    ("paid4winrar.png", "paid for winrar", "The banner the old site was built around.", "wide"),
    ("paulcheenis.png", "the name", "Six hundred pixels of enthusiasm.", "wide"),
]

# Posts mirrored from Instagram live in their own file, written by
# tools/sync_instagram.py. Kept apart so a sync never edits this one.
IG_STORE = ROOT / "tools" / "instagram.json"
IG_MEDIUM = ROOT / "tools" / "instagram_medium.json"


def ig_media() -> dict[str, str]:
    """Which page each mirrored post belongs on.

    tools/instagram_medium.json holds two lists of post ids: "sketch" for paper
    and ink, "digital" for work drawn on a screen. A post nobody has filed yet
    goes to sketches, since that is what most of the account is.
    """
    mapping: dict[str, str] = {}
    if not IG_MEDIUM.exists():
        return mapping
    try:
        data = json.loads(IG_MEDIUM.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("tools/instagram_medium.json is not valid JSON, treating all as sketches")
        return mapping
    for medium in ("sketch", "digital"):
        for post_id in data.get(medium, []):
            mapping[str(post_id)] = medium
    return mapping


def ig_title(caption: str) -> str:
    first = (caption.splitlines() or [""])[0].strip()
    if not first:
        return "from instagram"
    if len(first) <= 42:
        return first
    cut = first[:42].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def ig_date(post: dict) -> str:
    stamp = (post.get("timestamp") or "")[:10]
    try:
        year, month, day = stamp.split("-")
        return f"{int(day)} {MONTHS[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return "instagram"


def ig_caption(post: dict) -> str:
    lines = [ln.strip() for ln in (post.get("caption") or "").splitlines() if ln.strip()]
    title = ig_title(post.get("caption", ""))
    rest = " ".join(lines[1:]) if len(lines) > 1 else ""
    if not rest and lines and lines[0] != title:
        rest = lines[0]
    if not rest:
        return f"posted {ig_date(post)}"
    return rest if len(rest) <= 140 else rest[:140].rsplit(" ", 1)[0] + "…"


def instagram_pictures() -> tuple[list[tuple], list[tuple]]:
    """(sketches, digital) as (file, title, caption, shape, permalink), newest first."""
    if not IG_STORE.exists():
        return [], []
    try:
        posts = json.loads(IG_STORE.read_text(encoding="utf-8")).get("posts", [])
    except json.JSONDecodeError:
        print("tools/instagram.json is not valid JSON, ignoring it")
        return [], []
    media = ig_media()
    sketches: list[tuple] = []
    digital: list[tuple] = []
    for post in posts:
        if not post.get("file"):
            continue
        entry = (post["file"], ig_title(post.get("caption", "")),
                 ig_caption(post), "square", post.get("permalink", ""))
        if media.get(str(post.get("id")), "sketch") == "digital":
            digital.append(entry)
        else:
            sketches.append(entry)
    return sketches, digital


IG_SKETCHES, IG_DIGITAL = instagram_pictures()
ALL_PICTURES = IG_DIGITAL + PICTURES

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="Assets/{og}">
<meta name="theme-color" content="#fafafa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0c0c0c" media="(prefers-color-scheme: dark)">
<link rel="icon" type="image/png" href="Assets/favicon.png">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main" style="position:absolute;left:-9999px">skip to content</a>
{header}
<main id="main">
"""

FOOT = """</main>
<footer class="site-foot">
  <div class="wrap">
    <span>© <span data-year>2025</span> paulcheenis</span>
    <span>·</span>
    <a href="comics.html">comics</a>
    <a href="pictures.html">pictures</a>
    <a href="suggestions.html">suggestions</a>
    <span class="hand">hand-made, badly hosted, worth it</span>
  </div>
</footer>
<script src="script.js"></script>
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def url(path: str) -> str:
    return "Assets/" + path.replace(" ", "%20")


def header(active: str) -> str:
    links = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if label == active else ""}>{label}</a>'
        for href, label in NAV
    )
    return f"""<header class="site-head">
  <div class="wrap">
    <a class="brand" href="index.html">paul<b>cheenis</b><span class="dot">.</span></a>
    <nav class="nav" aria-label="main">{links}</nav>
  </div>
</header>"""


def page(filename: str, title: str, desc: str, active: str, body: str,
         og: str = "12032024.png") -> None:
    doc = HEAD.format(title=esc(title), desc=esc(desc), og=og, header=header(active))
    doc += body + FOOT
    (ROOT / filename).write_text(doc, encoding="utf-8")
    print("wrote", filename, f"({len(doc)} bytes)")


def comic_block(c: tuple, wide: bool = False) -> str:
    anchor, date, img, title_img, note, w, h = c
    cls = "comic comic--wide" if wide else "comic"
    note_html = f'<p class="comic__note">{esc(note)}</p>' if note else ""
    return f"""  <article class="{cls}" id="{anchor}">
    <a class="comic__img" href="{url(img)}" data-zoom="{url(img)}" data-label="{esc(date)}">
      <img src="{url(img)}" alt="Comic from {esc(date)}" width="{w}" height="{h}" loading="lazy" decoding="async">
    </a>
    <div class="comic__meta">
      <span class="comic__title-img"><img src="{url(title_img)}" alt="title card" loading="lazy" decoding="async"></span>
      <span class="comic__date">{esc(date)}</span>
    </div>
    {note_html}
  </article>"""


def tile(pic: tuple) -> str:
    img, name, caption, shape = pic[:4]
    permalink = pic[4] if len(pic) > 4 else ""
    cls = f"tile tile--{shape}" if shape != "square" else "tile"
    source = (f' <a class="tile__src" href="{esc(permalink)}" rel="noopener">'
              f'instagram</a>' if permalink else "")
    return f"""    <figure class="{cls}">
      <a href="{url(img)}" data-zoom="{url(img)}" data-label="{esc(name)}">
        <img src="{url(img)}" alt="{esc(name)}" loading="lazy" decoding="async">
      </a>
      <figcaption><b>{esc(name)}</b>{esc(caption)}{source}</figcaption>
    </figure>"""


# ---------------------------------------------------------------- pages
THUMB_W = 300


def ig_thumb(rel: str) -> str:
    """A strip-sized copy of an instagram image, generated once with Pillow.

    The mirrored posts are camera-sized (a few hundred KB each); a dozen of them
    on the home page would be several megabytes for something shown at 132 px.
    """
    src = ROOT / "Assets" / rel
    thumbs = ROOT / "Assets" / "thumbs"
    if not src.exists():
        return url(rel)
    out = thumbs / (src.stem + ".jpg")
    try:
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            from PIL import Image
            thumbs.mkdir(exist_ok=True)
            im = Image.open(src).convert("RGB")
            im.thumbnail((THUMB_W, THUMB_W), getattr(Image, "Resampling", Image).LANCZOS)
            im.save(out, "JPEG", quality=82, optimize=True)
        return f"Assets/thumbs/{out.name}"
    except Exception as exc:                      # noqa: BLE001 - never break the build
        print(f"  thumb failed for {src.name}: {exc}")
        return url(rel)


def sketch_strip(count: int = 14) -> str:
    """The auto-scrolling ribbon of the newest instagram sketches.

    The track is duplicated so the CSS can translate by exactly -50% and loop
    without a visible jump; hover pauses it, and reduced-motion turns it into a
    plain horizontal scroller.
    """
    picks = IG_SKETCHES[:count]
    if not picks:
        return ""
    cells = "".join(
        f'<a class="strip__cell" href="{esc(p[4]) or "sketch.html"}" '
        f'{"target=_blank rel=noopener " if p[4] else ""}aria-label="{esc(p[1])}">'
        f'<img src="{ig_thumb(p[0])}" alt="{esc(p[1])}" loading="lazy" decoding="async"></a>'
        for p in picks
    )
    return f"""  <section class="strip-section wrap">
    <div class="section-head">
      <h2>From the sketchbook</h2>
      <span class="eyebrow">newest from instagram</span>
      <a class="more" href="sketch.html">all sketches →</a>
    </div>
    <div class="strip">
      <div class="strip__track">{cells}{cells}</div>
    </div>
  </section>

"""


def build_index() -> None:
    latest = COMICS[0]
    recent = COMICS[1:5]
    body = f"""  <section class="hero wrap">
    <div>
      <p class="kicker">comics and shit</p>
      <h1>Drawings, comics, and whatever else falls out of my head.</h1>
      <p class="lede">No schedule, no theme. When something gets finished it goes up here.</p>
      <div class="hero-actions">
        <a class="btn btn--primary" href="comics.html#{latest[0]}">latest comic →</a>
        <a class="btn" href="pictures.html">look at pictures</a>
      </div>
    </div>
    <img class="hero-wordmark" src="{url('paulcheenis.png')}" alt="paulcheenis" width="600" height="250">
  </section>

{sketch_strip()}
  <section class="section wrap">
    <div class="section-head">
      <h2>Newest</h2>
      <span class="eyebrow">{esc(latest[1])}</span>
      <a class="more" href="comics.html">all 13 comics →</a>
    </div>
    <div class="comics">
{comic_block(latest, wide=True)}
    </div>
  </section>

  <section class="section wrap">
    <div class="section-head">
      <h2>Before that</h2>
      <a class="more" href="comics.html">archive →</a>
    </div>
    <div class="comics comics--grid">
{chr(10).join(comic_block(c) for c in recent)}
    </div>
  </section>

  <section class="section wrap">
    <div class="section-head">
      <h2>Pictures</h2>
      <a class="more" href="pictures.html">everything →</a>
    </div>
    <div class="gallery">
{chr(10).join(tile(p) for p in ALL_PICTURES[:6])}
    </div>
  </section>
"""
    page("index.html", "paulcheenis — comics and pictures",
         "Comics, sketches and random pictures by paulcheenis.", "home", body)


def build_comics() -> None:
    body = f"""  <section class="page-head wrap">
    <p class="kicker">the archive</p>
    <h1>Comics</h1>
    <p class="lede">{len(COMICS)} so far, newest first. Click any of them to see it full size.</p>
  </section>

  <section class="section wrap">
    <div class="comics comics--grid">
{chr(10).join(comic_block(c) for c in COMICS)}
    </div>
  </section>
"""
    page("comics.html", "comics — paulcheenis",
         "Every comic on the site, newest first.", "comics", body)


def build_pictures() -> None:
    body = f"""  <section class="page-head wrap">
    <p class="kicker">offcuts</p>
    <h1>Pictures</h1>
    <p class="lede">Things that aren't a comic. Click one to open it.
    The instagram ones put themselves here.</p>
  </section>

  <section class="section wrap">
    <div class="gallery">
{chr(10).join(tile(p) for p in ALL_PICTURES)}
    </div>
  </section>
"""
    page("pictures.html", "pictures — paulcheenis",
         "Sketches, gifs and assorted pictures.", "pictures", body)


def build_sketch() -> None:
    body = f"""  <section class="page-head wrap">
    <p class="kicker">sketches</p>
    <h1>Sketches</h1>
    <p class="lede">The looser stuff — pencil, gifs, things that never became a comic.
    The notebook pages from instagram land here too.</p>
  </section>

  <section class="section wrap">
    <div class="gallery">
      <figure class="tile">
        <a href="Assets/sketch1.png" data-zoom="Assets/sketch1.png" data-label="pencil portrait">
          <img src="Assets/sketch1.png" alt="Pencil portrait" loading="lazy" decoding="async">
        </a>
        <figcaption><b>pencil portrait</b>Drawn by hand. 2025.</figcaption>
      </figure>
      <figure class="tile">
        <a href="Assets/danke.gif" data-zoom="Assets/danke.gif" data-label="danke.gif">
          <img src="Assets/danke.gif" alt="Animated sketch" loading="lazy" decoding="async">
        </a>
        <figcaption><b>danke.gif</b>An animated thank-you.</figcaption>
      </figure>
      <figure class="tile">
        <a href="Assets/11092024.png" data-zoom="Assets/11092024.png" data-label="comic, 11/09/2024">
          <img src="Assets/11092024.png" alt="Comic from 11/09/2024" loading="lazy" decoding="async">
        </a>
        <figcaption><b>from the comic pile</b>11/09/2024, pencil and no patience.</figcaption>
      </figure>
{chr(10).join(tile(p) for p in IG_SKETCHES)}
    </div>
  </section>
"""
    page("sketch.html", "sketches — paulcheenis",
         "Sketches and loose drawings.", "sketches", body)


def build_about() -> None:
    body = """  <section class="page-head wrap">
    <p class="kicker">hello</p>
    <h1>About</h1>
  </section>

  <section class="section wrap">
    <div class="panel">
      <p>This is my personal website, where I practise drawing and slowly get better
         at building things on the internet.</p>
      <p>I post comics when one is finished and pictures when I like them enough.
         There is no posting schedule and there never will be.</p>
      <p>Everything here is drawn by me. The site is a pile of HTML files, a stylesheet
         and one small script — no framework, no build step, no cookies.</p>
      <p>If you want to see something drawn, there's a
         <a href="suggestions.html">suggestion box</a>.</p>
    </div>
  </section>
"""
    page("about.html", "about — paulcheenis",
         "Who makes this and why.", "about", body)


def build_suggestions() -> None:
    body = """  <section class="page-head wrap">
    <p class="kicker">tell me what to draw</p>
    <h1>Suggestion box</h1>
    <p class="lede">Leave an idea for a comic or a sketch. If it's good — or strange
       enough — it might get drawn.</p>
  </section>

  <section class="section wrap">
    <form class="panel form" action="thankyou.html" method="get">
      <div class="field">
        <label for="name">name (or leave it blank)</label>
        <input id="name" name="name" type="text" autocomplete="nickname" placeholder="who's asking">
      </div>
      <div class="field">
        <label for="idea">your idea</label>
        <textarea id="idea" name="idea" placeholder="a guy who..."></textarea>
      </div>
      <button class="btn btn--primary" type="submit">send it →</button>
    </form>
  </section>
"""
    page("suggestions.html", "suggestions — paulcheenis",
         "Leave an idea for a comic or sketch.", "suggestions", body)


def build_thankyou() -> None:
    body = """  <section class="page-head wrap">
    <p class="kicker">received</p>
    <h1>Thank you.</h1>
    <p class="lede">Noted, saved, possibly drawn. No promises on turnaround.</p>
    <div class="hero-actions">
      <a class="btn btn--primary" href="index.html">back home</a>
      <a class="btn" href="comics.html">read comics instead</a>
    </div>
  </section>
"""
    page("thankyou.html", "thank you — paulcheenis",
         "Thanks for the suggestion.", "", body)


def build_projects() -> None:
    body = """  <section class="page-head wrap">
    <p class="kicker">eventually</p>
    <h1>Projects</h1>
    <p class="lede">Things I'm building that aren't comics. So far, none of them are finished.</p>
  </section>

  <section class="section wrap">
    <div class="panel">
      <p>This page has said “first project tbd” since 2024 and honestly that's still
         accurate.</p>
      <p>When something ships it will appear here. In the meantime the
         <a href="comics.html">comics</a> are the actual project.</p>
    </div>
  </section>
"""
    page("projects.html", "projects — paulcheenis",
         "Projects, once there are any.", "", body)


def build_404() -> None:
    body = """  <section class="page-head wrap">
    <p class="kicker">404</p>
    <h1>There's nothing at this address.</h1>
    <p class="lede">Either it moved, or it never existed, or I broke a link again.</p>
    <div class="hero-actions">
      <a class="btn btn--primary" href="index.html">home</a>
      <a class="btn" href="comics.html">comics</a>
    </div>
  </section>
"""
    page("404.html", "not found — paulcheenis", "Page not found.", "", body)


def main() -> None:
    build_index()
    build_comics()
    build_pictures()
    build_sketch()
    build_projects()
    build_about()
    build_suggestions()
    build_thankyou()
    build_404()


if __name__ == "__main__":
    main()
