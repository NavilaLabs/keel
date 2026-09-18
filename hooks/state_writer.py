#!/usr/bin/env python3
"""state-writer: emit an event stream from state.json changes.

PostToolUse on Edit|Write, acting only on state.json.

The other hooks enforce. This one records: every change to state.json becomes
an append-only line in events.jsonl next to it. Step transitions, consultations
opening and closing, jumps, blocks finishing.

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

from workflow_state import fail_open, load_state, read_event, state_path, written_path

HOOK = "state-writer"


def snapshot(state: dict) -> dict:
    return {
        "phase": state.get("phase"),
        "intake_step": state.get("intake_step"),
        "blocks": {
            b.get("id"): {"step": b.get("step"), "status": b.get("status")}
            for b in state.get("blocks", [])
        },
        "open_consultations": [
            c.get("id") for c in state.get("consultations", []) if c.get("status") == "open"
        ],
        "jumps": len(state.get("jump_log", [])),
    }


def diff(previous: dict, current: dict) -> list[dict]:
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


def main() -> None:
    event = read_event()
    target = written_path(event)
    if not target or Path(target).name != "state.json":
        sys.exit(0)

    path = state_path(HOOK)
    try:
        if Path(target).resolve() != path.resolve():
            sys.exit(0)
    except OSError:
        sys.exit(0)

    state = load_state(HOOK)
    current = snapshot(state)

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
