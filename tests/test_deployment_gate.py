from __future__ import annotations

import json
import unittest
import contextlib
import io
from dataclasses import replace

from agent_starter.deployment import DeploymentOperation, list_deployment_contracts
from agent_starter.deployment_build import ArtifactBuildReport
from agent_starter.deployment_check import DeploymentCheckFinding, DeploymentCheckReport
from agent_starter.deployment_gate import (
    ApplyGateEvidence,
    ApplyGateState,
    REQUIRED_APPLY_CHECK_IDS,
    TargetAuthenticationEvidence,
    create_redacted_audit_event,
    evaluate_apply_gate,
    expected_confirmation_text,
    record_typed_human_confirmation,
)
from agent_starter.deployment_plan import DeploymentPlan
from agent_starter.cli import main


PLAN_DIGEST = "1" * 64
ARTIFACT_DIGEST = "2" * 64


def deployment_plan(*, digest: str = PLAN_DIGEST, target_identifier: str = "docs-staging") -> DeploymentPlan:
    payload = {
        "schema_version": 1,
        "authority": {},
        "project": {},
        "source": {},
        "target": {
            "id": "static-site",
            "environment": "staging",
            "target_identifier": target_identifier,
        },
        "effects": {},
        "health_checks": ["Require the reviewed staging health result."],
        "rollback_steps": ["Restore the previously reviewed artifact."],
    }
    return DeploymentPlan(json.dumps(payload, separators=(",", ":"), sort_keys=True), digest)


def passing_check(digest: str = PLAN_DIGEST) -> DeploymentCheckReport:
    return DeploymentCheckReport(
        digest,
        tuple(
            DeploymentCheckFinding(check_id, "passed", "Passed.", "No action required.")
            for check_id in sorted(REQUIRED_APPLY_CHECK_IDS)
        ),
    )


def artifact_report(digest: str = PLAN_DIGEST) -> ArtifactBuildReport:
    return ArtifactBuildReport(
        plan_digest=digest,
        artifact_path="dist/site.zip",
        artifact_digest=ARTIFACT_DIGEST,
        content_root_digest="4" * 64,
        artifact_bytes=100,
        payload_files=1,
        source_revision="5" * 40,
        reproducible=True,
        reproduction_runs=2,
        provenance={"plan_digest": digest},
    )


class DeploymentApplyGateTests(unittest.TestCase):
    def _complete_evidence(self, plan: DeploymentPlan) -> ApplyGateEvidence:
        environment = plan.payload["target"]["environment"]
        target_identifier = plan.payload["target"]["target_identifier"]
        confirmation = record_typed_human_confirmation(
            expected_confirmation_text(
                plan_digest=plan.digest,
                artifact_digest=ARTIFACT_DIGEST,
                environment=environment,
                target_identifier=target_identifier,
            ),
            input_source="local-tty-human",
            plan_digest=plan.digest,
            artifact_digest=ARTIFACT_DIGEST,
            environment=environment,
            target_identifier=target_identifier,
        )
        return ApplyGateEvidence(
            reviewed_plan_digest=plan.digest,
            check_report=passing_check(plan.digest),
            artifact_report=artifact_report(plan.digest),
            reviewed_artifact_digest=ARTIFACT_DIGEST,
            environment=environment,
            target_identifier=target_identifier,
            authentication=TargetAuthenticationEvidence(
                adapter_id="future-static-site-adapter",
                plan_digest=plan.digest,
                environment=environment,
                target_identifier=target_identifier,
                human_authenticated=True,
                source="target-tool-human-session",
            ),
            confirmation=confirmation,
            rollback_available=True,
            audit_event=create_redacted_audit_event(
                plan_digest=plan.digest,
                artifact_digest=ARTIFACT_DIGEST,
                environment=environment,
                target_identifier=target_identifier,
            ),
        )

    def test_current_registry_has_no_apply_adapter_and_gate_fails_closed(self) -> None:
        self.assertTrue(all(DeploymentOperation.APPLY not in item.enabled_operations for item in list_deployment_contracts()))
        plan = deployment_plan()
        result = evaluate_apply_gate(plan, self._complete_evidence(plan))
        self.assertEqual(result.state, ApplyGateState.BLOCKED_ADAPTER)
        self.assertFalse(result.ready)
        self.assertFalse(result.authority.apply_performed)
        self.assertFalse(result.authority.network_accessed)
        self.assertFalse(result.authority.target_contacted)
        self.assertEqual({item.gate_id: item.status for item in result.findings}["supported_target_adapter"], "blocked")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["deployment", "apply"])
        self.assertEqual(caught.exception.code, 2)

    def test_plan_or_artifact_change_invalidates_review_and_confirmation(self) -> None:
        original = deployment_plan()
        evidence = self._complete_evidence(original)
        changed = deployment_plan(digest="3" * 64, target_identifier="docs-staging-v2")
        result = evaluate_apply_gate(changed, evidence)
        self.assertEqual(result.state, ApplyGateState.INVALIDATED)
        self.assertIn("reviewed_plan_digest_mismatch", {item.code for item in result.findings})
        self.assertIn("confirmation_binding_mismatch", {item.code for item in result.findings})

        changed_artifact = replace(
            evidence,
            artifact_report=replace(evidence.artifact_report, artifact_digest="4" * 64),
        )
        result = evaluate_apply_gate(original, changed_artifact)
        self.assertEqual(result.state, ApplyGateState.INVALIDATED)
        self.assertIn("reviewed_artifact_digest_mismatch", {item.code for item in result.findings})

    def test_failed_or_unverified_checks_and_missing_evidence_block(self) -> None:
        plan = deployment_plan()
        evidence = self._complete_evidence(plan)
        failed_report = DeploymentCheckReport(
            plan.digest,
            (
                DeploymentCheckFinding("source_state", "failed", "Failed.", "Fix it."),
                DeploymentCheckFinding("target_identity", "unverified", "Unknown.", "Verify it."),
            ),
        )
        incomplete = replace(
            evidence,
            check_report=failed_report,
            authentication=None,
            confirmation=None,
            rollback_available=False,
            audit_event=None,
        )
        result = evaluate_apply_gate(plan, incomplete)
        statuses = {item.gate_id: item.status for item in result.findings}
        self.assertEqual(statuses["required_checks"], "blocked")
        self.assertEqual(statuses["human_authentication"], "pending")
        self.assertEqual(statuses["typed_human_confirmation"], "pending")
        self.assertEqual(statuses["rollback_available"], "blocked")
        self.assertEqual(statuses["redacted_local_audit_event"], "pending")
        self.assertFalse(result.ready)

    def test_confirmation_is_exact_typed_bound_and_does_not_retain_raw_input(self) -> None:
        expected = expected_confirmation_text(
            plan_digest=PLAN_DIGEST,
            artifact_digest=ARTIFACT_DIGEST,
            environment="staging",
            target_identifier="docs-staging",
        )
        with self.assertRaises(ValueError):
            record_typed_human_confirmation(
                expected,
                input_source="model-output",
                plan_digest=PLAN_DIGEST,
                artifact_digest=ARTIFACT_DIGEST,
                environment="staging",
                target_identifier="docs-staging",
            )
        with self.assertRaises(ValueError):
            expected_confirmation_text(
                plan_digest=PLAN_DIGEST,
                artifact_digest=ARTIFACT_DIGEST,
                environment="production",
                target_identifier="token=do-not-retain",
            )
        with self.assertRaises(ValueError):
            record_typed_human_confirmation(
                expected + " ",
                input_source="local-tty-human",
                plan_digest=PLAN_DIGEST,
                artifact_digest=ARTIFACT_DIGEST,
                environment="staging",
                target_identifier="docs-staging",
            )
        confirmation = record_typed_human_confirmation(
            expected,
            input_source="local-tty-human",
            plan_digest=PLAN_DIGEST,
            artifact_digest=ARTIFACT_DIGEST,
            environment="staging",
            target_identifier="docs-staging",
        )
        self.assertNotIn(expected, repr(confirmation))
        self.assertNotIn("typed_text", confirmation.__dataclass_fields__)

    def test_audit_event_is_closed_redacted_and_contains_no_free_form_or_secret_data(self) -> None:
        event = create_redacted_audit_event(
            plan_digest=PLAN_DIGEST,
            artifact_digest=ARTIFACT_DIGEST,
            environment="staging",
            target_identifier="docs-staging",
        )
        value = event.to_dict()
        self.assertEqual(
            set(value),
            {"schema_version", "event", "plan_digest", "artifact_digest", "environment", "target_identifier", "redacted"},
        )
        self.assertTrue(value["redacted"])
        serialized = json.dumps(value, sort_keys=True)
        for forbidden in ("password", "token", "authorization", "command", "prompt", "stdout", "stderr"):
            self.assertNotIn(forbidden, serialized.lower())


if __name__ == "__main__":
    unittest.main()
