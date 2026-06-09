---
layout: post
title: "An arbitrage bot with no slippage is a sandwich"
date: 2026-06-09
series: "Bridge & DeFi security"
tags: [defi, mev, flashloan, solidity, security]
image: /assets/og/an-arb-bot-with-no-slippage-is-a-sandwich.png
excerpt: "I rebuilt a 2021 flash-loan hackathon contract into a real Aave v3 arbitrage. The contract got the hard security right — and left the door open on the thing arb bots exist to exploit."
---

A flash-loan arbitrage contract is a neat trick: borrow a pile of money you don't have, use it to buy an asset cheap on one DEX and sell it dear on another, pay the loan back in the same transaction, and keep the difference. If the trade isn't profitable, the whole thing reverts and you're out nothing but gas. I had a 2021 hackathon skeleton of exactly this — an Aave **v1** contract in Solidity 0.5 with the borrowing wired up and no actual arb — and rebuilt it into a real Aave **v3** strategy.

The contract gets the genuinely hard part right. The part it left open is the one an arbitrage bot, of all things, should know about.

## The hard part it got right

The dangerous surface of a flash-loan receiver is the callback. Aave hands control to your `executeOperation` *in the middle of its own transaction*, holding your borrowed funds. Two things have to be true or you're drained:

```solidity
require(msg.sender == address(POOL_CONTRACT), "caller not pool");
require(initiator == address(this),          "bad initiator");
```

The first stops anyone but Aave from calling the callback directly. The second is subtler and more important: without it, *I* could call `flashLoanSimple` and name **your** contract as the receiver, and Aave would dutifully invoke your `executeOperation` with my parameters — running your logic with attacker-chosen routers. Binding `initiator == address(this)` means the loan had to originate from this contract's own `executeArb`. Both guards are there, and the repayment is enforced before any profit is swept. That's the stuff that usually gets these contracts emptied, and it was correct.

## The part it didn't

The swaps had no slippage protection. Each leg just took whatever the router gave:

```solidity
router.swapExactTokensForTokens(amountIn, 0, path, ...);  // amountOutMin = 0
```

Here's why that's the bug, and why it's almost funny that it's *this* contract: an arbitrage transaction sits in the public mempool announcing "I am about to do two profitable swaps." A searcher reads it, front-runs to move the pool against you, lets your swaps execute at the worse price, and back-runs to collect. The contract built to harvest a price spread becomes the perfect victim of one — it broadcasts its intent and then accepts any fill. The arb bot is the sandwich filling.

And the `minProfit` check at the end doesn't save you, which is the trap. Profit is measured *after both swaps*, so a sandwich that degrades each leg can still leave you above a loose `minProfit` while a searcher pockets the difference — or it pushes you to a tiny revert with nothing gained. You need a floor on **each swap** (`amountOutMin`) plus a `deadline`, not just a check on the final tally.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="arb-t">
<title id="arb-t">A flash-loan arb cycle, and where an unprotected swap gets sandwiched</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<rect class="c-box" x="20" y="60" width="120" height="44" rx="6"/>
<text class="c-label-sm" x="80" y="86" text-anchor="middle">borrow (flash)</text>
<line class="c-arrow" x1="142" y1="82" x2="174" y2="82"/>
<rect class="c-box-accent c-fill-soft" x="176" y="60" width="140" height="44" rx="8"/>
<text class="c-label-sm" x="246" y="80" text-anchor="middle">swap A (buy)</text>
<text class="c-label-sm" x="246" y="96" text-anchor="middle">amountOutMin = 0</text>
<line class="c-arrow" x1="318" y1="82" x2="350" y2="82"/>
<rect class="c-box-accent c-fill-soft" x="352" y="60" width="140" height="44" rx="8"/>
<text class="c-label-sm" x="422" y="80" text-anchor="middle">swap B (sell)</text>
<text class="c-label-sm" x="422" y="96" text-anchor="middle">amountOutMin = 0</text>
<line class="c-arrow" x1="494" y1="82" x2="526" y2="82"/>
<rect class="c-box" x="528" y="60" width="130" height="44" rx="6"/>
<text class="c-label-sm" x="593" y="82" text-anchor="middle">repay + profit?</text>
<rect class="c-box" x="176" y="150" width="100" height="36" rx="6"/>
<text class="c-label-sm" x="226" y="172" text-anchor="middle" fill="var(--accent)">front-run</text>
<rect class="c-box" x="392" y="150" width="100" height="36" rx="6"/>
<text class="c-label-sm" x="442" y="172" text-anchor="middle" fill="var(--accent)">back-run</text>
<line class="c-arrow" x1="226" y1="150" x2="240" y2="106"/>
<line class="c-arrow" x1="428" y1="106" x2="442" y2="150"/>
<text class="c-label-sm" x="334" y="172" text-anchor="middle">searcher's sandwich →</text>
<text class="c-label-sm" x="340" y="232" text-anchor="middle">With amountOutMin = 0, each public swap accepts any fill — the searcher moves the price,</text>
<text class="c-label-sm" x="340" y="254" text-anchor="middle">your swaps execute worse, and the final minProfit check can still pass. Bound each leg.</text>
</svg>
<figcaption>The callback guards (only-pool, initiator-bound) were correct; the unprotected swaps weren't. A per-leg <code>amountOutMin</code> + <code>deadline</code> is the fix — a trailing <code>minProfit</code> isn't enough.</figcaption>
</figure>

## Who found it

I didn't, on the first pass. The rebuild came out of a [model-tiered agent workflow](/blog/a-social-good-protocol-built-by-an-agent-fleet/) — one model writes the contract, a stronger one audits it before anything ships. The builder got the callback guards right and left the slippage at zero; the auditor flagged it medium-severity ("an arb with no `amountOutMin` is a free sandwich"), and the fix — per-leg `minOut1`/`minOut2` and a `deadline` — went in with a regression test. Then I re-ran all 17 tests myself and read the callback by hand, because a green check from the fleet is a claim, not a result.

The [contract, the mocks, and the tests](https://github.com/0xSoftBoi/marketmakehackathon) are public. It's tested against mock Aave and mock DEXes, not live ones — so it's a faithful model of the strategy, not a deployed bot. But the lesson generalizes past flash loans: the protections you're sure you don't need are the ones for the attack your own code is *designed around*. An arb contract is a price-spread predator that forgot it trades in public.
