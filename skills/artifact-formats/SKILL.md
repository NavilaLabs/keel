---
name: artifact-formats
description: Defines the format of the ticket workflow's artifacts - knowledge.md, ADRs and state.json - and where they live. Use when writing or updating any of them, at steps 5, 7.3 and on every jump.
---

# Artifact formats

All three live in the **ticket repo**, never in the code repo. The code repo
carries code and links back.

```
ticket-repo-<project>/
  architecture/              # main = as-is, ticket branch = to-be
  tickets/<ticket-id>/
    knowledge.md
    state.json
    adr/0001-short-title.md
```

## knowledge.md

Written at step 5, appended to on every jump. It is what someone reads in two
years to understand why this ticket went the way it did.

```markdown
# <ticket-id>: <ticket title>

## Goals
- [ ] <what must work, be new or be better, for whom>  `open`
- [x] <...>  `agreed`

## Problems
- <problem>  `open` | `resolved: <how>`

## Open questions
- <question>  `open` | `answered: <answer>`

## Theme blocks
- **block-1** <title> - `pending` | `in_progress` | `done`

## Log
- 2026-09-18 - PR feedback from <reviewer>: <what> led to a jump from 8 to 7.
```

Every goal, problem and question carries a status. A question that stayed
open through the whole ticket is a finding, not an oversight - leave it
visible rather than deleting it.

The log is prose alongside `jump_log[]` in `state.json`. The JSON is for the
machine, this is for the reader: it says *why*, not just *from where to
where*.

## ADR

Written at step 7.3, one file per decision, numbered sequentially and never
renumbered. An ADR is not updated when the decision changes later - a new ADR
supersedes it and names the one it replaces.

```markdown
# 0001. <decision in one line>

Status: accepted | superseded by 0007
Date: 2026-09-18
Ticket: <ticket-id>
Block: block-1

## Context
<what forced a decision, what constrained it>

## Options
### <option A>
<what it is, what it costs>
### <option B>
<...>

## Decision
<what was chosen>

## Consequences
<what this makes easy, what it makes hard, what it forecloses>
```

Write the options as they genuinely stood at the time, including the one
that was rejected for a reason that later turned out to be wrong. An ADR
that only justifies the winner is a press release.

Only write an ADR when there were several real options. If one approach was
obvious, the decision is not worth a document - see `decision-heuristics`.

## state.json

Conforms to `schema/state.schema.json`. Machine-readable, written by the
`state-writer` hook and the orchestrator, read on resume and by the UI.

Two rules when writing it by hand:

- **Never rewrite history.** `consultations[]` and `jump_log[]` are
  append-only. An answered consultation stays answered; a jump that happened
  stays logged even if it turned out to be unnecessary.
- **Status reflects reality, not intent.** A block sits at
  `awaiting_consultation` until the developer has actually answered, not
  from the moment the question was asked in the conversation.
