---
layout: post
title: "197 passing tests, four real-hardware bugs"
date: 2026-08-08 09:00:00 -0400
series: "Systems & infrastructure"
tags: [systems, networking, rdma, testing]
math: true
excerpt: "The unit suite was green. Then I gave the program an RDMA device. Real verbs and real sysfs state exposed four defects the 197 synthetic tests had not — including a tiebreak that selected the exact failure it existed to prevent, and a sysfs file that exists on no host on earth."
---

The unit suite was green. Then I gave the program an RDMA device.

The first real-device CI run of [roce-preflight](https://github.com/0xSoftBoi/roce-preflight) exposed **four defects** that **197 passing unit tests** had not. The useful lesson is narrower than "hardware testing is good":

> **Tests generated from the same mental model as the implementation can prove internal consistency while leaving the external boundary almost completely untested.**

* TOC
{:toc}

## The credibility gap

`roce-preflight` diagnoses whether a RoCE host is ready to bring queue pairs up. It reads GID tables, port state, MTU, and host configuration; it can also drive RC, UC, and UD queue pairs through the verbs lifecycle.

The original tests covered parsers, ranking logic, synthetic snapshots, and lifecycle decisions. They did **not** require an RDMA device. The fixtures were representations of Linux RDMA state written by the same project they were supposed to validate.

A green suite therefore established a real but narrower property: the implementation agreed with its own model.

## A job built to refuse to lie

GitHub's Ubuntu runner does not ship `rdma_rxe` for its Azure kernel, so the CI job compiles the upstream soft-RoCE module out-of-tree against the running kernel and creates `rxe0`. The load-bearing step is the one immediately after:

```yaml
- name: Assert we are NOT on the simulate backend
  # The whole point of this job. If backend detection falls back to
  # simulate, the real paths did not run and the job must fail.
  run: |
    python3 - <<'PY'
    from harness import backends
    resolved = backends.detect_backend("auto")
    print("resolved backend:", resolved)
    print("capabilities:", backends.capability_summary())
    assert resolved != backends.SIMULATE, (
        "FAILED: backend fell back to 'simulate' — the real RDMA paths were "
        "NOT exercised, so this job proves nothing."
    )
    PY
```

Without that assertion the job is worse than useless: it would go green by running the simulator and *report* that as hardware coverage. The same reasoning is why the workflow refuses the obvious fallback when `rxe` won't build:

> Deliberately NOT done: falling back to `siw` (Soft-iWARP) when rxe is unavailable. siw is TCP-based with no RoCEv2 UDP/4791, no GID table and no PFC/ECN/DSCP semantics — i.e. none of what this project diagnoses. A green siw run would be worse than no run, so this job fails loudly instead.

Soft-RoCE is not a performance proxy for a physical NIC. It *is* a real Linux RDMA device with real verbs, sysfs state, and a GID table — enough to test whether the software's assumptions about those interfaces survive contact with the kernel.

They did not.

## Defect 1: the MTU that was a link rate

`doctor` printed the port's active MTU. sysfs, on many kernels, exposes `rate` and no `active_mtu` at all. The code filled the gap from the field that *was* there, and produced this:

```text
active_mtu=2.5 Gb/sec (1X SDR)
```

A link rate, labelled as an MTU. Every fixture had an `active_mtu` key because the person writing the fixture knew MTUs exist, so nothing ever exercised the absent-field path. The fix is to refuse to invent the value:

```python
# MTU (informational). Only report a real MTU: sysfs exposes `rate`, not
# `active_mtu`, on many kernels, and printing the rate here labelled as an
# MTU produced nonsense like "active_mtu=2.5 Gb/sec (1X SDR)".
if snap.active_mtu:
    checks.append(Check("mtu", Status.PASS,
                        f"active_mtu={snap.active_mtu} (both ends must match; "
                        f"perftest falls back to the smaller of the two)"))
else:
    detail = "port MTU not exposed by sysfs; install rdma-core for `ibv_devinfo`"
    if snap.rate:
        detail += f" (link rate is {snap.rate})"
    checks.append(Check("mtu", Status.SKIP, detail))
```

`SKIP` is the honest status. The real MTU now comes from `ibv_devinfo` when that tool is present, and the field stays empty otherwise rather than being back-filled from an unrelated one.

## Defect 2: 1,024 entries for a table with three in it

A port's GID table is a fixed-size array — commonly 1,024 slots — of which a handful are populated and the rest read back as all zeros. The snapshot walked `gids/*` and kept everything, so a device with three real GIDs produced a 1,024-entry snapshot.

The fix is one filter, but the interesting part is the exception carved into it:

```python
def read_gid_table(device: str, port: int,
                   keep_zero_index: Optional[int] = None) -> List[GidEntry]:
    """Read a port's GID table from sysfs.

    Tables are commonly 1024 entries of which a handful are populated, so only
    the non-zero ones are returned -- plus ``keep_zero_index`` even when zero,
    because for the doctor that entry *is* the diagnosis.
    """
```

Drop the zeros — except the one index you were asked about, because "the entry you're looking at is empty" is the single most useful thing this tool can tell you. A filter that discarded it would have been correct and useless.

## Defect 3: the tiebreak that chose the failure it existed to prevent

This is the one worth the whole post.

RC, UC, and UD all failed with `ENETUNREACH` after the harness selected an unroutable `fe80::` link-local GID. There is a function whose entire purpose is to not do that:

```python
def rank(g):
    v2 = "v2" in (g.gtype or "").lower()
    return (v2, is_ipv4_mapped_gid(g.gid), -g.index)   # the original

return max(usable, key=rank).index
```

The reasoning was: prefer RoCEv2, then prefer an IPv4-mapped GID, then prefer a low index. "IPv4-mapped" was standing in for "routable." On a dual-stack fabric that proxy holds well enough. On an **IPv6-only** fabric it holds not at all, and the failure is mechanical.

`max` over a tuple is lexicographic. Write the table's entries as $$g_1,\dots,g_n$$ and the key as $$\bigl(v_2(g),\, m(g),\, -\mathrm{idx}(g)\bigr)$$. If every entry is RoCEv2 and none is IPv4-mapped — the ordinary case on an IPv6-only fabric — then $$v_2$$ and $$m$$ are constant across the table, the first two components cannot discriminate, and the order collapses to its last term:

$$
\arg\max_g \bigl(v_2, m, -\mathrm{idx}(g)\bigr) \;=\; \arg\max_g \bigl(-\mathrm{idx}(g)\bigr) \;=\; \arg\min_g \mathrm{idx}(g)
$$

The selector degenerates to "take the lowest index." And the lowest indices are exactly where the kernel puts the `fe80::` link-local entries. So on precisely the fabric where routability is hardest, the function picked the least routable entry available, deterministically, every time.

<figure class="chart">
<svg viewBox="0 0 680 330" role="img" aria-labelledby="gid-t">
<title id="gid-t">GID selection on an IPv6-only fabric: the original rank tuple ties and degenerates to lowest index</title>
<text class="c-title" x="20" y="22">GID table on an IPv6-only RoCEv2 fabric</text>
<text class="c-label-sm" x="20" y="41">every entry is v2, none is IPv4-mapped — so the first two rank terms are constant;</text>
<text class="c-label-sm" x="20" y="57">fe80:: is link-local and has no route, shaded cell = the entry each key selects</text>

<text class="c-label-sm" x="20" y="88">idx</text>
<text class="c-label-sm" x="62" y="88">GID</text>
<text class="c-label-sm" x="250" y="88">v2</text>
<text class="c-label-sm" x="300" y="88">ipv4-mapped</text>
<text class="c-label-sm" x="416" y="88">original key</text>
<text class="c-label-sm" x="546" y="88">fixed key</text>
<line class="c-axis" x1="20" y1="96" x2="660" y2="96"/>

<text class="c-val" x="20" y="108">0</text>
<text class="c-label-sm" x="62" y="108">fe80::5054:ff:fe12:3456</text>
<text class="c-label-sm" x="250" y="108">T</text>
<text class="c-label-sm" x="300" y="108">F</text>
<text class="c-label-sm" x="416" y="108">(T, F, 0)</text>
<text class="c-label-sm" x="546" y="108">(T, F, F, 0)</text>
<rect class="c-fill-soft" x="408" y="94" width="104" height="20" rx="3"/>

<text class="c-val" x="20" y="136">1</text>
<text class="c-label-sm" x="62" y="136">fe80::5054:ff:fe12:3457</text>
<text class="c-label-sm" x="250" y="136">T</text>
<text class="c-label-sm" x="300" y="136">F</text>
<text class="c-label-sm" x="416" y="136">(T, F, −1)</text>
<text class="c-label-sm" x="546" y="136">(T, F, F, −1)</text>

<text class="c-val" x="20" y="164">2</text>
<text class="c-label-sm" x="62" y="164">2001:db8::10</text>
<text class="c-label-sm" x="250" y="164">T</text>
<text class="c-label-sm" x="300" y="164">F</text>
<text class="c-label-sm" x="416" y="164">(T, F, −2)</text>
<text class="c-label-sm" x="546" y="164">(T, T, F, −2)</text>
<rect class="c-fill-soft" x="538" y="150" width="118" height="20" rx="3"/>

<text class="c-val" x="20" y="192">3</text>
<text class="c-label-sm" x="62" y="192">2001:db8::11</text>
<text class="c-label-sm" x="250" y="192">T</text>
<text class="c-label-sm" x="300" y="192">F</text>
<text class="c-label-sm" x="416" y="192">(T, F, −3)</text>
<text class="c-label-sm" x="546" y="192">(T, T, F, −3)</text>

<line class="c-grid" x1="20" y1="216" x2="660" y2="216"/>

<rect class="c-box-accent c-fill-soft" x="20" y="234" width="300" height="72" rx="8"/>
<text class="c-val" x="170" y="256" text-anchor="middle">original → max picks idx 0</text>
<text class="c-label-sm" x="170" y="276" text-anchor="middle">first two terms tie, so −idx decides</text>
<text class="c-label-sm" x="170" y="294" text-anchor="middle">RC / UC / UD fail: ENETUNREACH</text>

<rect class="c-box" x="352" y="234" width="308" height="72" rx="8"/>
<text class="c-val" x="506" y="256" text-anchor="middle">fixed → max picks idx 2</text>
<text class="c-label-sm" x="506" y="276" text-anchor="middle">routability is its own term, ranked above</text>
<text class="c-label-sm" x="506" y="294" text-anchor="middle">all three transports reach verify_data</text>
</svg>
<figcaption>The original key used “IPv4-mapped” as a proxy for “routable.” When no entry is IPv4-mapped the proxy carries no information, the comparison falls through to the index tiebreak, and index 0 is where the link-local entries live.</figcaption>
</figure>

The fix promotes routability to a term of its own, ranked above the proxy that was standing in for it:

```python
def rank(g):
    v2 = "v2" in (g.gtype or "").lower()
    # Routability is the property that actually matters, and it is NOT the
    # same as "IPv4-mapped". On an IPv6-only fabric there are no IPv4-mapped
    # GIDs, so ranking on that alone left every entry tied and the -index
    # tiebreak selected the LOWEST index -- exactly where the fe80::
    # link-local entries live. That picked the unroutable GID in precisely
    # the case this function exists to avoid.
    return (v2, not is_link_local_gid(g.gid), is_ipv4_mapped_gid(g.gid), -g.index)
```

No fixture would have caught this, because a fixture author writing "a plausible GID table" writes plausible GIDs — and the bug needs a table where every entry is *equally* plausible under the wrong metric. The kernel supplied that table without being asked.

## Defect 4: a report that contradicted itself

The doctor could print "GID table empty" beside a `PASS` containing a real GID. Two very different causes of an all-zeros entry at index $$i$$ had been collapsed into one message:

1. the netdev genuinely has no IPv6 link-local address, so the table really is empty; or
2. the table is **partitioned** — SR-IOV VFs, macvlan/IPVLAN sub-interfaces and network namespaces each get a slice of the shared port GID table, and the indices belonging to other slices read back as all-zeros.

In the wild the second is overwhelmingly the common one, and the old advice — regenerate your IPv6 link-local address — is actively wrong for it. Their netdev already has one; it just lives at a different index. Distinguishing the two takes one extra question, asked of the whole table rather than the one entry:

```python
# Is *anything* in this port's table usable? This distinguishes the two very
# different causes of an all-zeros entry, which used to be conflated.
alt = pick_gid_index(snap.gids)
```

Isolated unit scenarios never had to reconcile a per-index verdict against one live snapshot, so the contradiction had nowhere to show up.

## A fifth, from a different direction

The four above all came out of the real-device run. This one did not — a later vendor-portability audit caught it — and it is the most instructive of the set, because it is the same failure in a form no device could have surfaced either. `doctor` read a netdev's IPv6 address-generation mode from:

```text
/sys/class/net/<netdev>/addr_gen_mode
```

That file does not exist. Not on rxe, not on mlx5, not on any host or any vendor. `addr_gen_mode` is a **sysctl**, declared in `net/ipv6/addrconf.c`; `net/core/net-sysfs.c` exposes no such netdev attribute:

```python
def addr_gen_mode_path(netdev: str) -> str:
    """Path to a netdev's IPv6 ``addr_gen_mode``.

    It is a **sysctl** (declared in ``net/ipv6/addrconf.c``), not a netdev sysfs
    attribute — ``net/core/net-sysfs.c`` exposes no such file. Reading
    ``/sys/class/net/<nd>/addr_gen_mode`` silently returns nothing on every host
    and every vendor, which is what this project did until a vendor-portability
    audit caught it.
    """
    return f"/proc/sys/net/ipv6/conf/{netdev}/addr_gen_mode"
```

Note the failure mode: reading a nonexistent sysfs path returns *nothing*, not an error. The code got an empty string, treated it as "mode unknown," and carried on. There was no exception to catch, no assertion to trip, and no test that could have failed — the fixture supplied a value because the fixture author believed the file existed. A wrong belief about an external interface, encoded identically in the code and in the tests that check the code, is invisible to any number of those tests.

CI now asserts the absence directly, which is the only way this stays fixed:

```yaml
- name: Prove the addr_gen_mode path is the sysctl, not sysfs
  run: |
    nd=lo
    test ! -e "/sys/class/net/$nd/addr_gen_mode" \
      && echo "confirmed: /sys/class/net/$nd/addr_gen_mode does NOT exist"
    test -e "/proc/sys/net/ipv6/conf/$nd/addr_gen_mode"
```

## The best failure was the first fix

The first correction attempt passed the unit suite and changed nothing on the real device.

Hardware CI rejected it immediately.

That was more valuable than the initial bug discovery, because it turned real-device execution from a debugging trick into an **acceptance boundary**: a fix to an RDMA path is not accepted merely because the model says it should work.

After correction and re-verification, the active MTU reported as 4096 and matched perftest, the diagnosis agreed with the live GID state, the snapshot contained three entries, and RC/UC/UD all reached payload verification. The unit suite had grown to 208 tests.

But `197 → 208` is not the story.

**Synthetic state → independent device state** is the story.

## Three propositions, three kinds of tests

I now separate at least three questions in this kind of systems software:

1. **Logic:** does the algorithm behave correctly for a supplied state?
2. **Interface fidelity:** does that supplied state actually behave like the kernel/device interface?
3. **Physical behavior:** does traffic behave correctly on the target hardware and fabric?

Unit fixtures are excellent for the first. Soft-RoCE materially improves the second and exercises real verbs for part of the third.

It still cannot validate mlx5 firmware, PCIe behavior, SR-IOV topologies, switch configuration, PFC/ECN, NUMA placement, multi-host routing, or performance under sustained load. Those need different experiments.

Sort the five defects by that scheme and the pattern is not subtle. Defect 3 is the only genuine logic error — a wrong comparison, findable in principle by a sufficiently adversarial unit test. Defects 1, 2, 4 and the `addr_gen_mode` path are all **interface-fidelity** failures: the code's belief about what Linux exposes was wrong, and the fixtures encoded the same wrong belief. Four of the five sit in the one category unit tests are structurally unable to reach — and the fifth needed no hardware at all, only someone checking the claim against the kernel source.

## The strongest counterargument

These failures can be described as ordinary mocking mistakes. Better fixtures could reproduce every one **after the fact**.

That is true — and exactly why the independent boundary matters. Before the failures were known, the implementation and fixtures shared enough assumptions to be wrong in the same direction. The `addr_gen_mode` path is the clean demonstration: to write a fixture that catches it, you must already know the file does not exist, and if you knew that you would not have written the bug.

A mock is strongest when reproducing already-understood behavior quickly and deterministically. It is weakest when asked to discover that your model of an external system is wrong.

## What changed in the project

The project now treats evidence as tiers instead of collapsing everything into "tested."

- unit tests protect deterministic logic;
- the real-device job proves it did not silently fall back to simulation;
- inspectors read actual sysfs state;
- QP failures expose the underlying verbs error;
- real traffic goes through `ib_write_bw`;
- synthetic performance numbers are labeled synthetic rather than qualification data.

That separation is partly UX. Mostly it is epistemic hygiene. A diagnostic tool should be unusually explicit about which parts of its own diagnosis have touched reality.

## The rule I kept

The lesson is not "replace mocks with hardware." Fast synthetic layers are what make iteration possible.

The rule is:

> **When the external system is part of the claim, make the external system part of the test.**

And its corollary, which the `addr_gen_mode` path taught me and defect 3 confirmed: the assumptions most worth testing are the ones so obvious you wrote them into the fixture without noticing. A device finds some of those for you. The rest you find by reading the interface's own source instead of your memory of it.

### Primary evidence

- [roce-preflight](https://github.com/0xSoftBoi/roce-preflight)
- [real-device Soft-RoCE CI workflow](https://github.com/0xSoftBoi/roce-preflight/blob/main/.github/workflows/soft-roce.yml)
- [`harness/doctor.py`](https://github.com/0xSoftBoi/roce-preflight/blob/main/harness/doctor.py) — every code excerpt above is quoted from this file or the workflow

**Evidence boundary:** the four defects and post-fix payload verification are observations from the project's real-device path; the `addr_gen_mode` path error was found separately by a vendor-portability audit and is not part of the title's count. Every code block is quoted verbatim from the repository at `main`; the `rank` tuple labelled *original* is reconstructed from the fix's own description of what it replaced, and is derived, not quoted. The lexicographic argument is derived from Python's tuple ordering. The causal explanation for why fixtures missed each defect is a postmortem interpretation. Soft-RoCE on one hosted Linux machine is not evidence of physical-NIC or production-fabric performance.
