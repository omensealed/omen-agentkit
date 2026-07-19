from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.cli import command_deployment_check, main
from agent_starter.cli_app import deployment_commands
from agent_starter.deployment_check import check_deployment, load_immutable_plan, render_check_json
from agent_starter.deployment_plan import SourceState, build_deployment_plan, parse_target_profile, render_plan_json
from agent_starter.generator import ValidationReport, generate_project
from agent_starter.models import ProjectConfig


def profile_data(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "target": "static-site",
        "environment": "staging",
        "target_identifier": "docs-staging",
        "artifact_output": "dist/site.txt",
        "local_writes": ["dist/site.txt"],
        "remote_writes": ["staging:/srv/www/docs"],
        "commands": [["touch", "must-not-exist"]],
        "network_destinations": ["staging.example.invalid:22"],
        "credential_references": [{"name": "docs-deploy-ssh", "mechanism": "ssh-agent"}],
        "health_checks": ["Request the staging health endpoint and require HTTP 200."],
        "rollback_steps": ["Restore the previously recorded artifact digest."],
    }
    value.update(overrides)
    return value


class DeploymentCheckTests(unittest.TestCase):
    def _workspace(self, temp: str, *, profile: dict[str, object] | None = None) -> tuple[Path, Path]:
        root = Path(temp) / "project"
        config = ProjectConfig(project_name="Check Test", project_slug="check-test", project_path=str(root), git_enabled=False)
        self.assertTrue(generate_project(config).ok)
        (root / "dist").mkdir()
        (root / "dist/site.txt").write_text("stable artifact\n", encoding="utf-8")
        plan = build_deployment_plan(
            config,
            parse_target_profile(profile or profile_data()),
            SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True),
        )
        path = root / "deployment-plan.json"
        path.write_text(render_plan_json(plan), encoding="utf-8")
        return root, path

    def test_check_is_read_only_and_never_executes_plan_commands_or_contacts_target(self) -> None:
        self.assertIs(command_deployment_check, deployment_commands.command_deployment_check)
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self._workspace(temp)
            clean = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            validation = ValidationReport(root=root, checked=["AGENTS.md"])
            before = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            output = io.StringIO()
            with mock.patch("agent_starter.deployment_check.inspect_source_state", return_value=clean), mock.patch(
                "agent_starter.deployment_check.validate_project", return_value=validation
            ), contextlib.redirect_stdout(output):
                code = main(["deployment", "check", str(root), "--plan", "deployment-plan.json", "--format", "json"])
            self.assertEqual(code, 1)
            report = json.loads(output.getvalue())
            self.assertFalse(report["ready"])
            self.assertFalse(report["authority"]["target_contacted"])
            self.assertFalse(report["authority"]["credentials_accessed"])
            self.assertFalse(report["authority"]["project_commands_executed"])
            self.assertFalse(report["authority"]["apply_authorized"])
            self.assertIn("unverified", {finding["status"] for finding in report["findings"]})
            self.assertEqual(
                {finding["check_id"] for finding in report["findings"]},
                {
                    "plan_integrity", "project_identity", "project_validation", "project_tests", "source_state",
                    "artifact_checksum", "artifact_reproducibility", "target_identity", "credential_references",
                    "backup_migration_readiness", "health_rollback_completeness", "least_privilege",
                },
            )
            self.assertFalse((root / "must-not-exist").exists())
            after = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(after, before)

    def test_check_passes_complete_local_only_evidence_but_does_not_grant_apply(self) -> None:
        local = profile_data(
            remote_writes=[], network_destinations=[], credential_references=[],
            commands=[], health_checks=["Inspect the local artifact."], rollback_steps=["Delete the unshipped local artifact."],
        )
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self._workspace(temp, profile=local)
            plan = load_immutable_plan(root, Path("deployment-plan.json"))
            validation = ValidationReport(root=root, checked=["AGENTS.md"])
            source = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            with mock.patch("agent_starter.deployment_check.inspect_source_state", return_value=source), mock.patch(
                "agent_starter.deployment_check.validate_project", return_value=validation
            ):
                report = check_deployment(root, plan)
            statuses = {finding.check_id: finding.status for finding in report.findings}
            self.assertEqual(statuses["artifact_checksum"], "passed")
            self.assertEqual(statuses["artifact_reproducibility"], "unverified")
            self.assertEqual(statuses["project_tests"], "unverified")
            self.assertFalse(report.ready)
            self.assertEqual(json.loads(render_check_json(report))["plan_digest"], plan.digest)

    def test_plan_loader_rejects_digest_tampering_escape_symlink_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, path = self._workspace(temp)
            document = json.loads(path.read_text(encoding="utf-8"))
            document["plan"]["target"]["target_identifier"] = "other-target"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_immutable_plan(root, Path("deployment-plan.json"))

            root, path = self._workspace(str(Path(temp) / "shape"))
            document = json.loads(path.read_text(encoding="utf-8"))
            document["plan"]["unexpected"] = True
            canonical = json.dumps(document["plan"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            document["plan_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_immutable_plan(root, Path("deployment-plan.json"))
            with self.assertRaises(ValueError):
                load_immutable_plan(root, Path("../outside.json"))
            outside = Path(temp) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            (root / "link.json").symlink_to(outside)
            with self.assertRaises(ValueError):
                load_immutable_plan(root, Path("link.json"))
            path.write_text("x" * 2_100_000, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_immutable_plan(root, Path("deployment-plan.json"))


if __name__ == "__main__":
    unittest.main()
