---
layout: post
title: "Greedy was enough: active learning on top of a pretrained potential"
date: 2026-05-10
series: "Applied ML"
tags: [ml, materials, active-learning, ai]
image: /assets/og/greedy-was-enough-active-learning-pretrained-potential.png
excerpt: "I built a GNoME-style active-learning loop to find stable crystals on a labeling budget. The uncertainty-aware strategy I expected to win basically tied the greedy one — and that tie held from a 2,000-structure demo up to the full 256K-structure benchmark. The tie is the actual result."
---

DeepMind's [GNoME](https://www.nature.com/articles/s41586-023-06735-9) found a couple hundred thousand stable inorganic materials by pairing graph neural networks with active learning — a simple loop: train a cheap surrogate, let it pick which candidates are worth an expensive simulation, label those, repeat. The choice of *which to pick* is the whole game, and I wanted to know how much it matters when the surrogate is already very good.

So I built a small version: a pool of 2,000 candidate structures from the Materials Project, a pretrained [CHGNet](https://github.com/CederGroupHub/chgnet) potential as the surrogate, and a labeling budget of 400 — 20% of the pool. The question: with that budget, how many of the 100 most stable structures can you actually find, and does a clever acquisition strategy beat a dumb one?

## The result

| Strategy | Top-100 recall | Best found (eV/atom) | Labeled |
|---|:--:|:--:|:--:|
| Random | 25% | −4.375 | 400 / 2000 |
| Greedy (mean) | **95%** | −4.403 | 400 / 2000 |
| UCB (uncertainty-aware) | 93% | −4.403 | 400 / 2000 |

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="recall-t">
<title id="recall-t">Top-100 recall by acquisition strategy</title>
<text class="c-title" x="18" y="22">Top-100 recall by acquisition strategy</text>
<line class="c-grid" x1="18" y1="254.0" x2="662" y2="254.0"/>
<text class="c-label-sm" x="662" y="250.0" text-anchor="end">0%</text>
<line class="c-grid" x1="18" y1="149.0" x2="662" y2="149.0"/>
<text class="c-label-sm" x="662" y="145.0" text-anchor="end">50%</text>
<line class="c-grid" x1="18" y1="44.0" x2="662" y2="44.0"/>
<text class="c-label-sm" x="662" y="40.0" text-anchor="end">100%</text>
<rect class="c-bar-muted" x="69.5" y="201.5" width="111.6" height="52.5" rx="2"/>
<text class="c-val" x="125.3" y="194.5" text-anchor="middle">25%</text>
<text class="c-label" x="125.3" y="274.0" text-anchor="middle">Random</text>
<rect class="c-bar" x="284.2" y="54.5" width="111.6" height="199.5" rx="2"/>
<text class="c-val" x="340.0" y="47.5" text-anchor="middle">95%</text>
<text class="c-label" x="340.0" y="274.0" text-anchor="middle">Greedy</text>
<rect class="c-bar-muted" x="498.9" y="58.7" width="111.6" height="195.3" rx="2"/>
<text class="c-val" x="554.7" y="51.7" text-anchor="middle">93%</text>
<text class="c-label" x="554.7" y="274.0" text-anchor="middle">UCB</text>
<line class="c-axis" x1="18" y1="254.0" x2="662" y2="254.0"/>
</svg>
<figcaption>Top-100 recall on a 400/2000 labeling budget. Both active strategies recover ~94% of the best structures; greedy and UCB essentially tie.</figcaption>
</figure>

Both active strategies recovered 93–95% of the best structures while labeling a fifth of the pool; random sampling got 25%. That part is the expected GNoME-style win — active learning works, and it works hard.

The part I didn't expect, and the reason I think this is worth writing down: **greedy and UCB essentially tied.** I went in assuming the uncertainty-aware strategy — pick where the surrogate is both promising *and* unsure, to balance exploration against exploitation — would pull ahead. It didn't.

## Why the clever method didn't win

The tie isn't a null result; it's a measurement of the surrogate. UCB only beats greedy when the surrogate's uncertainty carries information greedy is ignoring — when "promising but unsure" candidates turn out to be where the wins hide. CHGNet is a *pretrained, physics-informed* potential. Its mean prediction of stability is already accurate enough across this pool that there's very little signal left in its uncertainty for exploration to exploit. The exploitation term alone is almost optimal, so adding an exploration term mostly reorders ties.

In other words: the better your prior, the less your uncertainty estimate buys you. You'd expect UCB to pull ahead in the regime where CHGNet is weak — a chemically unusual pool, far from its training distribution, where mean predictions are shaky and the model's "I'm not sure" actually means something. On a pool this well-covered by the pretrained backbone, greedy is enough, and paying for Monte-Carlo-Dropout uncertainty estimates is paying for exploration you don't need.

There's a humbler reading I can't fully rule out, and it's the honest caveat on the result: MC-Dropout is a cheap way to estimate uncertainty and a famously miscalibrated one. Part of the tie might be that UCB never got a fair trial — its "I'm not sure" was noise rather than signal, so the exploration term had nothing real to act on. Distinguishing "uncertainty bought nothing because the mean is already good" from "uncertainty bought nothing because our σ is junk" takes two checks: does the tie survive at real scale, and does the *same* uncertainty ever win when the model is weak? I ran both.

## Does the tie survive at scale?

The 2,000-structure run is a demo, and a single seed. The real test is [WBM](https://matbench-discovery.materialsproject.org/) — the 256,963-structure pool from the Matbench Discovery benchmark, of which 42,825 (16.7%) are actually stable. I ran the same loop there on a 2,200-label budget — *0.9%* of the pool — across five random seeds, so this time the spread is measured, not assumed.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="daf-t">
<title id="daf-t">Discovery Acceleration Factor on WBM, five seeds</title>
<text class="c-title" x="18" y="22">Discovery Acceleration Factor — WBM (256K), 5 seeds</text>
<line class="c-grid" x1="18" y1="254.0" x2="662" y2="254.0"/>
<text class="c-label-sm" x="662" y="250.0" text-anchor="end">0</text>
<line class="c-grid" x1="18" y1="184.0" x2="662" y2="184.0"/>
<text class="c-label-sm" x="662" y="180.0" text-anchor="end">0.5</text>
<line class="c-grid" x1="18" y1="114.0" x2="662" y2="114.0"/>
<text class="c-label-sm" x="662" y="110.0" text-anchor="end">1.0</text>
<line class="c-grid" x1="18" y1="44.0" x2="662" y2="44.0"/>
<text class="c-label-sm" x="662" y="40.0" text-anchor="end">1.5</text>
<rect class="c-bar-muted" x="69.5" y="114.7" width="111.6" height="139.3" rx="2"/>
<line class="c-axis" x1="125.3" y1="110.8" x2="125.3" y2="118.6"/>
<line class="c-axis" x1="119.3" y1="110.8" x2="131.3" y2="110.8"/>
<line class="c-axis" x1="119.3" y1="118.6" x2="131.3" y2="118.6"/>
<text class="c-val" x="125.3" y="104.0" text-anchor="middle">0.995</text>
<text class="c-label" x="125.3" y="274.0" text-anchor="middle">Random</text>
<rect class="c-bar" x="284.2" y="95.2" width="111.6" height="158.8" rx="2"/>
<line class="c-axis" x1="340.0" y1="92.8" x2="340.0" y2="97.6"/>
<line class="c-axis" x1="334.0" y1="92.8" x2="346.0" y2="92.8"/>
<line class="c-axis" x1="334.0" y1="97.6" x2="346.0" y2="97.6"/>
<text class="c-val" x="340.0" y="85.0" text-anchor="middle">1.134</text>
<text class="c-label" x="340.0" y="274.0" text-anchor="middle">Greedy</text>
<rect class="c-bar-muted" x="498.9" y="95.8" width="111.6" height="158.2" rx="2"/>
<line class="c-axis" x1="554.7" y1="92.2" x2="554.7" y2="99.4"/>
<line class="c-axis" x1="548.7" y1="92.2" x2="560.7" y2="92.2"/>
<line class="c-axis" x1="548.7" y1="99.4" x2="560.7" y2="99.4"/>
<text class="c-val" x="554.7" y="85.0" text-anchor="middle">1.130</text>
<text class="c-label" x="554.7" y="274.0" text-anchor="middle">UCB</text>
<line class="c-axis" x1="18" y1="254.0" x2="662" y2="254.0"/>
</svg>
<figcaption>Discovery Acceleration Factor on the full 256K-structure WBM pool (5-seed mean, whiskers ± std). Random sits at 1.0 by construction; a perfect oracle would reach ~6.0. Greedy (1.134 ± 0.017) and UCB (1.130 ± 0.026) overlap completely.</figcaption>
</figure>

The metric is the Discovery Acceleration Factor — how much more often you turn up a stable material than blind screening would. Random is 1.0 by construction; a perfect oracle would hit ~6.0 (one over the prevalence). Greedy lands at 1.134 ± 0.017, UCB at 1.130 ± 0.026. The error bars sit right on top of each other. The tie held — at a hundred times the scale, with the variance finally measured instead of hoped for.

That last part earned its keep. A *single* seed had put UCB ahead, 1.16 to 1.12 — exactly the kind of gap you'd happily write up as "uncertainty wins." Five seeds dissolved it. The honest version of this result only exists because I stopped trusting one run. (And note the modesty of the win itself: 1.13×, not 6×. At 0.9% budget a strong-but-imperfect surrogate helps, but it isn't magic — which is the right frame for asking whether the *clever* version earns the extra cost.)

## Was the uncertainty just noise?

The deeper worry is the one above: maybe MC-Dropout's σ is so miscalibrated that UCB never had a real exploration signal, and greedy won by default rather than on merit. The clean way to check is to run the *same* uncertainty machinery on a model that is actually weak — where exploration *should* pay — and see if it does.

So I did: a 50,000-structure synthetic pool with a graph network trained from scratch, no pretrained prior, genuinely unsure of itself. There, UCB beats greedy by 25 points in top-10 recall, **70% to 45%**. Same dropout, same acquisition rule — it just finally had something to act on.

That's the result that closes the loop. The uncertainty isn't junk; it carries real signal when the model is weak. So the CHGNet tie isn't "our σ is broken" — it's "our prior is good enough that there's nothing left for σ to find." Greedy was enough *because* the surrogate was strong, exactly where you'd predict, and not an inch further.

## A bonus lesson: use the foundation model frozen

One thing I expected to help and it consistently *hurt*: fine-tuning CHGNet on the freshly labeled structures each round. CHGNet was pretrained on 700,000 Materials Project structures; nudging it with a few hundred biased labels is enough to trigger catastrophic forgetting — you trade a broad, well-calibrated prior for a sharp, overfit one, and μ accuracy drops. Frozen won every time. If you're dropping a foundation-model potential into an active-learning loop, the boring move — leave it alone — is the right one.

## The takeaway I keep

This is the same lesson [the rest of my work keeps teaching](/blog/static-analysis-scores-zero-on-real-exploits/) from the other direction: know what your tool's confidence is actually worth before you build on it. A clever acquisition function on top of a strong pretrained model can quietly reduce to "trust the model," and the honest experiment is the one that measures whether the cleverness paid for itself. Here it didn't — and knowing *that*, and why, is more useful than a win would have been.
