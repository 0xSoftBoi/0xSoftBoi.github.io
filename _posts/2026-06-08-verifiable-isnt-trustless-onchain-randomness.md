---
layout: post
title: "Verifiable isn't trustless: a coin flip on Sui"
date: 2026-06-08
series: "On-chain randomness & verifiability"
tags: [randomness, sui, move, security, cryptography]
image: /assets/og/verifiable-isnt-trustless-onchain-randomness.png
math: true
excerpt: "A house-signed coin flip lets anyone verify the result — and still lets the house win. Every settled game is provably fair; the set of settled games is hand-picked. Here's what that lever is worth in closed form, why a 10% skim is invisible over a hundred games, and the trustless fix that has its own sharp edge."
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

That's the difference between **verifiable** and **trustless**, and the two get conflated constantly. Verifiable means you can check that the rule was followed. Trustless means no party had a lever to pull. House-signed BLS is the first without the second: every settled game is provably fair, and the set of games that got settled is quietly hand-picked.

## What the lever is worth

"Quietly hand-picked" is a hand-wave. The lever has a closed form, and writing it down is what convinced me this is worse than it sounds.

Let the coin be fair, the bet even money at stake \\(S\\), and let \\(\sigma \in [0,1]\\) be the fraction of *losing* games the house declines to settle. \\(\sigma = 0\\) is an honest house; \\(\sigma = 1\\) is the maximally greedy one. The house wins half the games and settles all of them; it loses the other half and settles \\((1-\sigma)\\) of those. So its expected take per game is

$$
\mathbb{E}[\text{house}] \;=\; \tfrac{1}{2}S \;-\; \tfrac{1}{2}(1-\sigma)S \;=\; \frac{\sigma}{2}\,S
$$

The house edge is \\(\sigma/2\\) — half the withholding rate, straight through, with no bound from the cryptography. Meanwhile the *public record* shows a win rate over settled games of

$$
q(\sigma) \;=\; \frac{\tfrac{1}{2}}{\tfrac{1}{2} + \tfrac{1}{2}(1-\sigma)} \;=\; \frac{1}{2-\sigma}
$$

Both of those are monotone in \\(\sigma\\), which is the whole problem: the house gets to pick its own edge, and the only thing that moves against it is how conspicuous the record looks.

| \\(\sigma\\) | house edge | settled win rate \\(q\\) |
|---|---|---|
| 0 | 0% | 0.500 |
| 0.1 | 5% | 0.526 |
| 0.2 | 10% | 0.556 |
| 0.5 | 25% | 0.667 |
| 1.0 | 50% | 1.000 |

The greedy corner is self-defeating — \\(\sigma = 1\\) means the house never loses in public, and seven straight wins is already \\(2^{-7} < 0.01\\). But a house that stops at \\(\sigma = 0.2\\) is taking **10% of everything staked** while posting a 55.6% win rate, and that is a hard number to see. Under the honest null the standard error of an observed win rate over \\(n\\) settled games is \\(0.5/\sqrt{n}\\), so the deviation \\(q - \tfrac12 = 0.0556\\) shows up at

$$
z \;=\; \frac{0.0556}{0.5/\sqrt{n}} \;=\; 0.111\sqrt{n}
$$

which is \\(z = 1.11\\) at \\(n = 100\\), \\(z = 3.51\\) at \\(n = 1000\\). A house skimming a tenth of the pot is **statistically indistinguishable from fair across its first hundred games**, and every single one of those games came with a signature anyone could check.

That is the sentence I want to leave with you. The verification is not fake, and it is not evidence of fairness. It is evidence about the games you were shown.

## The trustless version — and its sharp edge

Sui ships the honest fix: a native `Random` object (`0x8`) backed by the validators' distributed key generation. No single validator knows the seed; you'd need a third of them colluding. You seed a local generator from that beacon and the transaction, and nobody — house included — knows the result until the transaction has already committed. I implemented it alongside the BLS path as `finish_game_native`, and it's strictly better here: **anyone** can settle, which drives \\(\sigma\\) to zero by construction rather than by trust.

But native randomness has a footgun that's worth the whole post on its own:

> The function that consumes `&Random` must be a **private `entry` function — not `public`.**

Make it `public` and you've reopened the bias from a new direction. A `public` function can be called by *another* Move function, so a caller can wrap your settle call, read the result, and **abort the whole transaction if it's a loss** — paying only gas and retrying until it wins. "Preview-and-abort." An `entry` function can't be called from other Move code — only as a top-level transaction command — so its effects can't be inspected-and-reverted by a composing caller. The fix for one bias attack is exactly the surface for another, one keyword away.

And this one is even cheaper than the house's lever, because the attacker is paying in gas rather than in forgone stake. Retries until a win are geometric with parameter \\(p\\), so the expected number of *aborted* attempts before the winning one is \\((1-p)/p\\). If each abort costs \\(g\\) and the prize is \\(W\\), the attack clears whenever

$$
W \;>\; g\cdot\frac{1-p}{p}
$$

For a fair coin that reduces to \\(W > g\\): the attack is profitable the moment the pot exceeds the price of one failed transaction. On Sui, where an abort costs a fraction of a cent, there is no pot small enough for this to be uneconomic. A bias lever that costs nothing to pull will get pulled.

## The bias that was already there

While rewriting the settlement paths I found a smaller, older problem sitting underneath both of them: the dice game drew a face with `byte % sides`. That is the classic modulo bias, and unlike the two levers above it needs no attacker at all — it is just wrong.

A uniform byte takes \\(256\\) values. Write \\(256 = q\cdot s + r\\) for \\(s\\) sides. Then \\(r\\) of the faces are reachable from \\(q+1\\) distinct bytes and the remaining \\(s - r\\) faces from only \\(q\\):

$$
\Pr[\text{face } i] \;=\; \frac{\lfloor (255 - i)/s \rfloor + 1}{256}
$$

For a six-sided die, \\(256 = 42\cdot 6 + 4\\). Faces 0–3 land on \\(43/256\\) and faces 4–5 on \\(42/256\\), against a uniform \\(1/6 = 128/768\\):

$$
\frac{43}{256} = \frac{129}{768} \;\;(+0.78\%), \qquad \frac{42}{256} = \frac{126}{768} \;\;(-1.56\%)
$$

<figure class="chart">
<svg viewBox="0 0 680 290" role="img" aria-labelledby="mod-t">
<title id="mod-t">Modulo bias of byte % 6, as deviation from a uniform die</title>
<text class="c-title" x="20" y="24">byte % 6 — deviation from uniform</text>
<text class="c-label-sm" x="20" y="44">256 = 42·6 + 4, so four faces get one extra byte each</text>

<line class="c-grid" x1="86" y1="118" x2="640" y2="118"/>
<line class="c-grid" x1="86" y1="198" x2="640" y2="198"/>
<line class="c-grid" x1="86" y1="238" x2="640" y2="238"/>
<line class="c-axis" x1="86" y1="158" x2="640" y2="158"/>
<text class="c-label-sm" x="78" y="122" text-anchor="end">+1%</text>
<text class="c-label-sm" x="78" y="162" text-anchor="end">0</text>
<text class="c-label-sm" x="78" y="202" text-anchor="end">−1%</text>
<text class="c-label-sm" x="78" y="242" text-anchor="end">−2%</text>

<rect class="c-bar" x="98" y="127" width="64" height="31"/>
<rect class="c-bar" x="186" y="127" width="64" height="31"/>
<rect class="c-bar" x="274" y="127" width="64" height="31"/>
<rect class="c-bar" x="362" y="127" width="64" height="31"/>
<rect class="c-bar-muted" x="450" y="158" width="64" height="63"/>
<rect class="c-bar-muted" x="538" y="158" width="64" height="63"/>

<text class="c-val" x="130" y="120" text-anchor="middle">+0.78</text>
<text class="c-val" x="218" y="120" text-anchor="middle">+0.78</text>
<text class="c-val" x="306" y="120" text-anchor="middle">+0.78</text>
<text class="c-val" x="394" y="120" text-anchor="middle">+0.78</text>
<text class="c-val" x="482" y="236" text-anchor="middle">−1.56</text>
<text class="c-val" x="570" y="236" text-anchor="middle">−1.56</text>

<text class="c-label-sm" x="130" y="268" text-anchor="middle">face 0</text>
<text class="c-label-sm" x="218" y="268" text-anchor="middle">face 1</text>
<text class="c-label-sm" x="306" y="268" text-anchor="middle">face 2</text>
<text class="c-label-sm" x="394" y="268" text-anchor="middle">face 3</text>
<text class="c-label-sm" x="482" y="268" text-anchor="middle">face 4</text>
<text class="c-label-sm" x="570" y="268" text-anchor="middle">face 5</text>
</svg>
<figcaption>Plotted as deviation from 1/6, not as raw probability — at full scale the six bars look identical, which is exactly why this survives code review. Face 0 is 2.38% likelier than face 5.</figcaption>
</figure>

The total variation distance from uniform has a clean closed form, \\(r(s-r)/(256\,s)\\), which here is \\(1/192 \approx 0.0052\\). Small. It is also **exactly zero if and only if \\(s\\) divides 256** — that is, only for power-of-two face counts. Which is why the coin flip never had this problem and the dice always did, from the same line of reasoning, and why "we tested the coin" was never going to catch it. Sui's `random` module hands you a rejection-sampling `generate_u64_in_range`; the fix was to use it.

Three levers, then, in one small game: one the house pulls (selective settlement), one a composing caller pulls (preview-and-abort), and one nobody pulls because it is baked into an arithmetic operator. Only the third is a bug in the ordinary sense. The first two are correct code with a trust boundary drawn in the wrong place.

## A footnote that became the first thing I fixed

I should admit how this started. Before any of the randomness analysis, I ran `sui move build`. It failed. The dice module had been committed in a state that *never compiled* — it called functions that didn't exist on the house object and borrowed a value it had moved. And because the package didn't build, **not one of its tests had ever run** — including the fact that the dice game had no tests at all, and the coin flip's tests quietly bypassed the BLS verification they were supposedly covering.

This is the same lesson [the negation work](/blog/the-model-reads-not-it-just-cant-use-it/) and [the bridge](/blog/auditing-my-own-bridge/) keep handing me from different directions: code you haven't run is not code that works, it's a draft you're hoping about. A test that can't fail — because the build is red, or because it routes around the thing it claims to test — proves nothing. The repo now builds, both settlement paths are real, the fee is charged once instead of twice (it was), and there are nineteen tests that actually exercise the BLS rejection, the native path, and the dice game.

## Closing

Every number above is **derived**, not measured: it follows from the game's stated payout structure and Sui's documented primitives, and none of it requires observing a dishonest house in the wild. That is the useful property. You do not need to catch anyone to price the lever — you need to notice that the lever exists, and then the arithmetic tells you it is worth \\(\sigma/2\\) of everything staked, invisible for a hundred games at \\(\sigma = 0.2\\).

The runnable version — both paths, the threat model, and the `entry`-vs-`public` footgun written down where the next person will see it — is public: **[satoshi_flip](https://github.com/0xSoftBoi/satoshi_flip)**. The one-line takeaway I keep: *verifiable* tells you the result was computed honestly. It does not tell you the game was fair. For that, count who could have walked away, and price what walking away is worth to them.
