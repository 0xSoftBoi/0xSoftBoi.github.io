---
layout: post
title: "Anatomy of a fake dice game"
date: 2026-06-09 10:00:00
series: "On-chain randomness & verifiability"
tags: [solidity, randomness, security, gambling]
image: /assets/og/anatomy-of-a-fake-dice-game.png
excerpt: "I dug up a dice-game contract from 2018. It's 48 lines, and it's two bugs in a trenchcoat: its randomness is always zero, and it never uses the roll anyway — every bet just loses half. Here's the autopsy, and the provably-fair version it was pretending to be."
---

I went spelunking through some old repos and found a dice game from 2018 — `YungBet`, the on-chain half of a gambling project whose parent pitch deck claims it *"sold for $4.5m."* I can't verify that number, and after reading the contract I'd suggest not taking the deck at face value. It's 48 lines, and it is two bugs wearing a trenchcoat.

## Bug 1: the randomness is always zero

```solidity
function RandomNumber() public returns(uint) {
    total_bets[msg.sender]++;
    uint random_number = uint(keccak256(abi.encodePacked(
        blockhash(block.number),
        total_bets[msg.sender]
    )));
    ...
}
```

`blockhash(block.number)` — the hash of the block currently executing — is **always `0`**. The EVM only exposes the previous 256 block hashes; the current block isn't mined yet, so it has no hash. So the "random" number collapses to `keccak256(0, total_bets[msg.sender])` — a pure function of *your own bet counter*. You can compute every future roll you'll ever get, off-chain, before you bet. It's the same family as the [SmartBillions](/blog/the-on-chain-randomness-landscape/) lottery, which used a block hash that resolved to zero and got drained for ~400 ETH.

## Bug 2: it never uses the roll anyway

That bug almost doesn't matter, because of the second one:

```solidity
function makeBet() public payable {
    uint bet_roll = RandomNumber();          // computed...
    uint bet_payout = bet_amount.div(2);     // ...and ignored
    require(bet_payout < address(this).balance, "...");
    user.transfer(bet_payout);
    emit betPlaced(bet_amount, bet_payout, bet_roll);
}
```

`bet_roll` is computed, emitted in an event for flavour, and **never read**. The payout is unconditionally half your stake. There is no win condition, no target, no comparison — you send `x`, you get `x/2` back, every time. It's not a dice game with bad randomness; it's a guaranteed 50% drain with a random-number generator bolted on for decoration. The broken RNG is a red herring sitting on top of a contract that was never a game.

## Building the one it pretended to be

So I built the real thing — [`Dice.sol`](https://github.com/0xSoftBoi/dice/blob/main/src/Dice.sol). The starting constraint is the lesson of every randomness post I've written: **there is no safe single-transaction randomness on the EVM.** Anything you can read in the bet transaction, the bettor can read too. So you need a value that's fixed *before* the bet and unknown *until after* it — commit-reveal.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="d-t">
<title id="d-t">A fake dice flow versus a provably-fair commit-reveal flow</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">YungBet: a roll nobody rolls</text>
<rect class="c-box" x="20" y="46" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="95" y="70" text-anchor="middle">bet</text>
<line class="c-arrow" x1="172" y1="66" x2="214" y2="66"/>
<rect class="c-box" x="216" y="46" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="316" y="66" text-anchor="middle">blockhash(now) = 0 -> roll</text>
<text class="c-label-sm" x="316" y="80" text-anchor="middle">(predictable, and unused)</text>
<line class="c-arrow" x1="418" y1="66" x2="460" y2="66"/>
<rect class="c-box" x="462" y="46" width="198" height="40" rx="6"/>
<text class="c-label-sm" x="561" y="70" text-anchor="middle">always pay stake / 2</text>
<line class="c-grid" x1="20" y1="108" x2="660" y2="108"/>
<text class="c-title" x="20" y="136">Dice: house pre-commit + player seed + reveal</text>
<rect class="c-box-accent c-fill-soft" x="20" y="156" width="158" height="46" rx="8"/>
<text class="c-label-sm" x="99" y="176" text-anchor="middle">house commits</text>
<text class="c-label-sm" x="99" y="192" text-anchor="middle">keccak(serverSeed)</text>
<line class="c-arrow" x1="180" y1="179" x2="218" y2="179"/>
<rect class="c-box" x="220" y="156" width="170" height="46" rx="6"/>
<text class="c-label-sm" x="305" y="176" text-anchor="middle">bet + target + clientSeed</text>
<text class="c-label-sm" x="305" y="192" text-anchor="middle">(your entropy)</text>
<line class="c-arrow" x1="392" y1="179" x2="430" y2="179"/>
<rect class="c-box-accent c-fill-soft" x="432" y="156" width="228" height="46" rx="8"/>
<text class="c-label-sm" x="546" y="176" text-anchor="middle">reveal -> roll = keccak(server,</text>
<text class="c-label-sm" x="546" y="192" text-anchor="middle">client, id) % 100 decides; edge applied</text>
<text class="c-label-sm" x="340" y="232" text-anchor="middle">House can't pick the seed late; player can't see it early; the roll actually pays.</text>
<text class="c-label-sm" x="340" y="256" text-anchor="middle">No reveal by the deadline? Every bet pays as a WIN — withholding can't help the house.</text>
</svg>
<figcaption>The fake game computes an unused, predictable number and pays half. The real one binds the outcome to a seed the house committed before the bet and revealed after — and pays the house edge on a roll that decides.</figcaption>
</figure>

The shape:

- The **house commits** `keccak256(serverSeed)` *before* any bet references it, so it can't choose the seed after seeing the action.
- Each **bet** carries a player-chosen `clientSeed`. The roll is `keccak256(serverSeed, clientSeed, betId) % 100` — the house can't predict it without knowing the player's seed, the player can't predict it without the still-secret server seed, and neither can grind it.
- The **roll decides**: bet that it lands under a target, paid with a real **house edge** — a 50/50 bet pays `1.96×`, not `2×`. (The original couldn't even charge an edge; it just kept half.)

The one residual is the *house* withholding a losing reveal — the [last-revealer problem](/blog/verifiable-isnt-trustless-onchain-randomness/) that haunts every commit-reveal scheme. `claimRevealTimeout` closes it: miss the deadline and **every bet in the round pays as a win**, so withholding is strictly worse for the house than just revealing. Plus the boring-but-load-bearing parts the original lacked entirely: a bankroll that reserves each open bet's maximum loss (unbacked bets revert), pull-payment withdrawals, reentrancy guards. It's [seven Foundry tests](https://github.com/0xSoftBoi/dice), including one that confirms the outcome actually tracks the roll and one that pays the player when the house goes quiet.

## The lesson

The funny thing about `YungBet` is that the headline bug — the always-zero randomness — is the *less* serious one. You could fix the RNG perfectly and the contract would still just take half your money, because it never looked at the roll. It's the purest example of a pattern I keep running into: the cryptography is rarely where these things actually break. The break is in whether the outcome people are betting on is *bound to* the cryptography at all — the [randomness](/blog/the-on-chain-randomness-landscape/), the [proof](/blog/what-a-zk-proof-proves/), the roll. Here it wasn't bound to anything. It was decoration on a coin-flip you always lose.

The audit and the rebuild are at [github.com/0xSoftBoi/dice](https://github.com/0xSoftBoi/dice).
