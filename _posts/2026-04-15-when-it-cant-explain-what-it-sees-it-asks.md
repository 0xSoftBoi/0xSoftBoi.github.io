---
layout: post
title: "When it can't explain what it sees, it asks"
date: 2026-04-15
tags: [active-inference, rust, edge-ml]
excerpt: "I built a predictive-coding engine that runs a hierarchy of beliefs on a laptop GPU, minimizing prediction error layer by layer. The part I like most: when a layer can't explain away its own surprise, it doesn't just shrug and update — it asks the world a question, and the answer becomes knowledge that reshapes what it expects next."
---

There's an old idea in neuroscience — Friston's free energy principle, predictive coding before it — that a brain isn't a camera passively receiving the world. It's a prediction machine. Every layer is constantly guessing what the layer below it is about to report, and all that ever flows upward is the *error*: the part of the signal the prediction didn't already account for. Perception, on this account, is just the process of making that error small.

I wanted to feel what that's actually like to build, so I wrote one. **Qualia** is a small predictive-coding engine — a hierarchy of belief layers running on a laptop GPU, eating a webcam feed, trying to be unsurprised.

## What a belief is, concretely

In the engine, a belief isn't a vector — it's a little distribution. Each layer holds a `BeliefSlot`: a 64-dimensional `mean` (its best guess at the current state), a 64-dimensional `precision` (how *confident* it is, per dimension — the inverse of variance), a `prediction` for what comes next, and the `residual` — the prediction error left over after the fact arrives. There's a `vfe` field too: variational free energy, the quantity the whole system is trying to push down.

That precision term is the part people skip and it's the whole game. A prediction error isn't worth the same everywhere. An error in a dimension you're confident about is alarming and should move your beliefs hard; the identical error where you're already unsure is noise. So updates are *precision-weighted*: surprise scaled by how much you trusted the thing that got violated. The belief-update kernel does this for every slot, every cycle, on the GPU.

Seven of these layers stack up. The bottom ones predict raw sensory regularities; the top is grounded by a semantic embedding model (I used Gemini) that supplies the high-level "what should I expect to be looking at" that trickles down as top-down prediction. Lower layers learn to anticipate; the upper layer says what the scene *means*.

## The part that makes it active

Pure predictive coding is passive: minimize error by updating beliefs. **Active** inference adds the other lever. If you can't explain away your surprise by changing your mind, you can change the *world* — or at least go get the information that would make the surprise go away. Acting is just another way to minimize expected free energy.

So in Qualia, when a layer's residual stays stubbornly high — when it keeps being wrong in a way belief updates can't fix — it doesn't just keep absorbing the error. It writes a `QuestionSlot`: a question aimed at the outside world. The answer comes back and is stored as a `LoreEntry` — accumulated world-knowledge, tagged by the layer that needed it — and that LORE feeds back into future predictions. The engine literally gets curious about exactly the things it can't yet predict, and remembers the answers so it won't be surprised the same way twice. A machine that asks questions only about what confuses it is a surprisingly tidy consequence of "minimize free energy."

## The unglamorous half: keeping four languages agreeing

None of that runs if the bytes don't line up. The belief state lives in shared memory so a fleet of small processes — sensor capture, the belief kernels, the agent, a TUI supervisor — can all read and write it without copying. That means the *exact* memory layout of a `BeliefSlot` has to be identical in four places at once: the Rust struct (`repr(C, align(64))`), the Metal kernel, the CUDA kernel, and the Python bridge. One field added in the wrong spot and every process downstream reads garbage.

My favorite line in the whole project is a test:

```rust
assert_eq!(size, 1088, "BeliefSlot size changed — update CUDA kernel struct and Python bridge");
```

It's a tripwire. The moment someone changes the belief layout, the build fails with a message telling them every other place they now have to fix. The same kernel ships in two dialects — Metal for Apple Silicon, CUDA for a Jetson — so the engine runs on a laptop and on a robot from one design.

## Why I built it

I spend most of my time on the opposite kind of system: contracts and protocols where the whole job is to make behavior *exactly* predictable and then prove it. This was the inverse — a thing whose entire purpose is to be surprised well, to treat the gap between expectation and observation not as a bug to eliminate but as the signal to learn from. But the instinct underneath is the same one I bring to an audit: state precisely what you expect, watch the residual when reality disagrees, and chase the surprise instead of looking away from it. Here I just wired that loop directly into 64 floats and a GPU.

*Code: the `qualia/` engine in [sensorforge](https://github.com/0xSoftBoi/sensorforge) — a robotics monorepo with iPhone/ARKit sensor capture, a Jetson voice assistant, and this active-inference core.*
