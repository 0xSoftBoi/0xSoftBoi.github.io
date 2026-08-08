---
layout: post
title: "Upstream is a different kind of test"
date: 2026-08-08 10:00:00 -0400
series: "Engineering practice"
tags: [open-source, systems, ml, rust]
excerpt: "Eight merged patches across MatGL, MLX-LM, Alloy, coreutils, and parse_datetime changed the unit of correctness from “works for my project” to “what may downstream callers safely assume after this lands?”"
---

A patch in my own repository has one owner of the assumptions: me.

A patch merged into somebody else's library has to survive a different question:

> **What may downstream callers safely assume after this lands?**

I have eight selected merged patches across MatGL, MLX-LM, Alloy, uutils/coreutils, and uutils/parse_datetime. They look unrelated—uncertainty estimation, an activation gradient bug, sampling defaults, recursive types, timezone semantics, negative timestamps, AM/PM parsing, a timezone alias.

The pattern is what upstream review forced me to make explicit.

* TOC
{:toc}

## A feature needs a failure contract

The [MatGL MC-dropout wrapper](https://github.com/materialyzeai/matgl/pull/801) began as research machinery. In a benchmark, I could assume the right model shape and clean up state manually.

Upstream, the feature had to define:

- which model/readout configurations are supported;
- what happens when no compatible dropout site exists;
- whether stochastic mode leaks after the call;
- how batches and output shapes behave;
- which parts of the network remain deterministic.

The library patch is useful precisely because it promises **less** than the research story. It gives callers a supported stochastic mechanism. It does not promise calibrated uncertainty.

## Forward values are not the whole API

[MatGL #809](https://github.com/materialyzeai/matgl/pull/809) fixed `SoftExponential`, a learnable activation whose Python branch over `alpha` could preserve plausible forward behavior while breaking the differentiable contract and producing invalid gradients in part of its domain.

The regression boundary therefore had to include gradient behavior, not just expected output values.

That is a recurring lesson in shared infrastructure: the public API includes properties the function signature never lists—autograd connectivity, train/eval state, numerical finiteness, serialization, device behavior.

## Defaults are behavior

[MLX-LM #1372](https://github.com/ml-explore/mlx-lm/pull/1372) changed three defaults. The old XTC threshold of zero could compose with “enable XTC” into a near-total candidate mask.

Every individual value was valid. The user's likely partial configuration was not.

The fix also had to align the sampler factory, CLI, and server. A shared codebase with different defaults at different entry points is three products with one repository.

## Specifications contain distinctions generic algorithms erase

[Alloy #1105](https://github.com/alloy-rs/core/pull/1105) came from treating self-reference and mutual recursion as the same cycle.

EIP-712 canonical type encoding permits recursive struct definitions. Alloy's runtime resolver still cannot represent arbitrary recursive values. The right fix was not “allow cycles” or “reject cycles”; it was two policies attached to two operations, with tests for the newly legal case and the still-illegal neighbor.

Generic graph vocabulary had erased a domain distinction the protocol specification cared about.

## Compatibility is made of tiny promises

The uutils patches are the strongest reminder that diff size and behavior size are different things.

- [coreutils #12327](https://github.com/uutils/coreutils/pull/12327): parse a timezone abbreviation as input state, then render in the caller's output timezone.
- [parse_datetime #285](https://github.com/uutils/parse_datetime/pull/285): floor negative fractional epoch seconds instead of truncating toward zero.
- [#284](https://github.com/uutils/parse_datetime/pull/284): do not let a narrow time parser consume `12:00` before `PM` can participate in the grammar.
- [#287](https://github.com/uutils/parse_datetime/pull/287): accept `UT`, because GNU `date` does.

A two-character alias can be part of somebody's production interface.

## What a merge means

A merge is meaningful third-party evidence. Maintainers accepted the change into a project with its own tests, conventions, compatibility commitments, and review process.

It is not proof of correctness.

Maintainers miss things. Tests have blind spots. Projects make tradeoffs. The useful difference is independence: the patch is exposed to another set of assumptions and incentives.

That is why I keep merged upstream work separate from personal-project claims. “I wrote it” and “maintainers accepted it” are different evidence classes.

## The sentence I try to write before the code

For a patch now, I try to state two things:

1. the new assumption a caller should safely gain;
2. the nearby assumption that must **not** accidentally become true.

Examples:

- supported MatGL readouts can produce stochastic samples; **calibration is not promised**;
- EIP-712 self-reference can canonicalize; **mutual recursion and strict runtime resolution remain constrained**;
- enabling XTC without an explicit threshold should not create the degenerate zero-threshold behavior; **0.1 is not claimed to be universally optimal**;
- negative fractional Unix timestamps use GNU-compatible floor semantics; **this does not redesign the entire timestamp model**.

That second sentence is often the one that keeps a patch small enough to trust.

## The strongest counterargument

A personal portfolio can over-index on merged PRs. External maintainers may accept a narrow fix without learning much about the contributor's ability to own a large system.

True. Upstream patches are one kind of signal, not the whole story.

I value them because they exercise a skill that large personal projects do not automatically test: entering an existing codebase, respecting its constraints, isolating a behavior change, and leaving the maintenance surface clearer than you found it.

## The habit I kept

A local patch asks whether I can make something work.

Upstream asks what other people may safely build on top of it.

> **A good patch expands the set of safe assumptions without quietly expanding the set of claims.**

### Selected merged evidence

| Project | Patch | Boundary |
|---|---|---|
| MatGL | [#801](https://github.com/materialyzeai/matgl/pull/801) | mechanism vs calibration claim |
| MatGL | [#809](https://github.com/materialyzeai/matgl/pull/809) | forward value vs gradient semantics |
| MLX-LM | [#1372](https://github.com/ml-explore/mlx-lm/pull/1372) | valid parameter vs safe default composition |
| Alloy | [#1105](https://github.com/alloy-rs/core/pull/1105) | self-reference vs mutual recursion/runtime representation |
| coreutils | [#12327](https://github.com/uutils/coreutils/pull/12327) | input timezone vs output timezone |
| parse_datetime | [#284](https://github.com/uutils/parse_datetime/pull/284), [#285](https://github.com/uutils/parse_datetime/pull/285), [#287](https://github.com/uutils/parse_datetime/pull/287) | grammar, epoch rounding, compatibility language |

**Evidence boundary:** this synthesis intentionally uses merged third-party patches. Merge is evidence of external review and acceptance, not mathematical proof that the resulting software is bug-free.
