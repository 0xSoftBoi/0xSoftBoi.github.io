---
layout: post
title: "The model reads \"not\" — it just can't use it"
date: 2026-04-22
tags: [interpretability, llms, ai]
excerpt: "Ask GPT-2 to complete \"Paris is not the capital of\" and it still says France. The interesting part isn't that it fails — it's that the model clearly attends to the word \"not\" and then can't make that signal change its answer. Here's where, inside the network, the gating breaks."
---

Language models are famously bad at negation. Ask GPT-2 small to finish *"Paris is the capital of"* and it says France; ask it to finish *"Paris is **not** the capital of"* and it says France again, barely flinching. This is old news behaviorally — [Ettinger (2020)](https://arxiv.org/abs/1907.13528) showed BERT predicts "bird" for both *"A robin is a \_\_\_"* and *"A robin is not a \_\_\_"*, and [Truong et al. (2023)](https://arxiv.org/abs/2306.08189) confirmed it systematically across model families. I went looking for the *mechanism*: where in the forward pass does the "not" get lost?

The answer turned out to be more specific, and weirder, than "the model ignores negation."

## Weirder than ignoring it

First, the behavior, measured as the logit of the target token with and without "not":

| Prompt | Target | affirm | negated | change |
|---|---|--:|--:|--:|
| "Paris is the capital of" | France | 16.93 | 16.42 | −3.0% |
| "The sun is a" | star | 12.38 | 13.18 | **+6.5%** |
| "Dogs are" | animals | 10.29 | 11.81 | **+14.8%** |
| "Two plus two equals" | four | 14.84 | 16.29 | **+9.8%** |

In four of six cases on GPT-2 small, inserting "not" doesn't just fail to suppress the answer — it *raises* its probability. "Dogs are not animals" makes the model **more** confident in "animals." Whatever is happening, it isn't simple insensitivity; the negation is doing something, and the something points the wrong way.

## The model does read "not"

The easy hypothesis is that the token gets dropped. It doesn't. At the prediction position, attention head L11H8 puts **37.7%** of its weight on the "not" token. The model is looking right at it. So the failure isn't perception — it's that the signal can't reach the place where the answer is decided.

To find that place, I patched: take the residual stream at the "not" position and overwrite it with its value from the affirmative prompt — erasing the negation surgically — and watch where the logit gap moves. The negation effect concentrates **early**, in layers 0–2; patching at L0 recovers about 130% of the logit gap. So by the end of layer 2, the network has computed "there's a negation here."

And then the other thing happens. From a separate set of factual-recall experiments, the capital→country association in this kind of prompt resolves **late** — around layers 9–10, roughly 83% of the way through the network. By the time the factual lookup fires, the negation signal computed back at L0–2 has been diluted across positions and heads. You can watch it lose: the "France" direction in the residual stream drops from 186 to 167 activation units at L10 — the negation *is* pushing against it — but that's only about a 10% reduction, nowhere near enough to flip the prediction.

That's the whole story in one image. **Negation is a side road processed early and quietly; factual recall is a highway that opens late and loud.** The two never properly merge. The model knows there's a "not," and it knows the capital of France, and the architecture gives the fact far more computational runway than the operator that was supposed to override it.

## Why "not" sometimes helps

That still leaves the boost — why "Dogs are not" *increases* "animals." The most likely explanation is mundane and a little funny: training-data co-occurrence. Sentences like *"two plus two does not equal four — wait, yes it does"* exist; people discuss correct facts constantly inside negated constructions. So "does not equal" co-occurs with "four" all over the corpus. The model has learned that negation words, in a factual context, are *associated with the correct answer*, because that's the distribution it saw. It's optimizing predictive cues, not computing truth conditions — exactly Ettinger's framing.

## What this is and isn't

I want to be precise about the contribution, because mech interp has an overclaiming problem. The behavioral result is not mine — negation failure is well-trodden. What I'm adding is incremental and concrete: the **layer-level localization** (negation at L0–2, recall at L9–10, and the mismatch between them), a **quantified booster effect** (7 of 12 cases across three models show no-effect-or-boost; mean +4.9% on GPT-2 small), and the **attention evidence** that the token is read, not dropped. This is me learning the toolkit by taking a known failure apart, not announcing a discovery.

But the shape of it is the same thing I chase everywhere else. The bug isn't in the perception and it isn't in the knowledge — it's in the *seam* between them, where a signal that exists fails to gate a computation that happens somewhere else. That's the same place a bridge exploit lives, and the same place a parser bug lives: not in either correct half, but in the join nobody tested.

*Code and the full writeup are in [the repo](https://github.com/0xSoftBoi/anthropic-fellowship/tree/main/mech-interp). References: Ettinger 2020, Truong et al. 2023, [Meng et al. 2022](https://arxiv.org/abs/2202.05262) (causal tracing), Berglund et al. 2023 (the Reversal Curse).*
