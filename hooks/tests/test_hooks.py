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

    def run(self, hook: str, written_file: Path) -> int:
        event = {"tool_input": {"file_path": str(written_file)}}
        result = subprocess.run(
            [sys.executable, str(HOOKS / hook)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            cwd=self.code_repo,
            env={name: value for name, value in os.environ.items() if not name.startswith("KEEL_")},
        )
        return result.returncode

    def cleanup(self):
        self.directory.cleanup()


class SequentialImplementationTest(unittest.TestCase):
    def setUp(self):
        self.runner = HookRunner({"blocks": TWO_BLOCKS_IMPLEMENTING})
        self.addCleanup(self.runner.cleanup)

    def test_blocks_a_write_inside_the_code_repo(self):
        written = self.runner.code_repo / "src" / "main.py"
        self.assertEqual(2, self.runner.run("sequential_implementation.py", written))

    def test_allows_a_write_outside_the_code_repo(self):
        written = self.runner.ticket_repo / "notes.md"
        self.assertEqual(0, self.runner.run("sequential_implementation.py", written))


class ConsultationGateTest(unittest.TestCase):
    def setUp(self):
        self.runner = HookRunner({"blocks": [], "consultations": OPEN_CONSULTATION})
        self.addCleanup(self.runner.cleanup)

    def test_blocks_a_write_inside_the_code_repo(self):
        written = self.runner.code_repo / "src" / "main.py"
        self.assertEqual(2, self.runner.run("consultation_gate.py", written))

    def test_allows_a_write_outside_the_code_repo(self):
        written = self.runner.ticket_repo / "notes.md"
        self.assertEqual(0, self.runner.run("consultation_gate.py", written))

    def test_allows_writing_knowledge_inside_the_code_repo(self):
        written = self.runner.code_repo / "knowledge.md"
        self.assertEqual(0, self.runner.run("consultation_gate.py", written))


if __name__ == "__main__":
    unittest.main()
