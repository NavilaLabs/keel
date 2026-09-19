import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow_state import blocks_in_implementation, describe_services, is_inside_project


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


class IsInsideProjectTest(unittest.TestCase):
    def test_current_directory_content_is_inside(self):
        self.assertTrue(is_inside_project("some/new/file.txt"))

    def test_parent_directory_is_outside(self):
        self.assertFalse(is_inside_project(".."))


if __name__ == "__main__":
    unittest.main()
