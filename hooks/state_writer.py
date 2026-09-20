#!/usr/bin/env python3
"""state-writer: emit an event stream from state.json changes.

Runs after an editor write, after a shell command and at the end of every
turn. All three mean the same thing to this hook: re-read state.json and
compare it against the snapshot cache. It never interprets what was written,
which is why the trigger does not have to be the write itself - a state file
moved with a heredoc produces the same events as one moved with Edit.

The other hooks enforce. This one records: every change to state.json becomes
an append-only line in events.jsonl next to it. Step transitions,
consultations opening and closing, jumps, blocks finishing, and a hint at the
artefact the current step is about.

state.json answers "where are we now". The event stream answers "how did we
get here" - which is what the UI needs for a live view and a history, and what
nobody can reconstruct afterwards from a file that only ever holds its current
version. Git history of state.json would carry the same information, but only
for changes that were committed, and state moves far more often than it is
committed.

Despite the name this hook does not write state.json. The orchestrator does
that; this observes it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import json
from datetime import datetime, timezone

from workflow_state import (
    fail_open,
    find_state_path,
    load_state,
    read_event,
    state_path,
    written_path,
)

HOOK = "state-writer"


def snapshot(state: dict) -> dict:
    artifacts = state.get("artifacts") or {}
    return {
        "phase": state.get("phase"),
        "intake_step": state.get("intake_step"),
        "to_be_branch": state.get("to_be_branch"),
        "artifacts": {
            "knowledge": artifacts.get("knowledge"),
            "adrs": list(artifacts.get("adrs") or []),
            "c4_views": list(artifacts.get("c4_views") or []),
        },
        "blocks": {
            b.get("id"): {
                "step": b.get("step"),
                "status": b.get("status"),
                "stubs": [
                    {"path": s.get("path"), "symbol": s.get("symbol")}
                    for s in b.get("claimed_stubs") or []
                ],
                "adrs": list(b.get("adrs") or []),
            }
            for b in state.get("blocks", [])
        },
        "open_consultations": [
            c.get("id") for c in state.get("consultations", []) if c.get("status") == "open"
        ],
        # Beside open_consultations rather than replacing it: a cache written
        # by an earlier version has no step and block here, and a missing key
        # must not read as "nothing was open".
        "consultations": {
            c.get("id"): {"step": c.get("step"), "block": c.get("block")}
            for c in state.get("consultations", [])
            if c.get("status") == "open"
        },
        "jumps": len(state.get("jump_log", [])),
    }


def view_targets(current: dict, views: list) -> list[dict]:
    """A view id names nothing on its own: the to-be model lives on a branch."""
    branch = current.get("to_be_branch")
    targets = []
    for view in views:
        target = {"kind": "c4_view", "view": view}
        if branch:
            target["branch"] = branch
        targets.append(target)
    return targets


def stub_targets(stubs: list) -> list[dict]:
    targets = []
    for stub in stubs:
        if not stub.get("path"):
            continue
        target = {"kind": "stub", "repo": "code", "path": stub["path"]}
        if stub.get("symbol"):
            target["symbol"] = stub["symbol"]
        targets.append(target)
    return targets


def adr_targets(paths: list) -> list[dict]:
    return [{"kind": "adr", "repo": "ticket", "path": path} for path in paths]


def knowledge_of(current: dict, block: dict) -> list[dict]:
    path = current.get("artifacts", {}).get("knowledge")
    return [{"kind": "knowledge", "repo": "ticket", "path": path}] if path else []


def views_of(current: dict, block: dict) -> list[dict]:
    return view_targets(current, current.get("artifacts", {}).get("c4_views", []))


def stubs_of(current: dict, block: dict) -> list[dict]:
    return stub_targets(block.get("stubs", []))


def adrs_of(current: dict, block: dict) -> list[dict]:
    return adr_targets(block.get("adrs") or current.get("artifacts", {}).get("adrs", []))


# What each consultation step is about, in the order a UI should bring forward.
# A step that is absent has no artefact as its subject: step 4 is about
# blocks[] and step 6 about solution options, both of which a UI already has
# from state.json.
ARTIFACT_STEPS = {
    "5": (knowledge_of,),
    "7": (views_of, stubs_of, adrs_of),
    "7.1": (views_of,),
    "7.2": (stubs_of,),
    "7.3": (adrs_of,),
}


def added(before: list, now: list) -> list:
    return [item for item in now if item not in before]


def recorded_targets(previous: dict, current: dict) -> dict:
    """Artefacts the state names for the first time, grouped by block.

    Only a path or view id newly recorded counts. A file rewritten later,
    knowledge.md on a jump for instance, is invisible here: this hook sees
    state, not file contents.
    """
    grouped: dict = {}

    before = previous.get("artifacts", {})
    now = current.get("artifacts", {})

    ticket_wide = []
    if now.get("knowledge") and not before.get("knowledge"):
        ticket_wide += knowledge_of(current, {})
    ticket_wide += view_targets(
        current, added(before.get("c4_views", []), now.get("c4_views", []))
    )
    ticket_wide += adr_targets(added(before.get("adrs", []), now.get("adrs", [])))
    if ticket_wide:
        grouped[None] = ticket_wide

    old_blocks = previous.get("blocks", {})
    for block_id, block in current.get("blocks", {}).items():
        known = {stub.get("path") for stub in old_blocks.get(block_id, {}).get("stubs", [])}
        fresh = [stub for stub in block.get("stubs", []) if stub.get("path") not in known]
        if fresh:
            grouped[block_id] = stub_targets(fresh)

    return grouped


def consulted_targets(previous: dict, current: dict) -> dict:
    """What a consultation that just opened asks the developer to look at.

    Keyed by block, because that is what a hint is about. Two consultations
    opening for the same block in one observation would mean two steps in one
    state write; the first by id keeps the hint's step and id.
    """
    consulted: dict = {}
    opened = set(current.get("open_consultations", [])) - set(
        previous.get("open_consultations", [])
    )

    for consultation_id in sorted(opened):
        detail = current.get("consultations", {}).get(consultation_id) or {}
        subjects = ARTIFACT_STEPS.get(str(detail.get("step")))
        if not subjects:
            continue
        block_id = detail.get("block")
        if block_id in consulted:
            continue
        block = current.get("blocks", {}).get(block_id) or {}
        targets: list[dict] = []
        for subject in subjects:
            targets += subject(current, block)
        consulted[block_id] = (consultation_id, detail.get("step"), targets)

    return consulted


def step_of(current: dict, block_id) -> str | None:
    if block_id is None:
        return current.get("intake_step")
    return current.get("blocks", {}).get(block_id, {}).get("step")


def hint_of(current: dict, block_id, consulted: dict, recorded: list) -> dict | None:
    consultation_id, step, targets = consulted.get(block_id, (None, None, []))
    targets = list(targets)
    for target in recorded:
        if target not in targets:
            targets.append(target)
    if not targets:
        return None

    hint = {
        "type": "artifact_hint",
        "block": block_id,
        "step": step or step_of(current, block_id),
    }
    if consultation_id:
        hint["consultation"] = consultation_id
    hint["targets"] = targets
    return hint


def hints(previous: dict, current: dict) -> list[dict]:
    """At most one hint per block per observation, and none at all from a baseline.

    A hint is not state: it says what is worth looking at now, once. Against
    a snapshot that never recorded artefacts, whether because it is empty or
    because it was written before hints existed, every artefact the state
    names would look new at the same moment. Such an observation seeds the
    cache and hints nothing. The events either side of it are facts and
    survive being re-derived; a burst of stale hints would not.

    The ticket-wide hint comes first, so a UI that acts on the last one it
    reads lands on the more specific one.
    """
    if "artifacts" not in previous:
        return []

    recorded = recorded_targets(previous, current)
    consulted = consulted_targets(previous, current)

    blocks = sorted(block for block in set(recorded) | set(consulted) if block is not None)
    per_block = [hint_of(current, block, consulted, recorded.get(block, [])) for block in blocks]
    per_block = [hint for hint in per_block if hint]

    # A view or an ADR that a block's own hint already names needs no second
    # hint beside it: one observation should move the view once.
    named = [target for hint in per_block for target in hint["targets"]]
    ticket_wide = hint_of(
        current, None, consulted, [t for t in recorded.get(None, []) if t not in named]
    )

    return ([ticket_wide] if ticket_wide else []) + per_block


def state_events(previous: dict, current: dict) -> list[dict]:
    events: list[dict] = []

    if previous.get("phase") != current.get("phase"):
        events.append(
            {"type": "phase_changed", "from": previous.get("phase"), "to": current.get("phase")}
        )

    if previous.get("intake_step") != current.get("intake_step"):
        events.append(
            {
                "type": "step_changed",
                "block": None,
                "from": previous.get("intake_step"),
                "to": current.get("intake_step"),
            }
        )

    old_blocks = previous.get("blocks", {})
    for block_id, now in current.get("blocks", {}).items():
        before = old_blocks.get(block_id, {})
        if before.get("step") != now.get("step"):
            events.append(
                {
                    "type": "step_changed",
                    "block": block_id,
                    "from": before.get("step"),
                    "to": now.get("step"),
                }
            )
        if before.get("status") != now.get("status"):
            events.append(
                {
                    "type": "block_status_changed",
                    "block": block_id,
                    "from": before.get("status"),
                    "to": now.get("status"),
                }
            )

    old_open = set(previous.get("open_consultations", []))
    new_open = set(current.get("open_consultations", []))
    for opened in sorted(new_open - old_open):
        events.append({"type": "consultation_opened", "consultation": opened})
    for closed in sorted(old_open - new_open):
        events.append({"type": "consultation_closed", "consultation": closed})

    if current.get("jumps", 0) > previous.get("jumps", 0):
        events.append({"type": "jump_recorded", "total": current.get("jumps")})

    return events


def diff(previous: dict, current: dict) -> list[dict]:
    """The facts first, then the hint about them."""
    return state_events(previous, current) + hints(previous, current)


def observed_state(event: dict) -> Path | None:
    """The state file this invocation should re-read, if any.

    An editor write names its file, so anything but state.json is someone
    else's business and costs nothing to skip. A shell command and the end of
    a turn name nothing: there the only question is whether a ticket is
    active at all, and the diff decides whether anything moved.
    """
    target = written_path(event)
    if target is None:
        return find_state_path()

    if Path(target).name != "state.json":
        return None

    path = state_path(HOOK)
    try:
        return path if Path(target).resolve() == path.resolve() else None
    except OSError:
        return None


def main() -> None:
    path = observed_state(read_event())
    if path is None:
        sys.exit(0)

    current = snapshot(load_state(HOOK))

    directory = path.parent
    cache = directory / ".state-snapshot.json"
    stream = directory / "events.jsonl"

    previous = {}
    if cache.is_file():
        try:
            previous = json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}

    events = diff(previous, current)
    now = datetime.now(timezone.utc).isoformat()

    try:
        if events:
            with stream.open("a", encoding="utf-8") as handle:
                for item in events:
                    handle.write(json.dumps({"at": now, **item}, ensure_ascii=False) + "\n")
        cache.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except OSError as exc:
        fail_open(HOOK, f"could not write event stream: {exc}")

    sys.exit(0)


if __name__ == "__main__":
    main()
