---
layout: post
title: "An invariant is not an end-to-end proof"
date: 2026-06-07
series: "Bridge & DeFi security"
tags: [security, bridges, solidity, invariants]
image: /assets/og/auditing-my-own-bridge.png
excerpt: "Supply≤collateral is the right local invariant for a lock-and-mint bridge. The important lesson was learning what that invariant does not prove: an attestation gate can make operator coordination enforceable on-chain without independently proving a remote-chain event."
---

A lock-and-mint bridge reduces to one accounting sentence:

> **wrapped supply on the destination must never exceed collateral locked on the source.**

I wrote that sentence as a Foundry stateful invariant before writing the fix:

```solidity
function invariant_supply_le_collateral() public view {
    assertLe(wrapped.totalSupply(), vault.totalLocked(asset));
}
```

With the relayer modeled as an adversary, the invariant went red immediately. A forged destination mint could create wrapped supply without a corresponding source lock.

That result was useful. The more important lesson came later: a strong local invariant does not turn the bridge into a trustless proof system. It tells you exactly which **local property** the contracts enforce—and forces you to name the assumption underneath it.

* TOC
{:toc}

## The invariant catches the economic failure

A bridge can have thousands of lines of routing, finality, refund, and message-handling code. The economic failure is simpler: unbacked supply exists.

The public teaching lab drives the source vault and destination adapter with both honest and adversarial calls. Two properties matter most:

1. `wrapped.totalSupply() <= vault.totalLocked(asset)`;
2. the adversarial handler never succeeds in minting value.

The campaign is configured for **512 runs × depth 100**. The point of that number is not to claim exhaustive verification. It is to repeatedly explore sequences of state transitions while checking the accounting property after every sequence.

## The authorization gate closes a local path

Every value-moving operation—mint, unlock, refund—passes through a verifier over a digest that binds the operation to its context: domain, chain ID, contract address, commit ID, recipient, amount, and source-chain ID.

Conceptually:

```solidity
bytes32 digest = keccak256(abi.encode(
    DOMAIN,
    block.chainid,
    address(this),
    commitId,
    recipient,
    amount,
    sourceChainId
));
require(verifier.verify(digest, attestation), "unauthorized");
```

Those fields close distinct replay and substitution surfaces. A commit is also forced into one terminal source-side outcome so the same lock cannot both back a destination mint and later be refunded.

That is real security value. But the verifier proves a narrower proposition than people often attach to it.

## A signature proves authorization, not truth

If an operator signs “this source lock happened,” the destination contract can verify **who authorized the statement** and **which exact statement they authorized**.

It does not independently observe the source chain.

A malicious or compromised quorum can still authorize a false statement. The local accounting invariant can remain internally consistent relative to the signed state while the external fact is wrong.

That makes the attestation gate an **operator-coordination property made enforceable on-chain**. It is not a light client, validity proof, or independent consensus proof of the remote event.

This is the distinction I want the article to preserve:

> **Cryptographic authorization can prove who approved a statement without proving the statement was true.**

## The mutation test is the strongest part of the evidence

A passing invariant can be accidentally irrelevant. The useful check is whether removing the intended defense makes the property fail again.

The lab includes a gate-off mutation. With the authorization gate disabled, a forged mint breaks the supply invariant in one call.

That is a much better causal story than “the tests are green after my patch.” It shows that the tested defense is actually on the path preventing the tested failure.

This is the same reason I care about real-hardware CI elsewhere: a test is most informative when it has a credible way to prove the implementation wrong.

## Historical exploit names are controls, not borrowed credibility

The repository includes minimal Ronin-, Wormhole-, and Nomad-shaped tests to exercise broad failure categories: unauthorized operators, an unverified mint path, and default/zero authorization.

They are **not** fork-level exploit reenactments. They do not reproduce every contract, validator set, chain state, or historical precondition.

That boundary matters. Naming a famous exploit should not import the evidentiary weight of the historical incident into a small teaching model.

## Post-quantum signatures do not erase the bridge trust model

The larger bridge work experiments with multiple verifier backends, including post-quantum signature schemes on infrastructure designed to support them.

The safe claim is mechanical: if a verifier implements a specific signature scheme correctly, the contract can enforce that authorization rule under that scheme's assumptions.

The unsafe leap is: “the bridge is therefore post-quantum secure” or “the destination inherits post-quantum truth from consensus.” End-to-end bridge security still includes key management, validator/operator assumptions, replay domains, remote-state provenance, implementation correctness, and every cryptographic component actually used on the path.

A quantum-resistant signature primitive solves one component. It does not erase the system model around it.

## The strongest counterargument

If the operator set is intentionally the oracle for remote events, then saying the gate enforces operator coordination may sound like a distinction without a difference: authorization *is* the protocol's definition of truth.

That can be a valid system design. The distinction still matters for users and auditors because it tells them what compromise breaks safety.

- In an operator-attested bridge, compromise of the threshold authority can create false remote facts.
- In a light-client design, the relevant failure shifts toward consensus/finality verification and implementation assumptions.
- In a proof-based design, the statement proved and the provenance of its public inputs become the boundary.

Different systems can expose the same user interface while failing for completely different reasons.

## What the invariant actually earns

The evidence supports a narrow but valuable statement:

- under the lab's state machine and verifier assumptions, the authorization gate prevents the forged-mint path exercised by the adversarial handler;
- supply≤collateral remains green across the configured invariant campaign;
- disabling the gate makes the tested accounting failure reappear.

It does **not** prove that every relevant bridge invariant has been written, that the operator set is honest, that the remote event is independently verified, or that production funds-holding code is audited.

That is why I now prefer a page that names one invariant and one assumption over a diagram that simply says “secure bridge.”

### Primary evidence

- [lock-mint-bridge-lab](https://github.com/0xSoftBoi/lock-mint-bridge-lab) — minimal runnable invariant and mutation-testing artifact.
- [SECURITY.md](https://github.com/0xSoftBoi/lock-mint-bridge-lab/blob/main/SECURITY.md) — explicit scope and non-goals.

**Evidence boundary:** this is an unaudited teaching artifact. The historical exploit-shaped tests are minimal controls, not faithful exploit reproductions. The local invariant is strong evidence about the modeled accounting property, not an end-to-end proof of remote-chain truth.
