#!/usr/bin/env python3
"""stub-lock: refuse edits to frozen contracts during implementation.

PreToolUse on Edit|Write|NotebookEdit. PreToolUse is the only place this can
work: exit code 2 there cancels the tool call before it runs and hands stderr
back to Claude as the reason. PostToolUse cannot block, because the write has
already happened.

The rule it enforces: contracts are frozen in step 7.2 and may only change via
a jump back to step 7, which carries a consultation. Without this hook that
rule is a convention an agent can quietly ignore mid-implementation.

Language independence: the hook never parses signatures. It locks the *file*
that declares the contract (Rust trait, PHP interface, Dart abstract class),
which is the unit that stays stable across languages. Where contract and
implementation share one file, locking it would block all work, so such stubs
are marked shared_file and only produce a warning.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow_state import (
    IMPLEMENTATION_STEPS,
    block,
    load_state,
    read_event,
    written_path,
)

HOOK = "stub-lock"


def main() -> None:
    event = read_event()
    target = written_path(event)
    if not target:
        sys.exit(0)

    state = load_state(HOOK)

    try:
        target_resolved = Path(target).resolve()
    except OSError:
        sys.exit(0)

    for blk in state.get("blocks", []):
        step = str(blk.get("step", ""))
        if not step.startswith(IMPLEMENTATION_STEPS):
            continue

        for stub in blk.get("claimed_stubs", []):
            stub_path = Path(stub.get("path", ""))
            try:
                if stub_path.resolve() != target_resolved:
                    continue
            except OSError:
                continue

            symbol = stub.get("symbol") or stub_path.name

            if stub.get("shared_file"):
                print(
                    f"stub-lock: {symbol} shares this file with its implementation, "
                    f"so the file is not locked. Do not change the signature - that "
                    f"requires a jump back to step 7.",
                    file=sys.stderr,
                )
                sys.exit(0)

            block(
                f"Blocked: {symbol} in {stub.get('path')} is a contract frozen in "
                f"step 7.2, and block '{blk.get('id')}' is in step {step}.\n"
                f"Changing a signature here is not an implementation detail - it is "
                f"a jump back to step 7, which requires consulting the developer.\n"
                f"Stop, state what the contract needs to become and why, and wait "
                f"for a decision before editing this file."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
