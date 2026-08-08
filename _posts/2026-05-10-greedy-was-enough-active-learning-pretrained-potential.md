---
layout: post
title: "When uncertainty makes active learning worse"
date: 2026-05-10
series: "Applied ML"
tags: [ml, materials, active-learning, uncertainty]
image: /assets/og/greedy-was-enough-active-learning-pretrained-potential.png
excerpt: "A pretrained materials surrogate found promising structures about five times as efficiently as random screening on a static benchmark. The mean prediction was useful. Its MC-dropout uncertainty was not: σ was anti-correlated with absolute error, and overweighting it pushed acquisition below random."
---

I started this project expecting to write a familiar active-learning story: a pretrained surrogate predicts both value and uncertainty; a UCB-style acquisition rule spends labels where candidates look promising *and* uncertain; exploration beats greedy ranking.

The part that survived is simpler and more useful. On a static screening benchmark over **18,928** structures from `matbench_perovskites`, the pretrained mean prediction was genuinely useful for ranking. The readout-level MC-dropout standard deviation was not.

The distinction matters because a model can be a good predictor without being a good judge of when it is wrong.

* TOC
{:toc}

## The result

The benchmark defines the bottom 5% of formation energy as the positive screening target. That is a **proxy ranking task**, not a claim that these structures are thermodynamically stable against the convex hull. With a 5% acquisition budget and five random seeds:

| Strategy | Stable-proxy candidates found | Discovery acceleration | Top-100 recall |
|---|---:|---:|---:|
| Random | 49.8 ± 3.7 | 1.01 ± 0.07 | 5.0% |
| Greedy, rank by μ | 254.0 ± 1.8 | **5.15 ± 0.04** | 43.2% |
| UCB, λ = 0.5 | 254.8 ± 0.4 | **5.17 ± 0.01** | 43.8% |
| UCB, λ = 2 | 241.0 | 4.89 | 41.0% |
| UCB, λ = 5 | 45.0 | **0.91** | 1.6% |

At a low uncertainty weight, UCB and greedy are effectively tied. As σ receives more authority, performance declines. At λ=5, the acquisition rule performs below random.

That dose response is more informative than the tiny 5.15→5.17 difference at λ=0.5. If σ were identifying the places where the surrogate was most likely to be wrong in a useful way, increasing its influence should not systematically destroy the ranking this quickly.

## So I tested the uncertainty directly

The original version of this article made a stronger inference from `Greedy ≈ UCB`: I argued that the pretrained surrogate was already so well calibrated that there was little left for uncertainty-aware exploration to add.

That was not established by the acquisition result. Similar downstream performance does not prove calibrated uncertainty.

The later calibration experiment measures the relationship directly. For each structure, I compare the MC-dropout standard deviation σ with the absolute prediction error `|μ - y|`.

| Diagnostic | Observed | Useful/calibrated direction |
|---|---:|---:|
| Spearman corr(σ, |error|) | **−0.47** | positive |
| Spearman corr(σ, |μ|) | −0.72 | near zero |
| reliability slope | −1.12 | +1 |
| miscalibration area | 0.43 | 0 |
| coverage at nominal 68% | 0.02 | 0.68 |
| coverage at nominal 95% | 0.12 | 0.95 |

The sign of the first statistic changes the interpretation. Larger σ tended to correspond to **smaller** absolute errors. These values should not be read as calibrated predictive intervals.

The strong association with prediction magnitude is also a warning that the stochastic readout may be tracking a property of the output region rather than clean epistemic uncertainty. That is a diagnostic clue, not a fully identified mechanism.

## What the benchmark does establish

The mean prediction carries strong ranking information on this pool. Discovery Acceleration Factor is precision at the fixed budget divided by the target prevalence, so random screening sits around 1 by construction. A DAF around 5 means the policy is finding bottom-5%-formation-energy candidates at roughly five times the random rate at this budget.

That is useful even though the uncertainty is bad. It means the pretrained representation can provide a strong prior for screening without a trustworthy uncertainty estimate attached to it.

The clean statement is:

> **A good point predictor and a good uncertainty estimator are separate achievements.**

That sounds obvious when written down. It is easy to forget once a library returns `(mean, std)` and the second number looks like confidence.

## What changed from the earlier WBM result

The project also contains a historical WBM experiment using a pretrained CHGNet surrogate on a 256K-structure crystal-stability benchmark. Across five seeds at a 0.9% labeling budget, greedy and UCB were statistically indistinguishable: DAF 1.134 ± 0.017 versus 1.130 ± 0.026.

I still think that numerical result is useful. I no longer use it as evidence that the uncertainty was calibrated. The repository now carries an explicit erratum making that distinction.

The WBM result supports: **under that surrogate, acquisition rule, and budget, the tested UCB term did not improve over greedy mean ranking.**

It does not support: **the model therefore knows when it is wrong.**

## Why this can happen

The implementation makes the graph-network backbone deterministic and places stochasticity in the readout. That is computationally attractive: the expensive representation can be computed once and the cheap head replayed. In the application repository, the optimized backbone-once path reports about **16.5× faster inference at 20 passes on an RTX 3080** while matching the naive path numerically.

But computational convenience and epistemic validity are different questions. Last-layer or readout perturbations can under-represent uncertainty that comes from the learned representation itself. Distribution shift can make the problem worse. And the perovskite benchmark is being used as a proxy screening task for a pretrained formation-energy model, not as an in-distribution calibration benchmark designed for this exact uncertainty method.

Those are plausible reasons for the failure. This experiment does not identify which one dominates.

## The strongest counterargument

The narrow conclusion is about **this** uncertainty construction on **this** task. It is not an argument against uncertainty-aware active learning in general.

Deep ensembles, latent-distance methods, conformal approaches, Bayesian last-layer methods, or a model trained explicitly for calibrated uncertainty could behave differently. An iterative closed-loop campaign where new labels update the model could also create a different exploitation/exploration tradeoff from this static ranking setup.

In fact, that is the point. If a different uncertainty method produces σ that is positively associated with error and improves selection under a robustness sweep of acquisition weights, I would update the conclusion immediately.

## What I would measure before using UCB again

I would not start with a fancy acquisition curve. I would start with four cheap checks:

1. Does σ rank absolute error in the right direction?
2. Do nominal intervals achieve anything close to their claimed coverage?
3. Is σ mostly a disguised function of prediction magnitude or another nuisance variable?
4. Does increasing the uncertainty weight produce a sensible robustness curve rather than a cliff?

Only after those pass would I spend compute arguing about the best λ.

That is the lesson I keep from this project. **Having an uncertainty number is not the same thing as having uncertainty information.**

### Reproduction and sources

- [active-materials-discovery](https://github.com/0xSoftBoi/active-materials-discovery) — benchmark, acquisition code, calibration diagnostics, optimization check, and the historical WBM erratum.
- [MatGL](https://github.com/materialyzeai/matgl) — upstream materials graph library; the reusable MC-dropout wrapper from this work was merged as [PR #801](https://github.com/materialyzeai/matgl/pull/801).
- [Matbench Discovery](https://matbench-discovery.materialsproject.org/) — crystal-stability benchmark context.
- Gal & Ghahramani, *Dropout as a Bayesian Approximation* (ICML 2016) — the classic MC-dropout framing.

**Evidence boundary:** the perovskite experiment is static acquisition screening with existing labels. It is not a closed-loop DFT campaign or laboratory materials-discovery result. The 16.5× speed figure is a reported benchmark on one RTX 3080 configuration, not a universal MatGL performance guarantee.
