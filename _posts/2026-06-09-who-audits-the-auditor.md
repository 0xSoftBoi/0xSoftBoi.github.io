---
layout: post
title: "Who audits the auditor?"
date: 2026-06-09 18:00:00
series: "Applied ML"
tags: [security, static-analysis, agents, solidity, tooling]
image: /assets/og/who-audits-the-auditor.png
excerpt: "I built a Solidity static-analysis tool with an agent fleet. The phase that mattered wasn't writing the detectors — it was pointing a separate model at them and saying: lie detector, prove you lie."
---

I built a small Solidity static-analysis tool — `scaudit`, a dependency-free scanner that reads a contract and flags reentrancy, `tx.origin` auth, unchecked low-level calls, unprotected `selfdestruct`, and a dozen other things, plus some gas hints. Writing the detectors is the easy, satisfying part. It's also the part that means almost nothing, because a security tool's entire worth is **whether you can trust its verdict** — and the way that trust dies isn't a crash, it's a quiet lie.

A security scanner fails in two directions, and both are silent:

- **False negative** — a green light on vulnerable code. The worst outcome, because it manufactures confidence. You ran the tool, it said clean, you shipped the reentrancy.
- **False positive** — a red flag on safe code. Less dangerous but corrosive: enough of them and people stop reading the output, which converts every real finding into a false negative by way of fatigue.

So the interesting phase of building this wasn't the detectors. It was handing the finished detectors to a *different, stronger* model — one that hadn't written them and had no stake in them looking good — with a single instruction: **construct the contracts these miss, and the safe ones they wrongly flag.**

<figure class="chart">
<svg viewBox="0 0 620 320" role="img" aria-labelledby="wa-t">
<title id="wa-t">The two ways a detector lies: false negatives and false positives</title>
<text class="c-label-sm" x="150" y="40" text-anchor="middle">contract is VULNERABLE</text>
<text class="c-label-sm" x="430" y="40" text-anchor="middle">contract is SAFE</text>
<text class="c-label-sm" x="40" y="120" text-anchor="middle" transform="rotate(-90 40 120)">tool: FLAG</text>
<text class="c-label-sm" x="40" y="240" text-anchor="middle" transform="rotate(-90 40 240)">tool: clean</text>
<rect class="c-box" x="70" y="60" width="240" height="110" rx="8"/>
<text class="c-label-sm" x="190" y="112" text-anchor="middle">true positive</text>
<text class="c-label-sm" x="190" y="132" text-anchor="middle">✓ caught it</text>
<rect class="c-box" x="320" y="60" width="240" height="110" rx="8"/>
<text class="c-label-sm" x="440" y="106" text-anchor="middle" fill="var(--accent)">FALSE POSITIVE</text>
<text class="c-label-sm" x="440" y="126" text-anchor="middle">cries wolf →</text>
<text class="c-label-sm" x="440" y="146" text-anchor="middle">tx.origin in a log; uint x = 5</text>
<rect class="c-box-accent c-fill-soft" x="70" y="180" width="240" height="110" rx="8"/>
<text class="c-label-sm" x="190" y="226" text-anchor="middle" fill="var(--accent)">FALSE NEGATIVE</text>
<text class="c-label-sm" x="190" y="246" text-anchor="middle">manufactures confidence</text>
<text class="c-label-sm" x="190" y="266" text-anchor="middle">selfdestruct in fallback; returns(bool)</text>
<rect class="c-box" x="320" y="180" width="240" height="110" rx="8"/>
<text class="c-label-sm" x="440" y="232" text-anchor="middle">true negative</text>
<text class="c-label-sm" x="440" y="252" text-anchor="middle">✓ stayed quiet</text>
</svg>
<figcaption>The audit lived entirely in the two off-diagonal cells — the lies. Every finding it returned was a contract that landed in the wrong box.</figcaption>
</figure>

## What it found

The detectors were heuristics — regex and brace-counting over source, no compiler, no AST — and heuristics break on structure. The auditor found exactly where:

- A function's `returns (bool)` clause was being parsed into its **modifier list**. So a function that returned a value looked, to the access-control detector, like it had a guarding modifier — and its findings were suppressed. **False negatives, by punctuation.**
- `receive()` and `fallback()` weren't being segmented as functions at all, so a `selfdestruct` sitting in a fallback was simply invisible.
- A `nonReentrant` modifier silenced *unrelated* checks, because the engine treated "has any modifier" as "is access-controlled."
- On the other side: `tx.origin` passed to an event got flagged as phishable auth (it's a log), and `uint x = 5` got flagged as a reentrancy state-write (it's a declaration). **Crying wolf.**

Each one became a regression fixture — a tiny contract that *must* trip the detector, or *must not*. The suite went from 29 tests to 46. And then I did the part the fleet can't do for me: re-ran them myself, and pointed the CLI at a vulnerable fixture (one HIGH finding, correct line) and a clean one (no findings) to watch recall and precision with my own eyes.

## The honest footer

`scaudit` is a first-pass triage aid. It has no control-flow graph, no taint analysis, no inheritance resolution; it reads one file at a time; its access-control detector is high-false-positive by nature. [Slither](https://github.com/crytic/slither) compiles the contract and reasons over an IR; Mythril runs symbolic execution; real coverage is fuzzing and formal verification. I put all of that in the [README](https://github.com/0xSoftBoi/smart-contract-audit-framework) in plain words, because a tool that overstates its reach is just a better-dressed false negative.

But the structure is the point worth keeping. The same [agent workflow](/blog/a-social-good-protocol-built-by-an-agent-fleet/) that built `scaudit` is, itself, this idea: a builder model and a separate, sharper auditor model that exists only to disbelieve it. The most useful thing you can do with a second model isn't more output — it's adversarial doubt aimed at the first one. Who audits the auditor? A different auditor, who was told to assume it's lying.
