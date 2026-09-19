import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow_state import (
    blocks_in_implementation,
    configured_ticket_repo,
    describe_services,
    is_workflow_path,
)


def state_with(*blocks: dict) -> dict:
    return {"blocks": list(blocks)}


class BlocksInImplementationTest(unittest.TestCase):
    def test_counts_blocks_at_steps_8_and_9(self):
        state = state_with(
            {"id": "b1", "step": "8", "status": "in_progress"},
            {"id": "b2", "step": "9.1", "status": "in_progress"},
        )
        self.assertEqual(["b1", "b2"], [b["id"] for b in blocks_in_implementation(state)])

    def test_ignores_blocks_before_step_8(self):
        state = state_with({"id": "b1", "step": "7", "status": "awaiting_consultation"})
        self.assertEqual([], blocks_in_implementation(state))

    def test_ignores_done_block_that_kept_its_last_step(self):
        state = state_with(
            {"id": "b1", "step": "9", "status": "done"},
            {"id": "b2", "step": "8", "status": "in_progress"},
        )
        self.assertEqual(["b2"], [b["id"] for b in blocks_in_implementation(state)])


class DescribeServicesTest(unittest.TestCase):
    config = {
        "tickets": {
            "source": "github",
            "repository": "NavilaLabs/keel-web",
            "token_env": "GITHUB_PERSONAL_ACCESS_TOKEN",
        },
        "pull_requests": {"host": "bitbucket"},
    }

    def test_reports_kind_repository_and_token_variable(self):
        lines = describe_services(self.config, {"GITHUB_PERSONAL_ACCESS_TOKEN": "secret"})
        self.assertEqual(
            "Tickets: github, NavilaLabs/keel-web. Token in $GITHUB_PERSONAL_ACCESS_TOKEN (set).",
            lines[0],
        )

    def test_never_contains_the_token_value(self):
        lines = describe_services(self.config, {"GITHUB_PERSONAL_ACCESS_TOKEN": "secret"})
        self.assertNotIn("secret", "\n".join(lines))

    def test_reports_a_missing_token_variable(self):
        lines = describe_services(self.config, {})
        self.assertIn("NOT set in this environment", lines[0])

    def test_reports_a_service_without_token_variable(self):
        lines = describe_services(self.config, {})
        self.assertEqual("Pull requests: bitbucket. No token variable configured.", lines[1])

    def test_reports_nothing_without_configuration(self):
        self.assertEqual([], describe_services({}, {}))

    def test_reports_a_service_that_is_not_an_object(self):
        lines = describe_services({"tickets": "github"}, {})
        self.assertEqual("Tickets: configured as 'github', which is not an object.", lines[0])


class TicketRepoPathTest(unittest.TestCase):
    def test_expands_a_leading_tilde(self):
        with mock.patch.dict(os.environ, {"KEEL_TICKET_REPO": "~/tickets"}):
            self.assertEqual(Path.home() / "tickets", configured_ticket_repo())

    def test_is_none_without_configuration(self):
        self.addCleanup(os.chdir, Path.cwd())
        with mock.patch.dict(os.environ, {}, clear=True):
            with tempfile.TemporaryDirectory() as empty:
                os.chdir(empty)
                self.assertIsNone(configured_ticket_repo())


class IsWorkflowPathTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.code_repo = root / "code"
        self.ticket_repo = root / "tickets"
        self.code_repo.mkdir()
        self.ticket_repo.mkdir()
        (self.code_repo / ".claude").mkdir()
        (self.code_repo / ".claude" / "keel.json").write_text(
            json.dumps({"ticket_repo": str(self.ticket_repo)})
        )
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.code_repo)

    def test_code_repo_file_belongs_to_the_workflow(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(is_workflow_path("src/main.py"))

    def test_ticket_repo_file_belongs_to_the_workflow(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            model = self.ticket_repo / "architecture" / "container-api.c4"
            self.assertTrue(is_workflow_path(str(model)))

    def test_file_outside_both_repositories_does_not(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_workflow_path(str(Path(self.directory.name) / "elsewhere.md")))

    def test_file_outside_both_when_no_ticket_repo_is_configured(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            (self.code_repo / ".claude" / "keel.json").write_text("{}")
            self.assertFalse(is_workflow_path(str(self.ticket_repo / "notes.md")))


if __name__ == "__main__":
    unittest.main()
