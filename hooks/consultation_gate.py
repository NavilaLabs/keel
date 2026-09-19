#!/usr/bin/env python3
"""consultation-gate: refuse to keep working while a consultation is open.

PreToolUse on Edit|Write|NotebookEdit.

The workflow says: ask, stop, wait. Without enforcement that is a promise an
agent can break by asking a question and continuing in the same turn, which
turns the consultation into a notification.

There is no tool event for "moved to the next step", so this hook uses writes
as the proxy: an open consultation means nothing gets written. That covers
every way a step actually advances, since a step that changes nothing on disk
has nothing to review anyway.

Exempt: state.json, because answering a consultation means writing it, and
knowledge.md, because a consultation may be answered by recording something.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from workflow_state import (
    block,
    load_state,
    open_consultations,
    is_inside_project,
    read_event,
    state_path,
    written_path,
)

HOOK = "consultation-gate"
EXEMPT_NAMES = {"state.json", "knowledge.md"}


def main() -> None:
    event = read_event()
    target = written_path(event)
    if not target or not is_inside_project(target):
        sys.exit(0)

    if Path(target).name in EXEMPT_NAMES:
        sys.exit(0)

    state = load_state(HOOK)

    try:
        if Path(target).resolve() == state_path(HOOK).resolve():
            sys.exit(0)
    except OSError:
        pass

    pending = open_consultations(state)
    if not pending:
        sys.exit(0)

    first = pending[0]
    question = first.get("question", "(no question recorded)")
    step = first.get("step", "?")

    block(
        f"Blocked: consultation {first.get('id')} at step {step} is still open.\n"
        f"Question: {question}\n"
        f"The workflow pauses here until the developer answers. Do not continue "
        f"working around it. Present the result of the step, wait for the answer, "
        f"record it in state.json, then resume."
    )


if __name__ == "__main__":
    main()
