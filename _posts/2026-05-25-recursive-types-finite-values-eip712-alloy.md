---
layout: post
title: "Recursive types, finite values: an EIP-712 bug in alloy"
date: 2026-05-25
series: "Systems & infrastructure"
tags: [rust, ethereum, eip-712]
image: /assets/og/recursive-types-finite-values-eip712-alloy.png
excerpt: "EIP-712 explicitly supports recursive struct types — but alloy refused to canonicalize one. The fix turned on a distinction the spec makes and the code didn't: a type definition can be recursive even though every concrete value of it must be a finite tree."
---

EIP-712 says, in so many words, that it supports recursive struct types. [alloy](https://github.com/alloy-rs/core) — the Ethereum Rust library under Foundry and Reth — refused to canonicalize one. Neither side was being careless: the spec is explicit, and a library that rejects cyclic types is doing exactly what it should. The bug lived in the inch between those two facts.

EIP-712 is the standard behind almost every "sign this" prompt your wallet shows you: it takes a structured message, hashes it deterministically, and lets a contract verify the signature on-chain. The deterministic part hinges on *canonicalization* — turning a type like `Mail(address from,address to,string contents)` into exactly one agreed-upon string, so the signer and the verifier hash the same bytes. (What makes it *canonical*: when a struct references other structs, those referenced types are collected, sorted by name, and appended — exactly one legal ordering, so exactly one string per type.) Here's a type that is perfectly legal under EIP-712, and that alloy rejected anyway:

```rust
#[test]
fn canonicalize_self_referential_type() {
    // Per EIP-712: "The standard supports recursive struct types."
    let input = "Node(uint256 value,Node[] children)";
    let encoded = EncodeType::parse(input).unwrap();
    assert_eq!(encoded.canonicalize(), Ok(input.to_string()));
}
```

A `Node` has a value and some child `Node`s — a tree. On `main`, that test failed:

```
left:  Err(MissingType("primary component"))
right: Ok("Node(uint256 value,Node[] children)")
```

The parser accepted the string without complaint. The rejection happened later, in `canonicalize`.

## The distinction the spec makes and the code didn't

The [EIP-712 spec](https://eips.ethereum.org/EIPS/eip-712) says, plainly:

> The standard supports recursive struct types.

And then, in the rationale:

> The current standard is optimized for tree-like data structures and undefined for cyclical data structures.

Read those together and the whole bug falls out. A *recursive type definition* is allowed — it describes a possibly-self-referencing shape. A *cyclical data instance* — a runtime value that loops back on itself — is undefined; every concrete value still has to be a finite tree. `Node` the type can mention `Node`. A particular `Node` value cannot contain itself; it just contains some children, which eventually bottom out.

Canonicalization operates on the *type definition*. So it has to accept self-reference. The code conflated the two: anything that pointed at itself was treated as a cycle, and cycles were rejected wholesale. To find the "primary" type to canonicalize, the resolver leaned on its cycle/dependency machinery — and a self-referential type registers as depending on itself, so the lookup came back empty and bailed with `MissingType("primary component")` before it ever produced a string.

<figure class="chart">
<svg viewBox="0 0 680 300" role="img" aria-labelledby="ei-t">
<title id="ei-t">An EIP-712 type definition may reference itself, but every concrete value of it must be a finite tree</title>
<defs>
<marker id="c-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
<marker id="c-arrowhead-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker>
</defs>
<text class="c-title" x="20" y="26">Recursive type, finite value</text>
<line class="c-grid" x1="340" y1="50" x2="340" y2="280"/>
<text class="c-val" x="20" y="64">type definition</text>
<text class="c-label-sm" x="20" y="82">canonicalize · type-level · permissive</text>
<path class="c-arrow" d="M120,106 C120,90 250,90 250,106"/>
<rect class="c-box-accent c-fill-soft" x="36" y="110" width="276" height="50" rx="6"/>
<text class="c-val" x="174" y="140" text-anchor="middle">Node(uint256 value, Node[] children)</text>
<text class="c-label" x="36" y="196">self-reference ✓ allowed</text>
<text class="c-label-sm" x="36" y="216">it describes a possibly-self-referencing shape</text>
<text class="c-val" x="360" y="64">concrete value</text>
<text class="c-label-sm" x="360" y="82">resolve · builds a value · strict</text>
<circle class="c-dot-hi" cx="470" cy="116" r="8"/>
<line class="c-line" x1="470" y1="124" x2="430" y2="150"/>
<line class="c-line" x1="470" y1="124" x2="510" y2="150"/>
<circle class="c-dot" cx="430" cy="158" r="7"/>
<circle class="c-dot" cx="510" cy="158" r="7"/>
<line class="c-line" x1="430" y1="165" x2="430" y2="186"/>
<line class="c-line" x1="510" y1="165" x2="510" y2="186"/>
<circle class="c-dot" cx="430" cy="192" r="5"/>
<circle class="c-dot" cx="510" cy="192" r="5"/>
<text class="c-label" x="558" y="120">finite tree ✓</text>
<text class="c-label-sm" x="558" y="138">bottoms out</text>
<text class="c-label" x="360" y="244">a value that loops back on itself ✗</text>
<text class="c-label-sm" x="360" y="264">undefined — the strict check still rejects a true cycle (A→B→A)</text>
</svg>
<figcaption>The bug lived in the seam between two correct rules — “reject cyclic types” and “the spec allows recursion.” The fix splits one cycle check into a permissive (type-level) and a strict (value-level) pass.</figcaption>
</figure>

## The fix: two cycle checks, not one

The resolver already had one cycle detector. The fix splits it in two, keyed on *what the caller is going to build*:

- `Resolver::resolve` materializes a concrete `DynSolType` — an actual value shape. That genuinely cannot represent recursion (you can't build an infinitely-nested value), so it keeps the **strict** check and still rejects any self-reference.
- `Resolver::linearize` / `encode_type` only produce the `encodeType` *string*. That's pure type-level work, so it gets a **permissive** check that allows a type to reference itself.

Concretely, `detect_cycle_inner` gained an `allow_self_refs` flag, and the permissive path skips the self-edge instead of treating it as a cycle:

```rust
// EIP-712 permits recursive struct types, so a self-edge is
// not treated as a cycle when `allow_self_refs` is enabled.
if allow_self_refs && edge == type_name {
    continue;
}
```

Crucially, it only forgives a type pointing at *itself*. A cycle between two *distinct* types — `A` depends on `B` depends on `A` — is still a `CircularDependency` error, because that isn't a recursive struct, it's a malformed type graph.

The second half lived in the parser. `canonicalize` had been eagerly calling `resolver.resolve(primary)?` as a validation step before encoding — which is exactly the path that can't represent recursion. Dropping that pre-check and going straight to `encode_type` (which now walks the permissive `linearize`) lets the recursive type through while still surfacing genuine missing-type and circular-dependency errors:

```rust
// We intentionally do not call `Resolver::resolve` here, because that
// builds a `DynSolType` and therefore cannot represent recursive struct
// types (which EIP-712 explicitly permits).
resolver.encode_type(primary)
```

A second regression test covers the case that also has a real dependency — `Tree(Leaf root,Tree[] subtrees)Leaf(uint256 value)` — to make sure the recursive primary type still pulls in `Leaf` and orders it correctly.

## Why I care about a missing primary component

This is a small diff. But it's the kind of bug I go looking for. Two rules, each correct alone — *"reject cyclic types"* and *"the spec allows recursion"* — and no test ever stood in the gap where they disagree. That gap is where signature and verification bugs almost always live: [not in either rule, but in the join nobody wrote down](/blog/the-model-reads-not-it-just-cant-use-it/).

And EIP-712 canonicalization isn't a backwater. It's on the path of every typed-data signature that flows through the Rust Ethereum stack — every Foundry script that signs a permit, every tool built on alloy that verifies one. A type the spec says is valid should not be un-signable because of how the library happened to find its primary component.

*Fixed in [alloy-rs/core#1105](https://github.com/alloy-rs/core/pull/1105), closing [#1103](https://github.com/alloy-rs/core/issues/1103).*
