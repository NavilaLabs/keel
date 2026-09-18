---
name: likec4-conventions
description: Conventions and discipline rules for the LikeC4 architecture model - file layout, naming, what belongs in a diagram and what does not. Use when reading or updating any .c4 file, especially at steps 1.3, 7.1 and 12.
---

# LikeC4 conventions

The model lives in `architecture/` in the ticket repo. `main` holds the
as-is state, a ticket branch holds the to-be state for that ticket.

## File layout

LikeC4 scans the folder recursively and treats every `.c4` file as one
composed model - no imports, elements are referenced across files by name.

```
architecture/
  specification.c4      # element and relationship kinds - defined ONCE
  context.c4            # the system in its environment
  container-<name>.c4   # one file per container, with its components
  views.c4              # all view definitions
```

One file per container. Not one file for everything: a diff on
`container-api.c4` is reviewable, a diff on a single model file is not.

Element kinds go in `specification.c4` only. Redefining a kind in another
file is a conflict, not an override.

## What gets modelled

Model the containers you are actually working on. Modelling the entire
codebase down to component level produces something nobody maintains and
everybody stops trusting after the third stale diagram.

A component is an architectural building block - a controller, a service, a
repository, a builder. Not every class, and never a private helper. If
removing it from the diagram would not change how someone reasons about the
system, it does not belong in the diagram.

## What does not get modelled

**Signatures.** A diagram shows who talks to whom, never what the parameters
are. Method-level detail belongs in the code, where the compiler keeps it
honest.

**Behaviour.** Conditionals, retries, control flow - LikeC4 is structure. For
a specific sequence, use a dynamic view; for branching logic, prose or the
code itself.

**Anything re-derivable.** If it can be read off the code in ten seconds, the
diagram duplicating it only creates a second thing that can go stale.

## description and link

`description` is one sentence of responsibility, and it stays one sentence
however many methods the component grows:

```
orderService = component 'OrderService' {
  description 'Validates and persists orders'
  link ../../code/src/order/service.rs
}
```

Use `link` to point at the contract in the code rather than repeating it in
the diagram. The diagram then never lies about the signature, because it
never states it.

## Naming

Element ids are lowerCamelCase and match the code's own vocabulary:
`orderService`, not `svc_order_1` and not `OrderServiceComponent`. When the
codebase calls it an order service, so does the model - a model with its own
private naming forces everyone to translate twice.

## Changing the model

Touched elements get declared as the block's `claimed_components` in
`state.json`. Two blocks claiming the same element means they were never
independent: jump back to step 4.

Never edit `architecture/` on `main` during a ticket. `main` only moves in
step 12, with the developer.
