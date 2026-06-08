---
layout: post
title: "An AMM built to be attacked"
date: 2026-04-08
tags: [security, defi, foundry]
image: /assets/og/an-amm-built-to-be-attacked.png
excerpt: "Most AMM code is written to look safe. I wrote one to be a teaching specimen — where the exploits are tests in the repo, some of them passing, and the real lesson is which 'attacks' are contract bugs, which are economic facts of life, and which are mitigated and why."
---

The hard part of auditing an AMM isn't the swap math. It's judgment. An attack succeeds, and you have to say which of three things just happened: a *bug* you must fix, an *economic reality* you can only warn about, or a *weakness* you accepted on purpose. From the outside, all three look the same.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="am-t">
<title id="am-t">Three categories of AMM attack: contract bugs to fix, economic realities to warn about, and accepted weaknesses to document</title>
<text class="c-title" x="20" y="26">Someone walks away with money they didn’t deposit. Which kind is it?</text>
<rect class="c-box-accent c-fill-soft" x="20" y="56" width="204" height="210" rx="8"/>
<text class="c-val" x="36" y="82">contract bug</text>
<text class="c-label-sm" x="36" y="100">→ fix it</text>
<line class="c-grid" x1="36" y1="112" x2="208" y2="112"/>
<text class="c-label" x="36" y="138">x·y &lt; k after a swap</text>
<text class="c-label-sm" x="36" y="158">reserves shrink — the pool</text>
<text class="c-label-sm" x="36" y="174">is leaking value</text>
<text class="c-label-sm" x="36" y="240">caught by the invariant:</text>
<text class="c-label-sm" x="36" y="256">x·y ≥ k, always</text>
<rect class="c-box" x="238" y="56" width="204" height="210" rx="8"/>
<text class="c-val" x="254" y="82">economic reality</text>
<text class="c-label-sm" x="254" y="100">→ warn, can’t patch</text>
<line class="c-grid" x1="254" y1="112" x2="426" y2="112"/>
<text class="c-label" x="254" y="138">sandwich / MEV</text>
<text class="c-label-sm" x="254" y="158">x·y ≥ k holds — defense is</text>
<text class="c-label-sm" x="254" y="174">the caller’s slippage guard</text>
<text class="c-label" x="254" y="212">first-depositor donation</text>
<text class="c-label-sm" x="254" y="232">economics, not a leak —</text>
<text class="c-label-sm" x="254" y="248">a √-bootstrap makes it</text>
<text class="c-label-sm" x="254" y="264">cost N² to inflate N</text>
<rect class="c-box" x="456" y="56" width="204" height="210" rx="8"/>
<text class="c-val" x="472" y="82">accepted weakness</text>
<text class="c-label-sm" x="472" y="100">→ document the decision</text>
<line class="c-grid" x1="472" y1="112" x2="644" y2="112"/>
<text class="c-label" x="472" y="138">no TWAP oracle</text>
<text class="c-label-sm" x="472" y="156">spot price manipulable</text>
<text class="c-label" x="472" y="190">integer math rounds down</text>
<text class="c-label-sm" x="472" y="208">dust accrues to the pool</text>
<text class="c-label" x="472" y="242">no flash loans</text>
<text class="c-label-sm" x="472" y="260">a scope choice, not safety</text>
</svg>
<figcaption>All three look identical from outside — money leaves the pool. The skill is filing each correctly: bug, economics, or accepted limitation. A pool that’s merely safe hides that distinction.</figcaption>
</figure>

So I built [QuantDEX](https://github.com/0xSoftBoi/quantgroup): a constant-product (`x·y=k`) AMM with a 0.3% fee, written not to be production-safe but to be *annotated*. The invariants are proven. The attacks are reproduced as tests. Every "this is fine" is justified in a comment with an SWC or CWE reference. It's marked `@custom:audit-status unaudited — educational only`, because a safe pool was never the point. A precise map was.

## What must always be true

Three invariants, checked by a Foundry handler that hammers the pool with fuzzed swaps and liquidity operations while tracking ghost state on the side — the same invariant-fuzzing setup I use on bridges:

- **`x·y ≥ k` after every swap.** The product of reserves never decreases; fees can only push it up. If a sequence of operations ever shrinks `k`, the pool is leaking value and that *is* a bug.
- **Ghost share accounting.** The sum of every LP's shares equals `totalShares`, always. The handler mints and burns independently and asserts the contract agrees.
- **No ghost shares.** `totalShares > 0` if and only if reserves are nonzero — you can't end up with claims against an empty pool.

These are the line. Anything that holds all three while still moving money is, by definition, *not* a solvency bug — it's behavior the protocol permits. That distinction is the whole skill, and it's what the attack tests are there to illustrate.

## The attacks that work — on purpose

Two of the simulated attacks succeed, and the tests say so plainly:

**Sandwich.** The attacker front-runs a victim's 10k swap with a 20k swap on a 100k pool, lets the victim eat the price impact, then back-runs to sell into the move. The victim provably receives less than fair output; the attacker profits. And `x·y ≥ k` holds the entire time. That's the lesson: a sandwich is **not a contract bug** — the AMM did exactly what it promised. It's a mempool-ordering reality — transaction-order dependence, [SWC-114](https://swcregistry.io/docs/SWC-114) — and the defense lives in the *caller's* slippage guard, not the pool (private orderflow and batch auctions are the complementary fixes). A companion test, `testSlippageGuardBlocksMEV`, shows the same attack failing once the victim sets a `minAmountOut`. The 0.3% fee, notably, is friction — the attacker pays it on both legs — but friction isn't protection.

**First-depositor donation / share inflation.** The classic: be the first to deposit, mint a single share, then *donate* tokens straight to the contract to inflate what that one share is worth, so the next depositor's deposit rounds down to zero shares. But that attack only works if the pool reads its **token balance** as the reserve — then a raw transfer moves the price. QuantDEX never does: reserves are internal accounting (`pool.reserveA/reserveB`), touched only inside `addLiquidity` and `swap`, so a donation is invisible to the share math and the vector simply closes. The geometric-mean (`sqrt`) bootstrap on the first mint is doing a *different* job — Uniswap V2's trick (§3.4) to make initial share value independent of the deposit *ratio*, not a defense against inflation. (The canonical inflation defense elsewhere is burning a slug of dead shares — Uniswap V2's `MINIMUM_LIQUIDITY`, or ERC-4626's virtual shares; the cost it imposes is linear, never the `N²` I'd want it to be.) The test documents the attack and shows internal reserves defang it.

## The weaknesses I wrote down instead of fixing

The most useful comments in the contract are the ones admitting what it *doesn't* do, labeled as decisions rather than oversights:

- **No TWAP oracle** → the spot price is manipulable within a single transaction, classically via a flash loan. There's no SWC entry for oracle manipulation; the reference an auditor reaches for is samczsun's [*So you want to use a price oracle*](https://samczsun.com/so-you-want-to-use-a-price-oracle/). Documented, because anything reading this pool's price as an oracle is the real vulnerability, not the pool.
- **Integer math rounds down** → tiny amounts of dust accrue to the pool on each operation. Safe — it always rounds in the pool's favor — but an auditor should see it and confirm the direction, so it's noted.
- **No flash loans, single deployer** → smaller attack surface than a fully trustless v2, and called out as a *scope* choice, not a safety claim.

## Why a specimen beats a fortress

[The bridge I audited recently](/blog/auditing-my-own-bridge/) taught me from one direction: write the invariant that must never break, fuzz until something breaks it, fix the bug. This AMM teaches from the other. Start from the invariants that *do* hold, then walk the catalogue of things that can still go wrong *on top of* a correct contract — and file each one: bug, economics, or accepted limitation.

A pool that's merely safe hides all of that. A pool built to be attacked puts it on the table — the exploits in `test/Attacks.t.sol`, right beside the invariants in `test/InvariantTest.t.sol`. You can't look away from the taxonomy. That's the point, because telling the three apart is the whole skill.
