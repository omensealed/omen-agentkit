from __future__ import annotations

import json
import contextlib
import hashlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.deployment_plan import (
    DeploymentPlanError,
    SourceState,
    build_deployment_plan,
    inspect_source_state,
    load_target_profile,
    parse_target_profile,
    render_plan_json,
    render_plan_text,
)
from agent_starter.models import ProjectConfig
from agent_starter.cli import command_deployment_plan, main
from agent_starter.cli_app import deployment_commands
from agent_starter.generator import generate_project


def profile_data(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "target": "static-site",
        "environment": "staging",
        "target_identifier": "docs-staging",
        "artifact_output": "dist/site",
        "local_writes": ["dist/site"],
        "remote_writes": ["staging:/srv/www/docs"],
        "commands": [["./scripts/build.sh"], ["rsync", "dist/site/", "staging:/srv/www/docs/"]],
        "network_destinations": ["staging.example.invalid:22"],
        "credential_references": [{"name": "docs-deploy-ssh", "mechanism": "ssh-agent"}],
        "health_checks": ["Request the staging health endpoint and require HTTP 200."],
        "rollback_steps": ["Restore the previously recorded artifact digest."],
    }
    value.update(overrides)
    return value


class DeploymentPlanTests(unittest.TestCase):
    def test_cli_plan_reads_project_and_profile_without_executing_advertised_actions(self) -> None:
        self.assertIs(command_deployment_plan, deployment_commands.command_deployment_plan)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(generate_project(ProjectConfig(
                project_name="CLI Plan", project_slug="cli-plan", project_path=str(root), git_enabled=False,
            )).ok)
            profile = root / "deploy-target.json"
            data = profile_data(commands=[["touch", "must-not-exist"]])
            profile.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline"],
                cwd=root, check=True,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["deployment", "plan", str(root), "--profile", "deploy-target.json", "--format", "json"])
            self.assertEqual(code, 0)
            document = json.loads(output.getvalue())
            canonical = json.dumps(document["plan"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            self.assertEqual(document["plan_digest"], hashlib.sha256(canonical.encode()).hexdigest())
            self.assertEqual(document["plan"]["source"]["repository"], "git")
            self.assertFalse(document["plan"]["source"]["dirty"])
            self.assertFalse((root / "must-not-exist").exists())
            self.assertFalse(document["plan"]["authority"]["remote_changes_performed"])

    def test_cli_output_is_project_confined_atomic_and_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(generate_project(ProjectConfig(project_name="Output Plan", project_path=str(root), git_enabled=False)).ok)
            (root / "target.json").write_text(json.dumps(profile_data()), encoding="utf-8")
            args = ["deployment", "plan", str(root), "--profile", "target.json", "--output", "plans/staging.txt"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            target = root / "plans/staging.txt"
            original = target.read_text(encoding="utf-8")
            self.assertIn("# Immutable deployment plan", original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 2)
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["deployment", "plan", str(root), "--profile", "target.json", "--output", "../escape.txt"]), 2)
            self.assertFalse((Path(temp) / "escape.txt").exists())

    def test_profile_parser_is_closed_typed_secret_safe_and_path_confined(self) -> None:
        profile = parse_target_profile(profile_data())
        self.assertEqual(profile.target.value, "static-site")
        self.assertEqual(profile.commands[0], ("./scripts/build.sh",))
        cases = (
            profile_data(extra="no"),
            profile_data(schema_version=True),
            profile_data(target="kubernetes"),
            profile_data(environment="default"),
            profile_data(artifact_output="../outside"),
            profile_data(commands=["./scripts/build.sh"]),
            profile_data(credential_references=[{"name": "token=secret-value", "mechanism": "ssh-agent"}]),
            profile_data(health_checks=[]),
            profile_data(rollback_steps=[]),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(DeploymentPlanError) as caught:
                parse_target_profile(value)
            self.assertTrue(caught.exception.issues)
            self.assertTrue(caught.exception.issues[0].code)
            self.assertTrue(caught.exception.issues[0].remedy)

    def test_plan_is_deterministic_digest_bound_and_explicitly_non_authorizing(self) -> None:
        config = ProjectConfig(project_name="Plan Test", project_slug="plan-test", project_path="/tmp/plan-test")
        source = SourceState(
            repository="git",
            revision="0123456789abcdef0123456789abcdef01234567",
            dirty=True,
            changed_entry_count=2,
            project_is_repository_root=True,
        )
        plan = build_deployment_plan(config, parse_target_profile(profile_data()), source)
        self.assertEqual(plan.digest, build_deployment_plan(config, parse_target_profile(profile_data()), source).digest)
        self.assertEqual(plan.digest, "8fdee874a695282e7cd737a4ed0b7563c12241e08f3f132e7ad82cddc246818a")
        self.assertEqual(len(plan.digest), 64)
        self.assertFalse(plan.payload["authority"]["apply_authorized"])
        self.assertFalse(plan.payload["authority"]["remote_changes_performed"])
        self.assertEqual(plan.payload["source"]["revision"], source.revision)
        self.assertEqual(plan.payload["effects"]["commands"][1][0], "rsync")
        self.assertEqual(json.loads(render_plan_json(plan))["plan_digest"], plan.digest)
        text = render_plan_text(plan)
        self.assertIn(f"Plan digest (SHA-256): {plan.digest}", text)
        self.assertIn("Remote writes (advertised, not performed)", text)
        self.assertIn("Credential references (names/mechanisms only)", text)

    def test_source_inspection_uses_only_fixed_local_git_queries(self) -> None:
        responses = (
            subprocess.CompletedProcess([], 0, stdout="/tmp/project\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="0123456789abcdef0123456789abcdef01234567\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout=" M tracked.py\n?? new.py\n", stderr=""),
        )
        with mock.patch("agent_starter.deployment_plan.subprocess.run", side_effect=responses) as run:
            source = inspect_source_state(Path("/tmp/project"))
        self.assertTrue(source.dirty)
        self.assertEqual(source.changed_entry_count, 2)
        self.assertEqual(run.call_count, 3)
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[0], "git")
            self.assertIn("core.fsmonitor=false", argv)
            self.assertNotIn("fetch", argv)
            self.assertNotIn("push", argv)
            self.assertNotIn("remote", argv)
            self.assertNotIn("shell", call.kwargs)

    def test_profile_loading_refuses_escape_symlink_oversize_and_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            profile = root / "target.json"
            profile.write_text(json.dumps(profile_data()), encoding="utf-8")
            self.assertEqual(load_target_profile(root, Path("target.json")).target.value, "static-site")

            outside = Path(temp) / "outside.json"
            outside.write_text(json.dumps(profile_data()), encoding="utf-8")
            with self.assertRaises(DeploymentPlanError):
                load_target_profile(root, Path("../outside.json"))

            link = root / "link.json"
            link.symlink_to(outside)
            with self.assertRaises(DeploymentPlanError):
                load_target_profile(root, Path("link.json"))

            profile.write_text("{" + "x" * 140_000, encoding="utf-8")
            with self.assertRaises(DeploymentPlanError):
                load_target_profile(root, Path("target.json"))


if __name__ == "__main__":
    unittest.main()
