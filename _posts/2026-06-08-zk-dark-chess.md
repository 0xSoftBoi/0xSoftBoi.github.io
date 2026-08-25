---
layout: post
title: "Building ZK dark chess: real fog of war on a public chain"
date: 2026-06-08
series: "On-chain randomness & verifiability"
tags: [zk, circom, chess, cryptography, solidity]
image: /assets/og/zk-dark-chess.png
excerpt: "My on-chain chess engine has a fog-of-war mode that hides nothing — the board is plaintext. So I built the real version: the board lives off-chain behind a Poseidon commitment, and every move ships a zk-SNARK that it was legal without revealing the rest of your pieces. A real proof, verified on-chain. And an honest wall where the cryptography stops."
---

In the [last post](/blog/what-a-zk-proof-proves/) I admitted my chess engine's "dark chess" hides nothing — the board is a plaintext `uint256` emitted in every event, and the fog is a frontend convention. The honest follow-up was to actually build it. So I did: [**zk-dark-chess**](https://github.com/0xSoftBoi/zk-dark-chess), where the board lives off-chain behind a commitment and every move carries a zero-knowledge proof that it was legal — verified on-chain, against a real proof, in the test suite.

## Why chess fog is harder than Dark Forest

The reflex is "just do what [Dark Forest](https://blog.zkga.me/announcing-darkforest) does." Dark Forest hides planet coordinates as hash commitments and proves a move is in range without revealing where you are. It works because the hidden state is *independent*: your secret location doesn't change whether my move is legal. Chess fog — kriegspiel — isn't independent. The two armies share one board, and legality couples to the *opponent's* hidden pieces: a rook is blocked by an enemy piece you can't see, your destination might capture a piece you don't know is there, and "check" depends on pieces neither side reveals. You cannot prove *full* legality against only your own board.

That coupling is a real wall, not a missing feature. So the honest target is the part that *is* achievable without a trusted referee or multi-party computation: **prove your move is legal against your own committed board**, hiding the rest. That is also exactly where the state of the art stops — the only other real ZK fog-chess project, the Noir-based [tikan](https://github.com/tsujp/tikan), drops check entirely and wins by king-capture.

## The build

Three pieces, and the seam between them is the whole idea.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="zd-t">
<title id="zd-t">Off-chain board, on-chain commitment, a ZK proof per move</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<text class="c-title" x="20" y="24">What's hidden, what's proven, what's on-chain</text>
<rect class="c-box" x="20" y="52" width="180" height="58" rx="6"/>
<text class="c-val" x="110" y="76" text-anchor="middle">your full board</text>
<text class="c-label-sm" x="110" y="94" text-anchor="middle">off-chain, secret</text>
<line class="c-arrow" x1="202" y1="81" x2="266" y2="81"/>
<rect class="c-box-accent c-fill-soft" x="268" y="50" width="184" height="62" rx="8"/>
<text class="c-val" x="360" y="74" text-anchor="middle">Poseidon(board, salt)</text>
<text class="c-label-sm" x="360" y="92" text-anchor="middle">the only thing on-chain</text>
<line class="c-arrow" x1="454" y1="81" x2="518" y2="81"/>
<rect class="c-box" x="520" y="52" width="140" height="58" rx="6"/>
<text class="c-val" x="590" y="76" text-anchor="middle">reveals nothing</text>
<text class="c-label-sm" x="590" y="94" text-anchor="middle">about your pieces</text>
<line class="c-grid" x1="20" y1="142" x2="660" y2="142"/>
<text class="c-label-sm" x="20" y="170">A move publishes only the squares it touches + a proof it was legal:</text>
<rect class="c-box" x="20" y="188" width="300" height="44" rx="6"/>
<text class="c-label-sm" x="170" y="214" text-anchor="middle">public: (from, to, piece) + new commitment</text>
<rect class="c-box-accent c-fill-soft" x="332" y="188" width="328" height="44" rx="8"/>
<text class="c-label-sm" x="496" y="208" text-anchor="middle">ZK proof: piece at `from`, legal geometry, clear</text>
<text class="c-label-sm" x="496" y="224" text-anchor="middle">slider path, no self-capture, correct new board</text>
<text class="c-label-sm" x="340" y="264" text-anchor="middle">The opponent sees where you moved — never the rest of your army.</text>
</svg>
<figcaption>The board never touches the chain. A commitment does, and each move proves legality against it in zero knowledge — that's the fog.</figcaption>
</figure>

**The circuit** ([`move.circom`](https://github.com/0xSoftBoi/zk-dark-chess/blob/main/circuits/move.circom), ~4,300 constraints) takes the board as 64 private cells and a salt, and proves: `Poseidon(packed board, salt)` equals the public old commitment; the piece of the claimed type really sits at `from`; the geometry is legal for that piece (knight/king/pawn-push step tables, rook/bishop/queen rays); for sliders, **every square between `from` and `to` is empty on your own board**; `to` isn't one of your pieces; and the new commitment is exactly the board after the move. Everything except `(cOld, cNew, from, to, piece)` is private.

The slider path check is the fun part. The intermediate squares are a function of the public `from`/`to`, but a circuit is fixed — so you can't loop a variable number of times. You unroll the maximum (6), compute each candidate index `from + j·step`, select that cell out of the private board with an equality-sum, and only *enforce* emptiness when the piece is a slider and `j` is inside the ray. The same equality-sum trick applies the move to produce the new board.

**The contract** ([`DarkChessZK.sol`](https://github.com/0xSoftBoi/zk-dark-chess/blob/main/src/DarkChessZK.sol)) stores one commitment per player. `playMove` requires the proof's `cOld` to match your stored commitment, runs the snarkjs-generated Groth16 verifier, advances your commitment to `cNew`, and emits the public squares. The board is never on-chain — only the hash and the move coordinates.

## A real proof, verified on-chain

The point that matters: this isn't a mock. The repo compiles the circuit with circom, runs a Groth16 setup with snarkjs, and generates an actual proof for a concrete legal move — a rook sliding a1→a4 over empty squares (which exercises the path check). That proof, and a `MoveVerifier.sol` snarkjs emits from the circuit, go straight into a Foundry test:

```text
[PASS] test_realProof_verifiesOnChain_andAdvancesCommitment
[PASS] test_staleCommitment_reverts
[PASS] test_tamperedPublicInput_rejected
```

The first feeds the real proof to `playMove` and checks the on-chain verifier accepts it and the commitment advances. The third takes that same proof, flips one public input (the piece type, 4→5), and confirms the verifier rejects it — soundness, on-chain. The whole pipeline, circuit to verified-in-the-EVM, runs from `./build.sh` + `forge test`.

## Where it honestly stops

I want to be exact about the boundary, because "ZK chess" oversells constantly. This proves move legality **against your own board**. It does *not* handle the three things that need your opponent's hidden state: **capturing a hidden enemy piece, a slider blocked by an enemy you can't see, and check.** Those are not a weekend's more circom — they're a different machine. Resolving "is there an enemy piece on this square?" without either player revealing it is a secure-two-party-computation problem; the referee-free version is open, and nobody has shipped it. A real kriegspiel protocol would put an MPC or an FHE coprocessor where this design has a commitment.

So: real fog of war for the legal-move primitive, verified on-chain, and an honest wall exactly where the cryptography runs out. That's the same lesson as everything else this month — [randomness](/blog/the-on-chain-randomness-landscape/), [proof binding](/blog/what-a-zk-proof-proves/), and now hiding: the cryptography does precisely what it says and not one inch more, and the engineering is knowing where the inch ends.

The build is public — circuit, generated verifier, game contract, and the real on-chain proof test — at [zk-dark-chess](https://github.com/0xSoftBoi/zk-dark-chess).
