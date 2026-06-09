#!/usr/bin/env python3
"""Generate on-brand AI artwork (banners / page heroes / OG) for the site and
GitHub profile, via Hugging Face Inference (FLUX.1-schnell by default).

Why a script and not the MCP: the claude.ai HF connector has `invoke` disabled
(gradio=none), so images must be produced from a real HF token. This runs
anywhere you have one.

SETUP (once):
    pip install huggingface_hub pillow
    export HF_TOKEN=hf_xxx            # or: huggingface-cli login

RUN:
    python3 _charts/gen_ai_art.py            # all assets
    python3 _charts/gen_ai_art.py home og    # only named assets

Art direction: tasteful, abstract, on-palette (warm off-white #fbfaf7 +
terracotta #a23c24), heavy negative space, NO text/logos — text is overlaid
crisply elsewhere. Keeps the minimalist security-engineer brand intact.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.environ.get("ART_MODEL", "black-forest-labs/FLUX.1-schnell")

STYLE = ("minimalist abstract editorial artwork, warm off-white paper background, "
         "terracotta and burnt-sienna accents, generous negative space, flat muted "
         "palette, subtle paper grain, soft diffused light, no text, no logos, no "
         "lettering, tasteful, restrained, fine-art print quality")

# name -> (motif, width, height, output path relative to repo root)
ASSETS = {
    "home":     ("fine geometric line-work suggesting cryptographic lattices, hash trees and cross-chain bridge cables",
                 1600, 480, "assets/art/home-hero.png"),
    "security": ("interlocking padlocks dissolving into a merkle tree, faint hairline fault-lines through a ledger grid",
                 1600, 480, "assets/art/security-hero.png"),
    "research": ("scattered data points and a faint regression curve over a crystalline molecular lattice, an active-learning selection frontier",
                 1600, 480, "assets/art/research-hero.png"),
    "banner":   ("a wide quiet horizon of cryptographic lattice-work and bridge cables fading into negative space",
                 1280, 320, "assets/art/profile-banner.png"),
    "og":       ("balanced abstract composition of interlocking lattices and bridge geometry, centered, calm",
                 1200, 630, "assets/og/default.png"),
}


def main(which):
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        sys.exit("missing dep: pip install huggingface_hub pillow")
    token = os.environ.get("HF_TOKEN")
    client = InferenceClient(token=token)  # falls back to cached login if no env token
    os.makedirs(os.path.join(ROOT, "assets", "art"), exist_ok=True)
    for name in which:
        if name not in ASSETS:
            print("skip unknown:", name); continue
        motif, w, h, out = ASSETS[name]
        prompt = f"{motif}, {STYLE}"
        print(f"generating {name} ({w}x{h}) via {MODEL} ...")
        img = client.text_to_image(prompt, model=MODEL, width=w, height=h)
        path = os.path.join(ROOT, out)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
        print("  ->", out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    main(args or list(ASSETS.keys()))
