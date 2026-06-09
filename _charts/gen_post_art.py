#!/usr/bin/env python3
"""Per-post themed OG cards: FLUX art matched to each writing's subject,
composited magazine-style (themed art on top, post title below) so social
unfurls stay legible while the visual matches the post.

Output: assets/og/<slug>.png (1200x630), overwriting the generic text cards.

SETUP:  pip install huggingface_hub pillow ; export HF_TOKEN=hf_xxx
RUN:    python3 _charts/gen_post_art.py            # all posts
        python3 _charts/gen_post_art.py the-bridge-that-paid-twice   # one post
"""
import os, re, sys, glob, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OG = os.path.join(ROOT, "assets", "og")
TMP = os.path.join(ROOT, "_charts", "_ogtmp")
MODEL = os.environ.get("ART_MODEL", "black-forest-labs/FLUX.1-schnell")
CHROME = ("/Users/toma/Library/Caches/ms-playwright/chromium-1223/"
          "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
          "Google Chrome for Testing")
BG, INK, ACCENT, MUTED = "#fbfaf7", "#1b1b1a", "#a23c24", "#5f5e57"

STYLE = ("minimalist abstract editorial artwork, warm off-white background, terracotta "
         "and burnt-sienna accents, generous negative space, flat muted palette, subtle "
         "paper grain, soft diffused light, no text, no logos, no lettering, tasteful, "
         "restrained, fine-art print")

# slug -> themed motif (the subject of each writing)
MOTIFS = {
    "an-amm-built-to-be-attacked": "a constant-product price curve under crossed attack arrows, a liquidity pool cracking",
    "when-it-cant-explain-what-it-sees-it-asks": "a sensor eye over a blurred uncertain field resolving into a question",
    "the-model-reads-not-it-just-cant-use-it": "a neural attention lattice, a logit lens focusing scattered tokens",
    "greedy-was-enough-active-learning-pretrained-potential": "a crystalline molecular lattice with a few highlighted selected nodes",
    "static-analysis-scores-zero-on-real-exploits": "a rigid scanner grid missing a hidden compositional flaw, a stark zero versus forty",
    "recursive-types-finite-values-eip712-alloy": "a self-referential type tree, nested struct brackets folding into themselves",
    "post-quantum-proof-shor-breaks-anyway": "a cryptographic lattice shattering under a quantum wavefront",
    "auditing-my-own-bridge": "a lock-and-mint bridge over a ledger, a closed accounting seal",
    "how-cow-protocol-settles": "intersecting intent arrows settling at one clearing price, a coincidence-of-wants ring",
    "the-on-chain-randomness-landscape": "a landscape of dice and beacons, entropy scattering into ordered draws",
    "the-other-side-of-the-wall": "an encrypted wall with a chessboard glowing faintly through it",
    "verifiable-isnt-trustless-onchain-randomness": "a coin mid-flip beside a verifiable beacon, a trust boundary line",
    "what-a-zk-proof-proves": "a sealed envelope emitting a single verified checkmark behind a veil",
    "zk-dark-chess": "a fog-of-war chessboard over a Poseidon commitment lattice, hidden pieces",
    "anatomy-of-a-fake-dice-game": "loaded dice with a hidden predetermined seed, a rigged wheel",
    "anatomy-of-a-memecoin-honeypot": "a honeypot jar trapping a coin behind a one-way valve",
    "the-bridge-that-paid-twice": "a bridge paying out twice across a forked chain after a reorg",
    "the-index-fund-that-held-the-wrong-asset": "a basket of asset tokens that is secretly empty, a mismatched gauge",
    "rebuilding-a-perps-dex-from-its-docs": "a perpetual-futures price chart reconstructed from blueprint documents, a hidden house-edge tilt",
    "a-social-good-protocol-built-by-an-agent-fleet": "a fleet of small agent nodes collaboratively assembling a contract, one node inspecting another's work",
    "running-an-op-stack-l2-with-reth": "a layered rollup stack settling onto a base chain, four interlocking process blocks sharing a key, a pipeline of CI checks",
    "who-audits-the-auditor": "an auditor inspecting another auditor, a lie-detector needle sweeping a grid of code detectors, recursive scrutiny",
    "an-arb-bot-with-no-slippage-is-a-sandwich": "a trade caught between two sandwich slices, a flash-loan arbitrage loop with a slippage gap, MEV",
}


def front_matter(text):
    m = re.match(r"\A---\s*\n(.*?\n)---\s*\n", text, re.S)
    fm = {}
    if m:
        t = re.search(r'^title:\s*"?(.*?)"?\s*$', m.group(1), re.M)
        tg = re.search(r"^tags:\s*\[(.*?)\]", m.group(1), re.M)
        if t: fm["title"] = t.group(1).replace('\\"', '"')
        if tg: fm["tags"] = [x.strip() for x in tg.group(1).split(",") if x.strip()]
    return fm


def title_size(t):
    n = len(t)
    return 60 if n <= 38 else 52 if n <= 58 else 44 if n <= 80 else 38


def card_html(bg_path, title, tags_line, fs):
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{margin:0;box-sizing:border-box}}
html,body{{width:1200px;height:630px;background:{BG};overflow:hidden}}
.card{{width:1200px;height:630px;display:flex;flex-direction:column;background:{BG}}}
.art{{height:360px;width:1200px;background:url('file://{bg_path}') center/cover no-repeat;
  border-bottom:1px solid #e7e3da}}
.txt{{flex:1;padding:34px 90px;display:flex;flex-direction:column;justify-content:space-between;
  font-family:Georgia,'Times New Roman',serif;color:{INK}}}
.mark{{font-family:'Courier New',monospace;font-size:24px;color:{ACCENT};letter-spacing:.02em}}
.title{{font-size:{fs}px;line-height:1.1;font-weight:600;max-width:1020px;overflow-wrap:break-word}}
.row{{display:flex;justify-content:space-between;align-items:baseline;
  font-family:'Courier New',monospace;font-size:22px;color:{MUTED}}}
.tags{{color:{ACCENT}}}
</style></head><body><div class="card">
<div class="art"></div>
<div class="txt">
  <div class="mark">Tsolmondorj Natsagdorj &middot; security &amp; systems</div>
  <div class="title">{html.escape(title)}</div>
  <div class="row"><span class="tags">{html.escape(tags_line)}</span><span>0xsoftboi.github.io</span></div>
</div></div></body></html>"""


def render(html_str, out_png):
    os.makedirs(TMP, exist_ok=True)
    hp = os.path.join(TMP, "postcard.html")
    open(hp, "w").write(html_str)
    import subprocess
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-color-profile=srgb",
                    "--window-size=1200,630", f"--screenshot={out_png}", "file://" + hp],
                   capture_output=True)


def main(which):
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=os.environ.get("HF_TOKEN"))
    os.makedirs(OG, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(ROOT, "_posts", "*.md"))):
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(f))[:-3]
        if which and slug not in which:
            continue
        fm = front_matter(open(f).read())
        title = fm.get("title", slug)
        tags_line = " · ".join(fm.get("tags", [])[:4])
        motif = MOTIFS.get(slug, "an abstract security and systems motif")
        print(f"art: {slug} ...", flush=True)
        img = client.text_to_image(f"{motif}, {STYLE}", model=MODEL, width=1200, height=384)
        bg = os.path.join(TMP, f"bg-{slug}.png")
        img.save(bg)
        # text-less art doubles as the in-page post hero
        posts_art = os.path.join(ROOT, "assets", "art", "posts")
        os.makedirs(posts_art, exist_ok=True)
        img.save(os.path.join(posts_art, slug + ".png"))
        render(card_html(bg, title, tags_line, title_size(title)), os.path.join(OG, slug + ".png"))
        print(f"  -> assets/og/{slug}.png + assets/art/posts/{slug}.png", flush=True)


if __name__ == "__main__":
    main(set(a for a in sys.argv[1:] if not a.startswith("-")))
