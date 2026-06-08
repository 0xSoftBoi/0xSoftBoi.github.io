#!/usr/bin/env python3
"""Lightweight static renderer for local preview (no full Jekyll needed).
Resolves the specific Liquid used in this site + kramdown for markdown."""
import os, re, glob, shutil, subprocess, datetime, yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_preview")
KRAMDOWN = os.path.expanduser("~/.gem/ruby/2.6.0/bin/kramdown")
YEAR = "2026"

cfg = yaml.safe_load(open(os.path.join(ROOT, "_config.yml")))
SITE_TITLE = cfg.get("title", "0xSoftBoi")
SITE_DESC = cfg.get("description", "")

def split_fm(text):
    m = re.match(r"\A---\s*\n(.*?\n)---\s*\n(.*)\Z", text, re.S)
    if m:
        return yaml.safe_load(m.group(1)) or {}, m.group(2)
    return {}, text

def md_to_html(md):
    p = subprocess.run([KRAMDOWN, "--input", "GFM", "--no-auto-ids"],
                       input=md, capture_output=True, text=True)
    return p.stdout

def rel(u):  # relative_url -> served at root
    u = u.strip().strip("'\"")
    return u if u.startswith("/") else "/" + u

def resolve_common(s, page):
    s = re.sub(r"\{\{\s*'([^']*)'\s*\|\s*relative_url\s*\}\}", lambda m: rel(m.group(1)), s)
    s = re.sub(r'\{\{\s*"([^"]*)"\s*\|\s*relative_url\s*\}\}', lambda m: rel(m.group(1)), s)
    s = re.sub(r"\{\{\s*([^\}|]+?)\s*\|\s*relative_url\s*\}\}", lambda m: rel(m.group(1)), s)
    s = s.replace("{{ site.time | date: \"%Y\" }}", YEAR)
    s = s.replace("{{ site.title }}", SITE_TITLE)
    title = page.get("title", SITE_TITLE)
    seo = (f'<title>{title}</title>\n<meta name="description" content="{SITE_DESC}">'
           f'\n<meta property="og:title" content="{title}">')
    s = s.replace("{% seo %}", seo)
    s = s.replace("{% feed_meta %}", '<link rel="alternate" type="application/atom+xml" href="/feed.xml">')
    return s

DEFAULT = open(os.path.join(ROOT, "_layouts/default.html")).read()
POSTL = open(os.path.join(ROOT, "_layouts/post.html")).read()

def wrap_default(inner, page):
    out = DEFAULT.replace("{{ content }}", inner)
    return resolve_common(out, page)

# ---- collect posts ----
posts = []
for f in sorted(glob.glob(os.path.join(ROOT, "_posts/*.md")), reverse=True):
    fm, body = split_fm(open(f).read())
    base = os.path.basename(f)
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", base)[:-3]
    url = f"/blog/{slug}/"
    d = datetime.date.fromisoformat(base[:10])
    posts.append({"title": fm.get("title", ""), "url": url, "date": d,
                  "excerpt": fm.get("excerpt", ""), "tags": fm.get("tags", []),
                  "body": md_to_html(body), "fm": fm})

def expand_post_loop(body):
    """Expand {% for post in site.posts %}...{% endfor %} using `posts`."""
    m = re.search(r"\{% for post in site\.posts %\}(.*?)\{% endfor %\}", body, re.S)
    if not m:
        return body
    tpl = m.group(1)
    items = ""
    for p in posts:
        it = tpl
        # {{ post.date | date: "FMT" }}
        it = re.sub(r'\{\{\s*post\.date\s*\|\s*date:\s*"([^"]*)"\s*\}\}',
                    lambda mm: p["date"].strftime(mm.group(1)), it)
        it = re.sub(r"\{\{\s*post\.url\s*\|\s*relative_url\s*\}\}", p["url"], it)
        it = it.replace("{{ post.title }}", p["title"])
        # tags: {% if post.tags %}...{{ post.tags | join: "SEP" }}...{% endif %}
        def tagsblk(mm):
            inner = mm.group(1)
            if not p["tags"]:
                return ""
            return re.sub(r'\{\{\s*post\.tags\s*\|\s*join:\s*"([^"]*)"\s*\}\}',
                          lambda j: j.group(1).join(p["tags"]), inner)
        it = re.sub(r"\{% if post\.tags %\}(.*?)\{% endif %\}", tagsblk, it, flags=re.S)
        # excerpt: {% if post.excerpt %}...{{ post.excerpt | strip_html | truncate: N }}...{% endif %}
        def exblk(mm):
            inner = mm.group(1)
            if not p["excerpt"]:
                return ""
            def trunc(j):
                n = int(j.group(1))
                ex = re.sub("<[^>]+>", "", p["excerpt"])
                return (ex[:n - 1] + "…") if len(ex) > n else ex
            return re.sub(r'\{\{\s*post\.excerpt\s*\|\s*strip_html\s*\|\s*truncate:\s*(\d+)\s*\}\}',
                          trunc, inner)
        it = re.sub(r"\{% if post\.excerpt %\}(.*?)\{% endif %\}", exblk, it, flags=re.S)
        items += it
    body = body[:m.start()] + items + body[m.end():]
    body = re.sub(r"\{% if site\.posts\.size == 0 %\}.*?\{% endif %\}", "", body, flags=re.S)
    return body

def render_static(path):
    fm, body = split_fm(open(os.path.join(ROOT, path)).read())
    body = expand_post_loop(body)
    return wrap_default(body, fm)

def render_post(p):
    _, inner = split_fm(POSTL)
    inner = inner.replace("{{ content }}", p["body"])
    inner = inner.replace("{{ page.title }}", p["title"])
    inner = inner.replace('{{ page.date | date: "%B %-d, %Y" }}', p["date"].strftime("%B %-d, %Y"))
    repl = (" · " + " · ".join(p["tags"])) if p["tags"] else ""
    inner = re.sub(r"\{% if page\.tags %\}.*?\{% endif %\}", lambda _: repl, inner, flags=re.S)
    inner = resolve_common(inner, p["fm"])
    return wrap_default(inner, p["fm"])

# ---- write everything ----
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
open(os.path.join(OUT, "index.html"), "w").write(render_static("index.html"))
os.makedirs(os.path.join(OUT, "about"), exist_ok=True)
open(os.path.join(OUT, "about/index.html"), "w").write(render_static("about.html"))
for p in posts:
    d = os.path.join(OUT, p["url"].strip("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(render_post(p))
print(f"rendered {2+len(posts)} pages -> {OUT}")
