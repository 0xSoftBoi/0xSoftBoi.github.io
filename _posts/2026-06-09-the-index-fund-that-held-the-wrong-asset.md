---
layout: post
title: "The index fund that held the wrong asset"
date: 2026-06-09
tags: [sui, move, defi, oracle, security]
image: /assets/og/the-index-fund-that-held-the-wrong-asset.png
excerpt: "A Sui Move 'crypto index fund' lets you deposit SUI for exposure to a BTC/ETH/XRP/ADA/MATIC basket. The problem: it never buys any of them. It holds SUI and pays out basket gains it doesn't have — insolvent by construction, a bank run waiting for a green candle."
---

I found a Sui Move contract called `crypto_index_fund`. You deposit SUI, it mints you an `IndexFundToken` recording an equal-weighted basket — BTC, ETH, XRP, ADA, MATIC, priced through the Supra oracle — and when you withdraw it pays you out in SUI at the basket's current value. A one-click crypto index fund on-chain. Slick.

It is also insolvent the moment any price moves, and the reason is the first thing you should check in any fund: **does it actually hold what it says it holds?**

## It holds SUI. It pays a basket.

Here's the withdraw, trimmed:

```move
// value the token's NOTIONAL basket at current oracle prices...
let total_usd_value = btc_usd + eth_usd + xrp_usd + ada_usd + matic_usd;
let total_sui = ((total_usd_value / adjusted_sui_usd_price) as u64);
// ...and pay that many SUI out of the shared pool
let index_token_balance = balance::split(&mut index_fund.balance, total_sui);
```

Deposit only ever added SUI to `index_fund.balance`. The contract **never bought a single satoshi of BTC** — the basket is a number in a struct. So when BTC goes up, your token is "worth" more SUI, and `withdraw` pays it to you out of the common pool, which is just everyone else's SUI.

Play it forward with two depositors. Both put in 1,000 SUI; the pool holds 2,000. BTC rallies. Alice withdraws first: her token now values at, say, 1,400 SUI, so `balance::split` hands her 1,400 and leaves 600. Bob withdraws: his token also values at 1,400, `balance::split(&mut pool, 1400)` against a 600 balance — **abort**. Bob's money is stuck. It's a bank run, except the run is triggered by a green candle and the loser is whoever clicks second. (There's tangled decimal math and no oracle-staleness check on top, but the insolvency is the one that empties wallets.)

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="if-t">
<title id="if-t">A fund that pays a basket it doesn't hold vs a solvent pro-rata fund</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Original: holds SUI, owes a basket</text>
<rect class="c-box" x="20" y="46" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="95" y="70" text-anchor="middle">deposit SUI</text>
<line class="c-arrow" x1="172" y1="66" x2="214" y2="66"/>
<rect class="c-box" x="216" y="46" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="316" y="70" text-anchor="middle">record notional basket</text>
<line class="c-arrow" x1="418" y1="66" x2="460" y2="66"/>
<rect class="c-box-accent c-fill-soft" x="462" y="46" width="198" height="40" rx="8"/>
<text class="c-label-sm" x="561" y="63" text-anchor="middle">withdraw basket value in SUI</text>
<text class="c-label-sm" x="561" y="79" text-anchor="middle">→ drain pool, 2nd aborts</text>
<line class="c-grid" x1="20" y1="108" x2="660" y2="108"/>
<text class="c-title" x="20" y="136">Fixed: pro-rata shares of what's actually held</text>
<rect class="c-box" x="20" y="158" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="95" y="182" text-anchor="middle">deposit SUI</text>
<line class="c-arrow" x1="172" y1="178" x2="214" y2="178"/>
<rect class="c-box" x="216" y="158" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="316" y="182" text-anchor="middle">mint pro-rata shares</text>
<line class="c-arrow" x1="418" y1="178" x2="460" y2="178"/>
<rect class="c-box-accent c-fill-soft" x="462" y="158" width="198" height="40" rx="8"/>
<text class="c-label-sm" x="561" y="175" text-anchor="middle">withdraw pool·shares/total</text>
<text class="c-label-sm" x="561" y="191" text-anchor="middle">→ always ≤ pool, never aborts</text>
<text class="c-label-sm" x="340" y="234" text-anchor="middle">You can only ever be paid your slice of what the fund actually holds.</text>
<text class="c-label-sm" x="340" y="258" text-anchor="middle">The oracle becomes informational NAV — with a staleness guard — not the money path.</text>
</svg>
<figcaption>The original pays a basket's value out of a SUI-only pool; the fix pays each holder their pro-rata share of the pool that actually exists.</figcaption>
</figure>

## Fix it by only ever paying what you hold

The [solvent rebuild](https://github.com/0xSoftBoi/01/tree/main/move/index-fund) is a pro-rata **share** fund. Deposit mints shares proportional to the pool; withdraw returns `pool * shares / total_shares` SUI. That quantity is *always* ≤ the pool — so `balance::split` can never abort, and the fund can never owe SUI it doesn't have. The oracle drops out of the money path entirely and becomes an *informational* USD NAV view (now with the staleness check the original skipped). The [headline test](https://github.com/0xSoftBoi/01/blob/main/move/index-fund/tests/index_fund_tests.move) is just: two depositors, withdraw both — the second one *succeeds* instead of aborting. Five Move tests, green.

And here's the honest part I put in the README: this solvent thing **isn't really an index fund anymore**. It's a SUI pool with a NAV readout. A *real* on-chain index fund has to actually **custody the assets** — swap the deposited SUI into wrapped BTC/ETH/… through a DEX so the basket exists on-chain. That's the part the original skipped, and skipping it is the whole bug. You can't pay out exposure you never bought.

It's the same lesson as the [fake dice game](/blog/anatomy-of-a-fake-dice-game/) and the [bridge that paid twice](/blog/the-bridge-that-paid-twice/): the contract isn't where these break. They break on a promise the contract makes about value it doesn't actually hold — a roll it never reads, a release it never recorded, a basket it never bought. Read what the pool contains before you read what it claims to owe.

Audit, fix, and the five passing tests are at [github.com/0xSoftBoi/01](https://github.com/0xSoftBoi/01/tree/main/move/index-fund).
