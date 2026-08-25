#!/usr/bin/env python3
"""Validate the canonical Jekyll writing corpus and built `_site` output.

Zero runtime dependencies: this runs after `bundle exec jekyll build` in CI.
It checks that every post is present in the evidence-audit ledger, every audit
entry names a real post, key routes built, and local href/src targets resolve.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
POSTS = ROOT / "_posts"
AUDIT = ROOT / "_data" / "writing_audit.yml"
RESUME_PDF = SITE / "assets" / "Tsolmondorj-Natsagdorj-Resume.pdf"

class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[tuple[str, str]] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.targets.append(("href", d["href"] or ""))
        for key in ("src", "href"):
            if tag in {"img", "script", "link", "source"} and d.get(key):
                self.targets.append((key, d[key] or ""))

def post_slugs() -> set[str]:
    return {re.sub(r"^\d{4}-\d{2}-\d{2}-", "", p.stem) for p in POSTS.glob("*.md")}

def audit_slugs() -> set[str]:
    text = AUDIT.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^([a-z0-9][a-z0-9-]*):\s*$", text, flags=re.M)}

def built_target(source: Path, raw: str) -> Path | None:
    raw = raw.strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:", "data:")): return None
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc or raw.startswith("//"): return None
    path_text = unquote(parts.path)
    if not path_text: return None
    candidate = SITE / path_text.lstrip("/") if path_text.startswith("/") else source.parent / path_text
    if path_text.endswith("/") or candidate.is_dir(): candidate = candidate / "index.html"
    return candidate

def is_site_verification_file(path: Path) -> bool:
    return path.parent == SITE and bool(re.fullmatch(r"google[a-z0-9]+\.html", path.name))

MATH_DELIMS = re.compile(r"\\[(\[]")
# `$x$` is NOT math to kramdown -- it needs `$$x$$`. Writing the single-dollar
# form renders the LaTeX as literal text, silently. Catch the common shapes:
# a dollar followed by a backslash-command or a single letter, then a dollar.
LONE_DOLLAR = re.compile(r"(?<![$\w])\$(?!\$)(?=[\\A-Za-z])[^$\n`]{1,80}\$(?!\$)")

def strip_code(markdown: str) -> str:
    """Drop fenced blocks and inline spans -- `$nd` in shell is not math."""
    text = re.sub(r"```.*?```", "", markdown, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)

def math_errors() -> list[str]:
    """Math must actually render: KaTeX loads only when `math: true`, and
    kramdown only converts the `$$...$$` form."""
    out: list[str] = []
    for post in sorted(POSTS.glob("*.md")):
        raw = post.read_text(encoding="utf-8")
        head = raw.split("---", 2)[1] if raw.startswith("---") else ""
        body = strip_code(raw)
        for hit in LONE_DOLLAR.findall(body):
            out.append(f"{post.name}: single-$ math renders as literal text, use $$...$$: {hit.strip()!r}")
        declares = re.search(r"^math:\s*true\s*$", head, flags=re.M) is not None
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", post.stem)
        built = SITE / "blog" / slug / "index.html"
        if not built.exists():
            continue
        html = built.read_text(encoding="utf-8", errors="replace")
        start = html.find('<div class="post-body">')
        has_math = start != -1 and MATH_DELIMS.search(html[start:]) is not None
        if has_math and not declares:
            out.append(f"{post.name}: renders math delimiters but front matter lacks `math: true`, so KaTeX never loads")
        if declares and not has_math:
            out.append(f"{post.name}: declares `math: true` but emits no math; drop the flag or fix the delimiters")
    return out

def validate() -> list[str]:
    errors: list[str] = []
    posts, audits = post_slugs(), audit_slugs()
    if posts - audits: errors.append("posts missing writing_audit entries: " + ", ".join(sorted(posts - audits)))
    if audits - posts: errors.append("writing_audit entries without posts: " + ", ".join(sorted(audits - posts)))
    if not SITE.exists(): return ["_site does not exist; run jekyll build first"]
    key_routes = ["index.html","blog/index.html","research/index.html","about/index.html","formation/index.html","revisions/index.html","resume/index.html","research-standard/index.html","work/roce-preflight/index.html","work/bridge-bench/index.html","work/materials/index.html","work/upstream/index.html","blog/197-tests-four-real-hardware-bugs/index.html","blog/static-analysis-scores-zero-on-real-exploits/index.html","blog/greedy-was-enough-active-learning-pretrained-potential/index.html","blog/autograd-is-part-of-the-api/index.html","blog/delete-the-science-fiction-parts-first/index.html","blog/a-new-turbine-inside-a-1965-power-plant/index.html"]
    for route in key_routes:
        if not (SITE / route).exists(): errors.append(f"key built route missing: /{route}")
    if not RESUME_PDF.exists(): errors.append("downloadable resume PDF missing from built site")
    elif RESUME_PDF.stat().st_size < 5_000: errors.append("downloadable resume PDF is unexpectedly small")
    elif RESUME_PDF.read_bytes()[:5] != b"%PDF-": errors.append("downloadable resume asset is not a PDF")
    for html in SITE.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        if not is_site_verification_file(html):
            if "<title" not in text.lower(): errors.append(f"{html.relative_to(SITE)}: missing title")
            if "name=\"viewport\"" not in text.lower() and "name='viewport'" not in text.lower(): errors.append(f"{html.relative_to(SITE)}: missing viewport meta")
        parser = Links()
        try: parser.feed(text)
        except Exception as exc:
            errors.append(f"{html.relative_to(SITE)}: HTML parse error: {exc}"); continue
        for kind, raw in parser.targets:
            target = built_target(html, raw)
            if target is not None and not target.exists(): errors.append(f"{html.relative_to(SITE)}: broken local {kind}={raw!r}")
    for source in (ROOT / "index.html", ROOT / "research.html"):
        text = source.read_text(encoding="utf-8")
        for phrase in ("static analysis alone scores ~0% F1","static-pre-filtered LLM reaches ~40%","95% top-100 recall at a 20% labeling budget"):
            if phrase in text: errors.append(f"{source.name}: stale headline claim returned: {phrase}")
    errors.extend(math_errors())
    revisions = (SITE / "revisions/index.html").read_text(encoding="utf-8", errors="replace")
    if "13/24" not in revisions or "−0.47" not in revisions: errors.append("revisions page is missing the two material research corrections")
    homepage = (SITE / "index.html").read_text(encoding="utf-8", errors="replace")
    for href in ("/work/roce-preflight/","/work/bridge-bench/","/work/materials/","/work/upstream/"):
        if href not in homepage: errors.append(f"homepage is missing verification path: {href}")
    resume = (SITE / "resume/index.html").read_text(encoding="utf-8", errors="replace")
    for marker in ("13/24","197 unit tests","−0.47","Tsolmondorj-Natsagdorj-Resume.pdf","Problems I want to work on","correctness has to survive contact with reality"):
        if marker not in resume: errors.append(f"resume is missing required evidence/hiring marker: {marker}")
    social_cards = {"work/roce-preflight/index.html":"assets/evidence/roce-preflight.svg","work/bridge-bench/index.html":"assets/evidence/bridge-bench.svg","work/materials/index.html":"assets/evidence/materials-discovery.svg"}
    for route, image in social_cards.items():
        text = (SITE / route).read_text(encoding="utf-8", errors="replace")
        if "og:image" not in text or image not in text: errors.append(f"{route}: missing evidence-derived OpenGraph image")
        if "twitter:card" not in text: errors.append(f"{route}: missing Twitter card metadata")
    return errors

def main() -> int:
    errors = validate()
    if errors:
        print("site validation FAILED", file=sys.stderr)
        for error in errors: print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"site validation OK: {len(post_slugs())} posts, {len(list(SITE.rglob('*.html')))} built HTML pages")
    return 0

if __name__ == "__main__": raise SystemExit(main())
