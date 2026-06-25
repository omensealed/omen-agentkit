from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agent_starter.generator import REQUIRED_FILES, generate_project, validate_project
from agent_starter.models import AdvisorRecommendation, ProjectConfig


class GeneratorTests(unittest.TestCase):
    def make_config(self, root: Path, **overrides: object) -> ProjectConfig:
        values: dict[str, object] = {
            "project_name": "Generated Test",
            "project_slug": "generated-test",
            "project_path": str(root),
            "project_mode": "new",
            "project_type": "cli",
            "description": "A generated test project.",
            "languages": ["python"],
            "database": "sqlite",
            "primary_agent": "codex",
            "github_actions": True,
            "git_enabled": False,
        }
        values.update(overrides)
        return ProjectConfig(**values)

    def test_generation_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root, advisor=AdvisorRecommendation(raw_output="terminal noise", source="test"))
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            for relative in REQUIRED_FILES:
                self.assertTrue((root / relative).is_file(), relative)
            self.assertTrue(os.access(root / "START_AGENT.sh", os.X_OK))
            self.assertTrue((root / ".codex/config.toml").is_file())
            rsync_excludes = (root / ".agent-starter/rsync-excludes").read_text(encoding="utf-8")
            self.assertIn(".git/", rsync_excludes)
            self.assertIn(".agent-starter/proposals/", rsync_excludes)
            self.assertIn(".codex/sessions/", rsync_excludes)
            next_steps = (root / "NEXT_STEPS.md").read_text(encoding="utf-8")
            self.assertIn("Keep GitHub local-first", next_steps)
            self.assertIn("placeholder", next_steps)
            self.assertIn("./START_AGENT.sh", next_steps)
            self.assertIn(
                "OpenAI Codex CLI is the sole intended coding agent",
                (root / "AGENTS.md").read_text(encoding="utf-8"),
            )
            saved = json.loads((root / ".agent-starter/project.json").read_text())
            self.assertEqual(saved["advisor"]["raw_output"], "")
            self.assertTrue(validate_project(root).ok)

    def test_generated_gitignore_excludes_ai_local_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            for expected in (
                ".codex/*.jsonl",
                ".codex/sessions/",
                ".agent-starter/runtime.json",
                ".agent-starter/proposals/",
                "NEXT_PROMPT.md",
                "LOCAL_MODEL_HANDOFF.md",
                "*-codex-prompt.md",
            ):
                self.assertIn(expected, gitignore)

    def test_spdx_license_files_are_generated(self) -> None:
        cases = {
            "Apache-2.0": "SPDX-License-Identifier: Apache-2.0",
            "BSD-3-Clause": "SPDX-License-Identifier: BSD-3-Clause",
            "GPL-3.0-or-later": "SPDX-License-Identifier: GPL-3.0-or-later",
            "AGPL-3.0-or-later": "SPDX-License-Identifier: AGPL-3.0-or-later",
            "MPL-2.0": "SPDX-License-Identifier: MPL-2.0",
        }
        with tempfile.TemporaryDirectory() as temp:
            for license_name, expected in cases.items():
                with self.subTest(license_name=license_name):
                    root = Path(temp) / license_name.lower().replace(".", "-")
                    config = self.make_config(root, license_name=license_name)
                    report = generate_project(config)
                    self.assertTrue(report.ok, report.validation_errors)
                    license_text = (root / "LICENSE").read_text(encoding="utf-8")
                    self.assertIn(expected, license_text)

    def test_unchanged_generation_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            first = generate_project(config)
            second = generate_project(config)
            self.assertTrue(first.created)
            self.assertFalse(second.conflicts)
            self.assertFalse(second.created)
            self.assertTrue(second.unchanged)

    def test_conflict_is_preserved_as_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("user content\n", encoding="utf-8")
            report = generate_project(config)
            self.assertIn("README.md", report.conflicts)
            self.assertEqual((root / "README.md").read_text(), "user content\n")
            self.assertTrue(any(path.endswith("README.md") for path in report.proposals))

    def test_force_backs_up_before_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("old\n", encoding="utf-8")
            report = generate_project(config, force=True)
            self.assertIn("README.md", report.overwritten)
            self.assertTrue(any(path.endswith("README.md") for path in report.backups))
            self.assertNotEqual((root / "README.md").read_text(), "old\n")


    def test_invalid_package_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_config(Path(temp) / "project", cachyos_packages=["--overwrite=*"])
            with self.assertRaises(ValueError):
                generate_project(config)

    def test_symlinked_proposals_directory_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("user content\n", encoding="utf-8")
            outside = base / "outside"
            outside.mkdir()
            proposals = root / ".agent-starter" / "proposals"
            proposals.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                generate_project(config)
            self.assertFalse(any(outside.iterdir()))

    def test_dangerous_root_is_rejected(self) -> None:
        config = self.make_config(Path.home())
        with self.assertRaises(ValueError):
            generate_project(config, dry_run=True)


if __name__ == "__main__":
    unittest.main()
