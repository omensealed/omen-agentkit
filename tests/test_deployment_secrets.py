from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.deployment_plan import CredentialReference, SourceState, build_deployment_plan, parse_target_profile
from agent_starter.deployment_secrets import (
    CREDENTIAL_MECHANISMS,
    check_secret_references,
    list_secret_contracts,
    secret_contract,
)
from agent_starter.deployment_check import check_deployment
from agent_starter.generator import ValidationReport, generate_project
from agent_starter.models import ProjectConfig


class DeploymentSecretsTests(unittest.TestCase):
    def test_contracts_are_reference_only_exact_and_complete(self) -> None:
        self.assertEqual(
            tuple(contract.mechanism for contract in list_secret_contracts()),
            ("none", "environment-file", "os-keyring", "ci-secret-store", "target-secret-manager", "ssh-agent"),
        )
        self.assertEqual(CREDENTIAL_MECHANISMS, frozenset(contract.mechanism for contract in list_secret_contracts()))
        for contract in list_secret_contracts():
            self.assertFalse(contract.reads_values)
            self.assertFalse(contract.logs_values)
            self.assertFalse(contract.persists_values)
        self.assertEqual(secret_contract("environment-file").reference_convention, ".env.<reference-name>")
        with self.assertRaises(ValueError):
            secret_contract("ENV")

    def test_environment_file_checks_only_metadata_ignore_and_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reference = CredentialReference("docs-api", "environment-file")
            secret_file = root / ".env.docs-api"
            secret_file.write_text("DO_NOT_READ=sentinel-value\n", encoding="utf-8")
            secret_file.chmod(0o600)
            ignored = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            with mock.patch.dict(os.environ, {"UNRELATED_SECRET_VALUE": "must-not-reach-child"}), mock.patch(
                "agent_starter.deployment_secrets.subprocess.run", return_value=ignored
            ) as run, mock.patch("pathlib.Path.read_text", side_effect=AssertionError("secret content must not be read")):
                finding = check_secret_references(root, (reference,))[0]
            self.assertEqual(finding.status, "passed")
            self.assertEqual(finding.code, "secret_reference_present")
            self.assertNotIn("sentinel", finding.explanation)
            argv = run.call_args.args[0]
            self.assertEqual(argv[-3:], ["check-ignore", "--quiet", ".env.docs-api"])
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertNotIn("UNRELATED_SECRET_VALUE", run.call_args.kwargs["env"])

            secret_file.chmod(0o644)
            finding = check_secret_references(root, (reference,))[0]
            self.assertEqual((finding.status, finding.code), ("failed", "secret_reference_permissions"))
            secret_file.unlink()
            finding = check_secret_references(root, (reference,))[0]
            self.assertEqual((finding.status, finding.code), ("failed", "secret_reference_missing"))

    def test_external_stores_are_unverified_and_ssh_agent_uses_socket_metadata_only(self) -> None:
        references = tuple(
            CredentialReference(name, mechanism)
            for name, mechanism in (
                ("desktop-login", "os-keyring"),
                ("release-token", "ci-secret-store"),
                ("service-key", "target-secret-manager"),
            )
        )
        with tempfile.TemporaryDirectory() as temp:
            findings = check_secret_references(Path(temp), references, environment={})
        self.assertTrue(all(item.status == "unverified" for item in findings))
        self.assertNotIn("value", " ".join(item.evidence for item in findings))

        with tempfile.TemporaryDirectory() as temp:
            sock_path = str(Path(temp) / "agent.sock")
            finding = check_secret_references(
                Path(temp), (CredentialReference("deploy-agent", "ssh-agent"),),
                environment={"SSH_AUTH_SOCK": sock_path},
                socket_stat_probe=lambda path: mock.Mock(st_mode=stat.S_IFSOCK | 0o600),
            )[0]
            self.assertEqual((finding.status, finding.code), ("passed", "ssh_agent_present"))
            self.assertNotIn(sock_path, finding.explanation + finding.evidence)

    def test_deployment_check_uses_reference_findings_without_accessing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Secret Check", project_slug="secret-check", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)
            artifact = root / "dist/site.txt"
            artifact.parent.mkdir()
            artifact.write_text("artifact\n", encoding="utf-8")
            profile = parse_target_profile({
                "schema_version": 1, "target": "static-site", "environment": "staging",
                "target_identifier": "secret-check", "artifact_output": "dist/site.txt",
                "local_writes": ["dist/site.txt"], "remote_writes": [], "commands": [],
                "network_destinations": [],
                "credential_references": [{"name": "docs-api", "mechanism": "environment-file"}],
                "health_checks": ["Inspect local artifact."], "rollback_steps": ["Delete local artifact."],
            })
            source = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            plan = build_deployment_plan(config, profile, source)
            validation = ValidationReport(root=root)
            secret_finding = mock.Mock(status="passed", code="secret_reference_present", name="docs-api")
            with mock.patch("agent_starter.deployment_check.inspect_source_state", return_value=source), mock.patch(
                "agent_starter.deployment_check.validate_project", return_value=validation
            ), mock.patch("agent_starter.deployment_check.check_secret_references", return_value=(secret_finding,)) as checked:
                report = check_deployment(root, plan)
            credential = next(item for item in report.findings if item.check_id == "credential_references")
            self.assertEqual(credential.status, "passed")
            checked.assert_called_once()
            self.assertFalse(report.to_dict()["authority"]["credentials_accessed"])


if __name__ == "__main__":
    unittest.main()
