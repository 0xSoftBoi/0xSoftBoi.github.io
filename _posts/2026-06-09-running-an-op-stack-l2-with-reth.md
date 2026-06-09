---
layout: post
title: "Running an OP Stack L2 with reth"
date: 2026-06-09
tags: [optimism, rollup, reth, ethereum, devops]
image: /assets/og/running-an-op-stack-l2-with-reth.png
excerpt: "An OP Stack rollup is four processes and a shared secret. I finalized an old deployment of mine into something reproducible — and the part that actually caught bugs wasn't me, it was CI."
---

An OP Stack rollup looks intimidating until you see that it's four long-running processes wired to an L1, and one shared secret holding two of them together. I had a half-finished deployment of one — `op-stack-reth`, a docker-compose setup using **reth** as the execution client instead of the usual op-geth — and I finished it. The interesting parts were what "finishing" meant.

## The four processes and the handshake

```
op-reth     execution layer — runs the EVM, holds L2 state, serves eth_* RPC
op-node     consensus layer — derives the L2 chain from L1, drives block production
op-batcher  posts L2 transaction batches down to L1 (as blobs)
op-proposer posts L2 state roots to L1 (so withdrawals can be proven)
```

The handshake is the part worth internalizing. `op-node` doesn't execute transactions; `op-reth` doesn't decide what the chain is. They talk over the **Engine API** — the same `engine_forkchoiceUpdated` / `engine_getPayload` interface Ethereum L1 uses between its consensus and execution clients — and that interface is authenticated with a **JWT secret** the two share. `op-node` says "build a block on top of this head"; `op-reth` builds and executes it; `op-node` says "this is now canonical." That's the whole dance. Everything else — the batcher, the proposer — is about getting that L2 chain *onto* L1 so it inherits Ethereum's security.

<figure class="chart">
<svg viewBox="0 0 680 350" role="img" aria-labelledby="op-t">
<title id="op-t">OP Stack topology: op-reth and op-node over the Engine API, batcher and proposer to L1</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="40" y="28">L2 — your rollup</text>
<rect class="c-box" x="40" y="44" width="180" height="64" rx="8"/>
<text class="c-label-sm" x="130" y="70" text-anchor="middle">op-node</text>
<text class="c-label-sm" x="130" y="88" text-anchor="middle">consensus / derivation</text>
<rect class="c-box-accent c-fill-soft" x="300" y="44" width="180" height="64" rx="8"/>
<text class="c-title" x="390" y="70" text-anchor="middle">op-reth</text>
<text class="c-label-sm" x="390" y="90" text-anchor="middle">execution (EVM, state)</text>
<line class="c-arrow" x1="222" y1="68" x2="298" y2="68"/>
<line class="c-arrow" x1="298" y1="86" x2="222" y2="86"/>
<text class="c-label-sm" x="260" y="36" text-anchor="middle" fill="var(--accent)">Engine API + JWT</text>
<rect class="c-box" x="40" y="150" width="180" height="44" rx="6"/>
<text class="c-label-sm" x="130" y="176" text-anchor="middle">op-batcher → L1 (blobs)</text>
<rect class="c-box" x="300" y="150" width="180" height="44" rx="6"/>
<text class="c-label-sm" x="390" y="176" text-anchor="middle">op-proposer → L1 (roots)</text>
<line class="c-arrow" x1="130" y1="108" x2="130" y2="150"/>
<line class="c-arrow" x1="390" y1="108" x2="390" y2="150"/>
<line class="c-grid" x1="40" y1="232" x2="640" y2="232"/>
<text class="c-title" x="40" y="262">L1 — Ethereum (Sepolia / mainnet)</text>
<rect class="c-box" x="40" y="278" width="440" height="44" rx="6"/>
<text class="c-label-sm" x="260" y="304" text-anchor="middle">batch inbox · output oracle / dispute game · bridge</text>
<line class="c-arrow" x1="130" y1="194" x2="130" y2="278"/>
<line class="c-arrow" x1="390" y1="194" x2="390" y2="278"/>
<line class="c-arrow" x1="560" y1="278" x2="560" y2="120"/>
<text class="c-label-sm" x="560" y="200" text-anchor="middle">L1 →</text>
<text class="c-label-sm" x="560" y="218" text-anchor="middle">derivation</text>
<text class="c-label-sm" x="582" y="110" text-anchor="middle">op-node</text>
</svg>
<figcaption>op-node and op-reth share the Engine API (authenticated by a JWT); op-node also derives the chain from L1, while the batcher and proposer push data and state roots back down to L1.</figcaption>
</figure>

## What "finishing it" actually meant

The deployment mostly existed. What it lacked was everything that makes infra *trustworthy* rather than just present:

- **Every image was `:latest`.** That's a time bomb — `docker compose pull` six months apart gives you two different rollups, and one of them won't boot. I pinned all six (op-reth, op-node, batcher, proposer, prometheus, grafana) to released, env-overridable tags tracking `op-contracts v4.0.0`.
- **Genesis was a manual chore.** The README said "generate `genesis.json` and `rollup.json` using the Optimism monorepo" — a clone-and-pray step. The modern answer is **op-deployer**: one tool that deploys the L1 contracts and emits both files. I wired it into a `make config` so the path from nothing to a configured chain is a single command.
- **A real config bug.** In replica mode, reth's `--rollup.sequencer-http` defaulted to the node's *own* op-node. A replica is supposed to forward transactions to the *external* sequencer; pointing it at itself is a quiet footgun. Fixed.

## The part that caught bugs was CI, not me

Here's the honest bit. I can't run Docker in my environment, so I can't boot the chain to prove it works — and I said so in the README, in a "what's verified vs what needs Docker" section, rather than implying a green I didn't earn. What I *could* do is make the repo verify itself: a `make validate` (script syntax, YAML, JSON) that runs anywhere, plus a CI workflow that adds `shellcheck`, `yamllint`, and crucially `docker compose config` on GitHub's runners.

And the first thing CI did was fail — on **my own scripts**. `shellcheck` flagged the validation script I'd just written: an unguarded `cd`, a loop that could only run once, an unchecked `source`. `bash -n` had passed them happily; shellcheck didn't. I fixed the three, pushed, and watched `docker compose config` validate the pinned compose file on a machine that actually had Docker — the one check I couldn't run myself, now green.

That's the whole reason to wire up CI on an infra repo you can't fully exercise locally: it runs the checks your laptop can't, and it has no investment in your code being correct. The [finalized deployment](https://github.com/0xSoftBoi/op-stack-reth) boots a reth-powered OP Stack L2 in replica or sequencer mode; the green check next to it is the part I didn't have to take on faith.
