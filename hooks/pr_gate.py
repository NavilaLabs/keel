#!/usr/bin/env python3
"""pr-gate: refuse to open a pull request before the ticket is ready for one.

PreToolUse on Bash, plus the MCP tools that create pull requests.

Step 10 is where the ticket leaves the workflow and becomes something other
people read. Two things have to hold: every theme block is done, and the PR
description links the artifacts - knowledge.md, the ADRs, the LikeC4 views.

The second one is easy to forget and expensive to fix later. Artifacts live
in the ticket repo, so the only thing connecting a reviewer to the reasoning
behind the code is the link in the description. Without it the two repos
drift apart and the ADR nobody can find might as well not exist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import re

from workflow_state import block, load_state, read_event

HOOK = "pr-gate"

BASH_PR = re.compile(r"\b(gh\s+pr\s+create|glab\s+mr\s+create)\b")
MCP_PR = re.compile(r"(create|open).*(pull_request|pullrequest|_pr\b)", re.IGNORECASE)


def creates_pr(event: dict) -> bool:
    tool = event.get("tool_name", "")
    if tool == "Bash":
        return bool(BASH_PR.search(event.get("tool_input", {}).get("command", "")))
    return bool(MCP_PR.search(tool))


def main() -> None:
    event = read_event()
    if not creates_pr(event):
        sys.exit(0)

    state = load_state(HOOK)

    unfinished = [b for b in state.get("blocks", []) if b.get("status") != "done"]
    if unfinished:
        listed = "\n".join(
            f"  - {b.get('id')} ({b.get('title', 'untitled')}) is {b.get('status')} "
            f"at step {b.get('step')}"
            for b in unfinished
        )
        block(
            f"Blocked: {len(unfinished)} theme block(s) are not done:\n{listed}\n\n"
            f"Step 10 runs once, after every block has been through 6 to 9."
        )

    artifacts = state.get("artifacts", {})
    missing = []
    if not artifacts.get("knowledge"):
        missing.append("knowledge.md path")
    if not artifacts.get("c4_views"):
        missing.append("LikeC4 view ids")

    any_adr_expected = any(b.get("adrs") for b in state.get("blocks", []))
    if any_adr_expected and not artifacts.get("adrs"):
        missing.append("ADR paths (blocks recorded ADRs, artifacts lists none)")

    if missing:
        listed = "\n".join(f"  - {item}" for item in missing)
        block(
            f"Blocked: artifacts are not recorded in state.json:\n{listed}\n\n"
            f"The PR description has to link them - they live in the ticket repo, "
            f"so the link is the only thing connecting a reviewer to the reasoning "
            f"behind this code. Record them, put them in the description, then "
            f"open the PR."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
