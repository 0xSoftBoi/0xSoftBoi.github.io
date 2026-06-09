---
layout: post
title: "Anatomy of a memecoin honeypot"
date: 2026-06-09 12:00:00
series: "Bridge & DeFi security"
tags: [solidity, security, memecoin, rug]
image: /assets/og/anatomy-of-a-memecoin-honeypot.png
excerpt: "A token contract I found trades perfectly and looks like every other ERC-20. It also lets the deployer freeze your bag with one call. Here's the line that does it, proven against the real contract — and what an un-ruggable token looks like instead."
---

I found a memecoin contract in an old repo — `DarkPepe` (`DEPE`), the copy-pasted "token with a blacklist" template that's been deployed thousands of times. It compiles, it trades, it has a cute name. It also hands the deployer a button that freezes your tokens after you buy. Here is that button, in full:

```solidity
mapping(address => bool) public blacklists;

function blacklist(address _address, bool _isBlacklisting) external onlyOwner {
    blacklists[_address] = _isBlacklisting;
}

function _beforeTokenTransfer(address from, address to, uint256 amount) override internal {
    require(!blacklists[to] && !blacklists[from], "Blacklisted");
    ...
}
```

Every transfer runs `_beforeTokenTransfer` first. So the moment the owner calls `blacklist(you, true)`, every transfer touching your address reverts. You can't sell. You can't move it to another wallet. You can't even *receive* more. Your bag is frozen, on-chain, at the deployer's discretion. You buy at the top, they flip the switch, and the exit is gone. That's a honeypot — and it's not hidden in assembly or a proxy, it's eleven lines of plain Solidity.

There are two more levers in the same contract:

```solidity
// in _beforeTokenTransfer:
if (uniswapV2Pair == address(0)) {
    require(from == owner() || to == owner(), "trading is not started");
    return;
}
if (limited && from == uniswapV2Pair) {
    require(balanceOf(to) + amount <= maxHoldingAmount && ... >= minHoldingAmount, "Forbid");
}
```

The first means that **until the owner sets the pair, only the owner can move tokens** — they decide if and when trading ever opens, and can simply never open it. The second lets `setRule(...)` cap how much anyone can buy, down to zero. Mint 100% of supply to yourself, retain ownership, and you hold every lever.

<figure class="chart">
<svg viewBox="0 0 680 290" role="img" aria-labelledby="hp-t">
<title id="hp-t">A honeypot token freezes the buyer; a trap-free token can't</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">DarkPepe: the deployer keeps the keys</text>
<rect class="c-box" x="20" y="46" width="120" height="40" rx="6"/>
<text class="c-label-sm" x="80" y="70" text-anchor="middle">you buy</text>
<line class="c-arrow" x1="142" y1="66" x2="184" y2="66"/>
<rect class="c-box" x="186" y="46" width="210" height="40" rx="6"/>
<text class="c-label-sm" x="291" y="70" text-anchor="middle">owner calls blacklist(you, true)</text>
<line class="c-arrow" x1="398" y1="66" x2="440" y2="66"/>
<rect class="c-box-accent c-fill-soft" x="442" y="46" width="218" height="40" rx="8"/>
<text class="c-label-sm" x="551" y="70" text-anchor="middle">every transfer reverts — frozen</text>
<text class="c-label-sm" x="20" y="116">Three owner levers: freeze any holder · gate trading until "started" · cap/forbid buys.</text>
<line class="c-grid" x1="20" y1="138" x2="660" y2="138"/>
<text class="c-title" x="20" y="166">SafeToken: nothing privileged to call</text>
<rect class="c-box" x="20" y="188" width="120" height="40" rx="6"/>
<text class="c-label-sm" x="80" y="212" text-anchor="middle">you buy</text>
<line class="c-arrow" x1="142" y1="208" x2="184" y2="208"/>
<rect class="c-box" x="186" y="188" width="210" height="40" rx="6"/>
<text class="c-label-sm" x="291" y="208" text-anchor="middle">no owner / blacklist / gate exists</text>
<line class="c-arrow" x1="398" y1="208" x2="440" y2="208"/>
<rect class="c-box-accent c-fill-soft" x="442" y="188" width="218" height="40" rx="8"/>
<text class="c-label-sm" x="551" y="208" text-anchor="middle">you can always sell</text>
<text class="c-label-sm" x="340" y="262" text-anchor="middle">Read _beforeTokenTransfer (or _update) and every onlyOwner function before you ape.</text>
</svg>
<figcaption>The honeypot isn't subtle — it's a <code>blacklist</code> mapping checked on every transfer. A token nobody can rug simply has no privileged function to call.</figcaption>
</figure>

## Proving it, and the antidote

I didn't want to just assert this, so I [wrote three Foundry tests](https://github.com/0xSoftBoi/01/blob/main/audit/test/Honeypot.t.sol) against the *real* `DarkPepe` bytecode. One buys in as a holder, has the owner blacklist them, and asserts the next sell reverts with `"Blacklisted"` — and that they can no longer receive either. One shows that before trading is "started," a non-owner transfer reverts. They pass. The honeypot is exactly as advertised.

Then the antidote, also tested: `SafeToken` — a deliberately un-ruggable ERC-20. Fixed supply minted once, **no owner, no blacklist, no transfer gate, no mint, no holding caps.** There is no function any party can call to freeze or seize a balance, so the test that tries to trap a holder has nothing to call. That's the whole point: safety here isn't a feature you add, it's privilege you *remove*.

## The takeaway

This is the most actionable post I'll write, so here it is plainly: **before you ape a token, read two things** — its `_beforeTokenTransfer` / `_update` hook, and every `onlyOwner` function. A `blacklists` mapping, a `tradingEnabled` flag, a `setRule` that gates the pair, a `_mint` the owner can still call — any one of them means the deployer can stop you selling or dilute you at will. The contract will look friendly and trade fine right up until it doesn't. The exit being open today doesn't mean it's open tomorrow if someone else holds the key.

The audit, the proofs, and the trap-free reference are at [github.com/0xSoftBoi/01](https://github.com/0xSoftBoi/01/blob/main/AUDIT.md).
