from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.cli import build_parser, load_answers, main
from agent_starter.generator import generate_project
from agent_starter.models import ProjectConfig


class CliTests(unittest.TestCase):
    def test_version_and_toolchains(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("0.3.0", output.getvalue())

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["toolchains"])
        self.assertEqual(code, 0)
        self.assertIn("python", output.getvalue())


    def test_codex_only_parser_and_example(self) -> None:
        args = build_parser().parse_args(["auth", "--status"])
        self.assertTrue(args.status)
        with tempfile.TemporaryDirectory() as temp:
            answers = Path(temp) / "answers.json"
            self.assertEqual(main(["example-answers", "--output", str(answers)]), 0)
            data = json.loads(answers.read_text())
            self.assertEqual(data["primary_agent"], "codex")

    def test_example_answers_then_generate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            answers = temp_path / "answers.json"
            root = temp_path / "project"
            self.assertEqual(main(["example-answers", "--output", str(answers)]), 0)
            data = json.loads(answers.read_text())
            data["project_path"] = str(root)
            data["git_enabled"] = False
            answers.write_text(json.dumps(data), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["generate", "--answers", str(answers)]), 0)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "NEXT_STEPS.md").is_file())
            self.assertIn("NEXT_STEPS.md", output.getvalue())

    def test_custom_commands_require_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "answers.json"
            data = {
                "project_name": "Unsafe Test",
                "project_path": str(Path(temp) / "project"),
                "project_mode": "new",
                "description": "test",
                "primary_agent": "codex",
                "database": "none",
                "custom_test_commands": ["echo reviewed"],
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_answers(path, path_override=None, allow_custom_commands=False)
            loaded = load_answers(path, path_override=None, allow_custom_commands=True)
            self.assertEqual(loaded.custom_test_commands, ["echo reviewed"])

    def test_secret_like_answers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "answers.json"
            data = {
                "project_name": "Secret Test",
                "project_path": str(Path(temp) / "project"),
                "project_mode": "new",
                "description": "password=not-for-storage",
                "primary_agent": "codex",
                "database": "none",
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_answers(path, path_override=None, allow_custom_commands=False)

    def test_prompt_command_generates_codex_continuation_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Prompted Project",
                project_slug="prompted-project",
                project_path=str(root),
                project_mode="new",
                project_type="cli",
                description="A test project.",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
            )
            self.assertTrue(generate_project(config).ok)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["prompt", str(root), "--request", "Add an import command"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("User request", text)
            self.assertIn("Add an import command", text)
            self.assertIn("Read `AGENTS.md` completely", text)
            self.assertIn("Do not run `sudo`", text)
            self.assertIn("docs/11-IMPLEMENTATION-NOTES.md", text)

    def test_prompt_command_supports_named_templates(self) -> None:
        expected = {
            "feature": "Feature Implementation Template",
            "bug": "Bug Fix Template",
            "cleanup": "Cleanup Template",
            "docs": "Documentation Template",
            "test-baseline": "Test Baseline Template",
            "release-prep": "Release Preparation Template",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Template Prompt", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            for template, heading in expected.items():
                with self.subTest(template=template):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = main(["prompt", str(root), "--template", template, "--request", "Continue safely"])
                    text = output.getvalue()
                    self.assertEqual(code, 0)
                    self.assertIn(heading, text)
                    self.assertIn("Continue safely", text)
                    self.assertIn("./scripts/check.sh", text)

    def test_prompt_command_interactive_guides_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Interactive Prompt",
                project_slug="interactive-prompt",
                project_path=str(root),
                project_mode="new",
                project_type="cli",
                description="A test project.",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
            )
            self.assertTrue(generate_project(config).ok)
            answers = iter(
                [
                    "2",
                    "Fix the CSV import crash",
                    "A failing sample was added",
                    "import command and tests",
                    "High; preserve existing files",
                    "Run import tests and ./scripts/check.sh",
                    "bugfix phase",
                ]
            )

            output = io.StringIO()
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)), contextlib.redirect_stdout(output):
                code = main(["prompt", str(root), "--interactive"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Guided Codex continuation prompt", text)
            self.assertIn("Task type: Bug fix", text)
            self.assertIn("Bug Fix Template", text)
            self.assertIn("Fix the CSV import crash", text)
            self.assertIn("Risk level and concerns: High; preserve existing files", text)
            self.assertIn("Current phase focus: bugfix phase", text)

    def test_prompt_command_interactive_rejects_secret_like_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Interactive Secret", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)
            answers = iter(
                [
                    "feature",
                    "password=bad",
                    "Add a safe import view",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

            output = io.StringIO()
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)), contextlib.redirect_stdout(output):
                code = main(["prompt", str(root), "--interactive"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("resembles a credential", text)
            self.assertIn("Add a safe import view", text)
            self.assertNotIn("password=bad", text)

    def test_status_command_reports_workspace_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Status Project",
                project_slug="status-project",
                project_path=str(root),
                project_mode="new",
                project_type="cli",
                description="A test project.",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
            )
            self.assertTrue(generate_project(config).ok)

            adapter = mock.Mock()
            adapter.display_name = "OpenAI Codex CLI"
            adapter.exists.return_value = True
            adapter.version.return_value = "codex 1.2.3"
            adapter.auth_status.return_value = True

            output = io.StringIO()
            with mock.patch("agent_starter.cli.get_adapter", return_value=adapter), contextlib.redirect_stdout(output):
                code = main(["status", str(root)])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Workspace status:", text)
            self.assertIn("[ok] Metadata: Status Project", text)
            self.assertIn("[ok] Generated files:", text)
            self.assertIn("[ok] Codex: codex 1.2.3; authorized account reported", text)
            self.assertIn("AI-local prompt/session/proposal artifacts are ignored", text)
            self.assertIn("Next action:", text)

    def test_status_command_reports_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["status", temp])
            self.assertEqual(code, 2)
            self.assertIn("[fail] Metadata:", output.getvalue())

    def test_github_ready_reports_clean_local_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="GitHub Ready",
                project_slug="github-ready",
                project_path=str(root),
                project_mode="new",
                project_type="cli",
                description="A test project.",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
            )
            self.assertTrue(generate_project(config).ok)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline"],
                cwd=root,
                check=True,
                capture_output=True,
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["github-ready", str(root)])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("GitHub readiness:", text)
            self.assertIn("[ok] Local check: ./scripts/check.sh passed", text)
            self.assertIn("[ok] Git: repository", text)
            self.assertIn("GitHub Actions remain optional", text)

    def test_github_ready_blocks_dirty_or_failed_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="GitHub Blocked", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)
            (root / "untracked.txt").write_text("local\n", encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["github-ready", str(root), "--skip-check"])
            text = output.getvalue()
            self.assertEqual(code, 2)
            self.assertIn("[fail] Git:", text)
            self.assertIn("do not create a GitHub repository", text)

    def test_rsync_plan_prints_review_only_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            target = base / "mirror"
            config = ProjectConfig(project_name="Mirror Project", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["rsync-plan", str(root), str(target)])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Rsync mirror plan: Mirror Project", text)
            self.assertIn("--exclude-from", text)
            self.assertIn(".agent-starter/rsync-excludes", text)
            self.assertIn("Plan only", text)
            self.assertFalse(target.exists())

    def test_rsync_plan_refuses_target_inside_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Mirror Refuse", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["rsync-plan", str(root), str(root / "mirror")])
            self.assertEqual(code, 2)
            self.assertIn("Refusing to mirror into a path inside the project root", output.getvalue())

    def test_rsync_plan_run_requires_explicit_flag_and_invokes_rsync(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            target = base / "mirror"
            config = ProjectConfig(project_name="Mirror Run", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            calls: list[list[str]] = []

            def fake_run(command: list[str], **_: object) -> object:
                calls.append(command)
                return mock.Mock(returncode=0)

            output = io.StringIO()
            with (
                mock.patch("shutil.which", return_value="/usr/bin/rsync"),
                mock.patch("subprocess.run", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["rsync-plan", str(root), str(target), "--delete", "--run"])
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "rsync")
            self.assertIn("--delete", calls[0])
            self.assertIn(str(root) + "/", calls[0])
            self.assertIn(str(target), calls[0])

    def test_prompt_command_refuses_to_replace_output_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            target = Path(temp) / "NEXT_PROMPT.md"
            target.write_text("existing\n", encoding="utf-8")
            config = ProjectConfig(
                project_name="Prompt Output",
                project_slug="prompt-output",
                project_path=str(root),
                description="A test project.",
                git_enabled=False,
            )
            self.assertTrue(generate_project(config).ok)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["prompt", str(root), "--request", "Continue", "--output", str(target)])
            self.assertEqual(code, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")

            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["prompt", str(root), "--request", "Continue", "--output", str(target), "--force"])
            self.assertEqual(code, 0)
            self.assertIn("Continue", target.read_text(encoding="utf-8"))

    def test_ollama_check_allows_strong_context_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Local Ready", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            def fake_run(command: list[str], **_: object) -> object:
                if command[:2] == ["ollama", "list"]:
                    return mock.Mock(returncode=0, stdout="NAME ID SIZE MODIFIED\nqwen2.5-coder:32b abc 19 GB today\n", stderr="")
                if command[:3] == ["ollama", "show", "qwen2.5-coder:32b"]:
                    return mock.Mock(returncode=0, stdout='{"model_info":{"qwen2.context_length":131072}}', stderr="")
                raise AssertionError(command)

            output = io.StringIO()
            with (
                mock.patch("shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("subprocess.run", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["ollama-check", str(root), "--request", "Continue the import feature"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Assessment: suitable", text)
            self.assertIn("qwen2.5-coder:32b", text)
            self.assertIn("Continue the import feature", text)

    def test_ollama_check_blocks_undersized_model_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Local Blocked", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            def fake_run(command: list[str], **_: object) -> object:
                if command[:2] == ["ollama", "list"]:
                    return mock.Mock(returncode=0, stdout="NAME ID SIZE MODIFIED\nllama3.2:3b abc 2 GB today\n", stderr="")
                if command[:3] == ["ollama", "show", "llama3.2:3b"]:
                    return mock.Mock(returncode=0, stdout='{"model_info":{"llama.context_length":8192}}', stderr="")
                raise AssertionError(command)

            output = io.StringIO()
            with (
                mock.patch("shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("subprocess.run", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["ollama-check", str(root), "--model", "llama3.2:3b"])
            text = output.getvalue()
            self.assertEqual(code, 2)
            self.assertIn("Assessment: inadvisable", text)
            self.assertIn("--override", text)
            self.assertNotIn("## Local Model Handoff Prompt", text)

    def test_ollama_check_override_emits_warning_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Local Override", project_path=str(root), git_enabled=False)
            self.assertTrue(generate_project(config).ok)

            def fake_run(command: list[str], **_: object) -> object:
                if command[:2] == ["ollama", "list"]:
                    return mock.Mock(returncode=0, stdout="NAME ID SIZE MODIFIED\nllama3.2:3b abc 2 GB today\n", stderr="")
                if command[:3] == ["ollama", "show", "llama3.2:3b"]:
                    return mock.Mock(returncode=0, stdout='{"model_info":{"llama.context_length":8192}}', stderr="")
                raise AssertionError(command)

            output = io.StringIO()
            with (
                mock.patch("shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("subprocess.run", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["ollama-check", str(root), "--model", "llama3.2:3b", "--override"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Manual override accepted", text)
            self.assertIn("## Local Model Handoff Prompt", text)


if __name__ == "__main__":
    unittest.main()
