---
layout: post
title: "The model reads \"not\" — it just can't use it"
date: 2026-04-22
tags: [interpretability, llms, ai]
image: /assets/og/the-model-reads-not-it-just-cant-use-it.png
excerpt: "Ask GPT-2 to complete \"Paris is not the capital of\" and it still says France. The interesting part isn't that it fails — it's that the model clearly attends to the word \"not\" and then can't make that signal change its answer. Here's where, inside the network, the gating breaks."
---

Language models are famously bad at negation. Ask GPT-2 small to finish *"Paris is the capital of"* and it says France; ask it to finish *"Paris is **not** the capital of"* and it says France again, barely flinching. This is old news behaviorally — [Ettinger (2020)](https://arxiv.org/abs/1907.13528) showed BERT predicts "bird" for both *"A robin is a \_\_\_"* and *"A robin is not a \_\_\_"*, and [Truong et al. (2023)](https://arxiv.org/abs/2306.08189) confirmed it systematically across model families. I went looking for the *mechanism*: where in the forward pass does the "not" get lost?

The answer turned out to be more specific, and weirder, than "the model ignores negation."

* TOC
{:toc}

## Weirder than ignoring it

First, the behavior — the logit of the target token with and without "not," for four of the six prompts I ran on GPT-2 small:

| Prompt | Target | affirm | negated | change |
|---|---|--:|--:|--:|
| "Paris is the capital of" | France | 16.93 | 16.42 | −3.0% |
| "The sun is a" | star | 12.38 | 13.18 | **+6.5%** |
| "Dogs are" | animals | 10.29 | 11.81 | **+14.8%** |
| "Two plus two equals" | four | 14.84 | 16.29 | **+9.8%** |

<figure class="chart">
<svg viewBox="0 0 680 320" role="img" aria-labelledby="neg-t">
<title id="neg-t">Target-token logit, with and without “not”</title>
<text class="c-title" x="18" y="22">Target-token logit, with and without “not”</text>
<line class="c-grid" x1="18" y1="262.0" x2="640" y2="262.0"/>
<text class="c-label-sm" x="644" y="266.0">0</text>
<line class="c-grid" x1="18" y1="154.0" x2="640" y2="154.0"/>
<text class="c-label-sm" x="644" y="158.0">9</text>
<line class="c-grid" x1="18" y1="46.0" x2="640" y2="46.0"/>
<text class="c-label-sm" x="644" y="50.0">18</text>
<rect class="c-bar-muted" x="47.1" y="58.8" width="46.6" height="203.2" rx="2"/>
<text class="c-label-sm" x="70.4" y="53.8" text-anchor="middle">16.93</text>
<rect class="c-bar" x="97.8" y="65.0" width="46.6" height="197.0" rx="2"/>
<text class="c-label-sm" x="121.1" y="60.0" text-anchor="middle">16.42</text>
<text class="c-label" x="95.8" y="282.0" text-anchor="middle">France</text>
<rect class="c-bar-muted" x="202.6" y="113.4" width="46.6" height="148.6" rx="2"/>
<text class="c-label-sm" x="225.9" y="108.4" text-anchor="middle">12.38</text>
<rect class="c-bar" x="253.2" y="103.8" width="46.6" height="158.2" rx="2"/>
<text class="c-label-sm" x="276.6" y="98.8" text-anchor="middle">13.18</text>
<text class="c-label" x="251.2" y="282.0" text-anchor="middle">star</text>
<rect class="c-bar-muted" x="358.1" y="138.5" width="46.6" height="123.5" rx="2"/>
<text class="c-label-sm" x="381.4" y="133.5" text-anchor="middle">10.29</text>
<rect class="c-bar" x="408.8" y="120.3" width="46.6" height="141.7" rx="2"/>
<text class="c-label-sm" x="432.1" y="115.3" text-anchor="middle">11.81</text>
<text class="c-label" x="406.8" y="282.0" text-anchor="middle">animals</text>
<rect class="c-bar-muted" x="513.6" y="83.9" width="46.6" height="178.1" rx="2"/>
<text class="c-label-sm" x="536.9" y="78.9" text-anchor="middle">14.84</text>
<rect class="c-bar" x="564.2" y="66.5" width="46.6" height="195.5" rx="2"/>
<text class="c-label-sm" x="587.6" y="61.5" text-anchor="middle">16.29</text>
<text class="c-label" x="562.2" y="282.0" text-anchor="middle">four</text>
<line class="c-axis" x1="18" y1="262.0" x2="640" y2="262.0"/>
<rect class="c-bar-muted" x="22" y="294" width="13" height="13" rx="2"/>
<text class="c-label" x="41" y="305">affirmative</text>
<rect class="c-bar" x="140" y="294" width="13" height="13" rx="2"/>
<text class="c-label" x="159" y="305">with "not"</text>
</svg>
<figcaption>Adding “not” barely moves the target logit — and on three of four prompts it raises it. The negation is read, but it doesn’t suppress the answer.</figcaption>
</figure>

Three of those four go the wrong way; across all six prompts, four do. Inserting "not" doesn't just fail to suppress the answer — it *raises* the target's probability. "Dogs are not animals" makes the model **more** confident in "animals." This isn't simple insensitivity. The negation is doing something, and the something points the wrong way.

## The model does read "not"

The easy hypothesis is that the token gets dropped. It doesn't. At the prediction position, attention head L11H8 puts **37.7%** of its weight on the "not" token. The model is looking right at it. So the failure isn't perception — it's that the signal can't reach the place where the answer is decided.

To find that place, I patched: take the residual stream at the "not" position and overwrite it with its value from the affirmative prompt — erasing the negation surgically — and watch where the logit gap moves. The negation effect concentrates **early**, in layers 0–2; patching at L0 recovers about 130% of the logit gap. So by the end of layer 2, the network has computed "there's a negation here."

And then the other thing happens. From a separate set of factual-recall experiments, the capital→country association in this kind of prompt resolves **late** — around layers 9–10, roughly 83% of the way through the network. By the time the factual lookup fires, the negation signal computed back at L0–2 has been diluted across positions and heads. You can watch it lose: the "France" direction in the residual stream drops from 186 to 167 activation units at L10 — the negation *is* pushing against it — but that's only about a 10% reduction, nowhere near enough to flip the prediction.

<figure class="chart">
<svg viewBox="0 0 680 270" role="img" aria-labelledby="ly-t">
<title id="ly-t">Across GPT-2 small's 12 layers, negation is computed early (0–2) and factual recall late (9–10); the two never merge</title>
<defs>
<marker id="c-arrowhead-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker>
</defs>
<text class="c-title" x="20" y="26">Two computations that never meet</text>
<rect class="c-box-accent c-fill-soft" x="40" y="58" width="150" height="36" rx="5"/>
<text class="c-val" x="44" y="50">negation detected</text>
<rect class="c-box c-fill-soft" x="490" y="58" width="100" height="36" rx="5"/>
<text class="c-val" x="494" y="50">factual recall</text>
<line class="c-axis" x1="40" y1="112" x2="640" y2="112"/>
<text class="c-label-sm" x="40" y="128">L0</text>
<text class="c-label-sm" x="190" y="128" text-anchor="middle">L2</text>
<text class="c-label-sm" x="490" y="128" text-anchor="middle">L9</text>
<text class="c-label-sm" x="640" y="128" text-anchor="end">L11</text>
<text class="c-label-sm" x="44" y="146">~130% of the logit gap recovers here</text>
<text class="c-label-sm" x="590" y="146" text-anchor="end">capital → country resolves here</text>
<path class="c-arrow-muted" d="M150,150 C280,196 400,196 500,152" stroke-dasharray="5 4"/>
<text class="c-label-sm" x="325" y="218" text-anchor="middle">The negation signal, diluted across positions, reaches L10 as only a ~10% pull —</text>
<text class="c-label-sm" x="325" y="234" text-anchor="middle">never enough to flip the prediction. The “not” is known; it just can’t gate the fact.</text>
</svg>
<figcaption>Negation is a side road processed early and quietly; factual recall is a highway that opens late and loud. The architecture gives the fact far more runway than the operator meant to override it.</figcaption>
</figure>

That's the whole story in one image. **Negation is a side road processed early and quietly; factual recall is a highway that opens late and loud.** The two never properly merge. The model knows there's a "not," and it knows the capital of France, and the architecture gives the fact far more computational runway than the operator that was supposed to override it.

## Why "not" sometimes helps

That still leaves the boost — why "Dogs are not" *increases* "animals." The most likely explanation is mundane and a little funny: training-data co-occurrence. Sentences like *"two plus two does not equal four — wait, yes it does"* exist; people discuss correct facts constantly inside negated constructions. So "does not equal" co-occurs with "four" all over the corpus. The model has learned that negation words, in a factual context, are *associated with the correct answer*, because that's the distribution it saw. It's optimizing predictive cues, not computing truth conditions — exactly Ettinger's framing.

## What this is and isn't

I want to be precise about the contribution, because mech interp has an overclaiming problem. The behavioral result is not mine — negation failure is well-trodden. What I'm adding is incremental and concrete: the **layer-level localization** (negation at L0–2, recall at L9–10, and the mismatch between them), a **quantified booster effect** (7 of 12 cases across three models show no-effect-or-boost; mean +4.9% on GPT-2 small), and the **attention evidence** that the token is read, not dropped. This is me learning the toolkit by taking a known failure apart, not announcing a discovery.

But the shape of it is the same thing I chase everywhere else. The bug isn't in the perception and it isn't in the knowledge — it's in the *seam* between them, where a signal that exists fails to gate a computation that happens somewhere else. That's the same place [a bridge exploit lives](/blog/auditing-my-own-bridge/), and the same place [a parser bug lives](/blog/recursive-types-finite-values-eip712-alloy/): not in either correct half, but in the join nobody tested.

*Code and the full writeup are in [the repo](https://github.com/0xSoftBoi/anthropic-fellowship/tree/main/mech-interp). References: Ettinger 2020, Truong et al. 2023, [Meng et al. 2022](https://arxiv.org/abs/2202.05262) (causal tracing), Berglund et al. 2023 (the Reversal Curse).*
