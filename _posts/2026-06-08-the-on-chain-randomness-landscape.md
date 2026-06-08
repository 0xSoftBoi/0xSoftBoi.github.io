---
layout: post
title: "The on-chain randomness landscape, or: how to pick a chess position fairly"
date: 2026-06-08
tags: [randomness, vrf, cryptography, solidity, security]
image: /assets/og/the-on-chain-randomness-landscape.png
excerpt: "Fischer-random chess needs one of 960 starting positions, drawn so neither player can rig or foresee it. On a deterministic chain that's surprisingly hard — and the way you solve it is the whole map of on-chain randomness: commit-reveal, VRFs, beacons, native RNG, and the one footgun they all share."
---

I have a fully on-chain chess engine, and I wanted it to play [Chess960](https://en.wikipedia.org/wiki/Chess960) — Fischer Random, where the back rank is shuffled into one of 960 starting positions. Generating a position from a number is easy. The hard part is the number: the 960 setups are *not* equally advantageous, so whoever picks it — or merely knows it in advance — has an edge. You need to draw one of 960 such that **neither player can bias it and neither can foresee it.**

On a blockchain, that one little requirement opens onto the entire field of on-chain randomness. A chain is deterministic on purpose: every node must reach the same state, so there's no `rand()` to call. Anything already on-chain — a block hash, a timestamp, `prevrandao` — is visible to whoever builds the block, and they'll re-roll until it suits them. You have to *import* unpredictability, and every way of doing it makes a different trade.

## The four ways, and what each one trusts

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="rl-t">
<title id="rl-t">Four ways to get randomness on-chain, and the footgun each carries</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Even perfect randomness fails if the caller can see it and abort</text>
<rect class="c-box" x="20" y="52" width="150" height="48" rx="6"/>
<text class="c-val" x="95" y="74" text-anchor="middle">random value</text>
<text class="c-label-sm" x="95" y="91" text-anchor="middle">drawn / revealed</text>
<line class="c-arrow" x1="172" y1="76" x2="244" y2="76"/>
<rect class="c-box-accent c-fill-soft" x="246" y="46" width="190" height="60" rx="8"/>
<text class="c-val" x="341" y="70" text-anchor="middle">caller sees the outcome</text>
<text class="c-label-sm" x="341" y="88" text-anchor="middle">before the tx commits</text>
<line class="c-arrow" x1="438" y1="76" x2="510" y2="76"/>
<rect class="c-box" x="512" y="52" width="148" height="48" rx="6"/>
<text class="c-val" x="586" y="74" text-anchor="middle">loss? abort &amp; retry</text>
<text class="c-label-sm" x="586" y="91" text-anchor="middle">costless re-roll</text>
<text class="c-label-sm" x="340" y="132" text-anchor="middle">Abort = a free re-roll, which collapses a fair distribution into "keep only the wins."</text>
<line class="c-grid" x1="20" y1="158" x2="660" y2="158"/>
<text class="c-label-sm" x="20" y="184">The fix, everywhere: whoever can abort must commit BEFORE the value is revealed.</text>
<rect class="c-box" x="20" y="200" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="120" y="224" text-anchor="middle">Chess960: reveal-deadline forfeit</text>
<rect class="c-box" x="232" y="200" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="332" y="224" text-anchor="middle">Sui/Aptos: private entry fn</text>
<rect class="c-box" x="444" y="200" width="216" height="40" rx="6"/>
<text class="c-label-sm" x="552" y="224" text-anchor="middle">Chainlink: no re-request, fix inputs</text>
<text class="c-label-sm" x="340" y="266" text-anchor="middle">RANDAO's last-revealer is the same move: a proposer withholds a block to pick the result.</text>
</svg>
<figcaption>The approaches differ in their trust root, but share one failure mode — a consumer that lets the caller observe the result and revert. Every platform's headline rule is a patch for it.</figcaption>
</figure>

**Commit-reveal.** Each party commits `hash(seed)` up front, then both reveal; the output combines the seeds. No keys, no oracle — security rests on everyone revealing. Its failure mode is the **last revealer**, who can withhold their reveal once they've seen the others' and dislike the result. This is what I used for Chess960, because a 1v1 game has exactly two parties to commit against, and the last-revealer problem has a clean on-chain answer: a reveal deadline, and if your opponent stalls, you win by forfeit. A player can't dodge a position they don't like by going quiet.

**External oracle VRF** (Chainlink, and on Solana ORAO / Switchboard). A [Verifiable Random Function](https://www.rfc-editor.org/rfc/rfc9381.html) is the public-key analogue of a keyed hash: the key-holder produces an output plus a proof, and anyone can verify the output is the *unique* correct one for that input — without the key. That uniqueness is the magic: one input maps to exactly one output, so the oracle can't grind for a favorable result. (This is also why VRFs are built on **BLS**, a unique signature — there's exactly one valid signature per key and message — and *not* ECDSA, whose fresh per-signature nonce means many valid signatures exist.) The trust shifts to the oracle's liveness and the block your request lands in, which is why [Chainlink's own docs](https://docs.chain.link/vrf/v2-5/security) insist you wait for confirmations, **never re-request** randomness, and stop accepting user inputs once a request is in flight.

**Threshold beacon** ([drand](https://drand.love), and the validator-DKG randomness inside Sui and Aptos). A committee runs distributed key generation and threshold-signs each round, so no single member knows the key and a sub-threshold minority can't bias or predict the output. drand has emitted public randomness this way since 2019; it even supports timelock encryption — sealing a value until a future round's beacon exists. This is the strongest trust root (a third of validators, not one oracle), and it's what backs the native-randomness paths I used in the [Sui coin-flip](/blog/verifiable-isnt-trustless-onchain-randomness/).

**Native protocol RNG** — Ethereum's [`prevrandao`](https://eips.ethereum.org/EIPS/eip-4399). Free, in-protocol, and **biasable in a precise way**: each slot's proposer chooses to reveal (mix in their value) or skip (keep the old one) — one bit of influence. With *k* consecutive end-of-epoch slots a proposer gets 2^k choices for the final value. It self-heals (one honest proposal re-randomizes everything) and withholding forfeits the block reward, but it must never back a high-value single-block draw.

| | trust root | biasable? | the footgun |
|---|---|---|---|
| **commit-reveal** | the participants | last revealer can withhold | griefing → needs a reveal deadline |
| **oracle VRF** | the oracle key + request block | not by grinding (uniqueness) | re-request / inputs-after-request |
| **threshold beacon** | ⅔ of a committee | no (below threshold) | the *consumer* (see below) |
| **native RNG** | block proposers | yes — *k* bits for *k* slots | not for high-value single-block draws |

## What actually goes wrong, in the wild

None of these are theoretical. The predictable-seed era of EVM/EOS gambling is a graveyard: **SmartBillions** (2017) seeded its lottery from a blockhash but never checked the block's age — after 256 blocks `blockhash()` returns zero, so the "random" number was knowable, and ~400 ETH walked out. **EOSPlay** (2019) derived its number from a block ten ahead; an attacker rented network CPU to flood the chain, predicted the result block, and bet only on wins for ~28,000 EOS. And the most instructive one needs no naivety at all: a 2022 white-hat found that a malicious subscription owner could **block and re-roll Chainlink VRF** until it returned a favorable value — the "never re-request" rule, weaponized — and collected a [$300K bounty](https://blog.chain.link/smart-contract-research-case-study/). The randomness was perfect; the *integration* let someone re-roll it.

(Two corrections to common lore, since I checked: secp256k1 ECVRF is *not* in RFC 9381 — the RFC standardizes P-256, edwards25519, and RSA-FDH; Chainlink's secp256k1 VRF predates and sits outside it. And the famous "EOSBet hack" was a fake-transfer notification bug, not an RNG break — the RNG hack you're thinking of is EOSPlay.)

## The one footgun under all of them

Here's the thing that took me four repos to really see. The unifying failure isn't weak entropy — it's a **consumer that lets the caller observe the outcome and then abort the transaction.** Abort is a costless re-roll, and a costless re-roll turns any distribution, however perfect, into "keep only the wins."

Look at the headline rule on every platform and it's the same patch:

- **Sui** and **Aptos** *compiler-enforce* that a function reading randomness must be a private `entry` function — so no other contract can wrap it, read the draw, and revert on a loss. (Aptos even names the residual hole: undergasing, aborting an expensive branch by starving it of gas.)
- **Ethereum RANDAO's** last-revealer is literally this move at the protocol layer — withhold a block (abort the reveal) to choose between outcomes.
- **Chainlink's** "no re-request, fix your inputs after requesting" is the same principle at the integration layer.
- And my **Chess960** reveal-deadline-forfeit is the same principle for two players: you committed before you saw the draw, and you can't quietly abort by not revealing.

State it once and it covers all of them: **the party who can abort the transaction must be committed to acting before the random value is revealed.** Commit-then-reveal across two transactions; a private `entry` function; fixed inputs after the request; a forfeit if you stall. Pick your randomness source by its trust root and its cost — but the bug that will actually bite you lives at the boundary where someone gets to look before they leap.

The chess draw is real and tested — two-party commit-reveal wired into the wager, with the forfeit — in [the repo](https://github.com/0xSoftBoi/chess). The Sui side, where the language hands you the `entry` rule for free, is [the companion piece](/blog/verifiable-isnt-trustless-onchain-randomness/).
