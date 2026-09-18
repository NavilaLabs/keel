#!/usr/bin/env python3
"""block-overlap: catch theme blocks that were never independent.

PostToolUse on Edit|Write, acting only on state.json.

When two blocks claim the same LikeC4 component, the split made at step 4 was
wrong: they cannot be planned independently, and step 8's sequential rule
would have them editing the same contracts. The workflow's answer is a jump
back to 4.

This runs as PostToolUse rather than PreToolUse deliberately. An Edit call
carries only the replacement fragment, not the resulting document, so
checking beforehand would mean reconstructing the file and guessing. After
the write, the real state.json is on disk and the check is exact. PostToolUse
cannot cancel the write - it does not need to, because the violation is in
recorded state rather than in code, and exit 2 still delivers the message to
Claude, which is what triggers the jump.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from workflow_state import block, load_state, read_event, state_path, written_path

HOOK = "block-overlap"


def main() -> None:
    event = read_event()
    target = written_path(event)
    if not target or Path(target).name != "state.json":
        sys.exit(0)

    try:
        if Path(target).resolve() != state_path(HOOK).resolve():
            sys.exit(0)
    except OSError:
        sys.exit(0)

    state = load_state(HOOK)

    owners: dict[str, str] = {}
    collisions: list[tuple[str, str, str]] = []

    for blk in state.get("blocks", []):
        block_id = blk.get("id", "?")
        if blk.get("status") == "done":
            continue
        for component in blk.get("claimed_components", []):
            if component in owners and owners[component] != block_id:
                collisions.append((component, owners[component], block_id))
            else:
                owners[component] = block_id

    if not collisions:
        sys.exit(0)

    lines = "\n".join(
        f"  - {component}: claimed by both '{first}' and '{second}'"
        for component, first, second in collisions
    )
    block(
        f"Theme blocks overlap:\n{lines}\n\n"
        f"Blocks claiming the same component are not independently plannable, "
        f"which is what a theme block is supposed to be. This is a jump back to "
        f"step 4: re-cut the blocks, consult the developer, and log the jump with "
        f"trigger block_overlap."
    )


if __name__ == "__main__":
    main()
