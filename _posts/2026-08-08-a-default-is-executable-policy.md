---
layout: post
title: "A default is executable policy"
date: 2026-08-08 09:40:00 -0400
series: "Systems & infrastructure"
tags: [ml, inference, mlx, sampling]
excerpt: "Three changed defaults in MLX-LM fixed a configuration that could turn “enable XTC” into “mask nearly the whole candidate distribution.” The sampler formula was not the bug; the default composition was."
---

The bug I fixed in MLX-LM was three lines.

That is almost the point.

XTC sampling exposed a probability and a threshold. The old threshold default was `0.0`. If a user enabled XTC by setting its probability but left the threshold alone, virtually every token with nonzero softmax probability became eligible for the masking rule.

The sampler formula was doing what its inputs said. The **default composition** was the pathological behavior.

> **A default is executable policy.**

* TOC
{:toc}

## The natural partial configuration was the bad one

Advanced sampling controls often come in families: temperature, top-p, min-p, XTC probability, XTC threshold, repetition penalties, and so on.

Users rarely set every parameter. They change the one knob that sounds like “enable this feature” and rely on the rest of the API to complete the configuration sensibly.

With the previous XTC defaults, that natural path could create a degenerate state. A threshold of zero makes “probability greater than threshold” true for almost the entire candidate distribution.

Each value is individually legal:

- `xtc_probability > 0` is valid;
- `xtc_threshold = 0.0` is valid;
- the sampler's mask logic is valid for the values it receives.

The system behavior is still wrong for the ordinary user path.

## Why local review misses this class of bug

It is easy to review the mathematical implementation and miss the program formed by configuration defaults.

The failure spans layers:

1. a user changes one exposed parameter;
2. another parameter keeps its default;
3. the API composes them;
4. the algorithm receives a valid but unintended state;
5. inference changes dramatically without an error.

No single line needs to look suspicious.

This shows up far beyond sampling. Adapter paths, KV-cache settings, context limits, quantization, speculative decoding, server aliases, and generation defaults all create semantics through composition.

## The fix had to land in every public surface

[MLX-LM #1372](https://github.com/ml-explore/mlx-lm/pull/1372) changed the XTC threshold default from `0.0` to `0.1` in three places:

- the sampler factory;
- the generation CLI;
- the server request model.

Three additions, three deletions.

The important part is not the line count. It is that all public entry points agree.

If the Python factory, CLI, and OpenAI-compatible server disagree on a sampling default, they are effectively three different inference products that happen to share an implementation.

Correctness includes keeping those surfaces semantically aligned.

## The strongest counterargument

XTC is an advanced control. Users who enable it could be expected to specify its threshold explicitly.

That is reasonable for a low-level primitive with no defaults. It is weaker once software exposes the option through user-facing CLI and server schemas *with a default value*.

The moment an API accepts omission, it is deciding what omission means.

The question for a default is therefore not only:

> Is this value inside the parameter's valid numeric domain?

It is also:

> What program executes when a user changes exactly one obvious control and trusts the rest?

## Why 0.1 is not a universal truth

The patch establishes that `0.0` creates a pathological composition and that `0.1` is a safer non-degenerate default for the exposed behavior.

It does **not** establish that 0.1 is the optimal XTC threshold for every model, temperature, prompt distribution, or task.

Sampling policy remains workload-dependent. A user doing controlled experiments should still set the parameter explicitly.

That boundary is important because “fix the default” can otherwise be misread as “discover the best hyperparameter.” Those are different claims.

## The rule I kept

When I review configuration-heavy systems now, I treat defaults as a small program.

I try the minimal user edits:

- enable one feature and omit its companion settings;
- provide one alias and rely on default resolution;
- set one server field but not the CLI equivalent;
- cross a zero/empty/null boundary;
- combine a new non-default with every old default it can interact with.

The surprising failures often live there because every individual component passed its own validation.

> **If the system accepts a partial configuration, the defaults complete the program.**

### Primary evidence

- [MLX-LM PR #1372](https://github.com/ml-explore/mlx-lm/pull/1372) — merged XTC threshold default correction across sampler, CLI, and server.

**Evidence boundary:** the merged patch establishes a degenerate default interaction and aligns the public surfaces. It is not evidence that 0.1 is universally optimal sampling policy.
