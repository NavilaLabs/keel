#!/usr/bin/env python3
"""keel status line: show that keel is active, and where the ticket stands.

Claude Code passes session JSON on stdin and renders whatever this prints.
Enable it with /keel:statusline, which patches the user's settings - a plugin
cannot set statusLine itself, only the agent and subagentStatusLine keys.

What it shows, in rising order of usefulness:

    ⚓ keel                              installed, no project configured
    ⚓ keel · no ticket                  configured, nothing active
    ⚓ keel · PROJ-1234 · intake 2       working through the intake zone
    ⚓ keel · PROJ-1234 · block-1 · 7.2  inside a theme block
    ⚓ keel · PROJ-1234 · 7 · waiting    a consultation is open - your move

The last one is the point. Consultations are where the workflow hands control
back, and a run that is waiting looks exactly like a run that is thinking
unless something says otherwise.
"""

import json
import sys
from pathlib import Path

DIM = "\033[2m"
BOLD = "\033[1m"
AMBER = "\033[33m"
RESET = "\033[0m"

ANCHOR = "⚓"
SEP = f"{DIM} · {RESET}"


def emit(*parts: str) -> None:
    print(f"{DIM}{ANCHOR} keel{RESET}" + "".join(SEP + p for p in parts if p))
    sys.exit(0)


def main() -> None:
    try:
        session = json.load(sys.stdin)
    except json.JSONDecodeError:
        session = {}

    cwd = Path(session.get("workspace", {}).get("current_dir") or session.get("cwd") or ".")

    config_file = cwd / ".claude" / "keel.json"
    if not config_file.is_file():
        emit()

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        emit(f"{AMBER}config unreadable{RESET}")

    marker = cwd / ".keel-ticket"
    ticket = None
    if marker.is_file():
        ticket = marker.read_text(encoding="utf-8").strip() or None
    ticket = ticket or config.get("ticket_id")
    if not ticket:
        emit("no ticket")

    repo = config.get("ticket_repo")
    if not repo:
        emit(ticket, f"{AMBER}no ticket repo{RESET}")

    state_file = (cwd / repo) / "tickets" / ticket / "state.json"
    if not state_file.is_file():
        emit(ticket, "not started")

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        emit(ticket, f"{AMBER}state unreadable{RESET}")

    waiting = [c for c in state.get("consultations", []) if c.get("status") == "open"]
    phase = state.get("phase", "?")

    if phase == "intake":
        position = f"intake {state.get('intake_step', '?')}"
    elif phase == "blocks":
        active = [b for b in state.get("blocks", []) if b.get("status") != "done"]
        if not active:
            position = "blocks done"
        elif len(active) == 1:
            position = f"{active[0].get('id', '?')} · {active[0].get('step', '?')}"
        else:
            steps = ", ".join(sorted({str(b.get("step", "?")) for b in active}))
            position = f"{len(active)} blocks · {steps}"
    else:
        position = phase

    if waiting:
        emit(f"{BOLD}{ticket}{RESET}", position, f"{AMBER}waiting on you{RESET}")
    emit(ticket, position)


if __name__ == "__main__":
    main()
