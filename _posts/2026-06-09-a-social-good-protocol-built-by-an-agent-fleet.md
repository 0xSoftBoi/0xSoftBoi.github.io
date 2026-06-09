---
layout: post
title: "A social-good protocol, built by an agent fleet"
date: 2026-06-09
series: "Applied ML"
tags: [agents, claude, workflow, solidity, security]
image: /assets/og/a-social-good-protocol-built-by-an-agent-fleet.png
excerpt: "I had an empty repo and pointed a multi-agent workflow at it. The result was a tested rewards protocol — but the part worth writing down is which model sat in which seat, and the bug the auditor caught that the builder wrote."
---

One of my repos, `socialstack`, was empty: a 2021 license file and a README that said, in full, "socialstack frontend." The reference I had was [values.network](https://www.values.network) — a values-based social network where you go on **missions** (real action on causes: health, nature, local community, nonprofits) and earn a community reward token. Socialstack's whole DNA is social tokens, so the reward is on-chain.

So I knew the *what*. The question was how to build it well, and I wanted to try something: instead of writing it all myself on one model, run a fleet — and be deliberate about which Claude model does which job.

## The seating chart

The models aren't interchangeable, and the price difference is real (Opus output is 5× Sonnet, which is 5× Haiku). The skill is matching the model to the *kind* of thinking the task needs:

- **Opus 4.8** sits in the seats where being wrong is expensive and being thorough pays: **research, architecture, and the security audit.** Opus is meaningfully better at finding bugs — higher recall *and* precision — so it's wasted on boilerplate and indispensable on review.
- **Sonnet 4.6** is the builder. **Implementation and fixes** from a clear spec — strong, fast, and the right call when the design decisions are already made.
- **Haiku 4.5** does the **scaffolding** — the Foundry project, the Next.js skeleton, the config. Mechanical, high-volume, no judgment required. Cheap on purpose.

<figure class="chart">
<svg viewBox="0 0 700 300" role="img" aria-labelledby="af-t">
<title id="af-t">A six-phase workflow with each phase on the right model tier</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-label-sm" x="20" y="30">Opus 4.8 — judgment</text>
<text class="c-label-sm" x="250" y="30">Sonnet 4.6 — build</text>
<text class="c-label-sm" x="470" y="30">Haiku 4.5 — scaffold</text>
<circle cx="14" cy="26" r="5" fill="var(--accent)"/>
<circle cx="244" cy="26" r="5" class="c-box"/>
<circle cx="464" cy="26" r="5" class="c-grid" fill="currentColor" opacity="0.4"/>

<rect class="c-box-accent c-fill-soft" x="20" y="70" width="120" height="46" rx="8"/>
<text class="c-label-sm" x="80" y="90" text-anchor="middle">Research</text>
<text class="c-label-sm" x="80" y="106" text-anchor="middle">Opus</text>
<line class="c-arrow" x1="142" y1="93" x2="172" y2="93"/>

<rect class="c-box-accent c-fill-soft" x="174" y="70" width="120" height="46" rx="8"/>
<text class="c-label-sm" x="234" y="90" text-anchor="middle">Architecture</text>
<text class="c-label-sm" x="234" y="106" text-anchor="middle">Opus</text>
<line class="c-arrow" x1="296" y1="93" x2="326" y2="93"/>

<rect class="c-box" x="328" y="70" width="120" height="46" rx="6"/>
<text class="c-label-sm" x="388" y="90" text-anchor="middle">Scaffold</text>
<text class="c-label-sm" x="388" y="106" text-anchor="middle">Haiku</text>
<line class="c-arrow" x1="450" y1="93" x2="480" y2="93"/>

<rect class="c-box" x="482" y="58" width="150" height="32" rx="6"/>
<text class="c-label-sm" x="557" y="78" text-anchor="middle">Build: contracts — Sonnet</text>
<rect class="c-box" x="482" y="96" width="150" height="32" rx="6"/>
<text class="c-label-sm" x="557" y="116" text-anchor="middle">Build: frontend — Sonnet</text>

<line class="c-arrow" x1="557" y1="128" x2="557" y2="170"/>
<rect class="c-box-accent c-fill-soft" x="482" y="172" width="150" height="46" rx="8"/>
<text class="c-label-sm" x="557" y="192" text-anchor="middle">Audit (adversarial)</text>
<text class="c-label-sm" x="557" y="208" text-anchor="middle">Opus</text>
<line class="c-arrow" x1="480" y1="195" x2="326" y2="195"/>

<rect class="c-box" x="174" y="172" width="150" height="46" rx="6"/>
<text class="c-label-sm" x="249" y="192" text-anchor="middle">Finalize: fix + tests</text>
<text class="c-label-sm" x="249" y="208" text-anchor="middle">Sonnet</text>

<text class="c-label-sm" x="350" y="262" text-anchor="middle">The auditor reads the builder's code and tries to break it — a different model in a different seat.</text>
<text class="c-label-sm" x="350" y="284" text-anchor="middle">Its findings become the fixer's worklist. Then I re-ran the tests myself.</text>
</svg>
<figcaption>Six phases, each on the tier the work needs. The expensive model is reserved for research, design, and the adversarial audit; the cheap one for scaffolding.</figcaption>
</figure>

## What got built

A real missions/rewards layer, not a toy:

- **`RewardToken`** — IMPACT, the ERC-20 community reward. Minting is owner-only and the Missions contract holds no minter rights, so a bug in the protocol can't inflate the supply.
- **`Missions`** — the escrow. A creator funds a mission with a *capped* reward pool. A user claims exactly once, and only with an **EIP-712 attestation** signed by a trusted off-chain verifier (you did the mission). The claim is replay-proof per `(mission, user)`, the pool can't be over-claimed or siphoned across missions, it's `nonReentrant` with checks-effects-interactions, and there's an attestation epoch so the admin can revoke outstanding signatures.

## The bug the auditor caught the builder writing

Here's the part that justifies the seating chart. Sonnet built the contracts and 26 passing tests. Then Opus audited them, with one instruction that matters: *report everything, including low-severity and uncertain — don't filter.* (Tell Opus to "only report high-severity issues" and it obeys you literally, and recall drops.)

It found four real things the builder hadn't:

1. **`missionId` squatting** — creators chose their own mission IDs, so one creator could grief another by pre-claiming an ID. Fix: a cancel cooldown plus `delete` so IDs free up correctly.
2. **Single-step `Ownable`** on the attestor key — the key that authorizes *every* payout. A fat-fingered `transferOwnership` loses it forever. Fix: `Ownable2Step`.
3. **Pre-signable, never-expiring attestations** — an attestor could sign for a mission before it existed, with an unbounded deadline. Fix: the epoch mechanism.
4. A missing zero-address guard in `claim`.

It also did the opposite of finding bugs: a careful, affirmative proof that double-claim, signature forgery, malleability (OZ's ECDSA reverts on high-s), cross-chain and cross-mission replay, pool drain, and reentrancy were *actually closed* — citing the lines. That's the half of an audit people skip: saying what you checked and why it holds.

Sonnet then applied every fix with a regression test apiece. 26 tests became 34.

## I re-ran them anyway

A workflow telling me "34/34 green" is a claim, not a result. So before any of it shipped I re-ran `forge test` myself (34/34, confirmed), read the `claim` path line by line to check the safety properties were real rather than asserted, and secret-scanned the repo before flipping it public. The fleet does the work; the verification is still mine to own.

The contracts, the 34 tests, and the frontend scaffold are at [github.com/0xSoftBoi/socialstack](https://github.com/0xSoftBoi/socialstack). The whole thing — research to audited, tested protocol — was one workflow. The trick wasn't the agents. It was putting the careful model in the careful seat.
