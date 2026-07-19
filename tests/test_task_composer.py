from __future__ import annotations

import unittest

from agent_starter.policy_fragments import CODEX_DEPLOYMENT_BOUNDARY
from agent_starter.task_composer import (
    TASK_DEFINITIONS,
    TaskKind,
    TaskValidationError,
    approve_task_contract,
    build_task_contract,
    compose_task_packet,
    render_task_contract,
    render_task_request,
)


class TaskComposerTests(unittest.TestCase):
    def test_starting_choices_and_relevant_questions_match_the_phase_plan(self) -> None:
        self.assertEqual(
            [definition.label for definition in TASK_DEFINITIONS.values()],
            [
                "Add a feature",
                "Fix a problem",
                "Change existing behavior",
                "Review or improve code",
                "Improve tests/documentation",
                "Prepare a deployment plan",
            ],
        )
        feature_keys = [item.key for item in TASK_DEFINITIONS[TaskKind.FEATURE].questions]
        fix_keys = [item.key for item in TASK_DEFINITIONS[TaskKind.FIX].questions]
        change_keys = [item.key for item in TASK_DEFINITIONS[TaskKind.CHANGE].questions]
        self.assertEqual(feature_keys, ["outcome", "example", "preserve", "acceptance"])
        self.assertEqual(fix_keys, ["steps", "observed", "expected", "error_text", "frequency"])
        self.assertEqual(change_keys, ["current", "desired", "compatibility"])
        self.assertNotIn("error_text", feature_keys)

    def test_packet_is_strict_bounded_secret_safe_and_non_executable(self) -> None:
        answers = {
            "steps": "Import a CSV file.",
            "observed": "The program exits with an error.",
            "expected": "Invalid rows should be reported without a crash.",
            "error_text": "ValueError: invalid row",
            "frequency": "consistent",
        }
        packet = compose_task_packet("fix", answers)
        self.assertEqual(packet.kind, TaskKind.FIX)
        self.assertEqual(packet.to_dict()["answers"], answers)
        rendered = render_task_request(packet)
        self.assertIn("Task type: Fix a problem", rendered)
        self.assertIn("What happened", rendered)
        self.assertIn("Read `docs/AGENT-INDEX.md` first", rendered)
        self.assertIn("only the task-relevant files", rendered)
        with self.assertRaises(TaskValidationError):
            compose_task_packet("fix", {**answers, "command": "sudo true"})
        with self.assertRaises(TaskValidationError):
            compose_task_packet("fix", {**answers, "error_text": "api_key=secret-value"})
        with self.assertRaises(TaskValidationError):
            compose_task_packet("fix", {**answers, "observed": "x" * 4001})
        with self.assertRaises(TaskValidationError):
            compose_task_packet("fix", {**answers, "frequency": "sometimes-ish"})

    def test_deployment_choice_generates_plan_only_language(self) -> None:
        packet = compose_task_packet("deployment-plan", {
            "target": "A staging Linux host.",
            "current_state": "Local checks pass.",
            "constraints": "No production credentials or changes.",
            "approvals": "Human review before every remote action.",
            "acceptance": "A reviewable plan with rollback steps.",
        })
        rendered = render_task_request(packet)
        self.assertIn("planning only", rendered.lower())
        self.assertIn("must not deploy", rendered.lower())
        for statement in CODEX_DEPLOYMENT_BOUNDARY:
            self.assertEqual(rendered.count(statement), 1)

    def test_every_task_packet_and_approved_prompt_carries_the_codex_boundary(self) -> None:
        packet = compose_task_packet("feature", {
            "outcome": "A person can export a report.",
            "example": "Export one filtered CSV.",
            "preserve": "Keep existing CLI behavior.",
            "acceptance": "Focused tests pass.",
        })
        serialized = packet.to_dict()
        self.assertEqual(serialized["codex_deployment_boundary"], list(CODEX_DEPLOYMENT_BOUNDARY))
        request = render_task_request(packet)
        approved = approve_task_contract(build_task_contract(packet))
        for statement in CODEX_DEPLOYMENT_BOUNDARY:
            self.assertEqual(request.count(statement), 1)
            self.assertEqual(approved.prompt.count(statement), 1)

    def test_review_contract_has_all_required_sections_before_explicit_approval(self) -> None:
        packet = compose_task_packet("feature", {
            "outcome": "A person can export a filtered report.",
            "example": "Export only unresolved findings as CSV.",
            "preserve": "Keep existing report formats and CLI flags.",
            "acceptance": "Focused export tests and the trusted suite pass.",
        })
        contract = build_task_contract(packet)
        self.assertEqual(contract.state, "review-required")
        self.assertIn("export a filtered report", contract.attempt)
        self.assertEqual(contract.must_not_change, "Keep existing report formats and CLI flags.")
        self.assertIn("inspect", contract.likely_areas.lower())
        self.assertIn("trusted suite", contract.acceptance_checks)
        self.assertTrue(contract.risks_and_approvals)
        rendered = render_task_contract(contract)
        for heading in (
            "What Codex will attempt",
            "What it must not change",
            "Files/areas likely involved",
            "Tests/acceptance checks",
            "Risks/approvals that may be encountered",
        ):
            self.assertIn(heading, rendered)
        self.assertIn("Edit answers", rendered)
        self.assertIn("Approve prompt", rendered)

        approved = approve_task_contract(contract)
        self.assertEqual(approved.state, "approved")
        self.assertEqual(approved.contract, contract)
        self.assertIn("Task type: Add a feature", approved.prompt)
        self.assertNotIn("launch", approved.to_dict())

    def test_deployment_contract_preserves_plan_only_boundary_and_approval_risks(self) -> None:
        packet = compose_task_packet("deployment-plan", {
            "target": "A staging Linux host.",
            "current_state": "Local checks pass.",
            "constraints": "No downtime and no production data changes.",
            "approvals": "A human approves every remote action.",
            "acceptance": "A reviewable plan with rollback steps.",
        })
        contract = build_task_contract(packet)
        self.assertIn("planning only", contract.must_not_change.lower())
        self.assertIn("human approves", contract.risks_and_approvals.lower())
        self.assertIn("rollback", contract.acceptance_checks.lower())


if __name__ == "__main__":
    unittest.main()
