---
layout: post
title: "When it can't explain what it sees, it asks"
date: 2026-04-15
tags: [active-inference, rust, edge-ml]
image: /assets/og/when-it-cant-explain-what-it-sees-it-asks.png
excerpt: "I built a predictive-coding engine that runs a hierarchy of beliefs on a laptop GPU, minimizing prediction error layer by layer. The part I like most: when a layer can't explain away its own surprise, it doesn't just shrug and update — it asks the world a question, and the answer becomes knowledge that reshapes what it expects next."
---

**Qualia** is a small program that watches a webcam and tries not to be surprised. When it can't explain what it's seeing — when its prediction stays wrong no matter how it adjusts its beliefs — it does the thing most perception code never does: it asks a question, takes the answer, and remembers it. Next time, it isn't surprised.

That behavior falls out of an old idea from neuroscience. Friston's free energy principle — predictive coding before it — holds that a brain isn't a camera passively receiving the world; it's a prediction machine. Every layer guesses what the layer below is about to report, and all that flows upward is the *error*: the part of the signal the guess didn't already cover. Perception, on this account, is just the work of making that error small. I wanted to feel what that's like to build, so I wrote one — a hierarchy of belief layers on a laptop GPU, eating a webcam feed, trying to be unsurprised.

* TOC
{:toc}

## What a belief is, concretely

In the engine, a belief isn't a vector — it's a little distribution. Each layer holds a `BeliefSlot`: a 64-dimensional `mean` (its best guess at the current state), a 64-dimensional `precision` (how *confident* it is, per dimension — the inverse of variance), a `prediction` for what comes next, and the `residual` — the prediction error left over after the fact arrives. There's a `vfe` field too: variational free energy, the quantity the whole system is trying to push down.

That precision term is the part people skip and it's the whole game. A prediction error isn't worth the same everywhere. An error in a dimension you're confident about is alarming and should move your beliefs hard; the identical error where you're already unsure is noise. So updates are *precision-weighted*: surprise scaled by how much you trusted the thing that got violated. The belief-update kernel does this for every slot, every cycle, on the GPU.

Seven of these layers stack up. The bottom ones predict raw sensory regularities; the top is grounded by a semantic embedding model (I used Gemini) that supplies the high-level "what should I expect to be looking at" that trickles down as top-down prediction. Lower layers learn to anticipate; the upper layer says what the scene *means*.

## The part that makes it active

Pure predictive coding is passive: minimize error by updating beliefs. **Active** inference adds the other lever. If you can't explain away your surprise by changing your mind, you change the *world* — or go get the information that would make the surprise go away. Perception drives free energy down by fitting your beliefs to the world; action drives it down by fitting the world to your beliefs. (Which action to take is the part scored by *expected* free energy — the surprise you anticipate down each path you could choose.)

So in Qualia, when a layer's residual stays stubbornly high — when it keeps being wrong in a way belief updates can't fix — it doesn't just keep absorbing the error. It writes a `QuestionSlot`: a question aimed at the outside world. The answer comes back and is stored as a `LoreEntry` — accumulated world-knowledge, tagged by the layer that needed it — and that LORE feeds back into future predictions. The engine gets curious about exactly the things a good question could *resolve* — not noise it could never predict, but the ambiguities an answer would actually settle — and remembers what comes back so it won't be surprised the same way twice. A machine that asks questions only about what confuses it is a surprisingly tidy consequence of "minimize free energy."

<figure class="chart">
<svg viewBox="0 0 680 320" role="img" aria-labelledby="ai-t">
<title id="ai-t">The active-inference loop: predict, observe, measure the precision-weighted error, then either update beliefs or ask the world and remember the answer</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
<marker id="c-arrowhead-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker>
</defs>
<text class="c-title" x="20" y="26">Minimize surprise — by changing your mind, or changing the world</text>
<rect class="c-box" x="24" y="70" width="120" height="56" rx="6"/>
<text class="c-val" x="84" y="94" text-anchor="middle">predict</text>
<text class="c-label-sm" x="84" y="112" text-anchor="middle">top-down guess</text>
<line class="c-arrow" x1="146" y1="98" x2="226" y2="98"/>
<rect class="c-box" x="228" y="70" width="120" height="56" rx="6"/>
<text class="c-val" x="288" y="94" text-anchor="middle">observe</text>
<text class="c-label-sm" x="288" y="112" text-anchor="middle">webcam feed</text>
<line class="c-arrow" x1="350" y1="98" x2="430" y2="98"/>
<rect class="c-box-accent c-fill-soft" x="432" y="70" width="224" height="56" rx="6"/>
<text class="c-val" x="544" y="94" text-anchor="middle">prediction error</text>
<text class="c-label-sm" x="544" y="112" text-anchor="middle">residual, weighted by precision (confidence)</text>
<line class="c-arrow" x1="544" y1="128" x2="544" y2="166"/>
<text class="c-label-sm" x="560" y="152">explained away?</text>
<rect class="c-box" x="404" y="168" width="252" height="48" rx="6"/>
<text class="c-val" x="530" y="190" text-anchor="middle">yes → update belief</text>
<text class="c-label-sm" x="530" y="208" text-anchor="middle">change your mind, loop again</text>
<rect class="c-box-accent c-fill-soft" x="404" y="232" width="252" height="64" rx="6"/>
<text class="c-val" x="530" y="256" text-anchor="middle">no → ask the world</text>
<text class="c-label-sm" x="530" y="276" text-anchor="middle">write a question; the answer becomes</text>
<text class="c-label-sm" x="530" y="290" text-anchor="middle">Lore — memory that reshapes next prediction</text>
<path class="c-arrow-muted" d="M404,192 C150,192 84,168 84,128"/>
<path class="c-arrow" d="M404,264 C40,300 20,180 28,128"/>
<text class="c-label-sm" x="150" y="252" text-anchor="middle">curiosity aimed only at what it can’t yet predict</text>
</svg>
<figcaption>When a layer can’t explain its surprise by updating, it acts: it asks a question, stores the answer as Lore, and won’t be surprised the same way twice. State what you expect; chase the residual when reality disagrees.</figcaption>
</figure>

## The unglamorous half: keeping four languages agreeing

None of that runs if the bytes don't line up. The belief state lives in shared memory so a fleet of small processes — sensor capture, the belief kernels, the agent, a TUI supervisor — can all read and write it without copying. That means the *exact* memory layout of a `BeliefSlot` has to be identical in four places at once: the Rust struct (`repr(C, align(64))`), the Metal kernel, the CUDA kernel, and the Python bridge. One field added in the wrong spot and every process downstream reads garbage.

My favorite line in the whole project is a test:

```rust
assert_eq!(size, 1088, "BeliefSlot size changed — update CUDA kernel struct and Python bridge");
```

It's a tripwire. The moment someone changes the belief layout, the build fails with a message telling them every other place they now have to fix. The same kernel ships in two dialects — Metal for Apple Silicon, CUDA for a Jetson — so the engine runs on a laptop and on a robot from one design.

## Why I built it

I spend most of my time on the opposite kind of system: contracts and protocols where the whole job is to make behavior *exactly* predictable and then prove it. This was the inverse — a thing whose entire purpose is to be surprised well, to treat the gap between expectation and observation not as a bug to eliminate but as the signal to learn from. But the instinct underneath is the same one I bring to [an audit](/blog/auditing-my-own-bridge/): state precisely what you expect, watch the residual when reality disagrees, and chase the surprise instead of looking away from it. Here I just wired that loop directly into 64 floats and a GPU.

*Code: the `qualia/` engine in [sensorforge](https://github.com/0xSoftBoi/sensorforge) — a robotics monorepo with iPhone/ARKit sensor capture, a Jetson voice assistant, and this active-inference core.*
