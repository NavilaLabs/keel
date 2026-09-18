---
description: Derive the as-is LikeC4 model from the actual codebase - the first import when adopting keel in an existing project, or a full re-derivation when the model has drifted. Use when the user asks to bootstrap, import, resync or re-derive the architecture model, or asks how stale the model is.
---

# Re-derive the as-is model

`$ARGUMENTS` is an optional scope: a container name to re-derive only that
part. Empty means the whole model.

This is deliberately separate from `/keel:sync-architecture`, which closes out
one ticket. That one asks *did this ticket do what it said*. This one asks
*does the model still describe the code at all*, independently of any ticket.

It never runs automatically and never commits on its own.

## Before anything

1. Read `.claude/keel.json` for the ticket repo. Missing -> this project is
   not set up for keel; offer to create the config, and stop if declined.
2. The ticket repo must be clean and on `main`. Uncommitted changes there
   mean someone is mid-edit; stop and say so.
3. Read `architecture/.keel-sync.json` if it exists. It records what the model
   was last derived from, so you can say how stale it is in commits rather
   than in vague terms.
4. List tickets whose `state.json` has `phase` other than `done`. Their
   `as_is_base_commit` will go stale the moment this commits - that is
   intended, not a problem: the `as_is_staleness` hook then forces step 7.0 on
   each of them, which is exactly the check those tickets need. Name them, so
   the developer is not surprised later. **Never edit their
   `as_is_base_commit` to paper over it.**

Then pick the mode from what exists.

---

## Mode A: first import

`architecture/` is missing, empty, or has no element definitions.

### A.1 Scaffold, if needed

Offer to create the ticket repo layout: `architecture/`, `tickets/`, and a git
repo if there is none. Do not create it silently.

### A.2 Agree the scope -> consultation

This is the decision that determines whether the model survives its first
year, so it gets a consultation before any extraction.

**Default to context and container level only. Do not model components.**

Load `likec4-conventions` for why: a first import that dumps every class into
the model produces a diagram nobody maintains and everybody stops trusting
after the third stale view. Components earn their place one ticket at a time,
added at step 7.1 by the ticket that actually touches them.

Present:

- The containers you can identify: deployables, services, databases, queues,
  scheduled jobs, front ends. Say how you identified each one, so a wrong
  guess is visible
- External systems the code talks to
- What you are unsure about

Ask which of these are real containers and which are not, and whether any
container should get component-level detail right away. Accept "none" as the
answer for that last one - it is the right default.

### A.3 Write the model

`specification.c4` with the element and relationship kinds, `context.c4`, one
`container-<name>.c4` per container, `views.c4`. Naming follows the codebase's
own vocabulary, per `likec4-conventions`.

For any container the developer chose for component level, delegate to
`as-is-extractor` for that container only.

### A.4 Validate, present, commit -> consultation

Run `npx likec4 validate`. Present the model and what it leaves out. Commit to
`main` only after confirmation.

---

## Mode B: re-derivation

`architecture/` already holds a model.

### B.1 Extract

Delegate to `as-is-extractor`, one container at a time rather than the whole
codebase at once. A single extraction over a large repo returns more than can
be reviewed, and a diff nobody reads is a diff that gets accepted blindly.

With a scope argument, only that container.

**Re-derive what is already modelled. Do not expand scope on your own.** If
the code has grown a container that the model does not know about, that is a
finding to report, not a thing to add silently - report it and let the
developer decide whether it belongs in the model.

### B.2 Classify the differences

Per container, split the diff into three kinds, because they mean different
things:

- **Model stale** - the code has a component or relationship the model lacks.
  Usually the model simply lagged. Add it.
- **Model ahead** - the model has something the code does not. Either it was
  removed and the model was not updated, or it was never built. Say which you
  think it is and on what evidence.
- **Possible violation** - a relationship that crosses a boundary the model
  describes as not existing, especially into a container the model shows as
  isolated. This is the one that matters. It may be a legitimate change nobody
  modelled, or it may be the architecture quietly eroding. Never fold these in
  with the stale ones.

Anything the extraction marked as inferred rather than read directly from the
code carries that marking into your report. A confident diff built on a guess
is worse than an honest uncertainty.

### B.3 Present and decide -> consultation, per container

For each container: the diff, the classification, and a proposed `.c4` change.

For a possible violation, the choice is not just *update the model*. Updating
it records the erosion as the new normal. Offer both: update the model because
the change was intended, or leave the model and open a ticket because the code
is wrong. The second option is the reason this step is a consultation and not
a script.

### B.4 Commit

Only after confirmation, and only to `architecture/`. Never touch a ticket
branch and never merge one.

---

## After either mode

Write `architecture/.keel-sync.json`:

```json
{
  "schema_version": 1,
  "synced_at": "2026-09-18T21:00:00Z",
  "code_commit": "<code repo HEAD at extraction time>",
  "scope": ["context", "container-api", "container-worker"],
  "component_level": ["container-api"],
  "tool": "graphify",
  "unresolved": ["api.legacyBridge -> target could not be resolved"]
}
```

`unresolved` carries what the extractor could not work out, so the next
re-derivation does not re-litigate the same ambiguities from scratch.

Then report, in one short block: what changed, which tickets now have a stale
baseline and will hit step 7.0, and anything classified as a possible
violation that was left unresolved.
