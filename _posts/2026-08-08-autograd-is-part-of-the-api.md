---
layout: post
title: "Autograd is part of the API"
date: 2026-08-08 09:30:00 -0400
series: "Systems & infrastructure"
tags: [ml, pytorch, autograd, numerical-correctness]
excerpt: "An activation can return the expected forward value and still be broken if its learnable parameter cannot move through the function it supposedly controls. A MatGL fix made gradient semantics part of the regression contract."
---

An ML function can return the expected number and still be wrong.

That is what I ran into in MatGL's `SoftExponential` activation. Its learned parameter `alpha` selected one of three mathematical regimes with ordinary Python `if` statements. The forward values looked reasonable. The implementation still violated a more important contract: **the parameter was supposed to be learnable.**

For differentiable software, autograd is part of the API even when the type signature never says so.

* TOC
{:toc}

## The visible code hid an invisible interface

`SoftExponential` is piecewise in `alpha`: one formula for negative values, an identity limit near zero, and another formula for positive values.

The old implementation mirrored that definition with Python control flow. Conceptually:

```python
if alpha < 0:
    ...
elif alpha == 0:
    ...
else:
    ...
```

The problem is not that piecewise mathematics is invalid. The problem is asking Python to make a control decision from a learned tensor when that parameter is supposed to participate in a differentiable program.

The forward path can still return a plausible result for the current sign. But the optimization semantics are no longer the same thing as the mathematical function advertised by the layer.

## There was a second numerical boundary at zero

An exact `alpha == 0.0` branch is also a poor representation of the identity limit for a parameter being updated by gradient descent.

A learned scalar does not politely land on bit-exact zero whenever the formula becomes numerically delicate. Tiny positive and negative values are the regime where stable limiting behavior matters most.

The fix therefore uses a small epsilon neighborhood rather than treating zero as a special floating-point event.

## The negative branch could poison training

For sufficiently negative combinations of input and `alpha`, the logarithm's argument becomes non-positive. That generated NaN/Inf values and could propagate invalid numbers into `alpha.grad`.

This is a different correctness dimension again:

1. **forward semantics** — does the function compute its intended formula?
2. **gradient semantics** — can the trainable parameter receive the intended derivative?
3. **domain safety** — do evaluated formulas remain finite in the regions the implementation can reach?

A regression suite that only compares forward outputs can miss two of the three.

## The tensor-native fix

The merged patch, [MatGL #809](https://github.com/materialyzeai/matgl/pull/809), moved regime selection into tensor-native operations, used a stable near-zero treatment, guarded invalid logarithm/denominator regions, and used numerically friendlier expressions such as `expm1` where appropriate.

There is a subtle PyTorch detail here: replacing Python branching with `torch.where` does **not** mean the unselected mathematical branch can be numerically invalid. Both expressions may still be evaluated before selection. The implementation has to make the discarded branch safe too.

That is the kind of bug that appears when a mathematical piecewise definition is translated too literally into eager tensor code.

## The tests changed what “works” means

The important regressions were not just “output equals expected.” They included:

- finite outputs in the troublesome negative regime;
- finite gradients;
- a nonzero finite gradient reaching `alpha` from both sign initializations;
- preservation of the historical forward formula in its valid region.

The patch reports a maximum valid-region forward difference around **0–5×10⁻⁷** and the full affected layer suite passing **92 tests**.

One pre-existing test also had to change from `.numpy()` to `.detach().numpy()`. That tiny edit is almost a proof of the semantic repair: after the fix, the output correctly belonged to an autograd graph where the prior implementation had short-circuited around part of it.

## The strongest counterargument

Not every branch involving a tensor should be rewritten into differentiable control flow. Some state changes are deliberately discrete; some parameters are not optimized; some branches encode non-differentiable program semantics by design.

The deciding question is the contract.

If a layer exposes `alpha` as a trainable parameter controlling its response, callers reasonably assume optimization can move `alpha` through that response. If the implementation breaks that assumption, the forward value is not enough to call the layer correct.

## Why this generalizes beyond one activation

ML libraries have many interfaces that exist outside the Python signature:

- gradient connectivity;
- device/dtype propagation;
- train/eval state;
- determinism assumptions;
- serialization behavior;
- shape and batch semantics;
- numerical-domain constraints.

A function can satisfy its local unit test while violating one of those hidden contracts.

I now treat gradients the way I treat file formats or network protocols: if downstream code relies on them, they deserve explicit regression tests.

> **If a parameter is learnable, “does the value look right?” is only half the test.**

### Primary evidence

- [MatGL PR #809](https://github.com/materialyzeai/matgl/pull/809) — merged implementation, numerical guards, and gradient regressions.

**Evidence boundary:** this is a specific PyTorch/MatGL correctness case. It does not imply `torch.where` is universally preferable to Python control flow; the relevant question is whether the branch is part of a differentiable contract and whether all evaluated branches are numerically safe.
