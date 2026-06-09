#!/usr/bin/env python3
"""Deterministic OG-card compositor (Pillow, no browser).

Rebuilds assets/og/<slug>.png from the intact per-post hero art
(assets/art/posts/<slug>.png) + the post's real title/tags. Reliable and
race-free — the Chrome-screenshot path in gen_post_art can corrupt cards when
run concurrently (shared temp file). Use this to (re)stamp the name line.

RUN:  python3 _charts/recomposite_og.py
"""
import os, re, glob, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_post_art as g

ROOT = g.ROOT
OG = g.OG
HEROES = os.path.join(ROOT, "assets", "art", "posts")
W, H, ART_H, PADX = 1200, 630, 360, 90
BG, INK, ACCENT, MUTED, RULE = (251,250,247), (27,27,26), (162,60,36), (95,94,87), (231,227,218)
MARK = "Tsolmondorj Natsagdorj · security & systems"

GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_B = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
MONO = "/System/Library/Fonts/Supplemental/Courier New.ttf"
TITLE_FONT = GEORGIA_B if os.path.exists(GEORGIA_B) else GEORGIA

def f(path, size): return ImageFont.truetype(path, size)
def title_size(t):
    n = len(t)
    return 56 if n <= 38 else 48 if n <= 58 else 42 if n <= 80 else 36

def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def cover(img, tw, th):
    iw, ih = img.size
    s = max(tw/iw, th/ih)
    img = img.resize((round(iw*s), round(ih*s)), Image.LANCZOS)
    iw, ih = img.size
    l, t = (iw-tw)//2, (ih-th)//2
    return img.crop((l, t, l+tw, t+th))

def build(slug, title, tags_line):
    card = Image.new("RGB", (W, H), BG)
    hero_path = os.path.join(HEROES, slug + ".png")
    card.paste(cover(Image.open(hero_path).convert("RGB"), W, ART_H), (0, 0))
    d = ImageDraw.Draw(card)
    d.line([(0, ART_H), (W, ART_H)], fill=RULE, width=1)
    d.text((PADX, ART_H+28), MARK, font=f(MONO, 22), fill=ACCENT)
    fs = title_size(title)
    tf = f(TITLE_FONT, fs)
    y = ART_H + 66
    for line in wrap(d, title, tf, W-2*PADX):
        d.text((PADX, y), line, font=tf, fill=INK); y += int(fs*1.14)
    rowf = f(MONO, 20)
    d.text((PADX, H-46), tags_line, font=rowf, fill=ACCENT)
    url = "0xsoftboi.github.io"
    d.text((W-PADX-d.textlength(url, font=rowf), H-46), url, font=rowf, fill=MUTED)
    card.save(os.path.join(OG, slug + ".png"))

n = 0
for md in sorted(glob.glob(os.path.join(ROOT, "_posts", "*.md"))):
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(md))[:-3]
    if not os.path.exists(os.path.join(HEROES, slug + ".png")):
        print("skip (no hero):", slug); continue
    fm = g.front_matter(open(md).read())
    build(slug, fm.get("title", slug), " · ".join(fm.get("tags", [])[:4]))
    n += 1
print(f"rebuilt {n} OG cards (Pillow)")
