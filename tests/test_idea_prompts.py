from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from agent_starter.generator import generate_project
from agent_starter.idea_prompts import parse_mode_and_idea, write_idea_prompt
from agent_starter.models import ProjectConfig, SandboxConfig


class IdeaPromptTests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        config = ProjectConfig(
            project_name="Idea Prompt Project",
            project_slug="idea-prompt-project",
            project_path=str(root),
            project_type="cli",
            languages=["python"],
            database="sqlite",
            git_enabled=False,
        )
        self.assertTrue(generate_project(config).ok)

    def test_mode_and_idea_creates_prompt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.make_project(root)
            result = write_idea_prompt(
                start=root,
                mode="implement",
                idea="Add SQLite save/load support",
                today=date(2026, 6, 27),
            )

            self.assertTrue(result.prompt_path.is_file())
            self.assertEqual(result.mode, "implement")
            self.assertEqual(result.idea, "Add SQLite save/load support")
            self.assertEqual(
                result.prompt_path.relative_to(root).as_posix(),
                "docs/agent-prompts/2026-06-27-implement-add-sqlite-save-load-support.md",
            )
            text = result.prompt_path.read_text(encoding="utf-8")
            self.assertIn("Add SQLite save/load support", text)
            self.assertIn("Implement the smallest coherent change", text)
            self.assertIn("Avoid god files", text)
            self.assertIn("docs/11-IMPLEMENTATION-NOTES.md", text)
            self.assertLess(text.index("docs/AGENT-INDEX.md"), text.index("AGENTS.md"))
            self.assertIn("only the task-relevant files", text)
            self.assertIn("## Canonical policy references", text)
            self.assertIn("AGENTS.md#canonical-policy-registry", text)
            self.assertNotIn("Do not run `sudo`, install packages, create GitHub repositories, push", text)
            self.assertNotIn("docs/10-PROGRESS.md", text)

    def test_from_codex_parses_known_mode(self) -> None:
        mode, idea = parse_mode_and_idea(arguments="implement Add thing")
        self.assertEqual(mode, "implement")
        self.assertEqual(idea, "Add thing")

    def test_unknown_first_token_defaults_to_implement(self) -> None:
        mode, idea = parse_mode_and_idea(arguments="ship Add thing")
        self.assertEqual(mode, "implement")
        self.assertEqual(idea, "ship Add thing")

    def test_empty_idea_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_mode_and_idea(mode="implement", idea="")
        with self.assertRaises(ValueError):
            parse_mode_and_idea(arguments="implement")

    def test_prompt_generation_works_without_codex_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.make_project(root)
            with mock.patch("shutil.which", return_value=None):
                result = write_idea_prompt(start=root, mode="docs", idea="Refresh README")
            self.assertTrue(result.prompt_path.is_file())
            self.assertIn("Update documentation accurately", result.body)

    def test_same_day_duplicate_preserves_both_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.make_project(root)
            first = write_idea_prompt(start=root, mode="implement", idea="Add import", today=date(2026, 7, 14))
            first.prompt_path.write_text(first.body + "\nreviewed first draft\n", encoding="utf-8")
            second = write_idea_prompt(start=root, mode="implement", idea="Add import", today=date(2026, 7, 14))
            self.assertNotEqual(first.prompt_path, second.prompt_path)
            self.assertEqual(second.prompt_path.name, "2026-07-14-implement-add-import-02.md")
            self.assertIn("reviewed first draft", first.prompt_path.read_text(encoding="utf-8"))
            self.assertNotIn("reviewed first draft", second.prompt_path.read_text(encoding="utf-8"))

    def test_prompt_writer_refuses_symlinked_prompt_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (root / "docs").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                write_idea_prompt(start=root, mode="implement", idea="Do not escape")
            self.assertFalse(any(outside.iterdir()))

    def test_prompt_includes_sandbox_guidance_when_project_has_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Sandbox Prompt",
                project_slug="sandbox-prompt",
                project_path=str(root),
                project_type="web",
                languages=["python"],
                database="mariadb",
                git_enabled=False,
                sandbox=SandboxConfig(enabled=True, mode="toolchain"),
            )
            self.assertTrue(generate_project(config).ok)
            result = write_idea_prompt(start=root, mode="implement", idea="Add a dashboard")
            self.assertIn("Agent Kit sandbox mode: `toolchain`", result.body)
            self.assertIn("scripts/sandbox/check", result.body)
            self.assertIn("scripts/sandbox/db-up", result.body)
            self.assertIn("scripts/sandbox/web", result.body)
            self.assertIn("Do not mount host `~/.codex`", result.body)
            self.assertIn("Do not use host `danger-full-access`", result.body)
            self.assertIn("Treat enabled sandbox metadata as a requested execution boundary", result.body)
            self.assertIn("Do not silently fall back to host build/test commands", result.body)
            self.assertIn("BLOCKED_ENVIRONMENT", result.body)
            self.assertIn("Codex may still edit the host project directory", result.body)
            self.assertIn("already inside the container", result.body)
            self.assertIn("run `./scripts/check.sh`", result.body)
            self.assertIn("do not run host-side `scripts/sandbox/*` launchers", result.body)
            self.assertIn(".agent-starter/sandbox/preflight.json", result.body)
            self.assertIn("do not rerun `scripts/sandbox/doctor`", result.body)
            self.assertIn("Do not ask for Codex `danger-full-access`", result.body)
            self.assertIn("launch Codex inside the container", result.body)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.make_project(root)
            completed = subprocess.run(
                [
                    "./agent-starter",
                    "idea-prompt",
                    "--project",
                    str(root),
                    "--from-codex",
                    "--arguments",
                    "fix The generated check script fails",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            data = json.loads(completed.stdout)
            self.assertEqual(data["mode"], "fix")
            self.assertEqual(data["idea"], "The generated check script fails")
            self.assertTrue(Path(data["prompt_path"]).is_file())

    def test_no_shell_true_for_user_idea_text(self) -> None:
        for path in (Path("agent_starter/idea_prompts.py"), Path("agent_starter/cli.py")):
            self.assertNotIn("shell=True", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
