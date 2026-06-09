#!/usr/bin/env python3
"""Authoring tool — generates 1280x640 GitHub social-preview cards for the
pinned repos, in the same warm palette/typography as the per-post OG cards
(see gen_og.py). GitHub repos with a custom social image get ~64% more clicks,
and matching the site's identity ties the two surfaces together.

Output: _charts/repo-cards/<repo>.png  (1280x640, 1.91:1).
Upload each manually: repo → Settings → Social preview → Upload an image.

Usage:  python3 _charts/gen_repo_cards.py
"""
import os, subprocess, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_charts", "repo-cards")
TMP = os.path.join(ROOT, "_charts", "_ogtmp")

BG, INK, ACCENT, MUTED = "#fbfaf7", "#1b1b1a", "#a23c24", "#5f5e57"
CHROME = ("/Users/toma/Library/Caches/ms-playwright/chromium-1223/"
          "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
          "Google Chrome for Testing")

# repo -> (headline, tech line). Headline is the serif hero; repo name is the
# accent mono mark; tech line mirrors the repo topics for consistency.
REPOS = {
    "lock-mint-bridge-lab": (
        "Auditing a lock-and-mint bridge, end to end",
        "solidity · foundry invariants · slither · halmos"),
    "anthropic-fellowship": (
        "BRIDGE-bench: can an LLM find a bridge hack?",
        "security research · llm · ~0% vs ~40% f1"),
    "quantgroup": (
        "A constant-product AMM, built to be attacked",
        "solidity · invariant tests · wake fuzz · swc/cwe"),
    "zk-dark-chess": (
        "ZK move-legality over a Poseidon commitment",
        "circom · groth16 · verified on-chain"),
    "fhe-dark-chess": (
        "Fog-of-war chess over an encrypted board",
        "rust · zama tfhe-rs · fhe"),
    "cowswaprouter": (
        "A TWAP order splitter for CoW Protocol",
        "solidity · cow protocol · wake fuzz suite"),
    # second tier — extend the card treatment beyond the pinned set
    "gnome-materials": (
        "Active learning for materials discovery",
        "python · chgnet · 95% recall @ 20% budget"),
    "consensus-benchmarking-suite": (
        "Byzantine fault tolerance, benchmarked",
        "python · consensus · pow vs pos · latency"),
    "satoshi_flip": (
        "On-chain randomness, done right",
        "sui move · bls · vrf analysis"),
    "sensorforge": (
        "Edge AI inference on Jetson Orin",
        "python · jetson · real-time at the edge"),
    "chess": (
        "A full chess engine, on-chain",
        "solidity · move validation · game state"),
}


def title_size(t):
    n = len(t)
    if n <= 38:
        return 64
    if n <= 50:
        return 56
    return 48


def card_html(repo, headline, tech, fs):
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{margin:0;box-sizing:border-box}}
html,body{{width:1280px;height:640px;background:{BG};overflow:hidden}}
.card{{width:1280px;height:640px;padding:84px 100px;display:flex;flex-direction:column;
  justify-content:space-between;font-family:Georgia,'Times New Roman',serif;color:{INK};background:{BG}}}
.mark{{font-family:'Courier New',monospace;font-size:30px;color:{ACCENT};letter-spacing:.02em}}
.title{{font-size:{fs}px;line-height:1.12;font-weight:600;max-width:1080px;overflow-wrap:break-word}}
.row{{display:flex;justify-content:space-between;align-items:baseline;
  font-family:'Courier New',monospace;font-size:24px;color:{MUTED}}}
.tech{{color:{ACCENT}}}
</style></head><body><div class="card">
<div class="mark">0xSoftBoi/{html.escape(repo)}</div>
<div class="title">{html.escape(headline)}</div>
<div class="row"><span class="tech">{html.escape(tech)}</span><span>github.com/0xSoftBoi</span></div>
</div></body></html>"""


def render(html_str, out_png, w, h):
    os.makedirs(TMP, exist_ok=True)
    hp = os.path.join(TMP, "repocard.html")
    open(hp, "w").write(html_str)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-color-profile=srgb",
                    f"--window-size={w},{h}", f"--screenshot={out_png}",
                    "file://" + hp], capture_output=True)
    return os.path.exists(out_png)


def main():
    os.makedirs(OUT, exist_ok=True)
    for repo, (headline, tech) in REPOS.items():
        out = os.path.join(OUT, repo + ".png")
        ok = render(card_html(repo, headline, tech, title_size(headline)), out, 1280, 640)
        print(("ok " if ok else "FAIL "), os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
