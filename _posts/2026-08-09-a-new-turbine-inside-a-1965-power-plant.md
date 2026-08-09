---
layout: post
title: "A new turbine inside a 1965 power plant"
date: 2026-08-09 11:30:00 -0400
series: "Systems & infrastructure"
tags: [energy, power-systems, brownfield, scada, hardware]
image: /assets/darkhan-scada.jpeg
hero: /assets/darkhan-scada.jpeg
excerpt: "Darkhan did not convert a 1965 generator into a modern one. It added a fifth 35 MW turbine-generator to a 48 MW legacy plant—and the control-room screen shows why brownfield engineering is mostly interface work."
---

At first glance, this control-room screen looks like a solved problem: red
high-voltage buses, blue generator buses, green arrows, and a clean **50.01 Hz**.

The interesting part is not that the diagram is old. It is that old and new
equipment are operating on the same diagram.

<figure class="chart">
  <img src="{{ '/assets/darkhan-scada.jpeg' | relative_url }}" alt="Darkhan Thermal Power Plant SCADA power-balance screen photographed on January 22, 2022, showing five turbine-generators, station auxiliary consumption, and distribution power">
  <figcaption>Darkhan Thermal Power Plant power-balance screen, January 22, 2022 at 13:39. The arithmetic below is transcribed from this single operating snapshot; it is not an annual performance result.</figcaption>
</figure>

The screen is from Darkhan Thermal Power Plant in Mongolia. The station's first
equipment entered service in 1965. But the large `TG-5` value near the lower
left—**31.41 MW**—belongs to a fifth, much newer machine.

That distinction matters. Darkhan did not somehow convert one 1965 generator
into a modern 35 MW generator. It expanded a legacy plant around it.

> **The alpha is the interface tax: the new component can be excellent while the inherited system still decides how much value reaches the boundary.**

* TOC
{:toc}

## It was an addition, not a conversion

Mongolia's Energy Regulatory Commission says the plant's foundations were laid
in 1963 and its first main equipment was commissioned on October 2, 1965. In
October 2019, the station inaugurated a **new 35 MW turbine-generator** as its
third major modernization.

The turbine manufacturer is even more explicit: Kaluga Turbine Works calls it
the **fifth power unit**. Its account says the existing plant had four 12 MW
turbines totaling 48 MW and that the additional machine increased capacity by
35 MW.

So the nameplate arithmetic is:

| Before | Added | After |
|---:|---:|---:|
| 4 × 12 MW = 48 MW | 35 MW | 83 MW |

That is a 73% increase in installed electrical capacity.

[KfW's project record](https://www.kfw-entwicklungsbank.de/ipfz/Projektdatenbank/Programm-Energieeffizienz-20596.htm)
describes financing for an extension of the turbine hall, a new 35 MW steam
turbine, and associated auxiliary equipment. The
[ERC announcement](https://erc.gov.mn/mn/news/355) calls the result a 35 MW
expansion. The [OEM account](https://paoktz.ru/en/press/news/turbine-manufactured-by-kaluga-turbine-works-was-put-into-operation-in-mongolia/)
calls it unit five.

“Modernization” is therefore the right word for the station project. It is the
wrong mental model if it suggests that every inherited subsystem became new.
The published scope establishes a new turbine, generator, hall extension, and
auxiliaries. It does not establish wholesale replacement of the plant's steam
supply, coal and water systems, district-heating duty, switchyard, protection,
or operating organization.

## What the screen actually says

The bottom-left summary and five generator tiles make the operating point
reconstructable:

| Screen reading | MW |
|---|---:|
| TG-1 | 8.79 |
| TG-2 | 11.17 |
| TG-3 | 8.34 |
| TG-4 | 10.80 |
| TG-5, the new unit | 31.41 |
| **Sum of generator tiles** | **70.51** |
| Displayed gross generation | 70.52 |
| Station internal consumption | 9.16 |
| Displayed distribution | 61.15 |

The tile sum and displayed gross value differ by only 0.01 MW. From that one
instant we can derive four useful facts:

1. **The station was producing about 85.0% of its 83 MW installed capacity.**
2. **TG-5 was at about 89.7% of its 35 MW nameplate.**
3. **The new unit supplied 44.5% of the station's gross generation.**
4. **Internal consumption was about 13.0% of gross generation.**

The four legacy units together produced 39.10 MW, or about 81.5% of their
combined 48 MW nameplate. This was not a scene where the new machine ran while
the old plant sat idle. Both generations of equipment were carrying the load.

Gross generation minus displayed internal consumption is 61.36 MW, 0.21 MW
above the displayed distribution value. That small residual could be rounding,
losses, timing, or a metering-boundary difference. A photograph cannot tell us
which—and pretending otherwise would turn a good observation into a fake result.

What it does show is the right unit of value: not generator nameplate, but power
that survives station service and reaches the distribution boundary.

## The difficult sentence in the retrofit record

A separate Darkhan automation case study contains the most important line in
the project history:

> Additional equipment was needed for the increased capacity, and the existing automation system was too old to interface with it.

The [SATEC case study](https://www.satec-global.com/wp-content/uploads/2023/04/Case-Study-Power-Plant-Automation-February2017.pdf)
says the prior Russian fault-recording and automation equipment had been
commissioned in 2002. The retrofit did not wave that boundary away. It built a
new observability and control layer around it:

- 39 power-quality analyzers;
- three Ethernet switches, a server, five cabinets, and a satellite-synchronized clock;
- 380 analog signals and 624 status signals;
- 88 calculated parameters and 420 triggered alerts;
- one-second monitoring and dispatch updates;
- common fault waveforms, event history, metering, and mimic diagrams.

That is 1,512 measurements, states, derived values, and alerts before counting
the thousands of parameters available inside the analyzers themselves.

This is what brownfield modernization often looks like in practice. The visible
artifact is a turbine. The integration work is signal definitions, current
transformers, time synchronization, protocols, alarm semantics, operator
screens, fault behavior, and deciding which system owns the truth when readings
disagree.

The screen in the photograph is therefore more than presentation. It is part of
the machinery that lets a plant with two generations of equipment be operated
as one system.

## Capacity arrived through a project, not a purchase order

The upgrade also took years rather than one equipment-delivery cycle. A 2017
report said the expansion had been underway since 2012 and that its original
€16–17 million estimate was insufficient. KfW now records a **€20 million German
financing contribution** and marks the program complete.

The exact financing history is less important than the pattern: brownfield
work must fit outages, civil works, procurement, foreign suppliers, spare-parts
strategy, commissioning, and the operating obligation of a plant that cannot
simply disappear while being upgraded.

Kaluga's 2019 account says the parties were already discussing replacement of
two exhausted older turbines and how common equipment could simplify future
maintenance and spares. Commissioning one new unit did not end the legacy
problem. It changed the next version of it.

## Why 35 MW mattered beyond Darkhan

The national operating context makes the capacity more consequential. The
[Energy Regulatory Commission's 2022 review](https://erc.gov.mn/en/news/757)
says Mongolia imported **20.9%** of the electricity it consumed that year. It
also says combined heat-and-power plants were operating at full capacity during
the central grid's winter peak **without backup equipment**.

A well-loaded 31.41 MW machine inside an 83 MW plant is not a demo in that
system. It is material capacity.

But material does not mean independent. TG-5 still needs the plant around it:
steam, cooling, excitation, protection, station service, dispatch, operators,
and a path through the 6 kV, 35 kV, and 110 kV network shown on the screen.

## The same pattern from grid to gate

This is the connection to my power-electronics and chip work. The physics and
scale change; the architecture question does not.

| Layer | New component | Inherited system that can erase the gain | Evidence that matters |
|---|---|---|---|
| Darkhan | 35 MW turbine-generator | steam, auxiliaries, controls, protection, switchyard, district heat | gross-to-net power, faults, availability, synchronized telemetry |
| [VoltForge](https://github.com/0xSoftBoi/GaN-optimization-) | optimized GaN/SiC converter stage | magnetics, EMI, loop stability, cooling, protection, calibration | measured efficiency curves, transients, thermal and compliance tests |
| LCA-1 | lattice-cryptography arithmetic engine | bridge protocol, host transfers, memory, board power, thermals, security | real-backend workload, differential tests, synthesis, joules per completed operation |

I have now made that last connection executable. LCA-1 defines a versioned
time-domain trace with `idle`, `kem`, `dsa`, `dma`, `zeroize`, and `fault`
states. VoltForge's
[workload-power integration](https://github.com/0xSoftBoi/GaN-optimization-/pull/3)
parses the trace, requires measured watts by default, integrates energy, keeps
peak and slew behavior, and turns the peak load into a converter design input.

It deliberately does not collapse the trace into a made-up TDP. A cryptographic
operation is a burst, and the board must survive its load step, not only its
average.

The underlying bridge workload is pinned to the public
[Entanglement Transfer Protocol](https://github.com/0xSoftBoi/Entanglement-Transfer-Protocol):
ML-KEM-768 seals the lattice key; ML-DSA-65 authenticates commitments and relay
envelopes. LCA-1 itself remains private while the architecture is pre-FPGA, so I
am not presenting unfinished RTL as a public chip claim.

## Where the alpha actually is

The obvious story is “old coal plant gets a bigger turbine.”

The more reusable story is this:

> **A component upgrade creates value only after every inherited interface agrees to carry it.**

That suggests three engineering bets:

1. **Observability is part of capacity.** If old and new systems cannot share
   time, measurements, alarms, and fault records, installed hardware is harder
   to operate and trust.
2. **The useful metric lives at the system boundary.** Darkhan's screen separates
   70.52 MW gross from 61.15 MW distributed. A chip project should likewise
   report completed bridge operations and joules at the board, not isolated
   butterfly throughput.
3. **Interfaces are products.** The trace between LCA-1 and VoltForge is not
   glue. It is the contract that turns a workload into regulator, decoupling,
   thermal, and protection requirements.

The new turbine is impressive. The durable alpha is learning to price the
system it inherits.

## The strongest counterargument

A thermal power plant is not a chip, and a plant retrofit is not a semiconductor
design flow. Their safety regimes, economics, time constants, and failure modes
are radically different.

The analogy should not be stretched past one architectural claim: **local
component performance is not end-to-end system performance**. The evidence
required at each layer remains specific to that layer.

## Evidence boundary

The operating calculations above come from one photographed screen at one
instant. They do not establish annual generation, heat output, efficiency,
availability, emissions, or causal performance improvement. Translations of
the on-screen Mongolian labels are functional descriptions, not vendor-defined
metering terminology. The automation details come from a vendor case study and
should be treated as implementation evidence, not an independent reliability
assessment.

### Sources

- [Mongolia ERC: 35 MW Darkhan expansion commissioned, October 2019](https://erc.gov.mn/mn/news/355)
- [KfW: Energy Efficiency Program project record](https://www.kfw-entwicklungsbank.de/ipfz/Projektdatenbank/Programm-Energieeffizienz-20596.htm)
- [Kaluga Turbine Works: fifth Darkhan power unit](https://paoktz.ru/en/press/news/turbine-manufactured-by-kaluga-turbine-works-was-put-into-operation-in-mongolia/)
- [SATEC: Darkhan power-plant automation retrofit](https://www.satec-global.com/wp-content/uploads/2023/04/Case-Study-Power-Plant-Automation-February2017.pdf)
- [Mongolia ERC: 2022 energy-sector review](https://erc.gov.mn/en/news/757)
- [2017 report on the expansion's financing and schedule](https://mongolia.gogo.mn/r/movle)
