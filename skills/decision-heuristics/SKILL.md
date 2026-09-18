---
name: decision-heuristics
description: The judgement calls of the ticket workflow in one place - how to cut theme blocks, when an ADR is worth writing, what counts as a real jump back, and when to plan implementation internals. Use at steps 4, 7.3, 8.0 and whenever deciding whether to jump.
---

# Decision heuristics

Four judgement calls the workflow keeps asking. Each one has a failure mode
in both directions.

## Step 4 - where to cut theme blocks

A theme block is an **independently plannable** part of the ticket, not an
implementation step. "Filter feature" and "export feature" are blocks.
"Create endpoint" and "write migration" are not - those follow from the
design, which does not exist yet at step 4.

The test: could this block go through steps 6 and 7 - options, architecture,
contracts - without knowing the outcome of the other block? If not, they are
one block.

Practical signal: blocks that would claim the same LikeC4 components are not
independent. The `block-overlap` hook catches this at 7.1, but noticing it at
4 is cheaper.

- **Cut too fine**: blocks that constantly need each other's decisions.
  Every consultation drags the other block in, and the parallelism buys
  nothing.
- **Cut too coarse**: one block covering the whole ticket. Then step 7's
  consultation covers too much to review properly, which is where the
  workflow's main safeguard lives.

Most tickets are one block. Splitting is the exception, not the default.

## Step 7.3 - is this worth an ADR?

Write one when step 6 produced **more than one genuine option** and the
choice forecloses something.

- Two real approaches with different trade-offs -> ADR
- One obvious approach, the others dismissed in a sentence -> no ADR
- A choice that can be reversed in an afternoon -> usually no ADR
- A choice that shapes the interface others build against -> ADR, even if
  it felt easy

The question to ask: in two years, would someone looking at this code wonder
why it was done this way? Writing an ADR for every decision devalues the ones
that matter, because nobody reads twelve documents to find the one with
content.

## Real jump back, or just a correction?

**Real jump** - anything visible from outside the contract:

- a signature changes: parameters, return type, error type
- the guarantees in the doc comments change: idempotency, invariants, what
  can fail
- a relationship in the LikeC4 model changes
- a component appears or disappears

**Not a jump** - invisible from outside:

- renaming a local variable or a private helper
- a comment, formatting, a test
- an internal algorithm swapped for another with identical behaviour

When it could be read either way, treat it as a real jump. An unnecessary
consultation costs a minute. A contract that changed without one is the
failure this whole workflow is built around.

## Step 8.0 - plan the internals first?

Only when the inside of the methods is genuinely non-trivial: several
plausible algorithms, complex error paths, or a performance-critical section.

This is about **how** the contract is fulfilled, never **what** it
guarantees - that was settled at 7.2. If planning reveals the contract itself
has to change, that is not an 8.0 case but a jump to 7.

Skip it for straightforward implementations. A plan for code that writes
itself is bureaucracy, and 8.0 has no consultation precisely because it is
meant to be cheap.
