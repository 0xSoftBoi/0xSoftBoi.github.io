---
layout: post
title: "Greedy was enough: active learning on top of a pretrained potential"
date: 2026-05-10
tags: [ml, materials, active-learning]
excerpt: "I built a GNoME-style active-learning loop to find stable crystals on a labeling budget. The uncertainty-aware strategy I expected to win basically tied the greedy one — and that tie is the actual result."
---

DeepMind's [GNoME](https://www.nature.com/articles/s41586-023-06735-9) found a couple of hundred thousand stable inorganic materials by combining graph neural networks with active learning: instead of running an expensive simulation on every candidate, you train a cheap surrogate, use it to pick which candidates are worth the expensive label, and repeat. The choice of *which to pick* is the whole game. I wanted to see how much that choice actually matters when your surrogate is already very good.

So I built a small version: a pool of 2,000 candidate structures from the Materials Project, a pretrained [CHGNet](https://github.com/CederGroupHub/chgnet) potential as the surrogate, and a labeling budget of 400 — 20% of the pool. The question: with that budget, how many of the 100 most stable structures can you actually find, and does a clever acquisition strategy beat a dumb one?

## The result

| Strategy | Top-100 recall | Best found (eV/atom) | Labeled |
|---|:--:|:--:|:--:|
| Random | 25% | −4.375 | 400 / 2000 |
| Greedy (mean) | **95%** | −4.403 | 400 / 2000 |
| UCB (uncertainty-aware) | 93% | −4.403 | 400 / 2000 |

Both active strategies recovered 93–95% of the best structures while labeling a fifth of the pool; random sampling got 25%. That part is the expected GNoME-style win — active learning works, and it works hard.

The part I didn't expect, and the reason I think this is worth writing down: **greedy and UCB essentially tied.** I went in assuming the uncertainty-aware strategy — pick where the surrogate is both promising *and* unsure, to balance exploration against exploitation — would pull ahead. It didn't.

## Why the clever method didn't win

The tie isn't a null result; it's a measurement of the surrogate. UCB only beats greedy when the surrogate's uncertainty carries information greedy is ignoring — when "promising but unsure" candidates turn out to be where the wins hide. CHGNet is a *pretrained, physics-informed* potential. Its mean prediction of stability is already accurate enough across this pool that there's very little signal left in its uncertainty for exploration to exploit. The exploitation term alone is almost optimal, so adding an exploration term mostly reorders ties.

In other words: the better your prior, the less your uncertainty estimate buys you. You'd expect UCB to pull ahead in the regime where CHGNet is weak — a chemically unusual pool, far from its training distribution, where mean predictions are shaky and the model's "I'm not sure" actually means something. On a pool this well-covered by the pretrained backbone, greedy is enough, and paying for Monte-Carlo-Dropout uncertainty estimates is paying for exploration you don't need.

## The takeaway I keep

This is the same lesson the rest of my work keeps teaching from the other direction: know what your tool's confidence is actually worth before you build on it. A clever acquisition function on top of a strong pretrained model can quietly reduce to "trust the model," and the honest experiment is the one that measures whether the cleverness paid for itself. Here it didn't — and knowing *that*, and why, is more useful than a win would have been.
