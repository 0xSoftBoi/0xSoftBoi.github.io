---
layout: post
title: "Rebuilding a perps DEX from its docs"
date: 2026-06-09 15:00:00
series: "Bridge & DeFi security"
tags: [defi, perps, solidity, foundry, security]
image: /assets/og/rebuilding-a-perps-dex-from-its-docs.png
excerpt: "An old repo of mine had a perps-DEX frontend and nothing else — the protocol was gone. So I rebuilt it from the documentation of what it became. The interesting part is what the docs gave away: who the house is."
---

I had a repo, `blastperps`, that was a perpetual-futures DEX. Except all that survived was a zipped Next.js frontend — a trade page, an earn page — sitting on top of a private SDK that no longer exists. The entire on-chain protocol was gone, and I didn't have the source anymore.

The thing is, it shipped. It got rebranded to [Artura Finance](https://app.artura.finance) and it's live. So the protocol still exists *as documentation*, even though my copy of the code doesn't. That's enough to rebuild from — if you read the docs for the one thing that actually defines a perps DEX: **who is the counterparty?**

## The docs tell you who the house is

Artura's marketing says "inspired by Hyperliquid." Its *mechanics* say something much more specific. The liquidation rule is "you're liquidated once you've lost 90% of your collateral." The fees mention a "borrowing fee that goes into the vault." LPs "earn from trader losses." There's a single vault, and traders trade against it.

That's not an orderbook and it's not an AMM. That's the **[Gains Network / gTrade](https://gains.trade) pool model**: a single stablecoin vault is the *sole counterparty to every trade*. There's no other trader on the other side of your long — there's the LP pool, and it takes the opposite side of everything. When you win, the pool pays you. When you lose, the pool keeps it. The "earn" page in my old frontend wasn't a staking gimmick; it was people **funding the house**.

Once you know that, the whole protocol falls out of it.

<figure class="chart">
<svg viewBox="0 0 680 320" role="img" aria-labelledby="pp-t">
<title id="pp-t">The pool-perps money model: the LP vault is the counterparty to every trade</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<rect class="c-box-accent c-fill-soft" x="270" y="130" width="140" height="60" rx="10"/>
<text class="c-title" x="340" y="156" text-anchor="middle">LP vault</text>
<text class="c-label-sm" x="340" y="176" text-anchor="middle">the counterparty</text>
<text class="c-title" x="60" y="40">Trader wins</text>
<rect class="c-box" x="40" y="54" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="115" y="78" text-anchor="middle">profit paid out</text>
<line class="c-arrow" x1="266" y1="140" x2="192" y2="84"/>
<text class="c-label-sm" x="225" y="108" text-anchor="middle" fill="var(--accent)">LP NAV ↓</text>
<text class="c-title" x="510" y="40">Trader loses</text>
<rect class="c-box" x="490" y="54" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="565" y="78" text-anchor="middle">loss + fees kept</text>
<line class="c-arrow" x1="490" y1="84" x2="414" y2="140"/>
<text class="c-label-sm" x="455" y="108" text-anchor="middle">LP NAV ↑</text>
<rect class="c-box" x="270" y="240" width="140" height="44" rx="6"/>
<text class="c-label-sm" x="340" y="262" text-anchor="middle">borrowing fee +</text>
<text class="c-label-sm" x="340" y="277" text-anchor="middle">open/close fees</text>
<line class="c-arrow" x1="340" y1="240" x2="340" y2="192"/>
<text class="c-label-sm" x="340" y="306" text-anchor="middle">LPs are the house: their NAV is the inverse of net trader PnL, plus the fees.</text>
</svg>
<figcaption>No orderbook, no AMM curve. Every long and short is taken by the vault; LP share price = vault assets ÷ shares, which moves opposite to traders and up with fees.</figcaption>
</figure>

## The rebuild

Three contracts, in Foundry:

- **`ArturaVault`** — the LP vault, an ERC-20 share token (the "gToken"). Deposit the stablecoin, get pro-rata shares. Trader **profit is paid out of here**; trader **losses and fees flow in**. Share price is just `totalAssets / supply`, so it tracks net trader PnL exactly — and the vault can never pay out more than it holds (in the real protocol a backstop token mints to recapitalize; I left that as a documented seam).
- **`ArturaPerps`** — open/close leveraged longs and shorts against the vault. PnL is `collateral · leverage · (mark − entry) / entry`, priced off an oracle. A borrowing fee accrues over time to the vault. **Liquidation is permissionless once equity drops to 10% of collateral** — the gTrade signature.
- **`PriceFeed`** — keeper-pushed mark prices with a staleness guard. Artura's docs don't actually specify an on-chain staleness bound; I added one, because settling a trade on a stale price is how these get drained.

The one number I could check against reality: Artura's docs give a worked liquidation example — a 100× BTC long at \$20,000 with \$50 collateral liquidates at \$19,824. My `liquidationPrice` view, with the same inputs and zero fees, returns \$19,820; the \$4 is their \$1 borrowing-fee term. [That's a test](https://github.com/0xSoftBoi/blastperps/blob/main/test/Artura.t.sol). Nine of them pass: long and short PnL settled against the vault (LP NAV moving the right way each time), the liquidation threshold, the borrowing fee, the caps, the stale-oracle revert, and the solvency floor.

## What the docs don't make you honest about

This is the *core* money model, faithfully rebuilt and tested — not the whole of Artura. The backstop token that recapitalizes the vault, limit/stop orders, the OI-skew borrowing curve, referrals: all documented seams, none built. I wrote that down in the [README](https://github.com/0xSoftBoi/blastperps) rather than letting "rebuilt the perps DEX" imply more than nine tests' worth of protocol.

But the lesson that made the rebuild possible is the same one from the [index fund that held the wrong asset](/blog/the-index-fund-that-held-the-wrong-asset/) and the [bridge that paid twice](/blog/the-bridge-that-paid-twice/): in DeFi, the design *is* the answer to one question about where the value sits. For a perps DEX that question is "who's the counterparty," and once the docs answered it — the LPs are — there was nothing left to guess.

Contracts, tests, and the recovered frontend: [github.com/0xSoftBoi/blastperps](https://github.com/0xSoftBoi/blastperps).
