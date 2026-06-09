---
layout: post
title: "The bridge that paid twice"
date: 2026-06-09
tags: [solidity, bridges, security, reorg]
image: /assets/og/the-bridge-that-paid-twice.png
excerpt: "A token bridge whose relayer calls release() on every Deposit event. That sounds fine until you remember event delivery isn't exactly-once — and a reorg, a reconnect, or a restart makes the destination pay the same lock again. Here's the fix that makes a payout happen exactly once."
---

Here's a bridge relayer, more or less as I found it:

```ts
sepoliaBridge.on("Deposit", async (depositor, amount) => {
  await mumbaiBridge.release(depositor, amount);
});
```

Lock tokens on Sepolia, the bot sees the `Deposit` event, releases the same amount on Mumbai. And the destination `release` is exactly what you'd expect:

```solidity
function release(address _to, uint256 _amount) public onlyOwner {
    IERC20(token).transfer(_to, _amount);
}
```

It works in the demo. It is also a contract that will pay you twice.

## Events are not exactly-once

The bug is the unspoken assumption that each `Deposit` fires once and is handled once. Neither is guaranteed:

- The relayer **restarts** and replays recent blocks — same event again.
- The websocket **reconnects** and re-emits buffered logs — same event again.
- The source chain **reorgs**: the block with your `Deposit` gets re-mined, the subscription re-delivers it — same event again. (And in a reorg the *original* deposit may no longer exist at all.)

Each re-delivery calls `release` again, and the destination has **no memory** of what it already paid — no nonce, no record, nothing. So it transfers again. And again. The reserve drains one duplicate at a time, and there's not even a `Released` event to notice it happening. This isn't exotic; "the off-chain component double-submitted" is one of the most common ways real bridges have lost money.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="b-t">
<title id="b-t">An event re-delivered double-pays; an idempotent release pays once</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Original: release() on every event</text>
<rect class="c-box" x="20" y="46" width="210" height="40" rx="6"/>
<text class="c-label-sm" x="125" y="70" text-anchor="middle">Deposit event (re-delivered ×2)</text>
<line class="c-arrow" x1="232" y1="66" x2="274" y2="66"/>
<rect class="c-box" x="276" y="46" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="351" y="70" text-anchor="middle">release(to, amount)</text>
<line class="c-arrow" x1="428" y1="66" x2="470" y2="66"/>
<rect class="c-box" x="472" y="46" width="188" height="40" rx="6"/>
<text class="c-label-sm" x="566" y="70" text-anchor="middle">paid TWICE → drain</text>
<line class="c-grid" x1="20" y1="108" x2="660" y2="108"/>
<text class="c-title" x="20" y="136">Hardened: a transferId paid at most once</text>
<rect class="c-box" x="20" y="156" width="210" height="46" rx="6"/>
<text class="c-label-sm" x="125" y="176" text-anchor="middle">Locked(nonce) on source</text>
<text class="c-label-sm" x="125" y="192" text-anchor="middle">+ validator signs transferId</text>
<line class="c-arrow" x1="232" y1="179" x2="274" y2="179"/>
<rect class="c-box-accent c-fill-soft" x="276" y="156" width="200" height="46" rx="8"/>
<text class="c-label-sm" x="376" y="176" text-anchor="middle">release: check sig +</text>
<text class="c-label-sm" x="376" y="192" text-anchor="middle">processed[transferId]?</text>
<line class="c-arrow" x1="478" y1="179" x2="520" y2="179"/>
<rect class="c-box" x="522" y="156" width="138" height="46" rx="6"/>
<text class="c-label-sm" x="591" y="176" text-anchor="middle">1st: pay once</text>
<text class="c-label-sm" x="591" y="192" text-anchor="middle">2nd: AlreadyReleased</text>
<text class="c-label-sm" x="340" y="232" text-anchor="middle">The transferId binds the source lock + both chain ids + this contract — unique, unforgeable, paid once.</text>
<text class="c-label-sm" x="340" y="256" text-anchor="middle">And the relayer waits for source finality, so a reorg can't make it sign for a lock that vanished.</text>
</svg>
<figcaption>Idempotency keyed on a per-lock <code>transferId</code> turns "release on every event" into "release this lock at most once" — the re-delivered event reverts instead of paying again.</figcaption>
</figure>

## Making a payout happen once

The fix is to give every payout an identity and remember it:

- Each destination release is keyed by a **`transferId`** derived from the *unique* source lock — `srcChainId, srcBridge, srcNonce, to, amount` — plus the destination chain id and this contract's address. `mapping(bytes32 => bool) processed` means the second `release` for the same id reverts with `AlreadyReleased`. Re-deliver the event all you like; it pays once.
- The release carries a **validator signature** over that `transferId`, so authority to pay is explicit and verifiable, decoupled from the contract owner — and because the chain ids and both bridge addresses are baked into the id, a signature can't be replayed onto another deployment.
- `SafeERC20`, a `Released` event to reconcile against, `Pausable`, and a relayer that **waits for source finality** before signing. (Idempotency stops paying the same lock *twice*; finality stops paying for a lock a reorg *erased* — two different failures.)

[Six Foundry tests](https://github.com/0xSoftBoi/cross-evm-bridge), and the one that matters most just re-calls `release` with the same signature and asserts the second call reverts and the balance moved once.

## What it still isn't

I want to be precise about what this does and doesn't buy, because "bridge" oversells. The hardening removes the *mechanical* ways to lose money — double-pays, unsafe transfers, unauthorized releases. It does **not** remove the *trust*: this is still a **custodial** bridge, and a compromised validator can sign a payout for a lock that never happened. The trust-minimized version replaces the signature with a **light-client or Merkle proof** of the source `Locked` event, so the destination *verifies* the lock instead of *trusting* a signer — that's the real frontier, and it's the line between this and a bridge you'd actually trust with size.

It's the same shape as the [other bridge I annotated](https://github.com/0xSoftBoi/lock-mint-bridge-lab): the cryptography and the Solidity are rarely where these break. The break is an off-chain assumption — here, "events happen once" — that the chain never promised to keep.

The audit and the fix are at [github.com/0xSoftBoi/cross-evm-bridge](https://github.com/0xSoftBoi/cross-evm-bridge).
