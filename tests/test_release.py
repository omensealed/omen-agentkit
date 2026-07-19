from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from agent_starter import __version__
from agent_starter.deployment_ci import validate_github_action_references
from agent_starter.models import ProjectConfig


class ReleaseConsistencyTests(unittest.TestCase):
    def test_local_kfnotepad_workspace_is_excluded_from_git(self) -> None:
        root = Path(__file__).resolve().parents[1]
        gitignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("kfnotepad/", gitignore)

    def test_version_is_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        version_file = (root / "VERSION").read_text(encoding="utf-8").strip()
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(version_file, __version__)
        self.assertEqual(version_file, match.group(1))
        self.assertEqual(version_file, ProjectConfig().kit_version)

    def test_source_parses_with_python_311_grammar(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / "agent_starter").rglob("*.py")) + [root / "starter.py"]:
            with self.subTest(path=path.relative_to(root)):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))

    def test_setuptools_discovers_agent_starter_subpackages(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.setuptools.packages.find]", pyproject)
        self.assertIn('include = ["agent_starter*"]', pyproject)
        self.assertNotIn('packages = ["agent_starter", "agent_starter.gui"]', pyproject)
        smoke = Path("scripts/package-smoke-test.sh").read_text(encoding="utf-8")
        self.assertIn("python3 -m build --no-isolation", smoke)
        self.assertIn("pip install --no-index --no-deps", smoke)
        self.assertIn("pip install --no-index --no-deps --no-build-isolation", smoke)
        self.assertIn("agent_starter.__main__", smoke)
        self.assertIn("for name in sorted(names - excluded_imports)", smoke)
        self.assertIn('"$TMP/wheel-venv/bin/agent-starter-gui" --help', smoke)
        self.assertIn('"$TMP/wheel-venv/bin/agent-starter" validate', smoke)

    def test_user_installer_smoke_covers_owned_and_unowned_paths(self) -> None:
        install = Path("install.sh").read_text(encoding="utf-8")
        uninstall = Path("uninstall.sh").read_text(encoding="utf-8")
        smoke = Path("scripts/install-smoke-test.sh").read_text(encoding="utf-8")
        for text in (install, uninstall):
            self.assertIn(".agent-starter-install-owner", text)
            self.assertIn("Refusing", text)
        for evidence in (
            "unowned-data",
            "unowned-launcher",
            "managed reinstall",
            "legacy managed adoption",
            "Generated projects and vendor CLI authorization were not touched",
        ):
            self.assertIn(evidence, smoke)

    def test_maintainer_quality_extra_is_constrained_and_never_runtime_required(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        for requirement in (
            '"ruff>=0.15.20,<0.16"',
            '"mypy>=2.3,<2.4"',
            '"bandit>=1.9.4,<1.10"',
            '"coverage>=7.15.1,<7.16"',
        ):
            self.assertIn(requirement, pyproject)
        self.assertIn("fail_under = 80", pyproject)
        quality = Path("scripts/quality-check.sh").read_text(encoding="utf-8")
        manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("include scripts/quality-check.sh", manifest.splitlines())
        for module in ("ruff", "mypy", "bandit", "coverage"):
            self.assertIn(f'python3 -m {module}', quality)
        self.assertIn("mktemp", quality)
        self.assertNotRegex(quality, r"(?m)^\s*python3 -m pip install")
        for forbidden in ("curl ", "wget ", "sudo ", "shell=True", "eval ", "exec "):
            self.assertNotIn(forbidden, quality)
        trusted = Path("scripts/check.sh").read_text(encoding="utf-8")
        self.assertNotIn("quality-check.sh", trusted)
        self.assertNotIn("pip install", trusted)

    def test_github_action_update_policy_is_reviewable_and_offline_safe(self) -> None:
        policy = Path("docs/GITHUB-ACTIONS-UPDATE-POLICY.md").read_text(encoding="utf-8")
        normalized = policy.replace("\n", " ")
        for required in (
            "full 40-character commit SHA",
            "human-readable release comment",
            "official GitHub release and commit pages",
            "action.yml",
            "workflow-level `contents: read`",
            "./scripts/check.sh",
            "Do not auto-merge",
            "does not contact GitHub",
        ):
            self.assertIn(required, normalized)
        self.assertNotIn("curl ", policy)
        self.assertNotIn("gh api", policy)

    def test_source_ci_keeps_native_python_matrix_and_focused_provider_containers(self) -> None:
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        compact = workflow.replace('"', "'")
        self.assertEqual(validate_github_action_references(workflow), ())
        self.assertIn("python-version: ['3.11', '3.13', '3.14']", compact)
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertEqual(workflow.count("run: ./scripts/check.sh"), 1)
        self.assertIn("provider-container-smoke:", workflow)
        provider_job = workflow.split("  provider-container-smoke:\n", 1)[1]
        self.assertNotIn("./scripts/check.sh", provider_job)
        self.assertRegex(provider_job, r"docker\.io/library/debian@sha256:[0-9a-f]{64}")
        self.assertRegex(provider_job, r"docker\.io/library/archlinux@sha256:[0-9a-f]{64}")
        self.assertIn("AGENTKIT_RUN_CONTAINER_MATRIX: '1'", provider_job)
        self.assertIn("AGENTKIT_CONTAINER_RUNTIME: docker", provider_job)
        self.assertIn(
            "python3 -m unittest tests.test_provider_matrix.PreloadedContainerMatrixTests -v",
            provider_job,
        )
        self.assertNotIn("apt-get install", provider_job)
        self.assertNotIn("pacman -S", provider_job)

    def test_supply_chain_updates_are_review_only_and_release_evidence_is_local(self) -> None:
        dependabot = Path(".github/dependabot.yml").read_text(encoding="utf-8")
        policy = Path("docs/SUPPLY-CHAIN-POLICY.md").read_text(encoding="utf-8")
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertIn("package-ecosystem: pip", dependabot)
        self.assertNotIn("reviewers:", dependabot)
        self.assertNotIn("auto-merge", dependabot)
        self.assertIn("There is no auto-merge configuration", policy)
        self.assertIn("exactly one regular wheel", policy)
        self.assertIn("do not add PPAs", policy)
        self.assertIn("python3 -m agent_starter.release_artifacts", workflow)
        self.assertIn("subject-checksums: ${{ runner.temp }}/release/SHA256SUMS", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("packages: write", workflow)


if __name__ == "__main__":
    unittest.main()
