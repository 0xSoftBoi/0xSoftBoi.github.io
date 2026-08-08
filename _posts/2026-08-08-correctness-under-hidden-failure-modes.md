---
layout: post
title: "Correctness under hidden failure modes"
date: 2026-08-08 09:10:00 -0400
series: "Engineering practice"
tags: [systems, research, testing, evaluations]
excerpt: "Real hardware, contaminated benchmarks, miscalibrated uncertainty, and physical prototype gates look unrelated. They are the same engineering problem: the abstraction becomes the thing being tested, and both can be wrong together."
---

A surprising amount of my work has converged on the same failure pattern.

An RDMA diagnostic had 197 passing tests and four bugs the moment it touched a real device. An AI-security benchmark measured a model on prompts that sometimes contained the answer. A materials model produced useful mean predictions attached to an uncertainty estimate that was anti-correlated with error. An autonomous carrier concept became meaningful only after its performance numbers were demoted from “vision” to explicit future acceptance gates.

The domains are different. The failure is the same:

> **The abstraction quietly becomes the thing being tested, and the abstraction can share the same wrong assumption as the implementation.**

* TOC
{:toc}

## Internal consistency is not external validity

A synthetic test can show that a parser behaves correctly on the states I imagined. It cannot prove I imagined Linux RDMA correctly.

A benchmark scorer can consistently evaluate the labels in a dataset. It cannot prove the model-visible prompt did not leak those labels.

A function can return a number called `sigma`. It cannot prove that larger sigma corresponds to larger error.

A CAD model can satisfy a docking envelope. It cannot prove a flying vehicle repeatedly enters that envelope without contact.

These are all versions of the same gap: **the system satisfies the model of reality while the model itself is wrong or incomplete.**

## Four cases

### 1. Real hardware disagreed with the fixtures

`roce-preflight` had 197 passing unit tests before the first real-device CI run exposed four defects: wrong MTU reporting, contradictory GID diagnosis, unroutable GID selection, and incorrect GID-table enumeration.

The most important observation came next: the first attempted fix also passed unit tests and did not fix the real device.

That changed the acceptance rule. Unit tests could prove logic against modeled state. RDMA behavior required independent device state.

### 2. The benchmark contained its own answer

BRIDGE-bench originally included human-facing provenance headers in the exact prompt sent to the model. A later audit found severe author-injected leakage in **13 of 24** verified contracts.

The Euler example was the sharpest case: the header included the exact vulnerability label while the vulnerable function itself was absent from the committed source bundle.

The old aggregate score did not become fake. It became evidence for a weaker proposition: performance on a contaminated prompt distribution.

That downgrade is the correct response when measurement validity changes.

### 3. The uncertainty number was not uncertainty information

On a static materials-screening benchmark, a pretrained mean prediction produced roughly **5× discovery acceleration** relative to random selection at the tested budget.

Low-weight UCB tied greedy ranking. But direct calibration found the MC-dropout standard deviation had **Spearman correlation −0.47 with absolute error**. Increasing the uncertainty weight eventually drove the acquisition rule below random.

The useful mean and the useless uncertainty came out of the same model wrapper.

The lesson is simple: names such as “confidence,” “uncertainty,” and “probability” are hypotheses about semantics until calibration supports them.

### 4. A prototype target is not a prototype result

Aiur is an airborne-carrier concept built around autonomous launch and recovery. The easiest way to make such a project sound impressive is to quote target capture rates, approach speeds, payload counts, and compute budgets as if they describe a machine that already exists.

The current project does not do that. CARRIER-P0 defines those numbers as **gates** for future physical tests. The observed artifacts are models, CAD, a dock controller, fabrication plans, and acceptance definitions.

Until the physical telemetry exists, recovery performance is a target.

That is not a weakness in the project. It is what makes the project falsifiable.

## Evidence classes are a practical tool

I now try to label consequential statements as one of four kinds:

- **Observed:** measured directly in an experiment, trace, source artifact, or dataset.
- **Derived:** calculated from observed inputs with an explicit method.
- **Estimated:** inferred through a model or assumptions.
- **Target:** a design requirement or future acceptance threshold.

Most accidental overclaiming happens when a sentence crosses one of those boundaries without saying so.

A target becomes “performance.” An estimate becomes “cost.” A benchmark number becomes “capability.” A mock becomes “hardware validation.”

The labels are mundane. They force the argument to stay attached to the evidence.

## Negative results are part of the system

The temptation in project work is to preserve the original thesis.

- If UCB was supposed to beat greedy, tune until it wins.
- If a benchmark was supposed to show model reasoning, defend the headline score.
- If a prototype is supposed to be a carrier, keep adding features until it resembles one.

I increasingly prefer the opposite loop: make every pass harder for the thesis to survive.

A negative result can improve the artifact around it. The failed uncertainty result produced calibration tooling. The benchmark leakage produced a sanitizer and population checks. The hardware bugs produced a real-device acceptance boundary. The lack of Aiur telemetry produced a cleaner P0 gate.

The project gets stronger when the story gets weaker but more true.

## The strongest counterargument

It is possible to fetishize skepticism and make engineering unbearably slow. Not every unit test needs a hardware lab; not every internal metric needs a publication-grade causal design; not every prototype needs complete instrumentation before the first build.

Agreed.

The point is not maximal evidence everywhere. The point is **matching evidence strength to claim strength**.

A parser unit test can justify a parser claim. It cannot justify a physical-fabric claim. A design model can justify sizing a prototype. It cannot justify an achieved recovery rate.

The cost of evidence should rise with the consequence of the sentence it is supporting.

## The research loop I use now

For technical writing, I use a simple adversarial loop:

1. state a falsifiable claim;
2. map consequential sentences to primary artifacts;
3. expose denominator, assumptions, and uncertainty for quantitative claims;
4. write the strongest rival explanation;
5. test or preserve that rival honestly;
6. label limitations where the reader will see them;
7. publish only the conclusion that survives;
8. reopen the piece when new evidence arrives.

Publication is not the terminal state. A correction is not an embarrassment to hide. It is the system doing what it was built to do.

## The rule underneath the projects

The connective tissue across systems, ML, security, and autonomy is not a language or domain.

It is this:

> **If the claim depends on something outside the abstraction, eventually test the thing outside the abstraction.**

Hardware should touch hardware. Evaluation prompts should be audited as prompts. Uncertainty should be calibrated against error. Prototype performance should come from telemetry.

Everything before that is useful scaffolding. It just should not be confused with the wall.

### Primary evidence

- [roce-preflight](https://github.com/0xSoftBoi/roce-preflight)
- [BRIDGE-bench](https://github.com/0xSoftBoi/anthropic-fellowship)
- [active-materials-discovery](https://github.com/0xSoftBoi/active-materials-discovery)
- [Aiur](https://github.com/0xSoftBoi/aiur)

**Evidence boundary:** this article is a synthesis across separate projects. The project-specific measurements are observed in their source artifacts; the claim that they instantiate a common engineering pattern is my interpretation.
