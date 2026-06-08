---
layout: post
title: "An AMM built to be attacked"
date: 2026-04-08
tags: [security, defi, foundry]
excerpt: "Most AMM code is written to look safe. I wrote one to be a teaching specimen — where the exploits are tests in the repo, some of them passing, and the real lesson is which 'attacks' are contract bugs, which are economic facts of life, and which are mitigated and why."
---

When you're learning to audit AMMs, the hard part isn't reading the swap math. It's developing the judgment to look at a successful attack and know which kind it is — a *bug* you must fix, an *economic reality* you can only warn about, or a *known weakness* you've deliberately decided to accept. Those three look identical from the outside: in all of them, someone walks away with money they didn't deposit.

So I built [QuantDEX](https://github.com/0xSoftBoi/quantgroup): a constant-product (`x·y=k`) AMM with a 0.3% fee, written not to be production-safe but to be *annotated* — a reference where the invariants are proven, the attacks are reproduced as tests, and every "this is fine" is justified in a comment with an SWC or CWE reference. It's marked `@custom:audit-status unaudited — educational only`, because the point isn't a safe pool. The point is a precise map.

## What must always be true

Three invariants, checked by a Foundry handler that hammers the pool with fuzzed swaps and liquidity operations while tracking ghost state on the side — the same invariant-fuzzing setup I use on bridges:

- **`x·y ≥ k` after every swap.** The product of reserves never decreases; fees can only push it up. If a sequence of operations ever shrinks `k`, the pool is leaking value and that *is* a bug.
- **Ghost share accounting.** The sum of every LP's shares equals `totalShares`, always. The handler mints and burns independently and asserts the contract agrees.
- **No ghost shares.** `totalShares > 0` if and only if reserves are nonzero — you can't end up with claims against an empty pool.

These are the line. Anything that holds all three while still moving money is, by definition, *not* a solvency bug — it's behavior the protocol permits. That distinction is the whole skill, and it's what the attack tests are there to illustrate.

## The attacks that work — on purpose

Two of the simulated attacks succeed, and the tests say so plainly:

**Sandwich.** The attacker front-runs a victim's 10k swap with a 20k swap on a 100k pool, lets the victim eat the price impact, then back-runs to sell into the move. The victim provably receives less than fair output; the attacker profits. And `x·y ≥ k` holds the entire time. That's the lesson: a sandwich is **not a contract bug** — the AMM did exactly what it promised. It's a mempool-ordering reality, and the only defense lives in the *caller's* slippage guard, not the pool. A companion test, `testSlippageGuardBlocksMEV`, shows the same attack failing once the victim sets a `minAmountOut`. The 0.3% fee, notably, is friction — the attacker pays it on both legs — but friction isn't protection.

**First-depositor donation / share inflation.** The classic: be the first to deposit, mint a single share, then *donate* tokens straight to the contract to inflate what that one share is worth, so the next depositor's rounding gets eaten. QuantDEX mitigates it with a geometric-mean (`sqrt`) bootstrap on the initial mint, which changes the economics — inflating one share to be worth `N` ends up costing the attacker on the order of `N²`, which makes the attack pay to lose. The test documents both the attack and why the mitigation defangs it.

## The weaknesses I wrote down instead of fixing

The most useful comments in the contract are the ones admitting what it *doesn't* do, labeled as decisions rather than oversights:

- **No TWAP oracle** → the spot price is manipulable within a single block (SWC-120 adjacent). Documented, because anything reading this pool's price as an oracle is the real vulnerability, not the pool.
- **Integer math rounds down** → tiny amounts of dust accrue to the pool on each operation. Safe — it always rounds in the pool's favor — but an auditor should see it and confirm the direction, so it's noted.
- **No flash loans, single deployer** → smaller attack surface than a fully trustless v2, and called out as a *scope* choice, not a safety claim.

## Why a specimen beats a fortress

The bridge I audited recently taught me from one direction: write the invariant that must never break, fuzz until something breaks it, fix the bug. This AMM teaches from the other — start from the invariants that *do* hold, then walk the catalogue of things that can still go wrong *on top of* a correct contract, and force yourself to file each one correctly: bug, economics, or accepted limitation. A pool that's merely safe hides all of that. A pool built to be attacked, with the exploits sitting in `test/Attacks.t.sol` next to the invariants in `test/InvariantTest.t.sol`, makes the taxonomy impossible to look away from — which is exactly what you want when the skill you're building is telling the three apart.
