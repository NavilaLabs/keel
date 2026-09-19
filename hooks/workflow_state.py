#!/usr/bin/env python3
"""Shared helpers for the ticket workflow hooks.

Every hook in this directory follows the same two rules:

- **Fail open on its own problems.** Missing configuration, unreadable state,
  a tool that is not installed: exit 1. The message reaches the developer,
  Claude proceeds. A hook that halts development when it is itself
  misconfigured gets disabled within two days, and then it protects nothing.

- **Exit 2 only on a genuine workflow violation.** On PreToolUse that cancels
  the tool call and hands stderr back to Claude as the reason. On PostToolUse
  it cannot cancel anything, but the message still reaches Claude, which is
  what the state-level hooks rely on.

Configuration is read from .claude/keel.json in the project, with environment
variables taking precedence:

    {
      "ticket_repo": "../ticket-repo-myproject",
      "ticket_id": "PROJ-1234"
    }

ticket_id is usually left out of that file and kept in .keel-ticket instead,
since it changes per ticket while ticket_repo does not.

The same file records, once per project, where tickets and pull requests live
and which environment variable holds the token for each:

    {
      "tickets": {
        "source": "github",
        "repository": "NavilaLabs/keel-web",
        "token_env": "GITHUB_PERSONAL_ACCESS_TOKEN"
      },
      "pull_requests": {
        "host": "github",
        "repository": "NavilaLabs/keel-web",
        "token_env": "GITHUB_PERSONAL_ACCESS_TOKEN"
      }
    }

Only the name of the variable is stored, never the token.
"""

import json
import os
import sys
from pathlib import Path

IMPLEMENTATION_STEPS = ("8", "9")
CONFIG_FILE = Path(".claude/keel.json")
TICKET_MARKER = Path(".keel-ticket")


def fail_open(hook: str, message: str) -> None:
    print(f"{hook}: {message}", file=sys.stderr)
    sys.exit(1)


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def read_event() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def _config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def ticket_repo(hook: str) -> Path:
    repo = os.environ.get("KEEL_TICKET_REPO") or _config().get("ticket_repo")
    if not repo:
        fail_open(
            hook,
            f"no ticket repo configured - set KEEL_TICKET_REPO or ticket_repo in "
            f"{CONFIG_FILE}. Skipping check",
        )
    path = Path(repo)
    if not path.is_dir():
        fail_open(hook, f"ticket repo {path} is not a directory, skipping check")
    return path


def ticket_id(hook: str) -> str:
    tid = os.environ.get("KEEL_TICKET_ID")
    if not tid and TICKET_MARKER.is_file():
        tid = TICKET_MARKER.read_text(encoding="utf-8").strip()
    if not tid:
        tid = _config().get("ticket_id")
    if not tid:
        fail_open(
            hook,
            f"no active ticket - set KEEL_TICKET_ID or write the id to {TICKET_MARKER}. "
            f"Skipping check",
        )
    return tid


def state_path(hook: str) -> Path:
    return ticket_repo(hook) / "tickets" / ticket_id(hook) / "state.json"


def load_state(hook: str) -> dict:
    path = state_path(hook)
    if not path.is_file():
        fail_open(hook, f"no state file at {path}, skipping check")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail_open(hook, f"state file is not valid JSON: {exc}")


def written_path(event: dict) -> str | None:
    return event.get("tool_input", {}).get("file_path")


def written_content(event: dict) -> str | None:
    """Best-effort access to what a write or edit would produce.

    Write carries the whole content, Edit only the replacement fragment.
    Callers that need the full resulting document should read the file in a
    PostToolUse hook instead of reconstructing it here.
    """
    tool_input = event.get("tool_input", {})
    return tool_input.get("content") or tool_input.get("new_string")


def is_inside_project(path: str) -> bool:
    """Workflow hooks guard the code repo. Files elsewhere are none of their business."""
    try:
        return Path(path).resolve().is_relative_to(Path.cwd().resolve())
    except OSError:
        return True


def describe_service(label: str, service: dict, kind_key: str, environ: dict) -> str:
    """One line for the session banner. Never contains the token itself."""
    kind = service.get(kind_key, "(kind not configured)")
    repository = service.get("repository")
    where = f"{kind}, {repository}" if repository else kind
    token_env = service.get("token_env")
    if not token_env:
        return f"{label}: {where}. No token variable configured."
    state = "set" if environ.get(token_env) else "NOT set in this environment"
    return f"{label}: {where}. Token in ${token_env} ({state})."


def describe_services(config: dict, environ: dict) -> list[str]:
    lines = []
    if "tickets" in config:
        lines.append(describe_service("Tickets", config["tickets"], "source", environ))
    if "pull_requests" in config:
        lines.append(
            describe_service("Pull requests", config["pull_requests"], "host", environ)
        )
    return lines


def is_implementing(block: dict) -> bool:
    """A finished block keeps its last step (9) but no longer implements."""
    return (
        str(block.get("step", "")).startswith(IMPLEMENTATION_STEPS)
        and block.get("status") != "done"
    )


def blocks_in_implementation(state: dict) -> list[dict]:
    return [b for b in state.get("blocks", []) if is_implementing(b)]


def open_consultations(state: dict) -> list[dict]:
    return [c for c in state.get("consultations", []) if c.get("status") == "open"]
