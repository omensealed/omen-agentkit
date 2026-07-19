from __future__ import annotations

import contextlib
import io
import json
import unittest
from dataclasses import replace

from agent_starter.cli import main
from agent_starter.deployment import list_deployment_contracts
from agent_starter.deployment_build import ArtifactBuildReport
from agent_starter.deployment_check import DeploymentCheckFinding, DeploymentCheckReport
from agent_starter.deployment_gate import REQUIRED_APPLY_CHECK_IDS
from agent_starter.deployment_plan import DeploymentPlan
from agent_starter.deployment_staging import (
    DisposableStaticSiteStagingAdapter,
    RehearsalFailurePoint,
    StagingRehearsalError,
    StagingRehearsalEvidence,
    StagingRehearsalState,
    rehearse_static_site_staging,
)
from agent_starter.generation.registry import build_file_map
from agent_starter.models import ProjectConfig, SandboxConfig


PLAN_DIGEST = "1" * 64
ARTIFACT_DIGEST = "2" * 64
PREVIOUS_DIGEST = "3" * 64


def plan(
    *,
    digest: str = PLAN_DIGEST,
    target: str = "static-site",
    environment: str = "staging",
    target_identifier: str = "docs-staging",
    dirty: bool = False,
    health_checks: list[str] | None = None,
    rollback_steps: list[str] | None = None,
) -> DeploymentPlan:
    payload = {
        "schema_version": 1,
        "authority": {},
        "project": {},
        "source": {
            "repository": "git",
            "revision": "4" * 40,
            "dirty": dirty,
            "changed_entry_count": 1 if dirty else 0,
            "project_is_repository_root": True,
        },
        "target": {
            "id": target,
            "environment": environment,
            "target_identifier": target_identifier,
        },
        "effects": {
            "commands": [["agent-starter", "deployment", "apply", "SECRET_VALUE_SENTINEL"]],
            "credential_references": [{"mechanism": "ci-secret-store", "name": "docs-api"}],
        },
        "health_checks": ["Require the reviewed staging health result."] if health_checks is None else health_checks,
        "rollback_steps": ["Restore the prior staging artifact digest."] if rollback_steps is None else rollback_steps,
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


def artifact(digest: str = PLAN_DIGEST) -> ArtifactBuildReport:
    return ArtifactBuildReport(
        plan_digest=digest,
        artifact_path="dist/site.zip",
        artifact_digest=ARTIFACT_DIGEST,
        content_root_digest="5" * 64,
        artifact_bytes=100,
        payload_files=1,
        source_revision="4" * 40,
        reproducible=True,
        reproduction_runs=2,
        provenance={"plan_digest": digest},
    )


def evidence(digest: str = PLAN_DIGEST) -> StagingRehearsalEvidence:
    return StagingRehearsalEvidence(
        reviewed_plan_digest=digest,
        check_report=passing_check(digest),
        artifact_report=artifact(digest),
        reviewed_artifact_digest=ARTIFACT_DIGEST,
    )


class DeploymentStagingRehearsalTests(unittest.TestCase):
    def test_successful_rehearsal_proves_health_and_rollback(self) -> None:
        adapter = DisposableStaticSiteStagingAdapter("docs-staging", PREVIOUS_DIGEST)
        result = rehearse_static_site_staging(plan(), evidence(), adapter)
        self.assertEqual(result.state, StagingRehearsalState.VERIFIED)
        self.assertTrue(result.health_passed)
        self.assertTrue(result.rollback_proven)
        self.assertTrue(all(not contract.production_ready for contract in list_deployment_contracts()))
        self.assertEqual(adapter.current_artifact_digest, PREVIOUS_DIGEST)
        self.assertTrue(result.authority.disposable_staging_changed)
        self.assertFalse(result.authority.production_apply_performed)
        self.assertFalse(result.authority.network_accessed)
        self.assertFalse(result.authority.commands_executed)

    def test_partial_failure_rolls_back_to_the_exact_prior_state(self) -> None:
        adapter = DisposableStaticSiteStagingAdapter("docs-staging", PREVIOUS_DIGEST)
        result = rehearse_static_site_staging(
            plan(), evidence(), adapter, failure_point=RehearsalFailurePoint.HEALTH_CHECK
        )
        self.assertEqual(result.state, StagingRehearsalState.ROLLED_BACK)
        self.assertFalse(result.health_passed)
        self.assertTrue(result.rollback_proven)
        self.assertEqual(result.failure_code, "injected_staging_health_failure")
        self.assertEqual(adapter.current_artifact_digest, PREVIOUS_DIGEST)

    def test_wrong_target_production_dirty_and_stale_evidence_are_rejected_without_change(self) -> None:
        cases = (
            (plan(target="oci-image"), evidence(), "unsupported_staging_adapter"),
            (plan(environment="production"), evidence(), "production_rehearsal_forbidden"),
            (plan(target_identifier="wrong-staging"), evidence(), "staging_target_mismatch"),
            (plan(dirty=True), evidence(), "dirty_source_blocked"),
            (plan(), evidence("6" * 64), "stale_plan_evidence"),
        )
        for current_plan, current_evidence, code in cases:
            with self.subTest(code=code):
                adapter = DisposableStaticSiteStagingAdapter("docs-staging", PREVIOUS_DIGEST)
                with self.assertRaises(StagingRehearsalError) as caught:
                    rehearse_static_site_staging(current_plan, current_evidence, adapter)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(adapter.current_artifact_digest, PREVIOUS_DIGEST)

    def test_failed_checks_missing_health_or_rollback_and_stale_artifact_block(self) -> None:
        failed = replace(
            evidence(),
            check_report=DeploymentCheckReport(
                PLAN_DIGEST,
                (DeploymentCheckFinding("project_tests", "failed", "Failed.", "Fix tests."),),
            ),
        )
        stale_artifact = replace(evidence(), reviewed_artifact_digest="7" * 64)
        cases = (
            (plan(), failed, "required_checks_not_passing"),
            (plan(health_checks=[]), evidence(), "health_check_missing"),
            (plan(rollback_steps=[]), evidence(), "rollback_missing"),
            (plan(), stale_artifact, "stale_artifact_evidence"),
        )
        for current_plan, current_evidence, code in cases:
            with self.subTest(code=code):
                adapter = DisposableStaticSiteStagingAdapter("docs-staging", PREVIOUS_DIGEST)
                with self.assertRaises(StagingRehearsalError) as caught:
                    rehearse_static_site_staging(current_plan, current_evidence, adapter)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(adapter.current_artifact_digest, PREVIOUS_DIGEST)

    def test_audit_output_is_closed_redacted_and_excludes_plan_commands_and_secret_values(self) -> None:
        adapter = DisposableStaticSiteStagingAdapter("docs-staging", PREVIOUS_DIGEST)
        serialized = json.dumps(rehearse_static_site_staging(plan(), evidence(), adapter).to_dict(), sort_keys=True)
        self.assertNotIn("SECRET_VALUE_SENTINEL", serialized)
        self.assertNotIn("deployment", serialized)
        self.assertNotIn("docs-api", serialized)
        self.assertNotIn("credential_references", serialized)
        for event in json.loads(serialized)["audit_events"]:
            self.assertEqual(
                set(event),
                {"schema_version", "event", "plan_digest", "artifact_digest", "environment", "target_identifier", "redacted"},
            )
            self.assertTrue(event["redacted"])

    def test_codex_launch_and_generated_scripts_have_no_apply_or_rehearsal_entry_point(self) -> None:
        config = ProjectConfig(
            project_name="No Apply",
            project_slug="no-apply",
            project_path="/tmp/no-apply",
            description="Keep launch separate from staging rehearsal.",
            sandbox=SandboxConfig(enabled=True, mode="codex", codex_inside_container=True),
        )
        files = build_file_map(config)
        executables = "\n".join(content for path, content in files.items() if path.endswith(".sh") or path == "START_AGENT.sh")
        self.assertNotIn("deployment apply", executables)
        self.assertNotIn("deployment rehearse", executables)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["deployment", "rehearse"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
