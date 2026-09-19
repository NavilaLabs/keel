---
description: Runs the ticket development workflow end to end - context gathering, understanding, theme blocks, architecture and contracts, implementation, PR and as-is sync. Use when the user names a ticket to work on, asks to continue a ticket, or asks where a ticket stands.
---

# Ticket workflow orchestrator

You drive one ticket through a fixed workflow. You do not skip steps, and you do not start at step 1 when `state.json` says otherwise.

`$ARGUMENTS` is the ticket id.

## Before anything else

1. Write the ticket id to `.keel-ticket` in the code repo root. The hooks
   run outside this conversation and have no other way to know which ticket is
   active - without this file they fail open and enforce nothing.
2. Read `tickets/$ARGUMENTS/state.json` in the ticket repo.
   - **Missing** -> this is a new run. Create it from `${CLAUDE_PLUGIN_ROOT}/state.schema.json` with `phase: "intake"`, `intake_step: "1"`, empty `blocks`, and the ticket id. Then start at step 1.
   - **Ticket repo missing or empty** -> this is the first ticket for this project. Say so, and offer to scaffold `architecture/` and `tickets/` before starting. Do not silently create them.
   - **Present** -> resume. `phase` plus `intake_step` or the blocks' `step` fields tell you exactly where work stopped. Report that position to the developer in one line before continuing.
2. Never re-run a completed step to "refresh context". If you lack context, read the artifacts: `knowledge.md`, the ADRs, the LikeC4 model.

## Trackers and authentication

`.claude/keel.json` records once per project where tickets and pull requests live (`tickets.source`, `pull_requests.host`, each with `repository`) and the name of the environment variable holding its token (`token_env`). Read it before step 1 and use it for `ticket_source` and `pr.host` in `state.json`.

- **Missing** -> ask the developer once which tracker and pull request host the project uses and which variable holds the token, then write the answer to `.claude/keel.json`. Never ask again in later tickets.
- **Access** -> use the tracker's MCP server if one is available. Otherwise call its REST API with the token from `token_env`, passed only in the request header. Never print, log, echo or store the token, and never write its value into any file.
- **Unset variable** -> say which variable is missing and stop asking for anything else. The developer sets it.

## Hooks

A hook block is a decision, not an obstacle. Never work around a blocked write with Bash, sed, python or any other tool, and never edit the hooks or the state to get past one. Say what was blocked and why you think it is wrong or how you would proceed, and wait. Only the developer can allow a workaround.

## Zones

| Zone | Steps | Rule |
| --- | --- | --- |
| intake | 1-5 | Once per ticket, strictly sequential |
| blocks | 6-9 | Per theme block. 6-7 may run in parallel across blocks, 8-9 strictly one block at a time |
| delivery | 10-12 | Once per ticket, only when every block is `done` |

## Consultation rule

After every **main step** (2, 4, 5, 6, 7, and any step reached by a jump), stop and consult the developer. Not after sub-steps. Step 3 is explicitly exempt. Steps 8, 9, 10, 11 and 12 have no scheduled consultation - they consult only where this document says so.

A consultation is an object in `state.json`, not just a message: write it to `consultations[]` with `status: "open"`, ask the developer, then record the answer and set `status: "answered"`. Never proceed past an open consultation.

## The workflow

### Zone: intake

**1. Gather context** - delegate to the `context-gatherer` subagent. It returns a condensed report; the raw ticket, PR and code contents stay out of this conversation.

**2. Understand** - state the functional goals (what must work, be new or be better for the person or system using the application) and the problems. -> consult

**3. Ask functional questions** - ask what you need to know, take the answers, move on. No consultation, no summary of answers.

**4. Split into theme blocks** - divide the ticket into independently plannable themes. Load `decision-heuristics` for where to cut. Write them to `blocks[]` with `status: "pending"`. -> consult

**5. Persist knowledge** - write `knowledge.md`: goals, problems, open questions, each with a status. Link it on the ticket via the tracker's MCP server. -> consult

### Zone: blocks

Per block. Blocks may sit at different steps.

**6. Collect solution options**
- 6.1 check the gathered context for options already proposed
- 6.2 ask the developer for approaches
- 6.3 delegate to the `research-agent` subagent
-> consult

**7. Fix architecture and design**
- 7.0 if this block has been open a while or reuses an existing to-be branch: compare `as_is_base_commit` against the ticket repo's current `main`. On drift, rebase the to-be branch and -> consult
- 7.1 update the LikeC4 model on the to-be branch. Declare the touched elements as this block's `claimed_components`. Overlap with another block means the blocks were never independent -> jump to 4
- 7.2 make sure the code repo is on a ticket branch cut from a fetched, current `origin/main` (a stale local `main` silently drops merged work), then create empty stubs in the code repo: signatures only, no implementation. Put the contract - error behaviour, idempotency, invariants - in doc comments, not in the diagram. Record each in `claimed_stubs` with its fingerprint
- 7.3 write an ADR if a non-trivial decision was made between several real options from step 6
-> consult. This is the critical one: everything after it is implemented strictly against these stubs.

**8. Implement** - only one block may be here at a time.
- 8.0 if the internals are non-trivial, plan them first. This covers the inside of the methods only. If the plan turns out to need a different contract, that is not an 8.0 case but a jump to 7
- implement strictly against the stubs from 7.2 and the model from 7.1

**9. Verify** - tests, and check the implementation against stubs and LikeC4 model. A plain bug -> jump to 8. A design flaw -> jump to 7.

Mark the block `done` and move to the next one.

### Zone: delivery

**10. Open the PR** - only when every block is `done`. The description links `knowledge.md`, the ADRs and the LikeC4 views from `artifacts`.

**11. Process PR feedback** - delegate classification to the `review-triage` subagent, then re-enter per its verdict:

| Comment | Re-enter at |
| --- | --- |
| Implementation bug or nit | 8 |
| Contract or LikeC4 model must change | 7 (consult) |
| Functional goal was misunderstood | 2 (consult) |
| Context missed in step 1 | 1 |
| New scope, not part of this ticket | no re-entry - consult, propose a separate ticket |

Several comments may re-enter at different points. All paths run forward to 10 again, where 10 now means "update the existing PR".

**12. Sync the as-is model** - only on explicit request (`/keel:sync-architecture`). Never automatic.

## Jumping back

A jump reactivates the target step's own consultation rule, whatever zone you jumped from. "No consultation from 8 onward" governs the forward path only.

Contract or relationship changed -> real jump. Naming or an internal comment -> not a jump, just fix it.

Record every jump in `jump_log[]` and append a line to `knowledge.md`.

## Artifacts

Everything lives in the **ticket repo**, never in the code repo. The code repo only gets code and links.

```
ticket-repo-<project>/
  architecture/          # main = as-is, ticket branch = to-be
  tickets/<ticket-id>/
    knowledge.md
    state.json
    adr/
```
