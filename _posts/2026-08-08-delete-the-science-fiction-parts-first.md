---
layout: post
title: "Delete the science-fiction parts first"
date: 2026-08-08 10:10:00 -0400
series: "Autonomous systems"
tags: [autonomy, robotics, hardware, prototyping]
excerpt: "The first useful prototype of an airborne drone carrier is not a smaller carrier. It is the cheapest machine that can falsify the riskiest interaction in the architecture: repeated recovery onto a moving dock."
---

The motivating picture for [Aiur](https://github.com/0xSoftBoi/aiur) is intentionally excessive: a persistent lighter-than-air carrier deploying and recovering autonomous aircraft, eventually carrying coordination compute and energy infrastructure aloft.

That picture is a terrible prototype specification.

If the first build tries to resemble the final system, it inherits every hard problem at once: a large envelope, lift-gas tradeoffs, outdoor operation, multiple aircraft, perception, charging, high-power compute, thermal management, communications, and docking.

When that prototype fails, it tells you almost nothing about **which assumption** killed it.

> **The first useful prototype is the cheapest machine that can falsify the highest-risk interaction in the architecture.**

For Aiur, that interaction is recovery.

<figure class="evidence-figure dark-evidence">
  <img src="{{ '/assets/evidence/aiur-carrier.svg' | relative_url }}" alt="Aiur CARRIER-P0 schematic showing a buoyant carrier, a positive recovery dock, approach vector, and predeclared physical acceptance targets.">
  <figcaption><strong>Target, not result.</strong> The ≥50 attempts, ≥90% capture, and zero unsafe-contact numbers are predeclared acceptance gates. They remain unachieved until an instrumented physical dataset exists.</figcaption>
</figure>

* TOC
{:toc}

## P0 deletes almost everything

CARRIER-P0 is deliberately unimpressive compared with the rendering in my head.

It uses:

- helium, not hydrogen;
- one active belly dock;
- one micro-UAV first;
- indoor/tethered operation;
- externally referenced positioning where useful;
- no airborne charging requirement;
- no heavy compute payload;
- no swarm behavior until single-aircraft recovery is repeatable.

The baseline reference article is roughly a **4.5 m indoor airship** with a Crazyflie-class aircraft.

A 40 m envelope is gone. Eight aircraft are gone. DGX-class compute is gone. Outdoor/BVLOS autonomy is gone. Hydrogen is gone.

Those deletions are not a retreat from the concept. They are an attempt to preserve the one question whose answer can invalidate the concept cheaply:

> Can a buoyant carrier repeatedly recover a small autonomous aircraft onto a moving dock without unsafe contact?

## The dock is a state machine, not a magnet

The current mechanical concept uses a wide capture funnel and lightweight probe. The aircraft may disarm only after two independent physical signals agree:

1. a seat switch says the probe reached the seat;
2. a keeper switch says a positive mechanical lock closed beneath it.

The intended transition is `S1 AND S2`.

That is deliberately stricter than “vision says we docked” or “the magnet is energized.” A positive mechanical keeper makes attachment a checkable physical state rather than a perception estimate.

The same instinct shows up in software safety systems: use independent signals for a consequential state transition, and make the system fail closed when they disagree.

## The acceptance ladder prevents premature scale

The prototype is staged so each gate answers a different question.

### P0-A — bench capture

Before flight, test the dock as a mechanism:

- repeated manual capture/release cycles;
- mass and center-of-gravity constraints;
- independent seat/keeper sensor agreement;
- screening loads;
- emergency release.

If the mechanical interface is unreliable on a bench, adding flight control only makes debugging harder.

### P0-B — suspended moving dock

Move the dock while keeping the carrier problem out of the loop. Ask whether the micro-UAV can approach, enter the funnel, and achieve mechanically confirmed capture without prop/funnel contact.

### P0-C — tethered helium carrier

Only after the interaction works on a controlled moving target does it move to a buoyant carrier, still tethered and guarded.

### P0-D — multi-aircraft sequencing

A second aircraft is a scheduling problem that should not exist until one-aircraft recovery is boring.

Charging and airborne compute are later gates. If recovery fails, optimizing GPU power budgets is theater.

## Targets are not results

The repository contains concrete numbers for funnel size, approach speed, mass ceilings, cycle counts, and desired capture rates.

Those numbers are **engineering targets**. They exist to make failure legible and acceptance binary.

They are not achieved performance.

The observed artifacts today are:

- architecture and P0 specifications;
- mass/capture models;
- dock-controller logic;
- CAD/fabrication artifacts;
- acceptance definitions;
- evidence-reduction tooling.

The missing artifact is the important one: an instrumented physical recovery dataset.

That is why this page is a **design note**, not a research result.

## The strongest counterargument

Success on an indoor micro-UAV does not prove a large outdoor carrier works.

Correct.

P0 is not a scale-law proof. Wind, structural scaling, envelope dynamics, payload mass, outdoor localization, weather, charging, and fleet operations all remain.

The value of P0 is asymmetric. A failure can cheaply kill or redesign the recovery architecture. A success removes **one** uncertainty and leaves the rest alive.

That is exactly the amount of evidence a good prototype should provide.

## Why I prefer deletion to simulation depth

It is easy to add fidelity to a simulation until every subsystem exists as a parameter. That can be useful later. Early on, it often creates a model whose errors are hard to attribute.

Deleting features reduces the number of explanations a failure can have.

If a suspended moving dock cannot be recovered onto reliably, the failure is probably in approach, perception, capture geometry, relative motion, or control—not helium purity, generator sizing, or swarm scheduling.

The prototype becomes an experiment rather than a miniature product.

## What would upgrade this note to research

A committed dataset of physical attempts:

- approach error;
- relative closing speed;
- capture success/failure;
- seat/keeper state transitions;
- unsafe contacts;
- session conditions;
- enough repetitions to evaluate the predeclared acceptance gate;
- a script that regenerates the reported result from raw telemetry.

Until then, recovery performance remains a target.

> **Engineering maturity is partly the ability to say which numbers are measurements and which are promises to yourself.**

### Primary evidence

- [Aiur](https://github.com/0xSoftBoi/aiur)
- [CARRIER-P0 specification](https://github.com/0xSoftBoi/aiur/blob/main/docs/prototype-p0.md)

**Evidence boundary:** this article describes a design and falsification strategy. It makes no claim that the recovery acceptance rate, mass ceiling, or approach envelope has been achieved on physical hardware.
