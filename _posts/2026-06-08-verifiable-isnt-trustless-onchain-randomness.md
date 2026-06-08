---
layout: post
title: "Verifiable isn't trustless: a coin flip on Sui"
date: 2026-06-08
tags: [randomness, sui, move, security, cryptography]
image: /assets/og/verifiable-isnt-trustless-onchain-randomness.png
excerpt: "A house-signed coin flip lets anyone verify the result — and still lets the house win. The signature is honest; the choice of which games to settle isn't. Here's the gap, and the trustless fix that has its own sharp edge."
---

A blockchain is a machine built to never surprise itself: every node has to compute the same result from the same inputs. So where do you get a random number to settle a coin flip? Anything already on-chain — a block hash, a timestamp — is visible to whoever produces the block, and they'll re-roll it until they like the outcome. You have to bring the randomness in from somewhere, and *how* you bring it in is the whole security story.

I picked up an old Sui Move game of mine, `satoshi_flip`, to look at exactly this. It settles a bet with **house-signed randomness**: the player makes a guess, the house signs the game's id with a BLS12-381 key, and the hash of that signature is the coin. The appeal is that it's **verifiable** — the signature is checked on-chain against the house's public key, so anyone can confirm the house didn't just type in "you lose."

## Verifiable, and still rigged

Here's the part that's easy to wave past. A BLS signature is **deterministic**: for a given key and message there is exactly one valid signature. People reach for that as a *safety* property — "the house can't re-sign until it gets a result it likes." True. But run the determinism the other direction: the house can compute the one signature, and therefore the outcome, **off-chain, before it does anything on-chain**. It can't change a game's result — but it never has to settle a game it's going to lose.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="rng-t">
<title id="rng-t">Where the trust hides: house-signed BLS vs native randomness</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">Where the trust hides</text>

<text class="c-label-sm" x="20" y="52">BLS — verifiable, but house-trusted</text>
<rect class="c-box" x="20" y="62" width="118" height="46" rx="6"/>
<text class="c-val" x="79" y="82" text-anchor="middle">player bets</text>
<text class="c-label-sm" x="79" y="99" text-anchor="middle">guess + stake</text>
<line class="c-arrow" x1="140" y1="85" x2="206" y2="85"/>
<rect class="c-box-accent c-fill-soft" x="208" y="56" width="208" height="58" rx="8"/>
<text class="c-val" x="312" y="80" text-anchor="middle">house signs the game id</text>
<text class="c-label-sm" x="312" y="98" text-anchor="middle">deterministic → outcome known off-chain</text>
<line class="c-arrow" x1="418" y1="85" x2="484" y2="85"/>
<rect class="c-box" x="486" y="62" width="174" height="46" rx="6"/>
<text class="c-val" x="573" y="82" text-anchor="middle">settles a loss?</text>
<text class="c-label-sm" x="573" y="99" text-anchor="middle">only if the house wins</text>
<text class="c-label-sm" x="312" y="138" text-anchor="middle">The signature is honest. Choosing which games to settle is the rig.</text>

<line class="c-grid" x1="20" y1="166" x2="660" y2="166"/>

<text class="c-label-sm" x="20" y="196">Native — trustless</text>
<rect class="c-box" x="20" y="206" width="160" height="46" rx="6"/>
<text class="c-val" x="100" y="226" text-anchor="middle">validator DKG beacon</text>
<text class="c-label-sm" x="100" y="243" text-anchor="middle">0x8 · no one knows it early</text>
<line class="c-arrow" x1="182" y1="229" x2="248" y2="229"/>
<rect class="c-box-accent c-fill-soft" x="250" y="200" width="220" height="58" rx="8"/>
<text class="c-val" x="360" y="224" text-anchor="middle">entry fun settle(&amp;Random)</text>
<text class="c-label-sm" x="360" y="242" text-anchor="middle">must be entry, not public</text>
<line class="c-arrow" x1="472" y1="229" x2="538" y2="229"/>
<rect class="c-box" x="540" y="206" width="120" height="46" rx="6"/>
<text class="c-val" x="600" y="226" text-anchor="middle">anyone settles</text>
<text class="c-label-sm" x="600" y="243" text-anchor="middle">outcome is fair</text>
<text class="c-label-sm" x="340" y="282" text-anchor="middle">Trustless — but make it public and a caller previews the result and aborts on a loss.</text>
</svg>
<figcaption>BLS is verifiable but house-trusted: the house knows the outcome before it settles. Native randomness removes that power — at the cost of one sharp edge (it must be an <code>entry</code> function).</figcaption>
</figure>

That's the difference between **verifiable** and **trustless**, and the two get conflated constantly. Verifiable means you can check that the rule was followed. Trustless means no party had a lever to pull. House-signed BLS is the first without the second: every settled game is provably fair, and the set of games that got settled is quietly hand-picked. For a low-stakes, accountable house it's a reasonable trade. As "provably fair gaming," it's a half-truth.

## The trustless version — and its sharp edge

Sui ships the honest fix: a native `Random` object (`0x8`) backed by the validators' distributed key generation. No single validator knows the seed; you'd need a third of them colluding. You seed a local generator from that beacon and the transaction, and nobody — house included — knows the result until the transaction has already committed. I implemented it alongside the BLS path as `finish_game_native`, and it's strictly better here: it's unbiased (the old `byte % sides` is slightly skewed when the die's faces don't divide 256), and **anyone** can settle, which deletes the selective-participation lever entirely.

But native randomness has a footgun that's worth the whole post on its own:

> The function that consumes `&Random` must be a **private `entry` function — not `public`.**

Make it `public` and you've reopened the bias from a new direction. A `public` function can be called by *another* Move function, so a caller can wrap your settle call, read the result, and **abort the whole transaction if it's a loss** — paying only gas and retrying until it wins. "Preview-and-abort." An `entry` function can't be called from other Move code — only as a top-level transaction command — so its effects can't be inspected-and-reverted by a composing caller. The fix for one bias attack is exactly the surface for another, one keyword away.

## A footnote that became the first thing I fixed

I should admit how this started. Before any of the randomness analysis, I ran `sui move build`. It failed. The dice module had been committed in a state that *never compiled* — it called functions that didn't exist on the house object and borrowed a value it had moved. And because the package didn't build, **not one of its tests had ever run** — including the fact that the dice game had no tests at all, and the coin flip's tests quietly bypassed the BLS verification they were supposedly covering.

This is the same lesson [the negation work](/blog/the-model-reads-not-it-just-cant-use-it/) and [the bridge](/blog/auditing-my-own-bridge/) keep handing me from different directions: code you haven't run is not code that works, it's a draft you're hoping about. A test that can't fail — because the build is red, or because it routes around the thing it claims to test — proves nothing. The repo now builds, both settlement paths are real, the fee is charged once instead of twice (it was), and there are nineteen tests that actually exercise the BLS rejection, the native path, and the dice game.

The runnable version — both paths, the threat model, and the `entry`-vs-`public` footgun written down where the next person will see it — is public: **[satoshi_flip](https://github.com/0xSoftBoi/satoshi_flip)**. The one-line takeaway I keep: *verifiable* tells you the result was computed honestly. It does not tell you the game was fair. For that, check who could have walked away.
