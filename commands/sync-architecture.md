---
description: Syncs the as-is LikeC4 model after a ticket's pull request has been merged - extracts the actual structure from the merged code, compares it against the to-be model, and updates main only with the developer's confirmation. Use only when explicitly asked to sync architecture for a merged ticket.
---

# Sync the as-is model

Step 12 of the ticket workflow. `$ARGUMENTS` is the ticket id.

This never runs automatically. Parallel branches touching the same components
would overwrite each other, and a ticket that took weeks may have been
overtaken by work that landed on `main` meanwhile. The merge into `main` is a
decision, not a mechanical step.

## Preconditions

Read `tickets/$ARGUMENTS/state.json`. Refuse and say why if:

- `pr.state` is not `merged`
- any block is not `done`
- there is an open consultation

## 12.1 Extract the as-is state

Delegate to the `as-is-extractor` subagent against the merged code. It returns
the actual component structure plus a proposed diff, with tool noise left in
its own context.

## 12.2 Compare

Three things get compared, not two:

1. the to-be model on the ticket branch, against what was extracted
2. the ticket branch's base, against the current `main` - other tickets may
   have landed since `as_is_base_commit`
3. this ticket's `claimed_components`, against elements other merges touched

The second and third are why this step is manual. A clean match against the
extracted code still means nothing if someone else rewrote the same component
last week.

## 12.3 Match

Present the result and ask for confirmation. On confirmation, merge the
ticket branch's `architecture/` into `main`. Resolve conflicts with another
merge's changes by keeping both, never by overwriting - if they genuinely
conflict, that is a question for the developer, not a merge strategy.

## 12.4 Drift

Present the drift and consult. Drift where a contract or a relationship
differs from the to-be model means an undocumented jump happened during
implementation: step 7 said one thing, the code does another, and no jump was
logged. Say that plainly rather than quietly correcting `main` to match the
code.

The developer decides whether the code is right and `main` follows it, or the
code is wrong and a follow-up ticket fixes it.

Whichever way it goes, record it: a `jump_log` entry with trigger
`as_is_drift` and a line in `knowledge.md`. A drift that was silently
resolved teaches nothing; a drift with a reason on record is how the
next ticket's step 7 gets better.

## After syncing

Set `phase` to `done`. Leave the ticket branch in place - it is the record of
what this ticket intended, next to what it actually produced.
