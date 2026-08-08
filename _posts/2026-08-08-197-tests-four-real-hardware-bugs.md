---
layout: post
title: "197 passing tests, four real-hardware bugs"
date: 2026-08-08 09:00:00 -0400
series: "Systems & infrastructure"
tags: [systems, networking, rdma, testing]
excerpt: "The unit suite was green. Then I gave the program an RDMA device. Real verbs and real sysfs state exposed four defects the 197 synthetic tests had not — and rejected the first attempted fix too."
---

The unit suite was green. Then I gave the program an RDMA device.

The first real-device CI run of [roce-preflight](https://github.com/0xSoftBoi/roce-preflight) exposed **four defects** that **197 passing unit tests** had not. The useful lesson is narrower than “hardware testing is good”:

> **Tests generated from the same mental model as the implementation can prove internal consistency while leaving the external boundary almost completely untested.**

* TOC
{:toc}

## The credibility gap

`roce-preflight` diagnoses whether a RoCE host is ready to bring queue pairs up. It reads GID tables, port state, MTU, and host configuration; it can also drive RC, UC, and UD queue pairs through the verbs lifecycle.

The original tests covered parsers, ranking logic, synthetic snapshots, and lifecycle decisions. They did **not** require an RDMA device. The fixtures were representations of Linux RDMA state written by the same project they were supposed to validate.

A green suite therefore established a real but narrower property: the implementation agreed with its own model.

## A different evidence class

GitHub's Ubuntu runner does not ship `rdma_rxe` for its Azure kernel, so the CI job builds the upstream soft-RoCE kernel module against the running kernel, creates `rxe0`, and then **fails if backend detection silently falls back to simulation**.

Only after that assertion does it run the inspectors, queue-pair lifecycle, and real `ib_write_bw` traffic.

Soft-RoCE is not a performance proxy for a physical NIC. It *is* a real Linux RDMA device with real verbs, sysfs state, and a GID table. That is enough to test whether the software's assumptions about those interfaces survive contact with the kernel.

## What broke

| Defect | What the live device exposed | Why fixtures missed it |
|---|---|---|
| MTU reporting | `doctor` printed link rate where active MTU belonged | the synthetic representation encoded the expected shape rather than the real sysfs interface |
| contradictory GID diagnosis | the report could say “GID table empty” beside a PASS containing a real GID | isolated unit scenarios never had to reconcile against one live snapshot |
| QP lifecycle | RC, UC, and UD failed with `ENETUNREACH` after selecting an unroutable `fe80::` GID | a plausible fixture GID never had to be routed by the kernel |
| GID enumeration | a snapshot pulled 1,024 entries instead of the three that existed | the mock did not reproduce real sparsity and termination behavior |

None required exotic hardware. They required the program to stop talking to an imitation of Linux RDMA and talk to Linux RDMA.

## The best failure was the first fix

The first correction attempt passed the unit suite and changed nothing on the real device.

Hardware CI rejected it immediately.

That was more valuable than the initial bug discovery because it turned real-device execution from a debugging trick into an **acceptance boundary**: a fix to an RDMA path is not accepted merely because the model says it should work.

After correction and re-verification, the active MTU reported consistently, the diagnosis agreed with the live GID state, the snapshot contained three entries, and RC/UC/UD all reached payload verification. The unit suite had grown to 208 tests.

But `197 → 208` is not the story.

**Synthetic state → independent device state** is the story.

## Three propositions, three kinds of tests

I now separate at least three questions in this kind of systems software:

1. **Logic:** does the algorithm behave correctly for a supplied state?
2. **Interface fidelity:** does that supplied state actually behave like the kernel/device interface?
3. **Physical behavior:** does traffic behave correctly on the target hardware and fabric?

Unit fixtures are excellent for the first. Soft-RoCE materially improves the second and exercises real verbs for part of the third.

It still cannot validate mlx5 firmware, PCIe behavior, SR-IOV topologies, switch configuration, PFC/ECN, NUMA placement, multi-host routing, or performance under sustained load.

Those need different experiments.

## The strongest counterargument

These four failures can be described as ordinary mocking mistakes. Better fixtures could reproduce every one **after the fact**.

That is true—and exactly why the independent boundary matters. Before the failures were known, the implementation and fixtures shared enough assumptions to be wrong in the same direction.

A mock is strongest when reproducing already-understood behavior quickly and deterministically. It is weakest when asked to discover that your model of an external system is wrong.

## What changed in the project

The project now treats evidence as tiers instead of collapsing everything into “tested.”

- unit tests protect deterministic logic;
- the real-device job proves it did not silently fall back to simulation;
- inspectors read actual sysfs state;
- QP failures expose the underlying verbs error;
- real traffic goes through `ib_write_bw`;
- synthetic performance numbers are labeled synthetic rather than qualification data.

That separation is partly UX. Mostly it is epistemic hygiene. A diagnostic tool should be unusually explicit about which parts of its own diagnosis have touched reality.

## The rule I kept

The lesson is not “replace mocks with hardware.” Fast synthetic layers are what make iteration possible.

The rule is:

> **When the external system is part of the claim, make the external system part of the test.**

### Primary evidence

- [roce-preflight](https://github.com/0xSoftBoi/roce-preflight)
- [real-device Soft-RoCE CI workflow](https://github.com/0xSoftBoi/roce-preflight/blob/main/.github/workflows/soft-roce.yml)

**Evidence boundary:** the four defects and post-fix payload verification are observations from the project's real-device path. The causal explanation for why fixtures missed them is a postmortem interpretation. Soft-RoCE on one hosted Linux machine is not evidence of physical-NIC or production-fabric performance.
