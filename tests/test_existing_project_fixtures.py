from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_starter.cli import load_generated_config
from agent_starter.cli_app.generation_commands import load_answers
from agent_starter.generator import generate_project, validate_project
from agent_starter.models import ProjectConfig
from agent_starter.structure.audit import audit_project


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "existing-projects" / "scenarios.json"


class ExistingProjectFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual(
            self.fixture["scenario_ids"],
            [
                "clean-repository",
                "dirty-repository",
                "generated-file-conflicts",
                "symlinked-directory",
                "older-agentkit-metadata",
                "manually-edited-answers",
                "large-god-file-hotspot",
            ],
        )

    def _config(self, root: Path, *, name: str) -> ProjectConfig:
        return ProjectConfig(
            project_name=name,
            project_slug=name.lower().replace(" ", "-"),
            project_path=str(root),
            project_mode="existing",
            project_type="cli",
            languages=["python"],
            database="sqlite",
            git_enabled=False,
        )

    def _init_repository(self, root: Path) -> None:
        root.mkdir()
        (root / "README.md").write_text(self.fixture["owner_content"]["readme"], encoding="utf-8")
        (root / "app.py").write_text('"""Owner application."""\nVALUE = 1\n', encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        subprocess.run(["git", "add", "README.md", "app.py"], cwd=root, check=True)
        subprocess.run(
            [
                "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-qm", "owner baseline",
            ],
            cwd=root,
            check=True,
        )

    def test_clean_existing_repository_preserves_owner_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "clean"
            self._init_repository(root)
            before = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True
            )
            self.assertEqual(before.stdout, "")
            original_readme = (root / "README.md").read_text(encoding="utf-8")
            report = generate_project(self._config(root, name="Clean Existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), original_readme)
            self.assertIn("README.md", report.conflicts)
            self.assertTrue(any(path.endswith("README.md") for path in report.proposals))
            self.assertTrue(validate_project(root).ok)

    def test_dirty_existing_repository_keeps_uncommitted_owner_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "dirty"
            self._init_repository(root)
            marker = self.fixture["owner_content"]["dirty_marker"]
            app = root / "app.py"
            app.write_text(app.read_text(encoding="utf-8") + marker, encoding="utf-8")
            before = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True
            )
            self.assertIn("app.py", before.stdout)
            report = generate_project(self._config(root, name="Dirty Existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertIn(marker, app.read_text(encoding="utf-8"))
            after = subprocess.run(
                ["git", "diff", "--", "app.py"], cwd=root, text=True, capture_output=True, check=True
            )
            self.assertIn(marker.strip(), after.stdout)

    def test_conflicting_generated_files_become_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "conflicts"
            (root / "docs").mkdir(parents=True)
            readme = self.fixture["owner_content"]["readme"]
            deployment = self.fixture["owner_content"]["deployment"]
            (root / "README.md").write_text(readme, encoding="utf-8")
            (root / "docs/16-DEPLOYMENT.md").write_text(deployment, encoding="utf-8")
            report = generate_project(self._config(root, name="Conflict Existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), readme)
            self.assertEqual((root / "docs/16-DEPLOYMENT.md").read_text(encoding="utf-8"), deployment)
            self.assertIn("README.md", report.conflicts)
            self.assertIn("docs/16-DEPLOYMENT.md", report.conflicts)
            self.assertTrue(any(path.endswith("README.md") for path in report.proposals))
            self.assertTrue(any(path.endswith("docs/16-DEPLOYMENT.md") for path in report.proposals))

    def test_symlinked_directory_refuses_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "symlinked"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (root / "docs").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked directory"):
                generate_project(self._config(root, name="Symlink Existing"))
            self.assertEqual(list(outside.iterdir()), [])

    def test_older_agentkit_metadata_loads_and_keeps_arch_only_intent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "older"
            config = self._config(root, name="Older Metadata")
            self.assertTrue(generate_project(config).ok)
            metadata = root / ".agent-starter/project.json"
            data = json.loads(metadata.read_text(encoding="utf-8"))
            data["schema_version"] = 1
            data.pop("extra_packages_by_provider", None)
            data["cachyos_packages"] = ["ripgrep"]
            metadata.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            loaded = load_generated_config(root)
            self.assertEqual(loaded.arch_extra_packages, ["ripgrep"])
            self.assertEqual(loaded.extra_packages_by_provider, {"arch": ["ripgrep"]})
            validation = validate_project(root)
            self.assertTrue(validation.ok, validation.errors)

    def test_manually_edited_answers_require_custom_command_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "manual"
            root.mkdir()
            answers_path = Path(temp) / "answers.json"
            answers = dict(self.fixture["manual_answers"])
            answers["project_path"] = str(root)
            answers_path.write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "executable custom commands"):
                load_answers(answers_path, path_override=None, allow_custom_commands=False)
            config = load_answers(answers_path, path_override=None, allow_custom_commands=True)
            self.assertFalse(config.network_access)
            self.assertEqual(config.extra_packages_by_provider, {"arch": ["ripgrep"]})
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            self.assertFalse((root / "should-not-exist").exists())

    def test_large_god_file_is_advisory_and_survives_renovation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "hotspot"
            package = root / "legacy"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text('"""Legacy package."""\n', encoding="utf-8")
            lines = ['"""Large owner-maintained legacy module."""']
            lines.extend(f"value_{index} = {index}" for index in range(525))
            lines.extend((
                "class LegacyEverythingService:",
                "    def render_ui(self):",
                "        return 'ui'",
                "    def save_database(self):",
                "        return 'db'",
            ))
            owner_source = "\n".join(lines) + "\n"
            hotspot = package / "god_file.py"
            hotspot.write_text(owner_source, encoding="utf-8")
            audit = audit_project(root)
            self.assertTrue(audit.advisory_only)
            self.assertFalse(audit.blocking)
            finding_codes = {
                finding.code
                for item in audit.hotspots
                if item.path == "legacy/god_file.py"
                for finding in item.findings
            }
            self.assertIn("structure.module-size", finding_codes)
            self.assertIn("structure.mixed-responsibilities", finding_codes)
            report = generate_project(self._config(root, name="Hotspot Existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual(hotspot.read_text(encoding="utf-8"), owner_source)
            self.assertTrue(validate_project(root).ok)


if __name__ == "__main__":
    unittest.main()
