---
layout: post
title: "How CoW Protocol settles a trade (and what my TWAP router got wrong)"
date: 2026-06-08
tags: [cow-protocol, defi, solidity, mev, intents]
image: /assets/og/how-cow-protocol-settles.png
excerpt: "My TWAP router for CoW Protocol compiled, passed its tests, and called two functions that don't exist on mainnet. Fixing it meant actually learning how CoW settles: intents not swaps, why you approve the relayer and not the settlement contract, and why a smart contract presigns its orders instead of settling them."
---

I had a TWAP order-router for CoW Protocol — split a big sell into time-sliced parts to cut price impact. It built, it had seventeen passing tests, and its core did this:

```solidity
ICowVaultRelayer(cowRelayer).deposit(token, owner, amount);
ICowSettler(cowSettler).settle(orderUid);
```

Neither of those functions exists on mainnet. The contract was integrating with a CoW Protocol I'd imagined — and the tests passed because they mocked the imaginary interface. That's the trap with on-chain integrations: "compiles + green against mocks" tells you nothing about whether you're calling a real protocol. So here's how CoW actually settles a trade, and the three things I had backwards.

## Orders are intents, not swaps

On an AMM you submit a transaction that *executes* a swap against a pool. On CoW you sign an **intent**: "sell at most X of token A for at least Y of token B before time T." You never execute anything. A signed order is just the [`GPv2Order.Data`](https://docs.cow.fi/cow-protocol/reference/contracts/core/settlement) struct — tokens, amounts, limits, `validTo`, kind — and its EIP-712 digest is the order's id.

Orders are collected over a short window into a **batch**. Then off-chain **solvers** compete for the right to settle the batch, each proposing a solution that routes the orders (matching them directly against each other where possible — "coincidence of wants" — and only hitting external AMMs for the remainder). The winning solver is the one that returns the most surplus to users, and only that solver calls:

```solidity
function settle(IERC20[] tokens, uint256[] clearingPrices,
                GPv2Trade.Data[] trades, GPv2Interaction.Data[][3] interactions)
    external nonReentrant onlySolver;
```

Two things in that signature mattered for my bug. It's **`onlySolver`** — an allow-listed, bonded set; a random contract cannot call `settle`. And it takes a **`clearingPrices`** array with one price per token: every order in the batch touching a given token settles at the *same* price. That uniform clearing price is the actual MEV-protection mechanism — within a batch, transaction ordering carries no value, so there's no sandwich to run. ([CoW settlement docs](https://docs.cow.fi/cow-protocol/reference/contracts/core/settlement))

So my `settle(orderUid)` was wrong twice over: the real `settle` has a completely different shape, and my contract isn't a solver and could never call it.

## You approve the relayer, not the settlement contract

Here's the subtle one. To trade on CoW you grant your ERC-20 allowance to the **`GPv2VaultRelayer`** (`0xC92E…0110`) — *not* to `GPv2Settlement`. Why a second contract? Because `settle` executes arbitrary `interactions` (calls into external liquidity). If your allowance pointed at the settlement contract, a malicious solver could craft an "interaction" that just calls `transferFrom` on your tokens. So CoW puts the allowance on a minimal relayer that **only `GPv2Settlement` may call**, and interactions *to the relayer are forbidden*. Funds can move only as part of a settlement that respects your signed order. ([vault relayer docs](https://docs.cow.fi/cow-protocol/reference/contracts/core/vault-relayer))

My router approved the relayer and then *reset the approval to zero in the same transaction*, right after a synchronous `deposit`. But settlement is **asynchronous** — a solver fills your order minutes later. Resetting the allowance immediately would leave nothing for the relayer to pull when the fill actually happens. The approval has to persist. CoW's own guidance is a single standing relayer approval.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="cow-t">
<title id="cow-t">How an order goes from intent to settlement on CoW Protocol</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Intent → batch → solver competition → settlement</text>
<rect class="c-box" x="20" y="50" width="172" height="56" rx="6"/>
<text class="c-val" x="106" y="72" text-anchor="middle">you authorize</text>
<text class="c-label-sm" x="106" y="90" text-anchor="middle">sign / presign an intent</text>
<line class="c-arrow" x1="194" y1="78" x2="250" y2="78"/>
<rect class="c-box" x="252" y="50" width="150" height="56" rx="6"/>
<text class="c-val" x="327" y="72" text-anchor="middle">batch</text>
<text class="c-label-sm" x="327" y="90" text-anchor="middle">orders collected</text>
<line class="c-arrow" x1="404" y1="78" x2="460" y2="78"/>
<rect class="c-box-accent c-fill-soft" x="462" y="48" width="198" height="60" rx="8"/>
<text class="c-val" x="561" y="72" text-anchor="middle">solvers compete</text>
<text class="c-label-sm" x="561" y="90" text-anchor="middle">most surplus wins</text>
<line class="c-arrow" x1="561" y1="110" x2="561" y2="150"/>
<rect class="c-box" x="372" y="152" width="288" height="48" rx="6"/>
<text class="c-label-sm" x="516" y="180" text-anchor="middle">winner settles batch — one uniform price per token</text>
<line class="c-arrow" x1="372" y1="176" x2="316" y2="176"/>
<rect class="c-box" x="20" y="152" width="296" height="48" rx="6"/>
<text class="c-label-sm" x="168" y="173" text-anchor="middle">relayer pulls your tokens (only now,</text>
<text class="c-label-sm" x="168" y="189" text-anchor="middle">only via this settlement)</text>
<line class="c-grid" x1="20" y1="224" x2="660" y2="224"/>
<text class="c-label-sm" x="20" y="250">You approve the RELAYER, never settlement — so a solver's arbitrary calls can't touch your funds.</text>
<text class="c-label-sm" x="20" y="272">No on-chain swap to front-run: within a batch, ordering carries no value.</text>
</svg>
<figcaption>The user authorizes an intent; solvers compete; the winner settles the whole batch at uniform clearing prices, and only then does the relayer pull funds — bounded to that settlement.</figcaption>
</figure>

## A contract presigns; it doesn't settle

If you can't call `settle`, how does a *contract* place an order? CoW's `GPv2Signing` mixin allows four schemes: an EOA's **EIP-712** or **EthSign** signature, a smart contract's **ERC-1271** `isValidSignature`, or **PreSign** — calling `setPreSignature(orderUid, true)` on-chain to flag an order as authorized. ([GPv2Signing source](https://github.com/cowprotocol/contracts/blob/main/src/contracts/mixins/GPv2Signing.sol))

That's the hook my executor needed. Each slice is its own order (its own `validTo` window); when a slice comes due, the contract **presigns** that slice's `orderUid` and leaves the rest to solvers. The whole fix was: approve the real relayer once, presign per slice, and *delete the `settle` call entirely*. The contract authorizes; the network settles. I also added a `revokePresignature` so cancelling can kill a presigned-but-unfilled slice — the honest caveat being that an in-flight slice stays fillable until its `validTo` otherwise.

## Two ways to TWAP, and when to roll your own

The above is a *self-hosted* TWAP: your own keeper presigns slices on a timer. CoW also ships an official TWAP, and it's worth knowing why it exists. It's not a bespoke contract — it's a **conditional order** on [ComposableCoW](https://docs.cow.fi/cow-protocol/reference/contracts/periphery/composable-cow). You register one order with a handler implementing `getTradeableOrder(...)`; CoW's **watchtower** calls that each block to get the part valid *now* and posts it, and the settlement contract calls the handler's `verify(...)` through ERC-1271 so a solver can only ever fill the part the handler currently authorizes. That's **validated discretization** — the chain itself enforces the schedule — plus on-chain cancellation and a keeper you don't have to run.

A naive splitter gives all of that up: it trusts your off-chain service to presign the right thing, and any already-presigned part stays fillable until it expires. So I built both — a fixed `CowTwapExecutor` *and* a faithful ComposableCoW `IConditionalOrder` TWAP handler (part scheduling, `span` windows, the watchtower's poll/abort signals, the validation guards) — to have the self-hosted path *and* the framework path side by side. The honest default is the framework; you roll your own only when you need logic the handler can't express, and even then the right move is a new handler, not an off-chain loop.

## The lesson

The contract compiled and its tests were green the whole time it was calling functions that don't exist. Mocks test your code against *your model* of the protocol; they can't tell you the model is fiction. The fix wasn't really Solidity — it was reading [the actual contracts](https://github.com/cowprotocol/contracts) until the shape of a real settlement (intent, relayer, presign, solver) replaced the shape I'd assumed. It's the same theme as [getting randomness right](/blog/the-on-chain-randomness-landscape/) and [binding a ZK proof](/blog/what-a-zk-proof-proves/): the hard part isn't the code you write, it's checking it against the system it actually has to live in.

The fix, the handler, and the 26 tests are in [the repo](https://github.com/0xSoftBoi/cowswaprouter).
