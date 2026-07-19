from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from agent_starter.agents import parse_advisor_response
from agent_starter.config_schema import parse_config
from agent_starter.deployment_build import build_artifact, verify_built_artifact
from agent_starter.deployment_check import check_deployment
from agent_starter.deployment_plan import SourceState, build_deployment_plan, parse_target_profile
from agent_starter.doctor import CodexDoctorState, build_doctor_report, provider_for_detection
from agent_starter.generator import generate_project, validate_project
from agent_starter.gui.bridge import GuiBridge
from agent_starter.models import ProjectConfig, SandboxConfig
from agent_starter.platforms import (
    CapabilityRequest,
    CommandResult,
    PackageAvailability,
    detect_platform,
)
from agent_starter.recommendation import build_recommendation_review
from agent_starter.task_composer import approve_task_contract, build_task_contract, compose_task_packet


FIXTURES = Path(__file__).parent / "fixtures" / "os-release"
SOURCE_REVISION = "4" * 40


class EndToEndJourneyTests(unittest.TestCase):
    def _journey(self, *, fixture: str, provider_id: str, manager: str) -> None:
        metadata_calls: list[tuple[str, ...]] = []

        def lookup(name: str) -> str | None:
            return f"/synthetic/{name}" if name in {manager, "bash", "git", "curl"} else None

        def runner(argv: tuple[str, ...]) -> CommandResult:
            metadata_calls.append(argv)
            if argv[:2] == ("apt-cache", "policy"):
                return CommandResult(0, "  Candidate: 1.0\n")
            if argv[0] == "dpkg-query":
                return CommandResult(1)
            if argv[:2] == ("pacman", "-Si"):
                return CommandResult(0)
            if argv[:2] == ("pacman", "-Qq"):
                return CommandResult(1)
            raise AssertionError(f"Unexpected provider query: {argv!r}")

        detection = detect_platform(
            (FIXTURES / fixture).read_text(encoding="utf-8"),
            architecture="x86_64",
            executable_lookup=lookup,
        )
        self.assertEqual(detection.profile.package_provider, provider_id)
        provider = provider_for_detection(detection, runner=runner)
        self.assertIsNotNone(provider)
        doctor = build_doctor_report(
            kit_version="journey",
            python_version="3.11",
            detection=detection,
            provider=provider,
            executable_lookup=lookup,
            codex=CodexDoctorState(True, "codex synthetic", True),
        )
        self.assertEqual(doctor.exit_code, 0)
        self.assertEqual(doctor.to_dict()["provider"]["id"], provider_id)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / f"{provider_id}-journey"
            image_profile = "arch-toolchain" if provider_id == "arch" else "debian-toolchain"
            config = ProjectConfig(
                project_name=f"{provider_id.title()} Fresh Journey",
                project_slug=f"{provider_id}-fresh-journey",
                project_path=str(root),
                project_mode="new",
                project_type="cli",
                target_platforms=["linux"],
                languages=["python"],
                database="sqlite",
                git_enabled=False,
                sandbox=SandboxConfig(enabled=True, mode="toolchain", image_profile=image_profile),
            )

            deterministic = build_recommendation_review(
                config,
                profile=detection.profile,
                provider=provider,
            )
            self.assertIn("language.python", deterministic.capability_ids)
            self.assertIn("database.sqlite", deterministic.capability_ids)

            advisor = parse_advisor_response({
                "summary": "Keep the generated Python CLI small.",
                "languages": ["python"],
                "database": "sqlite",
                "recommended_capabilities": [{
                    "capability_id": "optional.shellcheck",
                    "purpose": "Review generated shell helpers.",
                    "requirement": "optional",
                    "rationale": "The workspace contains shell entry points.",
                    "confidence": "medium",
                }],
                "architecture_notes": ["Keep a thin CLI over pure functions."],
                "questions": [],
                "risks": [],
            })
            with mock.patch("agent_starter.agents.subprocess.run") as codex_process:
                assisted = build_recommendation_review(
                    config,
                    profile=detection.profile,
                    provider=provider,
                    advisor=advisor,
                )
            codex_process.assert_not_called()
            self.assertIn("optional.shellcheck", assisted.capability_ids)

            requests = tuple(CapabilityRequest(item) for item in (
                "base.tooling", "language.python", "database.sqlite", "sandbox.rootless-podman"
            ))
            resolved = provider.resolve_capabilities(requests)  # type: ignore[union-attr]
            verified = tuple(replace(item, availability=PackageAvailability.AVAILABLE) for item in resolved)
            install_plan = provider.install_plan(verified)  # type: ignore[union-attr]
            self.assertTrue(install_plan.requires_network)
            self.assertTrue(install_plan.requires_privilege)
            self.assertEqual(install_plan.argv[0], "sudo")
            self.assertFalse(any(call[0] == "sudo" for call in metadata_calls))
            allowed_query_heads = {"pacman"} if provider_id == "arch" else {"apt-cache", "dpkg-query"}
            self.assertTrue(all(call[0] in allowed_query_heads for call in metadata_calls))

            generated = generate_project(config)
            self.assertTrue(generated.ok, generated.validation_errors)
            validation = validate_project(root)
            self.assertTrue(validation.ok, validation.errors)
            local_check = subprocess.run(
                [str(root / "scripts/check.sh")],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(local_check.returncode, 0, local_check.stderr)
            self.assertIn("All configured checks passed", local_check.stdout)

            feature = approve_task_contract(build_task_contract(compose_task_packet("feature", {
                "outcome": "A person can inspect one saved record.",
                "example": "Show record 42.",
                "preserve": "Keep existing CLI flags compatible.",
                "acceptance": "A focused record-view test passes.",
            })))
            fix = approve_task_contract(build_task_contract(compose_task_packet("fix", {
                "steps": "Run the record view with an unknown identifier.",
                "observed": "The command exits without a useful message.",
                "expected": "The command reports that the record is missing.",
                "error_text": "No error text was shown.",
                "frequency": "consistent",
            })))
            self.assertEqual(feature.state, "approved")
            self.assertEqual(fix.state, "approved")
            self.assertIn("Treat `AGENTS.md` as binding", feature.prompt)

            preview = GuiBridge().launch_preview(str(root))
            self.assertTrue(preview["ok"], preview)
            self.assertEqual(preview["preview"]["model_policy"]["exact_model_id"], "gpt-5.6-sol")
            self.assertEqual(preview["preview"]["model_policy"]["reasoning_effort"], "medium")
            self.assertTrue((root / "scripts/sandbox/doctor").is_file())
            self.assertEqual(preview["preview"]["sandbox"]["project_mode"], "toolchain")
            self.assertFalse((root / ".agent-starter/sandbox/preflight.json").exists())

            public = root / "public"
            public.mkdir()
            (public / "index.html").write_text("<h1>Local journey artifact</h1>\n", encoding="utf-8")
            profile = parse_target_profile({
                "schema_version": 1,
                "target": "static-site",
                "environment": "staging",
                "target_identifier": f"{provider_id}-local-staging",
                "artifact_output": "dist/site.zip",
                "local_writes": ["dist/site.zip"],
                "remote_writes": [],
                "commands": [["touch", "must-not-exist"]],
                "network_destinations": [],
                "credential_references": [],
                "health_checks": ["Inspect the local artifact."],
                "rollback_steps": ["Delete the unshipped local artifact."],
            })
            source_state = SourceState("git", SOURCE_REVISION, False, 0, True)
            plan = build_deployment_plan(config, profile, source_state)
            self.assertFalse(plan.payload["authority"]["apply_authorized"])
            with mock.patch("agent_starter.deployment_build.inspect_source_state", return_value=source_state):
                artifact = build_artifact(root, plan, Path("public"), plan_reference="in-memory-plan")
            self.assertTrue(artifact.reproducible)
            self.assertTrue(verify_built_artifact(root / artifact.artifact_path, plan_digest=plan.digest).ok)
            with mock.patch("agent_starter.deployment_check.inspect_source_state", return_value=source_state):
                checked = check_deployment(root, plan)
            statuses = {item.check_id: item.status for item in checked.findings}
            self.assertEqual(statuses["artifact_checksum"], "passed")
            self.assertEqual(statuses["artifact_reproducibility"], "passed")
            self.assertFalse(checked.to_dict()["authority"]["target_contacted"])
            self.assertFalse((root / "must-not-exist").exists())

            migrated = parse_config({
                "schema_version": 1,
                "project_name": "Migrated Journey",
                "project_path": str(Path(temp) / "migrated"),
                "project_mode": "new",
                "primary_agent": "codex",
                "database": "none",
                "cachyos_packages": ["ripgrep"],
            })
            self.assertEqual(migrated.source_version, 1)
            self.assertEqual(migrated.config.extra_packages_by_provider, {"arch": ["ripgrep"]})
            self.assertNotIn("debian", migrated.config.extra_packages_by_provider)
            self.assertNotIn("ubuntu", migrated.config.extra_packages_by_provider)

    def test_cachyos_arch_fresh_user_journey(self) -> None:
        self._journey(fixture="cachyos", provider_id="arch", manager="pacman")

    def test_debian_fresh_user_journey(self) -> None:
        self._journey(fixture="debian", provider_id="debian", manager="apt-get")

    def test_ubuntu_fresh_user_journey(self) -> None:
        self._journey(fixture="ubuntu", provider_id="ubuntu", manager="apt-get")


if __name__ == "__main__":
    unittest.main()
