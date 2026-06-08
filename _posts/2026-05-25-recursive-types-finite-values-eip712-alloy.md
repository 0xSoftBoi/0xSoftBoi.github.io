---
layout: post
title: "Recursive types, finite values: an EIP-712 bug in alloy"
date: 2026-05-25
tags: [rust, ethereum, eip-712]
excerpt: "EIP-712 explicitly supports recursive struct types — but alloy refused to canonicalize one. The fix turned on a distinction the spec makes and the code didn't: a type definition can be recursive even though every concrete value of it must be a finite tree."
---

EIP-712 is the standard behind almost every "sign this" prompt your wallet shows you — it takes a structured message, hashes it deterministically, and lets a contract verify the signature on-chain. The deterministic part hinges on *canonicalization*: turning a type like `Mail(address from,address to,string contents)` into exactly one agreed-upon string, so the signer and the verifier hash the same bytes.

Here's a type that is perfectly legal under EIP-712, and that [alloy](https://github.com/alloy-rs/core) — the Ethereum Rust library underneath Foundry and Reth — refused to canonicalize:

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

This is a small diff. But it's the kind of bug I go looking for: it lived in the gap between two rules that are each correct on their own — *"reject cyclic types"* and *"the spec allows recursion"* — where neither side's author was wrong, and the seam between them was never tested. Signature and verification bugs almost always hide in exactly that kind of seam.

And EIP-712 canonicalization isn't a backwater. It's on the path of every typed-data signature that flows through the Rust Ethereum stack — every Foundry script that signs a permit, every tool built on alloy that verifies one. A type the spec says is valid should not be un-signable because of how the library happened to find its primary component.

*Fixed in [alloy-rs/core#1105](https://github.com/alloy-rs/core/pull/1105), closing [#1103](https://github.com/alloy-rs/core/issues/1103).*
