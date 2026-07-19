from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_starter.codex_skill import SKILL_MD, SKILL_META, SKILL_VERSION, inspect_skill, install_skill, uninstall_skill, update_skill
from agent_starter.generator import generate_project
from agent_starter.models import ProjectConfig


class CodexSkillTests(unittest.TestCase):
    def test_install_creates_skill_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            action, written, backup = install_skill(root)
            self.assertEqual(action, "installed")
            self.assertIsNone(backup)
            self.assertIn(root / SKILL_MD, written)
            self.assertIn(root / SKILL_META, written)

            skill = (root / SKILL_MD).read_text(encoding="utf-8")
            self.assertTrue(skill.startswith("---\nname: agentkit\n"))
            self.assertIn("description:", skill)
            self.assertIn(f"Agent Kit skill version: {SKILL_VERSION}", skill)
            self.assertIn("agent-starter idea-prompt", skill)
            self.assertLess(skill.index("docs/AGENT-INDEX.md"), skill.index("AGENTS.md"))
            self.assertLess(len(skill.splitlines()), 60)

            metadata = json.loads((root / SKILL_META).read_text(encoding="utf-8"))
            self.assertEqual(metadata["name"], "agentkit")
            self.assertEqual(metadata["skill_version"], SKILL_VERSION)
            self.assertEqual(metadata["agent_starter_min_version"], "0.3.0")
            self.assertTrue(metadata["managed"])
            self.assertEqual(metadata["prompt_builder_command"], "agent-starter idea-prompt")

    def test_status_detects_missing_current_and_outdated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = inspect_skill(root)
            self.assertFalse(missing.exists)
            self.assertFalse(missing.managed)

            install_skill(root)
            current = inspect_skill(root)
            self.assertTrue(current.exists)
            self.assertTrue(current.managed)
            self.assertEqual(current.installed_version, SKILL_VERSION)
            self.assertFalse(current.update_available)

            metadata_path = root / SKILL_META
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            data["skill_version"] = "0.0.1"
            metadata_path.write_text(json.dumps(data), encoding="utf-8")
            outdated = inspect_skill(root)
            self.assertTrue(outdated.update_available)

    def test_update_managed_skill_backs_up_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install_skill(root)
            (root / SKILL_MD).write_text("old managed text\n", encoding="utf-8")
            action, _written, backup = update_skill(root, yes=True)
            self.assertEqual(action, "updated")
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertTrue((backup / "SKILL.md").is_file())
            self.assertEqual((backup / "SKILL.md").read_text(encoding="utf-8"), "old managed text\n")
            self.assertIn("agent-starter idea-prompt", (root / SKILL_MD).read_text(encoding="utf-8"))

    def test_install_refuses_non_managed_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / SKILL_MD
            path.parent.mkdir(parents=True)
            path.write_text("---\nname: agentkit\n---\ncustom\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                install_skill(root)
            self.assertIn("custom", path.read_text(encoding="utf-8"))

    def test_uninstall_refuses_non_managed_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / SKILL_MD
            path.parent.mkdir(parents=True)
            path.write_text("custom\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                uninstall_skill(root)
            self.assertTrue(path.exists())

    def test_uninstall_managed_skill_preserves_extra_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install_skill(root)
            extra = root / SKILL_MD.parent / "notes.md"
            extra.write_text("user note\n", encoding="utf-8")
            action, backup = uninstall_skill(root)
            self.assertEqual(action, "removed")
            self.assertIsNotNone(backup)
            self.assertFalse((root / SKILL_MD).exists())
            self.assertFalse((root / SKILL_META).exists())
            self.assertTrue(extra.is_file())
            self.assertEqual(extra.read_text(encoding="utf-8"), "user note\n")

    def test_generated_projects_include_or_omit_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            enabled = Path(temp) / "enabled"
            disabled = Path(temp) / "disabled"
            enabled_config = ProjectConfig(project_name="Enabled", project_path=str(enabled), git_enabled=False)
            disabled_config = ProjectConfig(
                project_name="Disabled",
                project_path=str(disabled),
                git_enabled=False,
                codex_agentkit_skill=False,
            )
            self.assertTrue(generate_project(enabled_config).ok)
            self.assertTrue(generate_project(disabled_config).ok)
            self.assertTrue((enabled / SKILL_MD).is_file())
            self.assertTrue((enabled / SKILL_META).is_file())
            self.assertFalse((disabled / SKILL_MD).exists())
            self.assertFalse((disabled / SKILL_META).exists())


if __name__ == "__main__":
    unittest.main()
