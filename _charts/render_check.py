#!/usr/bin/env python3
"""Visual check for a chart figure: render it light + dark via WebKit (qlmanage
thumbnails HTML through the same engine Safari/GitHub-Pages browsers use) so the
themed CSS classes + var() palette resolve faithfully.

Usage:  python3 _charts/render_check.py _charts/recall-bars.svg
        python3 _charts/render_check.py <file.svg>   # writes _charts/_chk-*.png
"""
import re, subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(path):
    raw = open(path).read()
    m = re.search(r"(<figure.*?</figure>)", raw, re.S) or re.search(r"(<svg.*?</svg>)", raw, re.S)
    fig = m.group(1)
    css = open(os.path.join(ROOT, "assets/css/style.css")).read()
    css_light = re.sub(r"@media \(prefers-color-scheme:dark\)\{[^@]*?\}\s*\}", "", css, count=1)
    base = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(ROOT, "_charts")
    for mode, sheet in (("light", css_light), ("dark", css)):
        # dark: rely on system dark OR force override
        extra = ("\n:root{--bg:#16161a;--text:#e8e6df;--muted:#9b9a92;"
                 "--rule:#2c2c33;--accent:#e0936f;--accent-ink:#eaa886;}") if mode == "dark" else ""
        html = (f"<!doctype html><html><head><meta charset=utf-8><style>{sheet}{extra}\n"
                f"body{{background:var(--bg);color:var(--text);padding:24px}}"
                f".post-body{{max-width:680px;margin:0 auto}}</style></head>"
                f"<body><div class=post-body>{fig}</div></body></html>")
        h = os.path.join(out, f"_chk-{base}-{mode}.html")
        open(h, "w").write(html)
        subprocess.run(["qlmanage", "-t", "-s", "760", "-o", out, h], capture_output=True)
        print(f"  {mode}: _charts/_chk-{base}-{mode}.html.png")


if __name__ == "__main__":
    main(sys.argv[1])
