import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]

TWO_BLOCKS_IMPLEMENTING = [
    {"id": "b1", "step": "8", "status": "in_progress"},
    {"id": "b2", "step": "9", "status": "in_progress"},
]
OPEN_CONSULTATION = [{"id": "c1", "step": "7", "question": "Ok?", "status": "open"}]


class HookRunner:
    """A code repo and a ticket repo in temporary directories."""

    def __init__(self, state: dict):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.code_repo = root / "code"
        self.ticket_repo = root / "tickets"
        (self.code_repo / ".claude").mkdir(parents=True)
        (self.ticket_repo / "tickets" / "1").mkdir(parents=True)
        (self.code_repo / ".claude" / "keel.json").write_text(
            json.dumps({"ticket_repo": str(self.ticket_repo)})
        )
        (self.code_repo / ".keel-ticket").write_text("1")
        (self.ticket_repo / "tickets" / "1" / "state.json").write_text(json.dumps(state))

    def run(self, hook: str, written_file: Path | None = None) -> int:
        """A written file names itself; Bash and Stop events name nothing."""
        event = {"tool_input": {"file_path": str(written_file)}} if written_file else {}
        result = subprocess.run(
            [sys.executable, str(HOOKS / hook)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            cwd=self.code_repo,
            env={name: value for name, value in os.environ.items() if not name.startswith("KEEL_")},
        )
        self.result = result
        return result.returncode

    def cleanup(self):
        self.directory.cleanup()


class SequentialImplementationTest(unittest.TestCase):
    HOOK = "sequential_implementation.py"

    def setUp(self):
        self.runner = HookRunner({"blocks": TWO_BLOCKS_IMPLEMENTING})
        self.addCleanup(self.runner.cleanup)

    def test_blocks_a_write_in_the_code_repo(self):
        written = self.runner.code_repo / "src" / "main.py"
        self.assertEqual(2, self.runner.run(self.HOOK, written))

    def test_allows_the_state_file_that_resolves_the_situation(self):
        written = self.runner.ticket_repo / "tickets" / "1" / "state.json"
        self.assertEqual(0, self.runner.run(self.HOOK, written))

    def test_allows_a_write_outside_both_repositories(self):
        written = Path(self.runner.directory.name) / "elsewhere" / "settings.json"
        self.assertEqual(0, self.runner.run(self.HOOK, written))


class ConsultationGateTest(unittest.TestCase):
    HOOK = "consultation_gate.py"

    def setUp(self):
        self.runner = HookRunner({"blocks": [], "consultations": OPEN_CONSULTATION})
        self.addCleanup(self.runner.cleanup)

    def test_blocks_a_write_in_the_code_repo(self):
        written = self.runner.code_repo / "src" / "main.py"
        self.assertEqual(2, self.runner.run(self.HOOK, written))

    def test_blocks_the_architecture_model_in_the_ticket_repo(self):
        written = self.runner.ticket_repo / "architecture" / "container-api.c4"
        self.assertEqual(2, self.runner.run(self.HOOK, written))

    def test_allows_the_knowledge_file_that_may_hold_the_answer(self):
        written = self.runner.ticket_repo / "tickets" / "1" / "knowledge.md"
        self.assertEqual(0, self.runner.run(self.HOOK, written))

    def test_allows_a_write_outside_both_repositories(self):
        written = Path(self.runner.directory.name) / "elsewhere" / "settings.json"
        self.assertEqual(0, self.runner.run(self.HOOK, written))


if __name__ == "__main__":
    unittest.main()
