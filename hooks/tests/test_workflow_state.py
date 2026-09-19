import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow_state import blocks_in_implementation


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


if __name__ == "__main__":
    unittest.main()
