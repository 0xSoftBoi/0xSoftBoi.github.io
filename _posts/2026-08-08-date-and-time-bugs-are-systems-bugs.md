---
layout: post
title: "Date and time bugs are systems bugs"
date: 2026-08-08 09:50:00 -0400
series: "Systems & infrastructure"
tags: [rust, systems, coreutils, compatibility]
excerpt: "Four merged uutils fixes—timezone re-zoning, negative epoch flooring, AM/PM grammar, and a two-letter timezone alias—show why date/time correctness is compatibility engineering, not parsing trivia."
---

Four of my smallest upstream patches changed how I think about systems correctness.

One fixed timezone re-zoning. One changed how a negative fractional Unix timestamp becomes an integer second. One repaired AM/PM parsing after a sub-parser succeeded too early. One added the two-letter timezone alias `UT`.

None is algorithmically impressive. All are observable contracts that other software can depend on.

> **Date and time bugs are systems bugs because the hard part is not representing time. It is preserving the conventions around that representation.**

* TOC
{:toc}

## The timestamp was right and the output was wrong

In uutils `date`, one parsing path treated a trailing timezone abbreviation as both the timezone of the input **and** the timezone in which the result should be displayed.

Under `TZ=UTC`, parsing an input described in EST could preserve the `-05` presentation instead of converting the instant back into the caller's UTC output zone.

Both forms can denote the same instant. Only one matches GNU `date`'s observable behavior.

The bug lived in a boundary the internal timestamp representation does not know about:

- **interpretation:** what timezone did the input string use?
- **presentation:** what timezone should the resulting instant be rendered in?

[coreutils #12327](https://github.com/uutils/coreutils/pull/12327) restored that separation.

## Negative time exposes rounding policy

Another patch began with a much smaller number: `@-1.5`.

A helper truncated fractional epoch seconds toward zero, producing `-1`. GNU-compatible behavior requires floor semantics, producing `-2`.

For positive values the two operations often look interchangeable. Before the Unix epoch they differ by a full second.

[parse_datetime #285](https://github.com/uutils/parse_datetime/pull/285) added an explicit epoch-second helper with floor behavior and normalized fractional nanoseconds, plus regression cases covering the negative side of zero.

The implementation lesson is broader than timestamps. Whenever a continuous value crosses into an integer representation, **rounding is policy**. If the policy is not named, the language/runtime default can quietly become the product behavior.

## A parser can succeed too early

The combined date-time parser failed on inputs such as:

```text
2024-06-15 12:00 PM
```

A 24-hour ISO time parser could successfully consume the `12:00` prefix and leave `PM` behind. Locally, the parser succeeded. Globally, the grammar failed.

[parse_datetime #284](https://github.com/uutils/parse_datetime/pull/284) used the broader time parser in that composition so AM/PM syntax is tried before falling back to the narrower form.

This is a parser-combinator failure mode I like because it generalizes so cleanly:

> **A successful sub-parse can be the reason the whole parse is wrong.**

Greedy local success is not the same thing as consuming a valid sentence in the language.

## Sometimes compatibility really is one missing string

GNU `date -d` accepts bare `UT` as Universal Time. The parser already normalized UTC and GMT but omitted `ut` from its abbreviation table.

[parse_datetime #287](https://github.com/uutils/parse_datetime/pull/287) is basically the smallest kind of compatibility patch: teach the parser one existing word in the reference language.

The line count is trivial. The contract is not. A script written against GNU behavior does not care how intellectually interesting the missing alias was.

## Why these belong in one article

The four bugs sit at different layers:

| Layer | Failure |
|---|---|
| representation → presentation | input timezone leaked into output timezone |
| real → integer | truncation used where compatibility required floor |
| parser composition | a prefix parser succeeded before AM/PM could be consumed |
| language surface | a reference implementation's accepted alias was missing |

They share one property: the implementation can be internally coherent and still disagree with the external semantics users expect.

That is why compatibility work is systems work. The “system” includes years of scripts, shell behavior, documentation, standards, and human expectations—not just the timestamp object in memory.

## The strongest counterargument

Reproducing GNU quirks can fossilize historical design choices. A new date/time API might reasonably choose clearer grammar, explicit zones, or different rounding semantics.

Agreed. Compatibility software has a different contract from greenfield software.

For a new API, the question is:

> What semantics should we choose?

For a coreutils rewrite, the question is:

> What semantics have users already been promised?

The second question makes edge cases first-class.

## The habit I kept

When touching compatibility code now, I look for boundaries where an implementation choice can masquerade as a neutral representation choice:

- timezone used to parse vs timezone used to render;
- truncation vs floor vs round-to-nearest;
- greedy prefix parse vs whole-input grammar;
- canonical name vs accepted alias;
- platform convention vs library convention.

Those are exactly the places where “looks right” tests miss production behavior.

> **In compatibility software, an edge case is often somebody else's interface.**

### Primary evidence

- [uutils/coreutils #12327](https://github.com/uutils/coreutils/pull/12327) — GNU `date` timezone re-zoning.
- [uutils/parse_datetime #284](https://github.com/uutils/parse_datetime/pull/284) — combined AM/PM parsing.
- [uutils/parse_datetime #285](https://github.com/uutils/parse_datetime/pull/285) — negative fractional epoch floor semantics.
- [uutils/parse_datetime #287](https://github.com/uutils/parse_datetime/pull/287) — `UT` timezone compatibility.

**Evidence boundary:** these are four specific merged compatibility fixes, not a claim that uutils date/time behavior is completely GNU-compatible.
