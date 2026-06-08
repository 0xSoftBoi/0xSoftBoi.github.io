---
layout: post
title: "Auditing my own bridge: from “mints money from nothing” to all-criticals-closed"
date: 2026-06-07
tags: [security, bridges, solidity]
image: /assets/og/auditing-my-own-bridge.png
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

I made the verifier pluggable. On the home chain — a DAG L1 I control — it calls a native **ML-DSA-65 (FIPS 204) precompile**, so the check is genuinely post-quantum. On EVM destinations, where on-chain lattice verification costs 5–12M gas, it falls back to ECDSA and inherits PQ integrity transitively through consensus. (The tempting shortcut — an SP1→Groth16 proof — is [*not* post-quantum: the BN254 wrapper is broken by Shor](/blog/post-quantum-proof-shor-breaks-anyway/). A 270k-gas "PQ verify" that isn't PQ is worse than no claim.)

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="br-t">
<title id="br-t">The fix: an attestation gate that binds every value-moving call to an operator signature</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
<marker id="c-arrowhead-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker>
</defs>
<text class="c-title" x="20" y="26">One invariant, one gate</text>
<text class="c-label-sm" x="20" y="46">supply minted on destination  ≤  collateral locked on source</text>
<rect class="c-box" x="20" y="92" width="120" height="56" rx="6"/>
<text class="c-val" x="80" y="116" text-anchor="middle">relayer</text>
<text class="c-label-sm" x="80" y="134" text-anchor="middle">untrusted</text>
<line class="c-arrow" x1="142" y1="120" x2="246" y2="120"/>
<rect class="c-box-accent c-fill-soft" x="248" y="80" width="200" height="80" rx="8"/>
<text class="c-val" x="348" y="106" text-anchor="middle">attestation gate</text>
<text class="c-label-sm" x="348" y="126" text-anchor="middle">verify(digest, signature)</text>
<text class="c-label-sm" x="348" y="142" text-anchor="middle">binds commitId · recipient ·</text>
<text class="c-label-sm" x="348" y="156" text-anchor="middle">amount · chainId · address</text>
<line class="c-arrow" x1="450" y1="120" x2="554" y2="120"/>
<rect class="c-box" x="556" y="92" width="110" height="56" rx="6"/>
<text class="c-val" x="611" y="116" text-anchor="middle">mint · unlock</text>
<text class="c-label-sm" x="611" y="134" text-anchor="middle">finalize</text>
<path class="c-arrow-muted" d="M80,150 C80,212 611,212 611,152" stroke-dasharray="5 4"/>
<text class="c-label-sm" x="348" y="206" text-anchor="middle">the old path — relayer trusted directly, no on-chain proof — is removed</text>
<text class="c-label-sm" x="348" y="252" text-anchor="middle">Without the gate the invariant breaks in one call: mint(arbitraryCommitId, attacker, 1e30).</text>
<text class="c-label-sm" x="348" y="268" text-anchor="middle">The digest binds the parameters an operator signed, so a forged request no longer verifies.</text>
</svg>
<figcaption>Every critical reduced to one root cause — no on-chain binding between lock state, mint state, and a verified operator. The gate supplies it.</figcaption>
</figure>

## What the invariants taught me

The discipline that mattered most was **revert-fails**: every fix has a test that goes green when the fix lands *and red again when you revert the fix*. A passing test proves nothing if it never had the chance to fail.

By the end: all four criticals closed, the supply and double-spend invariants green over 400 runs × depth 80, each backed by a revert-fails proof. The adversarial pass surfaced a few more — a token admin that was a parallel unconstrained minter, an unbounded release path — all closed the same way.

Two honest caveats I kept throughout. The cross-domain "minted XOR refunded" guarantee is now an *operator-coordination* property the gates make *enforceable* — not eliminated. And no internal audit, however thorough, clears funds-holding code on its own; that's what independent audits and bug bounties are for.

The invariant that went red in a second is green now over 400 runs. That tells me the gate holds. It tells me nothing about whether the bug I should fear lives behind an invariant I never thought to write — which is the one I'd hire someone else to find.

*More on the architecture in [Suwappu](https://suwappu.bot).*
