# Development workflow

## Principles

- **Language-independent.** Whatever is called a "stub" means a trait in Rust, an interface in PHP, an abstract class in Dart, and so on. The workflow defines *what* has to happen, not *how*.
- **A consultation** is held after every main step, not after sub-steps, unless the step is explicitly marked as having none. A consultation is the developer's own check that everything was understood and defined correctly.
- **From step 8 (implementation) onward there is no scheduled consultation**, unless a jump back triggers one (see below).
- **Artifacts live in the ticket repo only, never in the code repo.** The two are connected by links (ticket, ticket repo, code repo pull request).
- **One ticket repo per project.**
- **Parallelism:** theme blocks run in parallel up to and including step 7, and strictly one at a time from step 8 on. The reason: from 8 there are no consultations left, so there is nothing to wait for, and several blocks writing to the same repository and branch at once produces nothing but conflicts.

## Zones

| Zone | Steps | Scope |
|---|---|---|
| Intake | 1 to 5 | Once per ticket, strictly sequential |
| Blocks | 6 to 9 | Per theme block; 6 and 7 may run in parallel, 8 and 9 are sequential |
| Delivery | 10 to 12 | Once per ticket, only when every block is done |

---

## 1. Gather context

### 1.1. Read the ticket and its comments
#### 1.1.1. Read related tickets where they exist (epics, milestones)
### 1.2. Read the pull request and its review comments, where one exists
### 1.3. Read the connected components of the LikeC4 as-is model, where one exists
### 1.4. Read the affected code, where it exists

## 2. Understand what was read

### 2.1. Define the functional goals
What must work, be new or be better at the end, for the person or the system interacting with the application?
### 2.2. Define the problems

## 3. Ask functional questions
*(no consultation: the questions are answered directly, and no separate summary is needed afterwards)*

## 4. Split the ticket into independently plannable theme blocks

## 5. Persist knowledge
Write what has been worked out so far to `knowledge.md` in the ticket repo, each item with a status (goals, problems, questions left open). Every jump back (see below) adds a log entry: *"PR feedback / finding of [date]: X led to a jump back to step Y."*

---
**From here on: per theme block** (6 and 7 may run in parallel across blocks, 8 and 9 are sequential)
---

## 6. Collect solution options

### 6.1. Look for options already proposed in the gathered context
### 6.2. Ask the developer for possible approaches
### 6.3. Think it through and research it

## 7. Fix architecture and design

### 7.0. Compare against the as-is model, if the block or ticket has been open a while or reuses an existing to-be branch
Check whether the as-is state (`main` in the ticket repo) has changed since the block started, because somebody else built on the same components in the meantime. On drift: rebase the to-be branch and **consult**.
### 7.1. Update the affected LikeC4 model on the to-be branch (the ticket branch in the ticket repo): components and relationships
The affected components are declared as the block's `claimed_components`. Where two blocks' claims overlap, the blocks were never independent, so jump 7 to 4.
### 7.2. Create empty stubs in the code: signatures, no implementation
### 7.3. Write an ADR if a non-trivial decision was made between several real options from step 6 (context, rejected options, reasoning, trade-offs)

-> **The consultation here is the critical one**, because everything after it is implemented strictly against these stubs and this model.

## 8. Implementation

### 8.0. Plan the implementation first, if it is non-trivial
Only where there are several sensible algorithmic approaches, complex error paths or performance-critical sections. This covers the *inside* of the methods, never the contract (signature and outward behaviour), which is already fixed by 7.2. It is not an artifact of its own and serves only to get clear.

-> If it turns out that the contract has to change after all (a different return type, for instance), it is no longer an 8.0 case but a regular jump from 8 to 7, with 7's consultation.

Implement strictly against the stubs defined in 7.2 and the model defined in 7.1. No deviation without a jump back to 7.

*(no scheduled consultation)*

## 9. Verification
Tests, and a comparison of the implementation against the stubs and the LikeC4 model.

*(no scheduled consultation)*

## 10. Open the pull request
The description links `knowledge.md`, the ADRs and the affected `.c4` view in the ticket repo.

*(no scheduled consultation)*

## 11. Process pull request feedback
### 11.1. Read each comment and classify it:
| Kind of comment | Re-enter at |
|---|---|
| Implementation bug or nit | 8 |
| A stub signature or the LikeC4 model must change | 7 (consult) |
| A functional goal or problem was misunderstood | 2 (consult) |
| Context that was missed in step 1 | 1 |
| Entirely new scope, not part of the original ticket | no re-entry: consult and propose a separate ticket |

### 11.2. Carry on normally from the point determined, including that point's consultation rules
### 11.3. Run forward to 10 again, where 10 now means updating the existing pull request rather than opening a new one

## 12. Sync the as-is model after the merge
Triggered by hand, with `/keel:sync-architecture <ticket-id>`. **Never merged automatically.** There is always a manual check, because parallel branches touching the same components would otherwise overwrite each other, and because the as-is state may have moved while the ticket was running.

### 12.1. Run the code graph tool over the freshly merged code for an automatic as-is extract
### 12.2. Compare the to-be branch from 7.1 against the extracted as-is
### 12.3. Where they agree: the developer confirms by hand, and the to-be branch becomes the new as-is state on `main`
### 12.4. Where they differ: correct `main` to the extracted as-is and **consult**, because a difference can point at an undocumented jump back during 8 or 9

---

## Rules for jumping back

**The rule:** a jump back to a step reactivates that step's own consultation rule, regardless of which phase the jump came from.

**A small correction against a real jump:** does a signature change (parameters, return type, which methods exist) or a relationship in the LikeC4 model? Then it is a real jump. Does only a name or an internal comment change? Then it is not.

| From | To | Trigger |
|---|---|---|
| 6 or 7 | 2 | A functional goal or problem was misunderstood or incomplete |
| 7 | 4 | The theme block is not independent after all and has to be cut again (detected automatically where two blocks' `claimed_components` overlap) |
| 8 | 7 | A stub signature or the LikeC4 model is wrong or incomplete |
| 9 | 8 | An ordinary implementation bug |
| 9 | 7 | A design flaw rather than an implementation bug |
| (PR) | 1, 2, 7 or 8 | See the table under step 11 |

Every jump back is recorded in `knowledge.md` (see step 5).

---

## Artifacts

Every artifact lives in the **ticket repo**, never in the code repo, and is connected by links only:

| Artifact | Location | Lifetime |
|---|---|---|
| The `.c4` model | `architecture/` in the ticket repo. `main` is the as-is state, the ticket branch the to-be state | Ongoing, project-wide |
| `knowledge.md` | `tickets/<ticket-id>/knowledge.md` | Per ticket |
| `state.json` | `tickets/<ticket-id>/state.json` | Per ticket. Machine-readable state: step and status per block, consultations, jumps, claims, stub fingerprints, `as_is_base_commit`. The basis for resuming and for the UI |
| `events.jsonl` | `tickets/<ticket-id>/events.jsonl` | Per ticket. Append-only stream of what changed, derived from `state.json` by the `state_writer` hook |
| ADR | `tickets/<ticket-id>/adr/000X-title.md` | Per ticket, kept permanently as the decision history |
| Code (stubs, implementation, tests) | Code repo | Per ticket, then permanent in the code |

## Repository structure (ticket repo, one per project)

```
ticket-repo-<project>/
  architecture/
    specification.c4
    context.c4
    container-*.c4
    views.c4
  tickets/
    <ticket-id>/
      knowledge.md
      state.json
      events.jsonl
      adr/
        0001-title.md
```
