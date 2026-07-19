from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from agent_starter import templates
from agent_starter.deployment_ci import CI_PROVIDER_IMAGES
from agent_starter.generator import generate_project, validate_project
from agent_starter.models import ProjectConfig, SandboxConfig
from agent_starter.platforms import (
    ArchProvider,
    CapabilityRequest,
    CommandResult,
    DebianFamilyProvider,
    PackageAvailability,
    SupportLevel,
    detect_platform,
)


FIXTURES = Path(__file__).parent / "fixtures"
OS_RELEASE = FIXTURES / "os-release"
GOLDEN = json.loads((FIXTURES / "provider-package-plans.json").read_text(encoding="utf-8"))


def _container_plan_argv(
    runtime: str, root: Path, image: str, provider_id: str,
) -> list[str]:
    return [
        runtime, "run", "--rm", "--pull=never", "--network=none",
        "--security-opt=no-new-privileges", "--cap-drop=all",
        "--volume", f"{root}:/workspace:ro", "--workdir", "/workspace", image,
        "bash", "scripts/bootstrap-dev.sh", "--provider", provider_id,
    ]


class ProviderMatrixTests(unittest.TestCase):
    @staticmethod
    def lookup(*available: str):
        names = set(available)
        return lambda name: f"/usr/bin/{name}" if name in names else None

    def test_representative_os_release_fixture_matrix(self) -> None:
        for fixture, expected in GOLDEN["providers"].items():
            manager = expected["package_manager"]
            with self.subTest(fixture=fixture):
                result = detect_platform(
                    (OS_RELEASE / fixture).read_text(encoding="utf-8"),
                    architecture="x86_64",
                    executable_lookup=self.lookup(manager),
                )
                self.assertEqual(result.support, SupportLevel.SUPPORTED)
                self.assertEqual(result.detected_provider, expected["detected_provider"])
                self.assertEqual(result.profile.package_provider, expected["detected_provider"])
                self.assertEqual(result.package_manager, manager)

    def test_unsupported_fixture_is_an_actionable_error_without_manager_probe(self) -> None:
        queried: list[str] = []

        def lookup(name: str) -> str | None:
            queried.append(name)
            return f"/usr/bin/{name}"

        result = detect_platform(
            (OS_RELEASE / "fedora-unsupported").read_text(encoding="utf-8"),
            architecture="x86_64",
            executable_lookup=lookup,
        )
        self.assertEqual(result.support, SupportLevel.UNSUPPORTED)
        self.assertIsNone(result.profile.package_provider)
        self.assertEqual(queried, [])
        issue = result.issues[-1]
        self.assertEqual(issue.code, "unsupported_platform")
        self.assertIn("reviewed supported provider override", issue.remedy)

    def test_golden_verified_install_plans_for_all_supported_hosts(self) -> None:
        requests = tuple(CapabilityRequest(item) for item in GOLDEN["capabilities"])
        for fixture, expected in GOLDEN["providers"].items():
            provider_id = expected["detected_provider"]
            provider = (
                ArchProvider(runner=lambda argv: CommandResult(0))
                if provider_id == "arch"
                else DebianFamilyProvider(provider_id, runner=lambda argv: CommandResult(0))
            )
            with self.subTest(fixture=fixture):
                resolved = provider.resolve_capabilities(requests)
                verified = tuple(replace(item, availability=PackageAvailability.AVAILABLE) for item in resolved)
                self.assertEqual(list(provider.install_plan(verified).argv), expected["install_argv"])
                if provider_id in {"debian", "ubuntu"}:
                    detection = detect_platform(
                        (OS_RELEASE / fixture).read_text(encoding="utf-8"),
                        architecture="x86_64",
                        executable_lookup=self.lookup("apt-get"),
                    )
                    self.assertEqual(list(provider.update_plan(detection.profile).argv), expected["refresh_argv"])

    def test_debian_and_ubuntu_representative_projects_generate_and_validate(self) -> None:
        for provider_id in ("debian", "ubuntu"):
            with self.subTest(provider=provider_id), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / provider_id
                config = ProjectConfig(
                    project_name=f"{provider_id.title()} Matrix",
                    project_slug=f"{provider_id}-matrix",
                    project_path=str(root),
                    project_mode="new",
                    project_type="cli",
                    target_platforms=["linux"],
                    languages=["python"],
                    database="sqlite",
                    git_enabled=False,
                    extra_packages_by_provider={provider_id: [f"{provider_id}-extra"]},
                    sandbox=SandboxConfig(enabled=True, mode="toolchain", image_profile="debian-toolchain"),
                )
                report = generate_project(config)
                self.assertTrue(report.ok, report.validation_errors)
                self.assertTrue(validate_project(root).ok)
                bootstrap = (root / "scripts/bootstrap-dev.sh").read_text(encoding="utf-8")
                containerfile = (root / ".agent-starter/sandbox/Containerfile").read_text(encoding="utf-8")
                self.assertIn(f"{provider_id.upper()}_PACKAGES=", bootstrap)
                self.assertIn(f"{provider_id}-extra", bootstrap)
                self.assertIn("debian:stable-slim", containerfile)
                self.assertNotIn("pacman", containerfile)
                self.assertNotIn("eval ", bootstrap)
                self.assertNotIn("source /etc/os-release", bootstrap)

    def test_plan_only_bootstrap_has_no_universal_pacman_gate_or_ai_execution(self) -> None:
        rendered = templates.bootstrap_script(ProjectConfig(
            project_name="Matrix",
            languages=["python"],
            database="sqlite",
            custom_setup_commands=["model-proposed-command --must-not-run"],
        ))
        self.assertIn("model-proposed-command --must-not-run", rendered)
        self.assertIn("Project-level setup commands to review/run after system packages", rendered)
        self.assertNotIn("command -v pacman ||", rendered)
        self.assertNotIn("eval ", rendered)
        self.assertNotIn("sh -c", rendered)

    def test_container_smoke_argv_is_read_only_network_off_and_plan_only(self) -> None:
        argv = _container_plan_argv(
            "/usr/bin/docker", Path("/tmp/generated-provider"),
            CI_PROVIDER_IMAGES["debian"].reference, "debian",
        )
        self.assertIn("--pull=never", argv)
        self.assertIn("--network=none", argv)
        self.assertIn("--security-opt=no-new-privileges", argv)
        self.assertIn("--cap-drop=all", argv)
        self.assertIn("/tmp/generated-provider:/workspace:ro", argv)
        self.assertEqual(argv[-4:], ["bash", "scripts/bootstrap-dev.sh", "--provider", "debian"])
        self.assertNotIn("--refresh", argv)
        self.assertNotIn("--install", argv)


@unittest.skipUnless(
    os.environ.get("AGENTKIT_RUN_CONTAINER_MATRIX") == "1",
    "set AGENTKIT_RUN_CONTAINER_MATRIX=1 only in CI with preloaded base images",
)
class PreloadedContainerMatrixTests(unittest.TestCase):
    """Opt-in, network-off verification for CI runners with preloaded images."""

    def test_preloaded_arch_and_debian_images_run_generated_plan_only_bootstrap(self) -> None:
        runtime_name = os.environ.get("AGENTKIT_CONTAINER_RUNTIME", "podman")
        if runtime_name not in {"docker", "podman"}:
            self.fail("AGENTKIT_CONTAINER_RUNTIME must be docker or podman")
        runtime = shutil.which(runtime_name)
        if runtime is None:
            self.skipTest(f"{runtime_name} is unavailable")
        images = (
            ("arch", CI_PROVIDER_IMAGES["arch"].reference, "pacman"),
            ("debian", CI_PROVIDER_IMAGES["debian"].reference, "apt-get"),
        )
        for provider_id, image, manager in images:
            with self.subTest(image=image):
                inspect_argv = (
                    [runtime, "image", "inspect", image]
                    if runtime_name == "docker"
                    else [runtime, "image", "exists", image]
                )
                exists = subprocess.run(
                    inspect_argv, check=False, capture_output=True, text=True, timeout=15
                )
                if exists.returncode != 0:
                    self.skipTest(f"preloaded image unavailable: {image}")
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp) / provider_id
                    report = generate_project(ProjectConfig(
                        project_name=f"{provider_id.title()} Container Matrix",
                        project_slug=f"{provider_id}-container-matrix",
                        project_path=str(root),
                        project_mode="new",
                        project_type="cli",
                        target_platforms=["linux"],
                        languages=["python"],
                        database="sqlite",
                        git_enabled=False,
                        extra_packages_by_provider={provider_id: [f"{provider_id}-extra"]},
                    ))
                    self.assertTrue(report.ok, report.validation_errors)
                    self.assertTrue(validate_project(root).ok)
                    result = subprocess.run(
                        _container_plan_argv(runtime, root, image, provider_id),
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f"Provider: {provider_id}", result.stdout)
                    self.assertIn("Review-only host plan; no package command was run", result.stdout)
                    self.assertIn(manager, result.stdout)


if __name__ == "__main__":
    unittest.main()
