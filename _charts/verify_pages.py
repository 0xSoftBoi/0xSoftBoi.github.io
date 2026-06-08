#!/usr/bin/env python3
"""Verification harness — composes faithful full pages (real layouts' structure +
real style.css, with the new Liquid logic mirrored in Python) and screenshots them
via headless Chrome in light + dark + mobile, so the new CSS/markup can be eyeballed
without a running Jekyll. NOT part of the site build."""
import os, re, glob, subprocess, html, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "_charts", "_vtmp")
KRAMDOWN = os.path.expanduser("~/.gem/ruby/2.6.0/bin/kramdown")
CHROME = ("/Users/toma/Library/Caches/ms-playwright/chromium-1223/"
          "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
          "Google Chrome for Testing")
CSS = open(os.path.join(ROOT, "assets/css/style.css")).read()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load_posts():
    posts = []
    for f in sorted(glob.glob(os.path.join(ROOT, "_posts/*.md")), reverse=True):
        t = open(f).read()
        fm = re.match(r"\A---\s*\n(.*?\n)---\s*\n(.*)\Z", t, re.S)
        meta, body = fm.group(1), fm.group(2)
        title = re.search(r'^title:\s*"?(.*?)"?\s*$', meta, re.M).group(1).replace('\\"', '"')
        tags = re.search(r"^tags:\s*\[(.*?)\]", meta, re.M).group(1)
        tags = [x.strip() for x in tags.split(",")]
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(f))[:-3]
        date = os.path.basename(f)[:10]
        posts.append(dict(title=title, tags=tags, slug=slug, date=date, body=body, url="/blog/%s/" % slug))
    return posts  # reverse-chronological, like site.posts


def md(body):
    p = subprocess.run([KRAMDOWN, "--input", "GFM"], input=body, capture_output=True, text=True)
    return p.stdout


def reading_time(body_html):
    words = len(re.sub("<[^>]+>", " ", body_html).split())
    return max(1, math.ceil(words / 200))


def related(posts, i):
    me = posts[i]
    out, shown = [], 0
    for n in range(len(me["tags"]), 0, -1):
        for p in posts:
            if p["slug"] != me["slug"] and shown < 3:
                shared = sum(1 for t in p["tags"] if t in me["tags"])
                if shared == n:
                    out.append(p); shown += 1
    return out


def meta_line(p, rt):
    tags = " · ".join('<a href="/tags/#%s">%s</a>' % (slugify(t), t) for t in p["tags"])
    return '%s · %s min · %s' % (p["date"], rt, tags)


def shell(inner, mode):
    forced = CSS
    if mode == "dark":
        forced += ("\n:root{--bg:#16161a;--text:#e8e6df;--muted:#9b9a92;--rule:#2c2c33;"
                   "--accent:#e0936f;--accent-ink:#eaa886;}")
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1"><style>{forced}</style></head>
<body><header class="site-header"><nav class="nav"><a class="brand" href="/">0xSoftBoi</a>
<div class="nav-links"><a href="/">writing</a><a href="/tags/">tags</a><a href="/about/">about</a>
<a href="#">github</a><a href="#">x</a></div></nav></header>
<main id="main" class="container">{inner}</main>
<footer class="site-footer"><span>© 2026 0xSoftBoi</span><span><a href="#">suwappu.bot</a></span></footer></body></html>"""


def post_page(posts, i):
    p = posts[i]
    body = md(p["body"])
    rt = reading_time(body)
    rel = related(posts, i)
    rel_html = "".join('<li><a href="%s">%s</a></li>' % (r["url"], html.escape(r["title"])) for r in rel)
    related_block = ('<aside class="related"><p class="related-title">Related</p><ul>%s</ul></aside>'
                     % rel_html) if rel else ""
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    nav = '<nav class="post-nav">'
    if older:
        nav += '<a class="pn-older" href="%s">← %s</a>' % (older["url"], html.escape(older["title"]))
    if newer:
        nav += '<a class="pn-newer" href="%s">%s →</a>' % (newer["url"], html.escape(newer["title"]))
    nav += '</nav>'
    inner = ('<article class="post"><a class="back" href="/">← writing</a>'
             '<h1 class="post-title">%s</h1><p class="post-meta">%s</p>'
             '<div class="post-body">%s</div>%s%s</article>'
             % (html.escape(p["title"]), meta_line(p, rt), body, related_block, nav))
    return inner


def tags_page(posts):
    tagmap = {}
    for p in posts:
        for t in p["tags"]:
            tagmap.setdefault(t, []).append(p)
    cloud = "".join('<li><a href="#%s">%s</a></li>' % (slugify(t), t) for t in sorted(tagmap))
    groups = ""
    for t in sorted(tagmap):
        ps = tagmap[t]
        n = len(ps)
        items = "".join('<li><a class="post-link" href="%s">%s</a>'
                        '<div class="post-meta">%s</div></li>' % (p["url"], html.escape(p["title"]), p["date"]) for p in ps)
        groups += ('<div class="tag-group"><h2 id="%s">%s<span class="count">%d post%s</span></h2>'
                   '<ul>%s</ul></div>' % (slugify(t), t, n, "" if n == 1 else "s", items))
    return ('<section class="tags-index"><h1>Tags</h1><ul class="tags-cloud">%s</ul>%s</section>'
            % (cloud, groups))


def shot(inner, name, mode, width=820):
    os.makedirs(TMP, exist_ok=True)
    hp = os.path.join(TMP, "%s-%s.html" % (name, mode))
    open(hp, "w").write(shell(inner, mode))
    out = os.path.join(TMP, "%s-%s.png" % (name, mode))
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--force-color-profile=srgb", "--window-size=%d,2400" % width,
                    "--screenshot=" + out, "file://" + hp], capture_output=True)
    print(out)


posts = load_posts()
bridge = next(i for i, p in enumerate(posts) if p["slug"] == "auditing-my-own-bridge")
neg = next(i for i, p in enumerate(posts) if p["slug"] == "the-model-reads-not-it-just-cant-use-it")
shot(post_page(posts, bridge), "post-bridge", "light")
shot(post_page(posts, bridge), "post-bridge", "dark")
shot(post_page(posts, neg), "post-neg", "light")  # has TOC
shot(post_page(posts, bridge), "post-bridge-mobile", "light", width=390)
shot(tags_page(posts), "tags", "light")
print("done")
