#!/usr/bin/env python3
"""keel session start: announce that keel governs this repo, and where it stands.

SessionStart hook. Its stdout is injected as context at the start of a
session, so this is what makes Claude aware of keel without you having to say
so - and, when a ticket is already running, what lets it re-enter at the
recorded step instead of asking you where things stood.

It never blocks. A session that starts while keel is misconfigured is a
session that works normally without keel, not a session that refuses to start.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow_state import CONFIG_FILE, TICKET_MARKER, _config

BANNER = "keel is active in this repository."

WORKFLOW = """Development here follows the keel workflow: gather context, agree
the goals, split into theme blocks, fix the architecture in LikeC4 and freeze
the contracts as stubs, and only then implement against them. Hooks enforce
the parts that matter, so an edit that changes a frozen contract during
implementation will be refused rather than silently accepted.

Run /keel:ticket <ticket-id> to start or resume a ticket. Do not start
implementing a ticket outside that command - the workflow's consultations are
where the developer stays in control of the design."""


def main() -> None:
    if not CONFIG_FILE.is_file():
        # Installed, but this repo is not set up for it. Say nothing: an
        # unconfigured repo is a repo keel has no opinion about.
        sys.exit(0)

    config = _config()
    repo = config.get("ticket_repo", "(not configured)")

    ticket = None
    if TICKET_MARKER.is_file():
        ticket = TICKET_MARKER.read_text(encoding="utf-8").strip() or None
    ticket = ticket or config.get("ticket_id")

    lines = [BANNER, "", f"Ticket repo: {repo}", ""]

    if ticket:
        lines += [
            f"Active ticket: {ticket}. Its state is in "
            f"{repo}/tickets/{ticket}/state.json - read it before doing anything "
            f"on this ticket, and re-enter at the step it records rather than "
            f"starting over.",
            "",
        ]
    else:
        lines += ["No active ticket.", ""]

    lines.append(WORKFLOW)
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
