---
layout: post
title: "Auditing my own bridge: from “mints money from nothing” to all-criticals-closed"
date: 2026-06-07
tags: [security, bridges, solidity]
excerpt: "A lock-and-mint bridge is one giant accounting invariant. Here's how I turned that invariant into a fuzz test that found every way the contracts could create unbacked supply — and the on-chain fix pattern that closed it."
---

A cross-chain lock-and-mint bridge is, underneath all the ceremony, **one accounting invariant**:

> wrapped tokens minted on the destination chain must never exceed the collateral locked on the source chain.

Break that, and the bridge prints money. So before writing a single fix, I wrote that invariant as a Foundry stateful fuzz test — deploying the source vault, the destination mint adapter, and the wrapped token *together*, with the relayer modeled as the adversary:

```solidity
function invariant_supply_le_collateral() public view {
    assertLe(wrapped.totalSupply(), vault.totalLocked(asset));
}
```

It went red in under a second. The fuzzer found a one-call counterexample: the relayer calling `mint(arbitraryCommitId, attacker, 1e30, ...)`. The contract had a declared `CommitIdMismatch` error — and never used it. The mint trusted the relayer completely.

## The bug class

Every critical reduced to the same root cause: **no on-chain binding between source-lock state, destination-mint state, and a verified operator.** Mint, unlock, and finalize all trusted a relayer set with no on-chain proof that the event they claimed had actually happened. That's the Ronin / Wormhole family — the most expensive bug class in the space.

A second invariant caught the cross-domain twin: a user could get their wrapped tokens minted *and* claim a refund of the original collateral, because the source vault's refund path had no idea the destination mint occurred.

## The fix pattern

The fix isn't "recompute the commitId" — a relayer can forge that too. It's an **attestation gate**: every value-moving call requires an authorized operator's signature over a digest that binds *all* the parameters plus `block.chainid` and the contract address:

```solidity
bytes32 digest = keccak256(abi.encode(
    DOMAIN, block.chainid, address(this),
    commitId, recipient, amount, sourceChainId
));
require(verifier.verify(digest, attestation), "unauthorized");
```

I made the verifier pluggable. On the home chain — a DAG L1 I control — it calls a native **ML-DSA-65 (FIPS 204) precompile**, so the check is genuinely post-quantum. On EVM destinations, where on-chain lattice verification costs 5–12M gas, it falls back to ECDSA and inherits PQ integrity transitively through consensus. (The tempting shortcut — an SP1→Groth16 proof — is *not* post-quantum: the BN254 wrapper is broken by Shor. A 270k-gas "PQ verify" that isn't PQ is worse than no claim.)

## What the invariants taught me

The discipline that mattered most was **revert-fails**: every fix has a test that goes green when the fix lands *and red again when you revert the fix*. A passing test proves nothing if it never had the chance to fail.

By the end: all four criticals closed, the supply and double-spend invariants green over 400 runs × depth 80, each backed by a revert-fails proof. The adversarial pass surfaced a few more — a token admin that was a parallel unconstrained minter, an unbounded release path — all closed the same way.

The honest caveat I kept throughout: the cross-domain "minted XOR refunded" guarantee is now an *operator-coordination* property the gates make enforceable — not eliminated. And no internal audit, however thorough, clears funds-holding code on its own. That's what independent audits and bug bounties are for.

*More on the architecture in [Suwappu](https://suwappu.bot).*
