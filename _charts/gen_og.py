#!/usr/bin/env python3
"""Authoring tool — generates per-post 1200x630 social cards + favicons.

Renders deterministic HTML cards through WebKit (qlmanage HTML->PNG, the same
engine the live site's readers use), then crops the square qlmanage output to
the exact OG aspect with `sips`. Run locally; commit the PNGs under assets/.

Usage:  python3 _charts/gen_og.py
"""
import os, re, glob, subprocess, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OG = os.path.join(ROOT, "assets", "og")
ASSETS = os.path.join(ROOT, "assets")
TMP = os.path.join(ROOT, "_charts", "_ogtmp")

BG, INK, ACCENT, MUTED = "#fbfaf7", "#1b1b1a", "#a23c24", "#5f5e57"

# Real headless browser (Playwright's cached Chromium) — exact viewport, unlike
# qlmanage which forces a square thumbnail.
CHROME = ("/Users/toma/Library/Caches/ms-playwright/chromium-1223/"
          "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
          "Google Chrome for Testing")


def front_matter(text):
    m = re.match(r"\A---\s*\n(.*?\n)---\s*\n", text, re.S)
    if not m:
        return {}
    fm = {}
    title = re.search(r'^title:\s*"?(.*?)"?\s*$', m.group(1), re.M)
    tags = re.search(r"^tags:\s*\[(.*?)\]", m.group(1), re.M)
    if title:
        fm["title"] = title.group(1).replace('\\"', '"')
    if tags:
        fm["tags"] = [t.strip() for t in tags.group(1).split(",") if t.strip()]
    return fm


def title_size(t):
    n = len(t)
    if n <= 42:
        return 66
    if n <= 72:
        return 56
    return 48


def card_html(title, tags_line, fs):
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{margin:0;box-sizing:border-box}}
html,body{{width:1200px;height:630px;background:{BG};overflow:hidden}}
.card{{width:1200px;height:630px;padding:80px 96px;display:flex;flex-direction:column;
  justify-content:space-between;font-family:Georgia,'Times New Roman',serif;color:{INK};background:{BG}}}
.mark{{font-family:'Courier New',monospace;font-size:29px;color:{ACCENT};letter-spacing:.03em}}
.title{{font-size:{fs}px;line-height:1.1;font-weight:600;max-width:1008px;overflow-wrap:break-word}}
.row{{display:flex;justify-content:space-between;align-items:baseline;
  font-family:'Courier New',monospace;font-size:25px;color:{MUTED}}}
.tags{{color:{ACCENT}}}
</style></head><body><div class="card">
<div class="mark">0xSoftBoi &middot; security &amp; systems</div>
<div class="title">{html.escape(title)}</div>
<div class="row"><span class="tags">{html.escape(tags_line)}</span><span>0xsoftboi.github.io</span></div>
</div></body></html>"""


def render(html_str, out_png, w, h):
    os.makedirs(TMP, exist_ok=True)
    hp = os.path.join(TMP, "card.html")
    open(hp, "w").write(html_str)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-color-profile=srgb",
                    f"--window-size={w},{h}", f"--screenshot={out_png}",
                    "file://" + hp], capture_output=True)
    return os.path.exists(out_png)


def main():
    os.makedirs(OG, exist_ok=True)
    # per-post cards
    for f in sorted(glob.glob(os.path.join(ROOT, "_posts", "*.md"))):
        fm = front_matter(open(f).read())
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(f))[:-3]
        title = fm.get("title", "")
        tags_line = " · ".join(fm.get("tags", []))
        out = os.path.join(OG, slug + ".png")
        render(card_html(title, tags_line, title_size(title)), out, 1200, 630)
        print("og:", os.path.relpath(out, ROOT))
    # default card (home/about/tags/404)
    render(card_html("security & systems", "writing · open source · selected work", 66),
           os.path.join(OG, "default.png"), 1200, 630)
    print("og: assets/og/default.png")
    # favicons — accent tile with 0x monogram, rendered via WebKit then resized
    ico = f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{margin:0}}html,body{{width:180px;height:180px;background:{BG}}}
.ico{{width:180px;height:180px;background:{ACCENT};color:{BG};border-radius:40px;
  display:flex;align-items:center;justify-content:center;
  font-family:'Courier New',monospace;font-weight:700;font-size:88px;letter-spacing:-3px}}
</style></head><body><div class="ico">0x</div></body></html>"""
    apple = os.path.join(ASSETS, "apple-touch-icon.png")
    render(ico, apple, 180, 180)
    fav = os.path.join(ASSETS, "favicon.png")
    subprocess.run(["cp", apple, fav], capture_output=True)
    subprocess.run(["sips", "-z", "32", "32", fav], capture_output=True)
    print("icons: assets/apple-touch-icon.png, assets/favicon.png")


if __name__ == "__main__":
    main()
