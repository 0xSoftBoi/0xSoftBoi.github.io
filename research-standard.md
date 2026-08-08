---
layout: default
title: "Research standard — Tsolmondorj Natsagdorj"
permalink: /research-standard/
---

<section class="about">
<h1>Research standard</h1>
<p class="lede">Make every pass harder to fool.</p>

<p>This is the publication loop behind the research notes on this site. A polished argument can still be wrong; presentation quality does not get to launder weak evidence.</p>

<h2>Five gates</h2>

<h3>1. Provenance</h3>
<p>Every consequential factual claim should trace to a primary artifact where practical: source code, raw measurements, specifications, filings, papers, benchmark prompts, traces, or experiment outputs. Secondary sources provide context, not the foundation.</p>

<h3>2. Quantitative validity</h3>
<p>A number should expose its denominator, units, comparison set, measurement window, assumptions, and uncertainty or sensitivity when material. A single seed is not a variance estimate. A target is not a measurement.</p>

<h3>3. Adversarial thesis</h3>
<p>Write the strongest rival explanation as if its author will review the piece. If it explains the evidence equally well, narrow the conclusion instead of writing around the ambiguity.</p>

<h3>4. Citation integrity</h3>
<p>A source must support the sentence adjacent to it. Facts, derivations, estimates, and engineering targets are different evidence classes and should remain visibly different.</p>

<h3>5. Reproducibility</h3>
<p>Link code, data, queries, configs, benchmark prompts, calculations, hardware logs, or exact commands where practical. If reproduction is impossible, state the missing dependency rather than implying it exists.</p>

<h2>Evidence classes</h2>
<table>
<thead><tr><th>Class</th><th>Meaning</th></tr></thead>
<tbody>
<tr><td><strong>Observed</strong></td><td>Measured directly in an experiment, system, trace, filing, source artifact, or dataset.</td></tr>
<tr><td><strong>Derived</strong></td><td>Calculated from observed inputs with an explicit method.</td></tr>
<tr><td><strong>Estimated</strong></td><td>Model-dependent or inferred; assumptions must be exposed.</td></tr>
<tr><td><strong>Target</strong></td><td>A design requirement, future gate, or intended performance level.</td></tr>
</tbody>
</table>

<h2>The loop</h2>
<ol>
<li>Choose a decision question, not a topic.</li>
<li>Harvest primary artifacts before drafting prose.</li>
<li>Lock one falsifiable claim.</li>
<li>Build an evidence ledger.</li>
<li>Run quantitative/sensitivity checks the claim depends on.</li>
<li>Draft results before rhetoric.</li>
<li>Red-team the thesis with the strongest rival explanation.</li>
<li>Add visuals only when they encode evidence or mechanism.</li>
<li>Audit every citation against the exact adjacent claim.</li>
<li>Compress the prose until the headline is no stronger than the body.</li>
<li>Publish with limitations and an update condition.</li>
<li>Reopen the piece when new evidence arrives.</li>
</ol>

<h2>Failure routes backward</h2>
<p>If provenance is weak, return to sourcing. If a sensitivity check changes the conclusion, return to the claim. If the rival explanation survives, narrow the thesis. If the required experiment is paid or unavailable, either find a zero-cost substitute, publish a bounded note, or park the stronger claim.</p>

<p>The most important rule is the last one:</p>
<blockquote><p><strong>The conclusion is allowed to get weaker.</strong></p></blockquote>

<p class="more"><a href="{{ '/blog/correctness-under-hidden-failure-modes/' | relative_url }}">Engineering thesis →</a> · <a href="{{ '/research/' | relative_url }}">Research programs →</a> · <a href="{{ '/blog/' | relative_url }}">Writing →</a></p>
</section>
