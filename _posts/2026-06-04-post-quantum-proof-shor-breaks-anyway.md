---
layout: post
title: "The post-quantum proof that Shor breaks anyway"
date: 2026-06-04
tags: [post-quantum, zk, cryptography, security, bridges]
image: /assets/og/post-quantum-proof-shor-breaks-anyway.png
excerpt: "A bridge verifies a lattice signature inside a zero-knowledge proof and calls itself post-quantum. The signature is post-quantum. The proof isn't — and a quantum adversary attacks the proof, not the signature. Here's where the claim snaps."
---

A pattern I keep seeing in "post-quantum" bridge designs: the team picks a real post-quantum signature — ML-DSA-65, the [FIPS-204](https://csrc.nist.gov/pubs/fips/204/final) lattice scheme — has an operator sign each cross-chain message with it, and then, because verifying a lattice signature directly on Ethereum costs millions of gas, wraps that verification inside a succinct zero-knowledge proof that verifies for ~270k gas. Ship it. *Post-quantum bridge.*

The signature is post-quantum. The proof is not. And a quantum adversary doesn't attack the signature — it attacks the proof.

## Where the claim snaps

The reasoning goes: the message is signed with a PQ scheme → the signature is checked inside a SNARK → therefore the whole thing is PQ. Each arrow looks fine. The error is that the SNARK's *own soundness* — the property that you can't produce a valid proof of a false statement — rests on a separate, classical assumption that has nothing to do with the signature inside it.

Groth16, the most common on-chain SNARK, verifies through elliptic-curve pairings, almost always over **BN254** (alt_bn128 — the curve with EVM precompiles at `0x06`/`0x07`/`0x08`). The soundness of a BN254 proof reduces to the hardness of the discrete logarithm problem on that curve. And the discrete log problem — including its elliptic-curve form — is precisely what **Shor's algorithm** solves in polynomial time on a cryptographically-relevant quantum computer.

So here is the actual attack. A quantum adversary never touches the ML-DSA signature. It uses Shor to break BN254, and then forges a SNARK proof for a statement that is *false* — "I verified a valid operator signature over this withdrawal" — when no such signature exists. The proof verifies on-chain. The bridge mints. The post-quantum signature scheme sat there, perfectly secure, attesting to nothing, because the thing wrapping it was forgeable. **The inner statement is irrelevant if the outer attestation can be forged.**

<figure class="chart">
<svg viewBox="0 0 680 290" role="img" aria-labelledby="pq-t">
<title id="pq-t">A post-quantum signature wrapped in a classical BN254 proof; a quantum adversary attacks the outer proof, not the inner signature</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="26">Where the “post-quantum” claim snaps</text>
<rect class="c-box-accent c-fill-soft" x="170" y="58" width="430" height="150" rx="8"/>
<text class="c-label" x="186" y="80">Groth16 proof over BN254</text>
<text class="c-label-sm" x="186" y="98">soundness = elliptic-curve discrete log · classical</text>
<rect class="c-box" x="250" y="116" width="270" height="74" rx="6"/>
<text class="c-val" x="385" y="146" text-anchor="middle">ML-DSA-65 signature</text>
<text class="c-label-sm" x="385" y="166" text-anchor="middle">post-quantum · secure</text>
<line class="c-arrow" x1="34" y1="120" x2="166" y2="120"/>
<text class="c-val" x="34" y="106">Shor</text>
<text class="c-label-sm" x="34" y="140">breaks BN254,</text>
<text class="c-label-sm" x="34" y="156">forges the proof</text>
<text class="c-label-sm" x="385" y="234" text-anchor="middle">The adversary never touches the inner signature — it forges the outer attestation,</text>
<text class="c-label-sm" x="385" y="250" text-anchor="middle">and the secure post-quantum signature ends up attesting to nothing.</text>
</svg>
<figcaption>The signature is post-quantum; the proof that wraps it is not. Shor breaks the outer BN254 proof — the boundary that actually touches the chain.</figcaption>
</figure>

## "But SP1 uses STARKs, and STARKs are post-quantum"

This is the strongest objection and it's half right. A zkVM like SP1 proves execution with a **STARK**, whose security comes from FRI — a hash-based, collision-resistance argument with no discrete-log assumption anywhere. STARKs are, as far as anyone knows, post-quantum. If you verified the STARK directly, the objection would hold.

But you don't verify a STARK on Ethereum. A FRI proof is tens to hundreds of kilobytes and costs millions of gas to check. So the toolchain does one more step: it **recursively wraps the STARK in a Groth16 or PLONK proof over BN254**, because *that* is the thing that verifies in a couple hundred thousand gas. The cheap proof on-chain is the broken one. The post-quantum part gets compiled away at the exact boundary that touches the chain — the on-chain verifier sees BN254, and BN254 is Shor-breakable. A "270k-gas PQ verification" is almost a tell: nothing genuinely post-quantum verifies that cheaply on the EVM today.

## What is actually post-quantum on-chain

Three honest options, all expensive in their own way:

- **Verify the STARK/FRI directly.** Genuinely PQ, genuinely millions of gas. Defensible on an L2 or a chain you control; rough on L1 mainnet.
- **Verify the lattice signature directly** — ML-DSA-65 in Solidity/Yul. Heavy (the signature alone is ~3.3 KB), but no classical assumption in the trust path.
- **Add a native precompile** on a chain you control, so the heavy verification runs at the protocol layer instead of in EVM bytecode.

For [the bridge I built](/blog/auditing-my-own-bridge/), the home chain is a DAG L1 I control, so I put a **native ML-DSA-65 precompile** on it and verify the operator's signature directly — no SNARK in the trust path at all. EVM destination chains, where on-chain lattice verification is prohibitive, fall back to ECDSA and inherit PQ integrity transitively through the home chain's consensus rather than pretending to check it locally. And the optimistic ZK path is **labeled non-post-quantum**, because it verifies a BN254 proof and I'm not going to call that something it isn't.

## Why I'd rather under-claim

A bridge with no post-quantum claim is just a bridge; a reviewer evaluates it on its merits. A bridge with a *false* post-quantum claim is worse, because the claim is plausible enough that a reviewer — or an auditor, or a user — will believe it and stop checking. The 270k-gas verify *looks* like diligence. It reads as "they thought about quantum."

If you're going to say post-quantum, the rule is simple: the thing that's expensive to verify on-chain has to be the thing you actually verify. The moment you wrap it in something cheap to make the gas number look good, check what curve that cheap thing is standing on — because that curve, not your lattice signature, is what a quantum adversary will come for.
