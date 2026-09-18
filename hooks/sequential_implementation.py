#!/usr/bin/env python3
"""sequential-implementation: only one block may be implementing at a time.

PreToolUse on Edit|Write|NotebookEdit.

Theme blocks run in parallel through steps 6 and 7, where the wait is the
developer's consultation and parallelism actually saves time. From step 8
onward there are no consultations, so there is nothing to wait for - and two
agents writing into the same branch at once produces conflicts nobody
planned, while stub-lock loses the ability to tell whose contract an edit
belongs to.

Without enforcement, "sequential from 8" is a sentence in a document.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from workflow_state import block, blocks_in_implementation, load_state, read_event, written_path

HOOK = "sequential-implementation"


def main() -> None:
    event = read_event()
    if not written_path(event):
        sys.exit(0)

    state = load_state(HOOK)
    active = blocks_in_implementation(state)

    if len(active) <= 1:
        sys.exit(0)

    listed = "\n".join(
        f"  - {b.get('id')} ({b.get('title', 'untitled')}) at step {b.get('step')}"
        for b in active
    )
    block(
        f"Blocked: {len(active)} blocks are in implementation at once:\n{listed}\n\n"
        f"Steps 8 and 9 run one block at a time. Pick one to finish, set the "
        f"others back to step 7 with status pending in state.json, and continue "
        f"with the one you chose."
    )


if __name__ == "__main__":
    main()
