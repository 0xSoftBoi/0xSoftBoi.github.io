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
    out: set[str] = set()
    for path in POSTS.glob("*.md"):
        out.add(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem))
    return out


def audit_slugs() -> set[str]:
    text = AUDIT.read_text(encoding="utf-8")
    return {
        m.group(1)
        for m in re.finditer(r"^([a-z0-9][a-z0-9-]*):\s*$", text, flags=re.M)
    }


def built_target(source: Path, raw: str) -> Path | None:
    raw = raw.strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc or raw.startswith("//"):
        return None
    path_text = unquote(parts.path)
    if not path_text:
        return None
    if path_text.startswith("/"):
        candidate = SITE / path_text.lstrip("/")
    else:
        candidate = source.parent / path_text
    if path_text.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def is_site_verification_file(path: Path) -> bool:
    return path.parent == SITE and bool(re.fullmatch(r"google[a-z0-9]+\.html", path.name))


def validate() -> list[str]:
    errors: list[str] = []
    posts = post_slugs()
    audits = audit_slugs()

    missing_audit = sorted(posts - audits)
    stale_audit = sorted(audits - posts)
    if missing_audit:
        errors.append("posts missing writing_audit entries: " + ", ".join(missing_audit))
    if stale_audit:
        errors.append("writing_audit entries without posts: " + ", ".join(stale_audit))

    if not SITE.exists():
        errors.append("_site does not exist; run jekyll build first")
        return errors

    key_routes = [
        "index.html",
        "blog/index.html",
        "research/index.html",
        "about/index.html",
        "formation/index.html",
        "revisions/index.html",
        "resume/index.html",
        "research-standard/index.html",
        "work/roce-preflight/index.html",
        "work/bridge-bench/index.html",
        "work/materials/index.html",
        "work/upstream/index.html",
        "blog/197-tests-four-real-hardware-bugs/index.html",
        "blog/static-analysis-scores-zero-on-real-exploits/index.html",
        "blog/greedy-was-enough-active-learning-pretrained-potential/index.html",
        "blog/autograd-is-part-of-the-api/index.html",
        "blog/delete-the-science-fiction-parts-first/index.html",
    ]
    for route in key_routes:
        if not (SITE / route).exists():
            errors.append(f"key built route missing: /{route}")

    if not RESUME_PDF.exists():
        errors.append("downloadable resume PDF missing from built site")
    elif RESUME_PDF.stat().st_size < 5_000:
        errors.append("downloadable resume PDF is unexpectedly small")
    elif RESUME_PDF.read_bytes()[:5] != b"%PDF-":
        errors.append("downloadable resume asset is not a PDF")

    for html in SITE.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        if not is_site_verification_file(html):
            if "<title" not in text.lower():
                errors.append(f"{html.relative_to(SITE)}: missing title")
            if "name=\"viewport\"" not in text.lower() and "name='viewport'" not in text.lower():
                errors.append(f"{html.relative_to(SITE)}: missing viewport meta")
        parser = Links()
        try:
            parser.feed(text)
        except Exception as exc:
            errors.append(f"{html.relative_to(SITE)}: HTML parse error: {exc}")
            continue
        for kind, raw in parser.targets:
            target = built_target(html, raw)
            if target is not None and not target.exists():
                errors.append(
                    f"{html.relative_to(SITE)}: broken local {kind}={raw!r} -> "
                    f"{target.relative_to(SITE) if target.is_relative_to(SITE) else target}"
                )

    for source in (ROOT / "index.html", ROOT / "research.html"):
        text = source.read_text(encoding="utf-8")
        banned = [
            "static analysis alone scores ~0% F1",
            "static-pre-filtered LLM reaches ~40%",
            "95% top-100 recall at a 20% labeling budget",
        ]
        for phrase in banned:
            if phrase in text:
                errors.append(f"{source.name}: stale headline claim returned: {phrase}")

    revisions = (SITE / "revisions/index.html").read_text(encoding="utf-8", errors="replace") if (SITE / "revisions/index.html").exists() else ""
    if "13/24" not in revisions or "−0.47" not in revisions:
        errors.append("revisions page is missing the two material research corrections")

    homepage = (SITE / "index.html").read_text(encoding="utf-8", errors="replace") if (SITE / "index.html").exists() else ""
    for href in ("/work/roce-preflight/", "/work/bridge-bench/", "/work/materials/", "/work/upstream/"):
        if href not in homepage:
            errors.append(f"homepage is missing verification path: {href}")

    resume = (SITE / "resume/index.html").read_text(encoding="utf-8", errors="replace") if (SITE / "resume/index.html").exists() else ""
    for marker in ("13/24", "197 unit tests", "−0.47", "Tsolmondorj-Natsagdorj-Resume.pdf"):
        if marker not in resume:
            errors.append(f"resume is missing required evidence marker: {marker}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("site validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"site validation OK: {len(post_slugs())} posts, {len(list(SITE.rglob('*.html')))} built HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
