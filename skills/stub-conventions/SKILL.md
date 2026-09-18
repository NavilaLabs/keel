---
name: stub-conventions
description: Defines what a stub is per language (Rust trait, PHP interface, Dart abstract class) and what belongs in its contract. Use at step 7.2 when freezing contracts, and at step 8 when implementing against them.
---

# Stub conventions

A stub is a **contract without an implementation**, written at step 7.2 and
frozen from then on. Changing one is a jump back to step 7, not an
implementation detail.

## What a stub is, per language

| Language | Stub |
| --- | --- |
| Rust | `trait` with method signatures, no default bodies |
| PHP | `interface`, or `abstract class` where shared state is unavoidable |
| Dart | `abstract class` / `abstract interface class` |
| TypeScript | `interface` or `type` |

## Put it in its own file

The `stub-lock` hook locks the file that declares the contract. Contract and
implementation in one file means the file cannot be locked, and the stub has
to be marked `shared_file: true` in `state.json` - which downgrades the hook
from blocking to warning.

So: declaration in its own file wherever the language allows it. This is not
style preference, it is what makes the freeze enforceable rather than
advisory.

## The contract is the doc comment

The signature alone does not say what the thing guarantees. Everything a
caller needs to rely on goes in the doc comment, because the diagram will not
carry it and the implementation must not invent it:

- **Error behaviour** - what fails, how it is reported, what is never thrown
  or panicked
- **Idempotency** - safe to call twice or not
- **Invariants** - what holds before and after
- **Ownership** - who owns what after the call returns
- **Concurrency** - safe to call from several threads or not

```rust
/// Validates an order and persists it.
///
/// Returns `ValidationError` for malformed input; never panics on
/// caller-supplied data. Not idempotent: calling twice creates two orders.
/// The returned `Order` owns its line items.
fn submit(&self, draft: OrderDraft) -> Result<Order, ValidationError>;
```

A doc comment that only restates the signature in prose is not a contract.
"Submits an order" adds nothing the reader could not see.

## What does not go in a stub

No implementation, not even an obvious one-liner. No `todo!()` with logic
sketched around it. The stub is reviewed at the step 7 consultation, and
anything beyond the contract distracts from the one question being asked
there: is this the right contract?

## During implementation

Implement strictly against the frozen stub. If the implementation turns out
to need a different contract - a different return type, an error case that
was not foreseen - that is the jump from 8 back to 7. State what the
contract needs to become and why, and wait for the decision.

Widening a signature quietly because it made the implementation simpler is
the exact failure this workflow exists to prevent. The `stub-lock` hook will
block the edit, but the hook is a backstop, not the rule.
