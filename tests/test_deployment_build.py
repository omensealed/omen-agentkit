from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from agent_starter.cli import command_deployment_build, main
from agent_starter.cli_app import deployment_commands
from agent_starter.deployment_build import verify_built_artifact
from agent_starter.deployment_check import check_deployment, load_immutable_plan
from agent_starter.deployment_plan import SourceState, build_deployment_plan, parse_target_profile, render_plan_json
from agent_starter.generator import ValidationReport, generate_project
from agent_starter.models import ProjectConfig


def profile_data(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "target": "static-site",
        "environment": "staging",
        "target_identifier": "docs-staging",
        "artifact_output": "dist/site.zip",
        "local_writes": ["dist/site.zip"],
        "remote_writes": [],
        "commands": [["touch", "must-not-exist"]],
        "network_destinations": [],
        "credential_references": [],
        "health_checks": ["Inspect the staged static site."],
        "rollback_steps": ["Restore the previous artifact digest."],
    }
    value.update(overrides)
    return value


class DeploymentBuildTests(unittest.TestCase):
    def _workspace(self, base: Path, *, target: str = "static-site") -> tuple[Path, str]:
        root = base / "project"
        config = ProjectConfig(project_name="Build Test", project_slug="build-test", project_path=str(root), git_enabled=False)
        self.assertTrue(generate_project(config).ok)
        source = root / "public"
        source.mkdir()
        (source / "index.html").write_text("<h1>Stable</h1>\n", encoding="utf-8")
        assets = source / "assets"
        assets.mkdir()
        script = assets / "app.js"
        script.write_text("console.log('stable');\n", encoding="utf-8")
        script.chmod(0o755)
        state = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
        plan = build_deployment_plan(config, parse_target_profile(profile_data(target=target)), state)
        (root / "deployment-plan.json").write_text(render_plan_json(plan), encoding="utf-8")
        return root, plan.digest

    def test_build_is_atomic_reproducible_provenanced_and_never_executes_plan_commands(self) -> None:
        self.assertIs(command_deployment_build, deployment_commands.command_deployment_build)
        with tempfile.TemporaryDirectory() as temp:
            root, plan_digest = self._workspace(Path(temp))
            state = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            validation = ValidationReport(root=root, checked=["AGENTS.md"])
            output = io.StringIO()
            with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=state), mock.patch(
                "agent_starter.deployment_build.validate_project", return_value=validation
            ), contextlib.redirect_stdout(output):
                code = main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public", "--format", "json"])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            artifact = root / "dist/site.zip"
            self.assertTrue(artifact.is_file())
            self.assertEqual(report["artifact_digest"], hashlib.sha256(artifact.read_bytes()).hexdigest())
            self.assertEqual(report["plan_digest"], plan_digest)
            self.assertTrue(report["reproducible"])
            self.assertEqual(report["reproduction_runs"], 2)
            self.assertFalse(report["authority"]["profile_commands_executed"])
            self.assertFalse(report["authority"]["network_accessed"])
            self.assertFalse(report["authority"]["push_performed"])
            self.assertFalse(report["authority"]["apply_authorized"])
            self.assertFalse((root / "must-not-exist").exists())
            with zipfile.ZipFile(artifact) as archive:
                self.assertEqual(
                    archive.namelist(),
                    [".agentkit/provenance.json", ".agentkit/sbom.spdx.json", "payload/assets/app.js", "payload/index.html"],
                )
                provenance = json.loads(archive.read(".agentkit/provenance.json"))
                sbom = json.loads(archive.read(".agentkit/sbom.spdx.json"))
            self.assertEqual(provenance["source"]["revision"], state.revision)
            self.assertEqual(provenance["plan_digest"], plan_digest)
            self.assertEqual(provenance["commands"]["profile_display_only"], [["touch", "must-not-exist"]])
            self.assertEqual(
                provenance["commands"]["builder_operation"],
                ["agent-starter", "deployment", "build", ".", "--plan", "deployment-plan.json", "--source", "public"],
            )
            self.assertEqual(provenance["commands"]["executed"], [])
            self.assertIn("python", provenance["tool_versions"])
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            verified = verify_built_artifact(artifact, plan_digest=plan_digest)
            self.assertTrue(verified.ok)
            tampered = root / "dist/tampered.zip"
            tampered_bytes = artifact.read_bytes().replace(b"Stable", b"Stabla", 1)
            tampered.write_bytes(tampered_bytes)
            self.assertFalse(verify_built_artifact(tampered, plan_digest=plan_digest).ok)
            loaded_plan = load_immutable_plan(root, Path("deployment-plan.json"))
            with mock.patch("agent_starter.deployment_check.inspect_source_state", return_value=state), mock.patch(
                "agent_starter.deployment_check.validate_project", return_value=validation
            ):
                check = check_deployment(root, loaded_plan)
            statuses = {finding.check_id: finding.status for finding in check.findings}
            self.assertEqual(statuses["artifact_checksum"], "passed")
            self.assertEqual(statuses["artifact_reproducibility"], "passed")
            checksum_finding = next(finding for finding in check.findings if finding.check_id == "artifact_checksum")
            self.assertEqual(checksum_finding.evidence, f"sha256:{report['artifact_digest']}")

            original = artifact.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public"]), 2)
            self.assertEqual(artifact.read_bytes(), original)

    def test_equal_inputs_and_plan_produce_equal_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            roots = [self._workspace(Path(first))[0], self._workspace(Path(second))[0]]
            state = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            for root in roots:
                with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=state), mock.patch(
                    "agent_starter.deployment_build.validate_project", return_value=ValidationReport(root=root)
                ), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public"]), 0)
            self.assertEqual((roots[0] / "dist/site.zip").read_bytes(), (roots[1] / "dist/site.zip").read_bytes())

    def test_build_fails_closed_for_unsupported_target_dirty_source_and_unsafe_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self._workspace(Path(temp), target="oci-image")
            clean = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=clean), mock.patch(
                "agent_starter.deployment_build.os.open"
            ) as opened, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public"]), 2)
            opened.assert_not_called()
            self.assertFalse((root / "dist/site.zip").exists())

        with tempfile.TemporaryDirectory() as temp:
            root, _ = self._workspace(Path(temp))
            dirty = SourceState("git", "0123456789abcdef0123456789abcdef01234567", True, 1, True)
            with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=dirty), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public"]), 2)
            self.assertFalse((root / "dist/site.zip").exists())

            (root / "public/.env").write_text("DO_NOT_READ=value\n", encoding="utf-8")
            clean = SourceState("git", "0123456789abcdef0123456789abcdef01234567", False, 0, True)
            with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=clean), mock.patch(
                "agent_starter.deployment_build.os.open"
            ) as opened, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["deployment", "build", str(root), "--plan", "deployment-plan.json", "--source", "public"]), 2)
            opened.assert_not_called()
            self.assertFalse((root / "dist/site.zip").exists())


if __name__ == "__main__":
    unittest.main()
