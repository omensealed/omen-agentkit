from __future__ import annotations

import re
from pathlib import Path
import unittest

from agent_starter import templates
from agent_starter.deployment_ci import (
    ACTION_PIN_REVIEW_DATE,
    CI_PROVIDER_IMAGES,
    DEPLOYMENT_CI_POLICY,
    GITHUB_ACTION_PINS,
    github_action_reference,
    validate_github_action_references,
)
from agent_starter.models import ProjectConfig


class DeploymentCIPolicyTests(unittest.TestCase):
    def test_policy_is_fail_closed_and_uses_short_lived_identity(self) -> None:
        policy = DEPLOYMENT_CI_POLICY
        self.assertFalse(policy.deployment_enabled)
        self.assertEqual(policy.identity_mode, "github-oidc")
        self.assertFalse(policy.long_lived_credentials_allowed)
        self.assertEqual(policy.build_permissions, ("contents: read",))
        self.assertEqual(policy.future_deploy_permissions, ("contents: read", "id-token: write"))
        self.assertTrue(policy.separate_build_and_deploy_jobs)
        self.assertTrue(policy.separate_environments)
        self.assertTrue(policy.production_protected_environment)
        self.assertTrue(policy.production_manual_approval)
        self.assertEqual(policy.artifact_evidence, ("sha256-checksum", "artifact-attestation"))

    def test_official_actions_are_pinned_to_full_commits(self) -> None:
        self.assertEqual(
            set(GITHUB_ACTION_PINS),
            {
                "actions/checkout",
                "actions/setup-python",
                "actions/setup-node",
                "actions/setup-go",
                "actions/setup-java",
                "actions/dependency-review-action",
                "actions/upload-artifact",
                "actions/attest",
                "actions/download-artifact",
            },
        )
        for action, pin in GITHUB_ACTION_PINS.items():
            self.assertRegex(pin.commit_sha, r"^[0-9a-f]{40}$")
            self.assertRegex(pin.version, r"^v[0-9]+\.[0-9]+\.[0-9]+$")
            expected_review_date = "2026-07-19" if action == "actions/checkout" else ACTION_PIN_REVIEW_DATE
            self.assertEqual(pin.reviewed_on, expected_review_date)
            self.assertEqual(pin.source_url, f"https://github.com/{action}/commit/{pin.commit_sha}")
            self.assertEqual(github_action_reference(action), f"{action}@{pin.commit_sha} # {pin.version}")

    def test_reference_validator_rejects_mutable_unreviewed_or_mismatched_actions(self) -> None:
        valid = templates.github_ci(ProjectConfig(
            project_name="Pin Validation",
            project_slug="pin-validation",
            project_path="/tmp/pin-validation",
            description="Validate action references.",
            languages=["python"],
            github_actions=True,
        ))
        self.assertEqual(validate_github_action_references(valid), ())
        cases = {
            "uses: actions/checkout@v7 # v7.0.0": "mutable_action_reference",
            "uses: actions/checkout@9c091bb # v7.0.0": "mutable_action_reference",
            f"uses: actions/checkout@{GITHUB_ACTION_PINS['actions/checkout'].commit_sha}": "missing_action_version_comment",
            f"uses: actions/checkout@{GITHUB_ACTION_PINS['actions/checkout'].commit_sha} # v5.0.0": "reviewed_action_pin_mismatch",
            "uses: example/unreviewed@" + "a" * 40 + " # v1.0.0": "unreviewed_action",
        }
        for workflow, code in cases.items():
            with self.subTest(code=code):
                issues = validate_github_action_references(workflow)
                self.assertEqual([issue.code for issue in issues], [code])
                self.assertTrue(issues[0].remedy)

    def test_ci_provider_images_are_official_digest_pins(self) -> None:
        self.assertEqual(set(CI_PROVIDER_IMAGES), {"arch", "debian"})
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        for pin in CI_PROVIDER_IMAGES.values():
            self.assertRegex(pin.digest, r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(pin.platform, "linux/amd64")
            self.assertEqual(pin.reviewed_on, ACTION_PIN_REVIEW_DATE)
            self.assertIn(pin.reference, workflow)
        self.assertNotIn("docker pull docker.io/library/debian:stable-slim", workflow)
        self.assertNotIn("docker pull docker.io/library/archlinux:base-devel", workflow)

    def test_generated_check_workflow_has_no_deploy_authority(self) -> None:
        rendered = templates.github_ci(ProjectConfig(
            project_name="CI Contract",
            project_slug="ci-contract",
            project_path="/tmp/ci-contract",
            description="Exercise all pinned setup actions.",
            languages=["python", "javascript", "go", "java"],
            github_actions=True,
        ))
        uses = re.findall(r"^\s*uses:\s*(\S+)", rendered, flags=re.MULTILINE)
        self.assertTrue(uses)
        for reference in uses:
            self.assertRegex(reference, r"^[^@\s]+@[0-9a-f]{40}$")
        self.assertIn("permissions:\n  contents: read", rendered)
        self.assertNotIn("id-token: write", rendered)
        self.assertNotIn("environment:", rendered)
        self.assertNotIn("deploy:", rendered)
        self.assertNotRegex(rendered, r"uses:\s*[^\n]+@v\d")

    def test_generated_deployment_guidance_derives_provenance_contract(self) -> None:
        rendered = templates.deployment_doc(ProjectConfig(
            project_name="Deployment Contract",
            project_slug="deployment-contract",
            project_path="/tmp/deployment-contract",
            description="Render deployment guidance.",
        ))
        self.assertIn("## CI/CD identity and artifact provenance", rendered)
        self.assertIn("GitHub OIDC", rendered)
        self.assertIn("`id-token: write` only on that future deploy job", rendered)
        self.assertIn("full 40-character commit SHA", rendered)
        self.assertIn("separate build and deploy jobs", rendered)
        self.assertIn("protected production environment", rendered)
        self.assertIn("SHA-256 checksum", rendered)
        self.assertIn("artifact attestation", rendered)
        self.assertIn("Deployment jobs remain absent and disabled", rendered)

    def test_source_ci_supply_chain_actions_are_reviewed_and_scoped(self) -> None:
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertEqual(validate_github_action_references(workflow), ())
        self.assertIn("dependency-review:", workflow)
        self.assertIn("github.event_name == 'pull_request'", workflow)
        self.assertIn("supply-chain-artifacts:", workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertIn("run: ./scripts/check.sh --skip-package-smoke", workflow)
        self.assertIn("if: matrix.python-version == '3.11'", workflow)
        self.assertIn("run: ./scripts/package-smoke-test.sh", workflow)
        self.assertNotIn("release", workflow.lower().split("jobs:", 1)[0])


if __name__ == "__main__":
    unittest.main()
