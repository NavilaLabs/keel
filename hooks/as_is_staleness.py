#!/usr/bin/env python3
"""as-is-staleness: require step 7.0 when main moved under the to-be branch.

PreToolUse on Edit|Write, acting only on files under architecture/.

A ticket that ran for weeks may be planning against an as-is model that
someone else has since changed. Without this check, step 7.1 quietly builds
a to-be model on top of a stale base, and the conflict only surfaces at the
merge in step 12, long after the design consultation that should have caught
it.

Compares as_is_base_commit from state.json against the ticket repo's current
main. On drift it blocks and names the architecture files that changed, so
step 7.0 has something concrete to consult about.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import subprocess

from workflow_state import block, fail_open, load_state, read_event, ticket_repo, written_path

HOOK = "as-is-staleness"
MAIN = "main"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        fail_open(HOOK, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    event = read_event()
    target = written_path(event)
    if not target or "architecture" not in Path(target).parts:
        sys.exit(0)

    state = load_state(HOOK)
    base = state.get("as_is_base_commit")
    if not base:
        fail_open(HOOK, "state.json has no as_is_base_commit, skipping check")

    repo = ticket_repo(HOOK)
    current = git(repo, "rev-parse", MAIN)
    if current == base:
        sys.exit(0)

    changed = git(repo, "diff", "--name-only", f"{base}..{MAIN}", "--", "architecture/")
    if not changed:
        # main moved, but not the architecture model. No drift that matters.
        sys.exit(0)

    files = "\n".join(f"  - {line}" for line in changed.splitlines())
    block(
        f"Blocked: the as-is model has moved since this ticket branched.\n"
        f"Base was {base[:8]}, {MAIN} is now {current[:8]}. Changed:\n{files}\n\n"
        f"This is step 7.0. Rebase the to-be branch onto current {MAIN}, check "
        f"whether the changes overlap this block's claimed_components, and consult "
        f"the developer before continuing with 7.1. Then update as_is_base_commit."
    )


if __name__ == "__main__":
    main()
