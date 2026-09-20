# Workflow components: agents, hooks, skills, state

---

## 1. Orchestrator

**Slash command:** `/keel:ticket <ticket-id>`

It knows the order of the steps, reads `state.json` and re-enters **at the position recorded there**, not at step 1. It calls agents, skills and artifact writes at the right points and respects the zones (intake sequential, blocks 6 and 7 parallel, 8 and 9 sequential, delivery only once every block is `done`).

That covers re-entry (11.2), the merge sync (12) and carrying on tomorrow without any chat context.

The other commands:

| Command | Purpose |
|---|---|
| `/keel:ticket <id>` | Start or resume |
| `/keel:sync-architecture <id>` | Step 12, triggered by hand |
| `/keel:resync` | Derive the as-is model from the code, for a first import or after drift |
| `/keel:statusline` | Toggle the status line, which shows the active ticket, the current step and whether a consultation is waiting |

---

## 2. Agents

Subagents get their own isolated context. The criterion: a lot of raw material in, a little condensate out. Deliberately **no** agent for step 7 or for consultations, where everything belongs in the main context, in front of the developer.

| Agent | Step | Input | Output |
|---|---|---|---|
| `context-gatherer` | 1 | Ticket, related tickets and PR comments (through the tracker's MCP server), the LikeC4 as-is model, the affected code | One condensed context report, no raw material |
| `research-agent` | 6.3 | The block's problem statement | Solution options with their sources, without the search noise |
| `review-triage` | 11.1 | PR comments | A structured list: comment to re-entry point (1, 2, 7, 8 or a separate ticket) |
| `as-is-extractor` | 12.1 | The merged code | The extracted as-is state as a `.c4` diff proposal against `main` |

---

## 3. Skills

Reusable knowledge and conventions, without a context of their own.

| Skill | Content |
|---|---|
| `artifact-formats` | The structure of `knowledge.md`, the ADR template, `state.json` |
| `likec4-conventions` | File layout, naming, discipline rules: do not model the whole codebase at component level, keep `description` to one sentence of responsibility, `link` instead of duplicating signatures, one file per container |
| `stub-conventions` | What a stub is per language (Rust: trait, PHP: interface, Dart: abstract class) and that the contract, meaning error behaviour, idempotency and invariants, belongs in doc comments rather than in the diagram |
| `decision-heuristics` | The "is this worth it" rules in one place: where to cut theme blocks (4), when an ADR is worth writing (7.3: only where several real options stood), a small correction against a real jump (did a signature or relationship change?), the 8.0 trigger |
| `consultation-protocol` | How a consultation is prepared, presented and recorded as an object in `state.json` |

---

## 4. Hooks

Hooks are the only layer that actually **enforces** rather than suggests, and at the same time the event source for the UI.

| Hook | Trigger | Effect |
|---|---|---|
| `stub_lock` | A file edit during step 8 or 9 | Compares against the fingerprints in the active block's `claimed_stubs`. A changed contract is blocked, which forces the jump from 8 to 7. **The hook that matters**, because it is what enforces the central rule of the workflow |
| `consultation_gate` | Any write while a consultation is open | Blocks until the consultation in `state.json` has been answered |
| `as_is_staleness` | Entering step 7 | Compares `as_is_base_commit` against the ticket repo's current `main`. On drift it forces step 7.0 |
| `block_overlap` | Writing `claimed_components` (7.1) | An overlap with another block's claims means a jump from 7 to 4 |
| `sequential_implementation` | Entering step 8 | Blocks while another block is already in 8 or 9 |
| `pr_gate` | Opening the pull request (10) | Blocks while any block is not `done`, or while links to `knowledge.md`, the ADRs and the `.c4` view are missing |
| `state_writer` | After every editor write, after every shell command and at the end of every turn | Compares `state.json` against its snapshot and appends the difference to `events.jsonl`: step changes, consultations, jumps, plus an `artifact_hint` naming the artefact the current step is about. It does not write `state.json` itself, it observes it |
| `session_start` | The start of a session | Announces keel and the active ticket to Claude |

Every hook fails open on its own problems. Missing configuration or unreadable state produces a warning and lets development continue, because a hook that halts work when it is itself misconfigured gets disabled within two days, and then it protects nothing.

---

## 5. `state.json` (sketch)

`state.schema.json` in the repository root is the authoritative version.

```json
{
  "ticket_id": "PROJ-1234",
  "phase": "intake | blocks | delivery | done",
  "intake_step": "5",
  "as_is_base_commit": "a1b2c3d",
  "to_be_branch": "ticket/PROJ-1234",
  "artifacts": {
    "knowledge": "tickets/PROJ-1234/knowledge.md",
    "adrs": ["tickets/PROJ-1234/adr/0001-....md"],
    "c4_views": ["api-components"]
  },
  "blocks": [
    {
      "id": "block-1",
      "title": "...",
      "step": "7.2",
      "status": "pending | in_progress | awaiting_consultation | blocked | done",
      "claimed_components": ["api.orderService"],
      "claimed_stubs": [
        { "path": "src/order/service.rs", "symbol": "OrderService", "fingerprint": "..." }
      ],
      "adrs": []
    }
  ],
  "consultations": [
    {
      "id": "c1",
      "block": "block-1",
      "step": "7",
      "question": "...",
      "options": [],
      "answer": "...",
      "status": "open | answered | skipped",
      "asked_at": "...",
      "answered_at": "..."
    }
  ],
  "jump_log": [
    { "from": "8", "to": "7", "block": "block-1", "trigger": "contract_change", "reason": "...", "at": "..." }
  ]
}
```

Consultations are deliberately **objects with an id** rather than terminal text: only that way can a UI render them as cards, and the audit log of decisions comes out of it for free.

---

## 6. Toward the UI

This makes the UI pure presentation over data that already exists, with no chat history to interpret:

- `state.json` as the backend and the progress display
- `events.jsonl` as the live stream and the history
- `consultations[]` as interactive cards (question, options, answer)
- `c4_views` as the diagram pane
- `jump_log` as the history of why something changed
- `artifact_hint` as a one-shot signal of which artefact belongs in front right now.
  It is not state: nothing waits for it, a terminal with no UI attached is the
  normal case, and the developer's own navigation overrides it at any time
