---
layout: post
title: "The post-quantum proof that Shor breaks anyway"
date: 2026-06-04
tags: [post-quantum, zk, cryptography]
excerpt: "A bridge verifies a lattice signature inside a zero-knowledge proof and calls itself post-quantum. The signature is post-quantum. The proof isn't — and a quantum adversary attacks the proof, not the signature. Here's where the claim snaps."
---

A pattern I keep seeing in "post-quantum" bridge designs: the team picks a real post-quantum signature — ML-DSA-65, the FIPS-204 lattice scheme — has an operator sign each cross-chain message with it, and then, because verifying a lattice signature directly on Ethereum costs millions of gas, wraps that verification inside a succinct zero-knowledge proof that verifies for ~270k gas. Ship it. *Post-quantum bridge.*

The signature is post-quantum. The proof is not. And a quantum adversary doesn't attack the signature — it attacks the proof.

## Where the claim snaps

The reasoning goes: the message is signed with a PQ scheme → the signature is checked inside a SNARK → therefore the whole thing is PQ. Each arrow looks fine. The error is that the SNARK's *own soundness* — the property that you can't produce a valid proof of a false statement — rests on a separate, classical assumption that has nothing to do with the signature inside it.

Groth16, the most common on-chain SNARK, verifies through elliptic-curve pairings, almost always over **BN254** (alt_bn128 — the curve with EVM precompiles at `0x06`/`0x07`/`0x08`). The soundness of a BN254 proof reduces to the hardness of the discrete logarithm problem on that curve. And the discrete log problem — including its elliptic-curve form — is precisely what **Shor's algorithm** solves in polynomial time on a cryptographically-relevant quantum computer.

So here is the actual attack. A quantum adversary never touches the ML-DSA signature. It uses Shor to break BN254, and then forges a SNARK proof for a statement that is *false* — "I verified a valid operator signature over this withdrawal" — when no such signature exists. The proof verifies on-chain. The bridge mints. The post-quantum signature scheme sat there, perfectly secure, attesting to nothing, because the thing wrapping it was forgeable. **The inner statement is irrelevant if the outer attestation can be forged.**

## "But SP1 uses STARKs, and STARKs are post-quantum"

This is the strongest objection and it's half right. A zkVM like SP1 proves execution with a **STARK**, whose security comes from FRI — a hash-based, collision-resistance argument with no discrete-log assumption anywhere. STARKs are, as far as anyone knows, post-quantum. If you verified the STARK directly, the objection would hold.

But you don't verify a STARK on Ethereum. A FRI proof is tens to hundreds of kilobytes and costs millions of gas to check. So the toolchain does one more step: it **recursively wraps the STARK in a Groth16 or PLONK proof over BN254**, because *that* is the thing that verifies in a couple hundred thousand gas. The cheap proof on-chain is the broken one. The post-quantum part gets compiled away at the exact boundary that touches the chain — the on-chain verifier sees BN254, and BN254 is Shor-breakable. A "270k-gas PQ verification" is almost a tell: nothing genuinely post-quantum verifies that cheaply on the EVM today.

## What is actually post-quantum on-chain

Three honest options, all expensive in their own way:

- **Verify the STARK/FRI directly.** Genuinely PQ, genuinely millions of gas. Defensible on an L2 or a chain you control; rough on L1 mainnet.
- **Verify the lattice signature directly** — ML-DSA-65 in Solidity/Yul. Heavy (the signature alone is ~3.3 KB), but no classical assumption in the trust path.
- **Add a native precompile** on a chain you control, so the heavy verification runs at the protocol layer instead of in EVM bytecode.

For the bridge I built, the home chain is a DAG L1 I control, so I put a **native ML-DSA-65 precompile** on it and verify the operator's signature directly — no SNARK in the trust path at all. EVM destination chains, where on-chain lattice verification is prohibitive, fall back to ECDSA and inherit PQ integrity transitively through the home chain's consensus rather than pretending to check it locally. And the optimistic ZK path is **labeled non-post-quantum**, because it verifies a BN254 proof and I'm not going to call that something it isn't.

## Why I'd rather under-claim

A bridge with no post-quantum claim is just a bridge; a reviewer evaluates it on its merits. A bridge with a *false* post-quantum claim is worse, because the claim is plausible enough that a reviewer — or an auditor, or a user — will believe it and stop checking. The 270k-gas verify *looks* like diligence. It reads as "they thought about quantum."

If you're going to say post-quantum, the rule is simple: the thing that's expensive to verify on-chain has to be the thing you actually verify. The moment you wrap it in something cheap to make the gas number look good, check what curve that cheap thing is standing on — because that curve, not your lattice signature, is what a quantum adversary will come for.
