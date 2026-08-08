---
layout: post
title: "A research primitive should outlive the result that motivated it"
date: 2026-08-08 09:20:00 -0400
series: "Engineering practice"
tags: [ml, open-source, materials, infrastructure]
excerpt: "I needed MC-dropout uncertainty for one active-learning experiment. The more durable result was upstreaming the mechanism into MatGL so it remained useful even after the motivating uncertainty result became a negative result."
---

I needed uncertainty estimates for one active-learning experiment. It would have been easy to leave the implementation inside a benchmark script: toggle dropout, run the model repeatedly, take a mean and standard deviation, feed both into UCB.

Instead I pulled the uncertainty mechanism out of the experiment and upstreamed it into [MatGL](https://github.com/materialyzeai/matgl) as `MCDropoutWrapper`.

That turned out to be the more durable result, especially because the later experiment made the original uncertainty story *worse*.

> **A research primitive should survive the falsification of the result that motivated it.**

* TOC
{:toc}

## The wrong unit of reuse is the experiment

A benchmark can get away with a lot of implicit state:

- which layers are stochastic;
- whether the model is left in `train()` afterward;
- whether batching changes output shapes;
- which architectures even have a meaningful dropout site;
- whether default pretrained weights contain dropout at all.

A shared library cannot.

The upstream wrapper takes a supported pretrained MatGL model and exposes stochastic inference as a narrow mechanism: produce repeated predictions, aggregate a mean and standard deviation, then return the model to its previous evaluation semantics.

The patch merged as [MatGL #801](https://github.com/materialyzeai/matgl/pull/801), with 529 added lines across implementation, export wiring, and targeted tests.

## What had to become explicit

### Where stochasticity lives

The wrapper keeps the graph-convolutional backbone deterministic and activates stochasticity only in supported readout layers. That is both an implementation choice and a semantic limitation: the returned variation measures the perturbation represented by those dropout sites, not every source of epistemic uncertainty in the model.

### A default model may not contain dropout

A pretrained CHGNet configuration can expose an identity placeholder where the final dropout layer would be. The wrapper can replace that supported site with real dropout at construction time so users do not have to retrain the model just to obtain stochastic readout samples.

### Not every architecture is supportable

Some MatGL readouts do not expose a compatible place to inject this style of dropout. The upstream implementation rejects unsupported configurations rather than returning a tensor called `std` whose meaning would be unclear.

That failure behavior is part of the feature.

### State cleanup is correctness

The model returns to `eval()` after the call, including exceptional paths. A convenience wrapper that silently leaves a pretrained model in stochastic training mode would be more dangerous than having no wrapper.

## Performance changed what was practical

In the application repository, I later optimized the same structure. If the expensive backbone is deterministic and only the readout is stochastic, there is no reason to recompute the representation for every Monte Carlo pass.

The optimized path computes the backbone once and replays the stochastic head. On the reported RTX 3080 configuration at 20 passes, that path measured roughly **16.5× faster** than the naive full-forward loop while matching it numerically.

That number is not a universal MatGL benchmark. It belongs to one hardware/model/configuration path. The reusable idea is broader: **do not rerun deterministic computation merely because the API is phrased as repeated model inference.**

## Then the research result failed

The later calibration study on `matbench_perovskites` found the readout-level MC-dropout standard deviation was **anti-correlated with absolute error**: Spearman −0.47.

As the uncertainty term received more weight in acquisition, performance eventually fell below random screening.

That result does not make the upstream wrapper pointless. It clarifies what the wrapper is.

It is a mechanism for generating a particular stochastic uncertainty signal. It is **not** a guarantee that the signal is calibrated, epistemically complete, or useful for a downstream decision.

That separation is exactly what I want from research infrastructure.

## The strongest counterargument

Adding a convenient uncertainty API can increase misuse. Users may see `(mean, std)` and infer “predictive distribution,” “confidence,” or “Bayesian posterior” more strongly than the implementation warrants.

I agree. The correct response is a narrow contract and explicit scope, not hiding useful machinery in private notebooks.

A library can guarantee:

- supported model types;
- state restoration;
- output shape;
- stochastic execution at specified sites;
- batching behavior;
- deterministic failure for unsupported configurations.

It cannot guarantee calibration on a dataset it has never seen.

## What upstream review changed

The core experiment only needed a number. The upstream patch had to define what other users were allowed to assume about that number-producing mechanism.

That difference is why I value external open-source review. It changes the question from:

> Can I make this work for my run?

into:

> What behavior should remain safe for a caller I do not control?

The answer requires more code around the central idea: exceptions, cleanup, model boundaries, tests, and documentation of unsupported states.

## The rule I kept

An experiment owns the hypothesis. A library should own only the mechanism it can actually guarantee.

That lets the infrastructure survive a negative result without needing to rewrite history.

### Primary evidence

- [MatGL PR #801](https://github.com/materialyzeai/matgl/pull/801) — merged `MCDropoutWrapper` implementation and tests.
- [active-materials-discovery](https://github.com/0xSoftBoi/active-materials-discovery) — downstream benchmark, calibration, and optimized inference path.
- [When uncertainty makes active learning worse](/blog/greedy-was-enough-active-learning-pretrained-potential/) — the later negative result.

**Evidence boundary:** upstream acceptance is independent engineering evidence, not proof that MC dropout is calibrated. The ~16.5× measurement is application-level performance on one RTX 3080 configuration.
