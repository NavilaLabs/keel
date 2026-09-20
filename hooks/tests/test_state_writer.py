import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state_writer import diff, snapshot
from test_hooks import HookRunner

KNOWLEDGE = "tickets/1/knowledge.md"
ADR = "tickets/1/adr/0004-pino-with-own-request-middleware.md"
LOGGER_STUB = {"path": "server/src/logging/types.ts", "symbol": "Logger"}


def state(**overrides) -> dict:
    base = {
        "ticket_id": "1",
        "phase": "intake",
        "intake_step": "4",
        "blocks": [],
        "consultations": [],
    }
    base.update(overrides)
    return base


def consultation(identifier: str, step: str, block=None, status="open") -> dict:
    return {
        "id": identifier,
        "block": block,
        "step": step,
        "status": status,
        "asked_at": "2026-09-19T13:35:18Z",
    }


def hints_of(previous: dict, current: dict) -> list[dict]:
    return [e for e in diff(previous, current) if e["type"] == "artifact_hint"]


class BaselineTest(unittest.TestCase):
    """A first observation has no history to compare against."""

    def setUp(self):
        self.current = snapshot(
            state(
                intake_step="5",
                artifacts={"knowledge": KNOWLEDGE},
                consultations=[consultation("c3", "5")],
            )
        )

    def test_hints_nothing_without_a_previous_snapshot(self):
        self.assertEqual([], hints_of({}, self.current))

    def test_still_derives_the_state_events(self):
        types = [e["type"] for e in diff({}, self.current)]
        self.assertEqual(["phase_changed", "step_changed", "consultation_opened"], types)


class ConsultationHintTest(unittest.TestCase):
    def setUp(self):
        self.previous = snapshot(state())

    def test_names_knowledge_when_the_step_5_consultation_opens(self):
        current = snapshot(
            state(
                intake_step="5",
                artifacts={"knowledge": KNOWLEDGE},
                consultations=[consultation("c3", "5")],
            )
        )
        self.assertEqual(
            [
                {
                    "type": "artifact_hint",
                    "block": None,
                    "step": "5",
                    "consultation": "c3",
                    "targets": [{"kind": "knowledge", "repo": "ticket", "path": KNOWLEDGE}],
                }
            ],
            hints_of(self.previous, current),
        )

    def test_names_views_stubs_and_adrs_at_a_plain_step_7_consultation(self):
        current = snapshot(
            state(
                phase="blocks",
                to_be_branch="ticket/1",
                artifacts={"knowledge": KNOWLEDGE, "c4_views": ["server"]},
                blocks=[
                    {
                        "id": "b2",
                        "title": "Logging",
                        "step": "7",
                        "status": "awaiting_consultation",
                        "claimed_stubs": [LOGGER_STUB],
                        "adrs": [ADR],
                    }
                ],
                consultations=[consultation("c7", "7", block="b2")],
            )
        )
        hint = {h["block"]: h for h in hints_of(self.previous, current)}["b2"]
        self.assertEqual("c7", hint["consultation"])
        self.assertEqual(
            [
                {"kind": "c4_view", "view": "server", "branch": "ticket/1"},
                {"kind": "stub", "repo": "code", **LOGGER_STUB},
                {"kind": "adr", "repo": "ticket", "path": ADR},
            ],
            hint["targets"],
        )

    def test_names_the_views_only_at_step_7_1(self):
        # The stubs are already recorded, so only the consultation's own
        # subject remains to be hinted.
        block = {
            "id": "b1",
            "title": "Sessions",
            "step": "7.1",
            "status": "awaiting_consultation",
            "claimed_stubs": [LOGGER_STUB],
        }
        previous = snapshot(state(phase="blocks", blocks=[block]))
        current = snapshot(
            state(
                phase="blocks",
                to_be_branch="ticket/1",
                artifacts={"c4_views": ["context", "server"]},
                blocks=[block],
                consultations=[consultation("c8", "7.1", block="b1")],
            )
        )
        hint = {h["block"]: h for h in hints_of(previous, current)}["b1"]
        self.assertEqual(
            [
                {"kind": "c4_view", "view": "context", "branch": "ticket/1"},
                {"kind": "c4_view", "view": "server", "branch": "ticket/1"},
            ],
            hint["targets"],
        )

    def test_carries_no_branch_before_a_to_be_branch_exists(self):
        current = snapshot(
            state(
                phase="blocks",
                artifacts={"c4_views": ["server"]},
                blocks=[
                    {"id": "b1", "title": "Sessions", "step": "7.1", "status": "in_progress"}
                ],
                consultations=[consultation("c8", "7.1", block="b1")],
            )
        )
        hint = {h["block"]: h for h in hints_of(self.previous, current)}["b1"]
        self.assertEqual([{"kind": "c4_view", "view": "server"}], hint["targets"])

    def test_names_the_stubs_of_that_block_only_at_step_7_2(self):
        current = snapshot(
            state(
                phase="blocks",
                blocks=[
                    {
                        "id": "b1",
                        "title": "Sessions",
                        "step": "7.2",
                        "status": "awaiting_consultation",
                        "claimed_stubs": [LOGGER_STUB],
                    },
                    {
                        "id": "b2",
                        "title": "Client",
                        "step": "6",
                        "status": "pending",
                        "claimed_stubs": [{"path": "client/src/connection/types.ts"}],
                    },
                ],
                consultations=[consultation("c9", "7.2", block="b1")],
            )
        )
        hints = {h["block"]: h for h in hints_of(self.previous, current)}
        self.assertEqual("c9", hints["b1"]["consultation"])
        self.assertEqual(
            [{"kind": "stub", "repo": "code", **LOGGER_STUB}], hints["b1"]["targets"]
        )
        self.assertNotIn("consultation", hints["b2"])

    def test_hints_nothing_for_a_step_whose_subject_is_not_an_artefact(self):
        current = snapshot(
            state(consultations=[consultation("c2", "4")], artifacts={"knowledge": KNOWLEDGE})
        )
        hints = hints_of(self.previous, current)
        self.assertEqual([], [h for h in hints if h.get("consultation")])


class RecordedArtifactTest(unittest.TestCase):
    """An artefact the state names for the first time, consultation or not."""

    def test_hints_a_newly_recorded_adr(self):
        previous = snapshot(state(phase="blocks", artifacts={"knowledge": KNOWLEDGE}))
        current = snapshot(
            state(phase="blocks", artifacts={"knowledge": KNOWLEDGE, "adrs": [ADR]})
        )
        self.assertEqual(
            [{"kind": "adr", "repo": "ticket", "path": ADR}],
            hints_of(previous, current)[0]["targets"],
        )

    def test_takes_the_step_from_the_state_when_no_consultation_opened(self):
        previous = snapshot(state(intake_step="5"))
        current = snapshot(state(intake_step="5", artifacts={"knowledge": KNOWLEDGE}))
        hint = hints_of(previous, current)[0]
        self.assertEqual("5", hint["step"])
        self.assertNotIn("consultation", hint)

    def test_hints_a_rewritten_artefact_only_once(self):
        previous = snapshot(state(artifacts={"knowledge": KNOWLEDGE}))
        current = snapshot(state(intake_step="5", artifacts={"knowledge": KNOWLEDGE}))
        self.assertEqual([], hints_of(previous, current))

    def test_merges_a_newly_recorded_stub_into_the_consultation_hint(self):
        previous = snapshot(
            state(
                phase="blocks",
                blocks=[{"id": "b1", "title": "Sessions", "step": "7.1", "status": "in_progress"}],
            )
        )
        current = snapshot(
            state(
                phase="blocks",
                blocks=[
                    {
                        "id": "b1",
                        "title": "Sessions",
                        "step": "7.2",
                        "status": "awaiting_consultation",
                        "claimed_stubs": [LOGGER_STUB],
                    }
                ],
                consultations=[consultation("c9", "7.2", block="b1")],
            )
        )
        hints = hints_of(previous, current)
        self.assertEqual(1, len(hints))
        self.assertEqual("c9", hints[0]["consultation"])
        self.assertEqual([{"kind": "stub", "repo": "code", **LOGGER_STUB}], hints[0]["targets"])

    def test_leaves_out_what_a_block_hint_already_names(self):
        # Step 7 records the views, the stubs and the ADRs in one write, so
        # every one of them is both newly recorded and the consultation's
        # subject. A UI should still move the view once.
        previous = snapshot(
            state(
                phase="blocks",
                blocks=[{"id": "b1", "title": "Sessions", "step": "7.1", "status": "in_progress"}],
            )
        )
        current = snapshot(
            state(
                phase="blocks",
                to_be_branch="ticket/1",
                artifacts={"c4_views": ["server"], "adrs": [ADR]},
                blocks=[
                    {
                        "id": "b1",
                        "title": "Sessions",
                        "step": "7",
                        "status": "awaiting_consultation",
                        "claimed_stubs": [LOGGER_STUB],
                        "adrs": [ADR],
                    }
                ],
                consultations=[consultation("c6", "7", block="b1")],
            )
        )
        hints = hints_of(previous, current)
        self.assertEqual(["b1"], [h["block"] for h in hints])
        self.assertEqual(
            [
                {"kind": "c4_view", "view": "server", "branch": "ticket/1"},
                {"kind": "stub", "repo": "code", **LOGGER_STUB},
                {"kind": "adr", "repo": "ticket", "path": ADR},
            ],
            hints[0]["targets"],
        )

    def test_keeps_a_ticket_wide_artefact_no_block_claims(self):
        shared = "tickets/1/adr/0002-claude-code-config-as-named-volume.md"
        previous = snapshot(
            state(
                phase="blocks",
                blocks=[{"id": "b1", "title": "Sessions", "step": "7.1", "status": "in_progress"}],
            )
        )
        current = snapshot(
            state(
                phase="blocks",
                artifacts={"adrs": [ADR, shared]},
                blocks=[
                    {
                        "id": "b1",
                        "title": "Sessions",
                        "step": "7",
                        "status": "awaiting_consultation",
                        "adrs": [ADR],
                    }
                ],
                consultations=[consultation("c6", "7", block="b1")],
            )
        )
        hints = hints_of(previous, current)
        self.assertEqual([None, "b1"], [h["block"] for h in hints])
        self.assertEqual(
            [{"kind": "adr", "repo": "ticket", "path": shared}], hints[0]["targets"]
        )

    def test_hints_nothing_when_the_state_did_not_move(self):
        unchanged = snapshot(state(artifacts={"knowledge": KNOWLEDGE}))
        self.assertEqual([], diff(unchanged, unchanged))


class OlderCacheTest(unittest.TestCase):
    """A snapshot written before hints existed is still a valid comparison."""

    def setUp(self):
        self.previous = {
            "phase": "intake",
            "intake_step": "5",
            "blocks": {},
            "open_consultations": ["c3"],
            "jumps": 0,
        }
        self.current = snapshot(
            state(
                intake_step="5",
                artifacts={"knowledge": KNOWLEDGE, "adrs": [ADR]},
                consultations=[consultation("c3", "5")],
            )
        )

    def test_does_not_reopen_a_consultation_it_has_no_detail_for(self):
        self.assertEqual([], [e for e in diff(self.previous, self.current) if "consultation" in e])

    def test_hints_nothing_for_artefacts_it_never_recorded(self):
        self.assertEqual([], hints_of(self.previous, self.current))


class TriggerTest(unittest.TestCase):
    HOOK = "state_writer.py"

    def setUp(self):
        self.runner = HookRunner(state())
        self.addCleanup(self.runner.cleanup)
        self.state_file = self.runner.ticket_repo / "tickets" / "1" / "state.json"
        self.stream = self.runner.ticket_repo / "tickets" / "1" / "events.jsonl"

    def advance(self) -> None:
        self.state_file.write_text(
            json.dumps(
                state(
                    intake_step="5",
                    artifacts={"knowledge": KNOWLEDGE},
                    consultations=[consultation("c3", "5")],
                )
            )
        )

    def events(self) -> list[dict]:
        return [json.loads(line) for line in self.stream.read_text().splitlines()]

    def test_observes_a_state_file_moved_by_a_shell_command(self):
        self.assertEqual(0, self.runner.run(self.HOOK, self.state_file))
        self.advance()
        self.assertEqual(0, self.runner.run(self.HOOK))
        hints = [e for e in self.events() if e["type"] == "artifact_hint"]
        self.assertEqual("c3", hints[0]["consultation"])
        self.assertIn("at", hints[0])

    def test_exits_quietly_when_no_ticket_is_active(self):
        (self.runner.code_repo / ".keel-ticket").unlink()
        self.assertEqual(0, self.runner.run(self.HOOK))
        self.assertEqual("", self.runner.result.stderr)
        self.assertFalse(self.stream.exists())

    def test_ignores_an_editor_write_to_another_file(self):
        self.assertEqual(0, self.runner.run(self.HOOK, self.runner.code_repo / "src" / "main.py"))
        self.assertFalse(self.stream.exists())


if __name__ == "__main__":
    unittest.main()
