---
layout: post
title: "The other side of the wall: FHE where ZK stops"
date: 2026-06-08
tags: [fhe, zama, cryptography, chess, mev]
image: /assets/og/the-other-side-of-the-wall.png
excerpt: "My ZK fog-of-war chess hit a wall: it could prove a move legal against your own board, but not the things that depend on the opponent's hidden pieces — captures, blocked sliders, check. Those are joint predicates over two secret boards. So I crossed the wall with FHE: real homomorphic computation that decides 'is my king in check?' over an encrypted enemy board in 7.6 seconds — and an honest line between what that proves and what it doesn't."
---

When I [built ZK dark chess](/blog/zk-dark-chess/) I was careful about where it stopped. It proves your move is legal against **your own** committed board — right piece, legal geometry, clear path over *your* pieces — and hides the rest. But fog-of-war chess has three things that don't fit in that box, because they depend on the **opponent's** hidden pieces:

- **capturing a hidden piece** — is the square I'm moving onto occupied?
- **a blocked slider** — is there an enemy piece on my rook's path?
- **check** — does a hidden enemy piece attack my king?

No proof about *your* board can answer these. They're **joint predicates over two secret boards**, and that's a real wall — the place every honest ZK fog-of-war project (mine included) stops. This post is about crossing it.

## Why FHE is the tool

A ZK proof convinces someone of a statement about a witness *you hold*. But here neither player holds the whole truth: whether your king is in check is a function of *my* hidden pieces and *your* hidden king together. You can't prove what you can't see.

Fully homomorphic encryption flips the move. Instead of proving a statement about plaintext you have, you **compute on ciphertext you don't**. Encrypt the opponent's board; evaluate "is this square attacked?" homomorphically; decrypt only the one resulting bit. The board stays encrypted the whole way through — the computation itself never sees a plaintext piece.

So I built it, for real, with Zama's [`tfhe-rs`](https://github.com/zama-ai/tfhe-rs).

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="w-t">
<title id="w-t">ZK decides own-board legality; FHE decides joint predicates over the encrypted opponent board</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Two halves of fog of war</text>
<rect class="c-box" x="20" y="48" width="300" height="86" rx="6"/>
<text class="c-val" x="170" y="74" text-anchor="middle">ZK — your own board</text>
<text class="c-label-sm" x="170" y="96" text-anchor="middle">prove your move is legal vs your</text>
<text class="c-label-sm" x="170" y="112" text-anchor="middle">committed pieces · hides the rest</text>
<rect class="c-box-accent c-fill-soft" x="360" y="48" width="300" height="86" rx="8"/>
<text class="c-val" x="510" y="74" text-anchor="middle">FHE — the opponent's board</text>
<text class="c-label-sm" x="510" y="96" text-anchor="middle">compute capture / block / check on</text>
<text class="c-label-sm" x="510" y="112" text-anchor="middle">ciphertext · reveal only the bit</text>
<text class="c-label-sm" x="340" y="128" text-anchor="middle" style="font-weight:600">the wall →</text>
<line class="c-grid" x1="20" y1="158" x2="660" y2="158"/>
<text class="c-label-sm" x="20" y="184">Measured over an ENCRYPTED board (Apple Silicon laptop):</text>
<rect class="c-box" x="20" y="198" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="120" y="223" text-anchor="middle">capture: ~35 ms</text>
<rect class="c-box" x="232" y="198" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="332" y="223" text-anchor="middle">blocked slider: ~135 ms</text>
<rect class="c-box-accent c-fill-soft" x="444" y="198" width="216" height="40" rx="8"/>
<text class="c-label-sm" x="552" y="223" text-anchor="middle">in check?: ~7.6 s (one bit)</text>
<text class="c-label-sm" x="340" y="266" text-anchor="middle">One key locally = the COMPUTATION is referee-free. Distributing the key = the TRUST.</text>
</svg>
<figcaption>ZK covers legality against your own board; FHE covers the predicates that touch the opponent's hidden pieces. The check predicate — the one ZK can't decide — runs on an encrypted board in 7.6 seconds and leaks a single bit.</figcaption>
</figure>

## A real check, over an encrypted board

`in_check` is the interesting one. Over the opponent's encrypted 64-cell board it walks the eight rays from the king: at each step it OR-accumulates "an enemy rook/queen (or bishop/queen) sits here," gated by a running encrypted "the ray is still clear" flag, then folds in knight, pawn, and king-adjacency offsets — all reduced to a single encrypted boolean. (Your *own* pieces block rays too, but you know your board in the clear, so those truncate the walk before any FHE happens.) The contract decrypts exactly that one bit.

The tests are the proof it's real: each predicate is computed on **encrypted** boards and asserted equal to a plaintext oracle on known positions — an open rook on the file is check; the same rook behind an enemy pawn is not; a knight on the right square is check; a quiet position isn't. It runs:

```
1. occupancy(e8)   = true   (captured piece = rook)   [35 ms]
2. blocked(a1->a4) = true   (pawn on a3 blocks)        [135 ms]
3. in_check(e1)    = true   (open enemy rook)          [7.6 s]
```

Each line leaks exactly one bit — or, for a capture, the single square you captured on, which is precisely what fog of war is supposed to reveal.

## The line I won't cross: computation vs trust

Here's the part it would be easy to oversell, so I'll be blunt. My demo encrypts **both** boards under one key. Whoever holds that key can decrypt everything — which is *exactly the referee I set out to remove*. So the local program proves one thing and not another:

- **The computation is referee-free.** The predicate runs on ciphertext and only the answer bit is ever revealed. That's real, and it's what `cargo test` checks.
- **The trust is not.** Removing the single key-holder needs a **threshold KMS** — a committee where no member can decrypt alone. That's [Zama's fhEVM](https://docs.zama.ai/fhevm): the board lives on-chain as ciphertext handles, a coprocessor runs the FHE, and the committee reveals only the ACL-permitted bit. I wrote that contract as a design (`FogChessFHE.sol`) — it needs the Zama network, so it's *designed, not deployed*.

> **Update.** I took that contract off the sketchpad. `FogChessFHE.sol` now compiles against the real fhEVM SDK (`@fhevm/solidity` 0.11.1) and *runs* in its mock coprocessor: a hardhat test commits an encrypted 64-cell board on-chain, runs `occupancy` and the full `inCheck` ray-walk on the coprocessor, and the caller decrypts exactly one ACL-gated bit — open rook on the file is check, blocked rook is not, the same positions the Rust tests use. So the on-chain *path* is real now, not pseudocode. What's still designed-and-not-deployed is precisely the trust: the mock decrypts with one key, where a live deployment uses the threshold committee. A Sepolia run against the real Gateway/KMS is the one remaining step — and it's the one that matters most.

The maths runs today; the trust distribution is drawn, not built. Conflating those two is how "trustless" gets oversold, and I'd rather show you the seam.

## The honest cost

FHE isn't free: 7.6 seconds for one check, and an estimated **eight minutes** if you also hide the king's square (you'd multiplex the predicate over all 64 candidates). That's correspondence chess, not blitz — and on fhEVM it's the coprocessor's latency, not your laptop's. But "minutes per move, leaking one bit" is a real answer to a problem that didn't have a referee-free one before.

## The whole arc

Put the three pieces together and you can see the shape of a real kriegspiel protocol: **ZK** proves each player's move legal against their own hidden board; **FHE** decides the predicates that couple the two boards; a **threshold KMS** holds the key so no one is the referee. Each tool does precisely what it claims and not an inch more — the same lesson as [randomness](/blog/the-on-chain-randomness-landscape/), [proof binding](/blog/what-a-zk-proof-proves/), and [CoW settlement](/blog/how-cow-protocol-settles/): the cryptography is rarely the hard part. Composing it honestly, and marking exactly where the real ends and the designed begins, is.

The running predicates, the tests, and the fhEVM sketch are at [fhe-dark-chess](https://github.com/0xSoftBoi/fhe-dark-chess).
