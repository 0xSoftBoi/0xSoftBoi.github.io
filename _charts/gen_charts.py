#!/usr/bin/env python3
"""Authoring tool — generates static, themed inline SVG for blog data charts.

Not a site dependency: run locally, paste the emitted <figure> into the post.
All colors come from CSS classes (defined in assets/css/style.css) so the SVG
re-themes with the site's light/dark variables. No runtime JS.

Usage:  python3 _charts/gen_charts.py        # writes each chart to _charts/*.svg
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def figure(svg, caption, fid):
    """Wrap an <svg> body in the figure pattern. No blank lines, minimal indent
    (kramdown passes block HTML through only if it isn't tripped into md/code)."""
    lines = [
        '<figure class="chart">',
        svg.strip(),
        f"<figcaption>{esc(caption)}</figcaption>",
        "</figure>",
    ]
    return "\n".join(lines) + "\n"


def vbars(values, labels, vlabels, title, width=680, height=300,
          ml=18, mr=18, mt=44, mb=46, fid="c", baseline=0, ymax=100,
          highlight=None):
    """Vertical bar chart. `highlight` = index drawn with .c-bar (accent),
    others .c-bar-muted. If highlight is None, all bars use .c-bar."""
    iw = width - ml - mr
    ih = height - mt - mb
    n = len(values)
    gap = iw / n
    bw = gap * 0.52
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{fid}-t">',
        f'<title id="{fid}-t">{esc(title)}</title>',
        f'<text class="c-title" x="{ml}" y="22">{esc(title)}</text>',
    ]
    # gridlines + y ticks (0, mid, max)
    for frac in (0, 0.5, 1.0):
        val = baseline + (ymax - baseline) * frac
        y = mt + ih - ih * frac
        parts.append(f'<line class="c-grid" x1="{ml}" y1="{y:.1f}" x2="{width-mr}" y2="{y:.1f}"/>')
        parts.append(f'<text class="c-label-sm" x="{width-mr}" y="{y-4:.1f}" text-anchor="end">{val:.0f}%</text>')
    for i, v in enumerate(values):
        bh = ih * (v - baseline) / (ymax - baseline)
        x = ml + gap * i + (gap - bw) / 2
        y = mt + ih - bh
        cls = "c-bar" if (highlight is None or i == highlight) else "c-bar-muted"
        parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2"/>')
        parts.append(f'<text class="c-val" x="{x+bw/2:.1f}" y="{y-7:.1f}" text-anchor="middle">{esc(vlabels[i])}</text>')
        parts.append(f'<text class="c-label" x="{x+bw/2:.1f}" y="{mt+ih+20:.1f}" text-anchor="middle">{esc(labels[i])}</text>')
    parts.append(f'<line class="c-axis" x1="{ml}" y1="{mt+ih:.1f}" x2="{width-mr}" y2="{mt+ih:.1f}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def grouped_bars(groups, series, title, width=680, height=320, ml=18, mr=40,
                 mt=46, mb=58, ymax=18, fid="g"):
    """groups: list of group labels. series: list of (name, cls, [values]).
    Two bars per group side by side."""
    iw = width - ml - mr
    ih = height - mt - mb
    n = len(groups)
    gap = iw / n
    ns = len(series)
    bw = gap * 0.30
    cluster = bw * ns + 4
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{fid}-t">',
        f'<title id="{fid}-t">{esc(title)}</title>',
        f'<text class="c-title" x="{ml}" y="22">{esc(title)}</text>',
    ]
    for frac in (0, 0.5, 1.0):
        y = mt + ih - ih * frac
        parts.append(f'<line class="c-grid" x1="{ml}" y1="{y:.1f}" x2="{width-mr}" y2="{y:.1f}"/>')
        parts.append(f'<text class="c-label-sm" x="{width-mr+4}" y="{y+4:.1f}">{ymax*frac:.0f}</text>')
    for gi, glabel in enumerate(groups):
        cx = ml + gap * gi + gap / 2
        x0 = cx - cluster / 2
        for si, (sname, scls, vals) in enumerate(series):
            v = vals[gi]
            bh = ih * v / ymax
            x = x0 + si * (bw + 4)
            y = mt + ih - bh
            parts.append(f'<rect class="{scls}" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2"/>')
            parts.append(f'<text class="c-label-sm" x="{x+bw/2:.1f}" y="{y-5:.1f}" text-anchor="middle">{v}</text>')
        parts.append(f'<text class="c-label" x="{cx:.1f}" y="{mt+ih+20:.1f}" text-anchor="middle">{esc(glabel)}</text>')
    parts.append(f'<line class="c-axis" x1="{ml}" y1="{mt+ih:.1f}" x2="{width-mr}" y2="{mt+ih:.1f}"/>')
    # legend
    lx = ml + 4
    ly = height - 16
    for sname, scls, _ in series:
        parts.append(f'<rect class="{scls}" x="{lx}" y="{ly-10}" width="13" height="13" rx="2"/>')
        parts.append(f'<text class="c-label" x="{lx+19}" y="{ly+1}">{esc(sname)}</text>')
        lx += 30 + len(sname) * 8
    parts.append("</svg>")
    return "\n".join(parts)


def scatter(points, title, xlabel, ylabel, width=680, height=330, ml=54, mr=24,
            mt=46, mb=52, xmax=0.5, ymax=50, fid="s"):
    """points: list of (x, y, label, highlight_bool). Connected by a frontier line."""
    iw = width - ml - mr
    ih = height - mt - mb

    def px(x):
        return ml + iw * x / xmax

    def py(y):
        return mt + ih - ih * y / ymax
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{fid}-t">',
        f'<title id="{fid}-t">{esc(title)}</title>',
        f'<text class="c-title" x="{ml-36}" y="22">{esc(title)}</text>',
    ]
    for frac in (0, 0.5, 1.0):
        y = py(ymax * frac)
        parts.append(f'<line class="c-grid" x1="{ml}" y1="{y:.1f}" x2="{width-mr}" y2="{y:.1f}"/>')
        parts.append(f'<text class="c-label-sm" x="{ml-8}" y="{y+4:.1f}" text-anchor="end">{ymax*frac:.0f}%</text>')
    # frontier line
    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y, *_ in points)
    parts.append(f'<polyline class="c-line" points="{pts}"/>')
    for x, y, label, hi in points:
        cls = "c-dot-hi" if hi else "c-dot"
        r = 7 if hi else 5
        parts.append(f'<circle class="{cls}" cx="{px(x):.1f}" cy="{py(y):.1f}" r="{r}"/>')
        anchor = "start" if x < xmax * 0.7 else "end"
        dx = 12 if anchor == "start" else -12
        vcls = "c-val" if hi else "c-label"
        parts.append(f'<text class="{vcls}" x="{px(x)+dx:.1f}" y="{py(y)+4:.1f}" text-anchor="{anchor}">{esc(label)}</text>')
    parts.append(f'<line class="c-axis" x1="{ml}" y1="{mt+ih:.1f}" x2="{width-mr}" y2="{mt+ih:.1f}"/>')
    parts.append(f'<line class="c-axis" x1="{ml}" y1="{mt:.1f}" x2="{ml}" y2="{mt+ih:.1f}"/>')
    parts.append(f'<text class="c-label-sm" x="{ml+iw/2:.1f}" y="{height-10:.1f}" text-anchor="middle">{esc(xlabel)}</text>')
    parts.append(f'<text class="c-label-sm" x="{ml-40:.1f}" y="{mt+ih/2:.1f}" text-anchor="middle" transform="rotate(-90 {ml-40:.1f} {mt+ih/2:.1f})">{esc(ylabel)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def funnel(stages, title, width=680, height=250, ml=18, mr=18, mt=46, mb=20,
           fid="f"):
    """stages: list of (label, sublabel, width_frac, highlight_bool)."""
    iw = width - ml - mr
    rows = len(stages)
    rh = (height - mt - mb) / rows
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{fid}-t">',
        f'<title id="{fid}-t">{esc(title)}</title>',
        f'<text class="c-title" x="{ml}" y="22">{esc(title)}</text>',
    ]
    for i, (label, sub, frac, hi) in enumerate(stages):
        bw = iw * frac
        x = ml + (iw - bw) / 2
        y = mt + i * rh + 6
        bh = rh - 12
        cls = "c-bar" if hi else "c-bar-muted"
        parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3"/>')
        parts.append(f'<text class="c-val" x="{width/2:.1f}" y="{y+bh/2+1:.1f}" text-anchor="middle" style="fill:var(--bg)">{esc(sub)}</text>')
        parts.append(f'<text class="c-label" x="{ml}" y="{y+bh/2+1:.1f}">{esc(label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write(name, svg, caption, fid):
    path = os.path.join(OUT, name + ".svg")
    with open(path, "w") as f:
        f.write(figure(svg, caption, fid))
    print("wrote", path)


# ---- Chart 1 (GATE): active-learning recall bars (post 4) ----
write(
    "recall-bars",
    vbars(
        values=[25, 95, 93],
        labels=["Random", "Greedy", "UCB"],
        vlabels=["25%", "95%", "93%"],
        title="Top-100 recall by acquisition strategy",
        highlight=1,
        ymax=100,
        fid="recall",
    ),
    "Top-100 recall on a 400/2000 labeling budget. Both active strategies "
    "recover ~94% of the best structures; greedy and UCB essentially tie.",
    "recall",
)

# ---- Chart 2: negation logit grouped bars (post 3) ----
write(
    "negation-logits",
    grouped_bars(
        groups=["France", "star", "animals", "four"],
        series=[
            ("affirmative", "c-bar-muted", [16.93, 12.38, 10.29, 14.84]),
            ('with "not"', "c-bar", [16.42, 13.18, 11.81, 16.29]),
        ],
        title="Target-token logit, with and without “not”",
        ymax=18,
        fid="neg",
    ),
    "Adding “not” barely moves the target logit — and on three of four "
    "prompts it raises it. The negation is read, but it doesn’t suppress the answer.",
    "neg",
)

# ---- Chart 3: static-analysis cost/F1 Pareto scatter (post 5) ----
write(
    "cost-f1",
    scatter(
        points=[
            (0.0, 0.5, "static ~0%", False),
            (0.01, 20, "+light LLM", False),
            (0.08, 40, "hybrid — $0.08, ~40%", True),
            (0.44, 45, "full frontier", False),
        ],
        title="Accuracy vs cost per contract",
        xlabel="cost per contract (USD)  —  $0  →  $0.44",
        ylabel="F1",
        xmax=0.5,
        ymax=50,
        fid="cf",
    ),
    "The cost/accuracy frontier. The hybrid point buys ~40% F1 at $0.08 — "
    "nearly all the accuracy of full frontier reasoning at a fraction of the cost.",
    "cf",
)

# ---- Chart 4: false-positive funnel (post 5) ----
write(
    "fp-funnel",
    funnel(
        stages=[
            ("single analyzer", "56 false positives", 0.62, False),
            ("3-tool consensus", "<10", 0.30, False),
            ("LLM on the filtered set", "0", 0.10, True),
        ],
        title="False positives, by filtering stage",
        fid="fp",
    ),
    "Three-tool consensus cuts 56 false positives to under 10; the LLM, handed "
    "only the agreed shortlist, adds none.",
    "fp",
)

if __name__ == "__main__":
    pass
