---
layout: post
title: "What a ZK proof proves (and what it doesn't)"
date: 2026-06-08
tags: [zk, risc-zero, security, cryptography, solidity]
image: /assets/og/what-a-zk-proof-proves.png
excerpt: "My on-chain chess engine had a zk settlement path you could forge to steal any in-progress game — not by breaking the proof, but by proving the wrong thing. That bug, and a fog-of-war variant that hides nothing, are the two halves of ZK: soundness is binding the proof to the right statement; privacy is proving without revealing."
---

I went back to the parts of my on-chain chess engine I'd skipped — the zero-knowledge bits — because that's where the interesting failures live. I found a clean one: a settlement path you could **forge to steal any game in progress**. Not by breaking the proof. The proof was perfectly valid. It just proved the wrong thing.

That's the whole lesson, so let me say it plainly up front. A zk-SNARK does two things people constantly conflate. It proves a statement is true *without revealing the witness* (**privacy**), and it proves *that exact statement* and nothing else (**soundness**). A proof is only as useful as the statement it's bound to — and binding is entirely the application's job, not the prover's. Get it wrong and you get a flawless proof of something you didn't mean.

## Soundness: a valid proof of an unbound statement

The chess wager lets two players stake on a game, play off-chain, and settle on-chain. One settlement path is a [RISC Zero](https://dev.risczero.com/api/blockchain-integration/contracts/verifier) proof: a guest program replays the moves, decides the outcome, and commits its public output (the **journal**); an on-chain verifier checks the proof cheaply instead of replaying 60 moves of chess in the EVM.

Here's what the guest committed to its journal: `(gameId, outcome, movesHash)`. And here's the bug: **`gameId` and `moves` were private inputs the prover chose.** Nothing tied them to anything on-chain. So:

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="zk-t">
<title id="zk-t">A valid ZK proof of the wrong statement, and the binding that fixes it</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">The forge: a perfect proof, the wrong statement</text>
<rect class="c-box" x="20" y="50" width="190" height="54" rx="6"/>
<text class="c-val" x="115" y="72" text-anchor="middle">any White-wins game</text>
<text class="c-label-sm" x="115" y="90" text-anchor="middle">from a database, + victim's gameId</text>
<line class="c-arrow" x1="212" y1="77" x2="276" y2="77"/>
<rect class="c-box-accent c-fill-soft" x="278" y="48" width="150" height="58" rx="8"/>
<text class="c-val" x="353" y="72" text-anchor="middle">valid proof</text>
<text class="c-label-sm" x="353" y="90" text-anchor="middle">verifier says ✓</text>
<line class="c-arrow" x1="430" y1="77" x2="494" y2="77"/>
<rect class="c-box" x="496" y="50" width="164" height="54" rx="6"/>
<text class="c-val" x="578" y="72" text-anchor="middle">steals the game</text>
<text class="c-label-sm" x="578" y="90" text-anchor="middle">journal bound to nothing</text>
<line class="c-grid" x1="20" y1="138" x2="660" y2="138"/>
<text class="c-label-sm" x="20" y="166">The fix: bind the journal to the on-chain context the contract relies on.</text>
<rect class="c-box" x="20" y="184" width="150" height="40" rx="6"/>
<text class="c-label-sm" x="95" y="208" text-anchor="middle">pin the image id</text>
<rect class="c-box" x="184" y="184" width="200" height="40" rx="6"/>
<text class="c-label-sm" x="284" y="208" text-anchor="middle">journal = gameId + players</text>
<rect class="c-box-accent c-fill-soft" x="398" y="184" width="262" height="40" rx="8"/>
<text class="c-label-sm" x="529" y="208" text-anchor="middle">+ both players' signed move-list hash</text>
<text class="c-label-sm" x="340" y="258" text-anchor="middle">The attacker can fake a game and a proof — but not the victim's signature.</text>
</svg>
<figcaption>The proof verifies; that was never the question. Soundness lives in what the journal is bound to — gameId, the actual players, and a move-list both of them signed.</figcaption>
</figure>

An attacker takes any real game where White wins — Scholar's mate, anything from a database — runs the guest with `gameId` set to *your* active game, and gets a cryptographically valid proof that "your game" ended in a White win. They submit it, the verifier passes (the moves really do produce that outcome), and the contract pays them. You can't even dispute: the contract's challenge path needs a *conclusive* outcome, and your real game is still in progress.

The image ID — the fingerprint that pins *which guest program* ran — was checked correctly, so you couldn't swap in a different program. But [RISC Zero's docs](https://dev.risczero.com/api/blockchain-integration/contracts/verifier) are explicit about the second half: the journal must commit *everything the contract relies on*, and the contract must reconstruct and check it. The journal here committed an outcome and a moves hash bound to no game and no players. A valid receipt is replayable by anyone; without context-binding it replays — or here, *forges* — into another game.

The fix is to bind the journal to the game and make the moves a *commitment* both players signed:

- The guest now commits `(gameId, white, black, outcome, movesHash)`.
- On-chain, settlement requires the journal's `white`/`black` to **be** this game's players, and **both players' EIP-712 signatures over `(gameId, movesHash)`**.

Now the attacker is stuck: they can fabricate any game and a valid proof of its outcome, but they cannot produce the victim's signature over its move-list hash. The general checklist for *any* zkVM integration falls out of this one bug — pin the image ID, bind the journal to context (ids, addresses, a nonce), reconstruct-and-digest the journal on-chain, and use the canonical immutable verifier.

I'll be honest about the punchline, because it's instructive: once both players sign the move list, you're a hair away from just signing the *outcome* — which is a plain multisig settlement needing no proof at all. The zk path's genuine edge is narrow (the players agree on what was *played* but want the *result* computed trustlessly — say, a contested fifty-move draw). The proof was never the weak point. The binding was. That's almost always where it is.

## Privacy: you can't hide a chessboard on a public chain

The other zk variant in the repo is Dark Chess — fog of war, where you see only the squares your pieces reach. Except it hides nothing: the full board is a plaintext `uint256`, emitted in every move event. Anyone reading chain state sees both armies. The "fog" is a frontend convention; the contract still enforces move legality (it sees the whole board), so you can't cheat the rules — you just can't hide.

This isn't a bug so much as a wall. Every byte of on-chain state is public and replicated to every node; there is no private storage slot. You cannot keep *mutable, shared* secret state on a public chain by storing it. What you *can* do is store something that reveals nothing — a commitment or a ciphertext — and prove statements about it:

| approach | what it hides | what it proves | cost / trust |
|---|---|---|---|
| **commit–reveal** | one value, until you open it | the opened value matches the earlier hash | cheap; but the last revealer can abort |
| **ZK over a commitment** | *one party's* private state | "this move is legal," "this shot is a hit" — without opening | proving is heavy; verify is cheap; SNARK soundness |
| **FHE** (e.g. Zama) | *shared* mutable encrypted state | the homomorphic computation is correct, re-checkable | very high compute; threshold-key committee |
| **MPC** | secret-shared state | the joint result, no party sees inputs | communication-heavy; threshold honesty |
| **TEE** | arbitrary state in an enclave | an attestation that the right code ran | hardware trust + side-channels |

The canonical cryptographic fog of war is [Dark Forest](https://blog.zkga.me/announcing-darkforest), a zk MMO where planet coordinates are never published — players "submit commitments to their planet locations (by hashing the planet coordinates)," and a move ships "a zero-knowledge proof to prove that this constitutes a valid move" (the destination is within range of the source) without revealing either coordinate. The fog isn't a UI filter; it's a hash you have to *brute-force* to pierce. The same pattern runs [ZK Battleship](https://github.com/BattleZips/BattleZips-Circom) (prove a shot's hit/miss is consistent with a committed private board) and on up to mental poker. Dark Chess could be rebuilt this way — commit the board, prove each move legal in zero knowledge — but that's a different and much larger machine than a `uint256` and an honest client.

## The one line

ZK separates *what is stored* from *what is proven*. **Privacy** is proving a statement without revealing its witness. **Soundness** is binding the proof to the statement you actually meant. The fog-of-war board failed the first — it revealed everything. The chess settlement failed the second — it proved a true thing about the wrong game. A perfect proof of an unbound statement attests to nothing, and that, far more than any broken curve, is how zk systems actually get robbed. It's the same shape as [getting randomness wrong](/blog/the-on-chain-randomness-landscape/): the cryptography is rarely the hole — the binding to your context is.

The fix is real and tested — the journal binding, the co-signed moves commitment, and five tests including the forge attempt — in [the repo](https://github.com/0xSoftBoi/chess).
