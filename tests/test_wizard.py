from __future__ import annotations

import unittest

from agent_starter.models import ProjectConfig
from agent_starter.wizard import Prompter, build_advisor_prompt, run_wizard, slugify


class WizardHelpersTests(unittest.TestCase):
    def wizard_input(self, answers: list[str]):
        iterator = iter(answers)

        def _input(prompt: str) -> str:
            if prompt.startswith("After generation, launch Codex"):
                return "n"
            return next(iterator, "")

        return _input

    def test_slugify(self) -> None:
        self.assertEqual(slugify(" My Cool_Game! "), "my-cool-game")
        self.assertEqual(slugify("***"), "new-project")

    def test_advisor_prompt_contains_constraints_not_tokens(self) -> None:
        config = ProjectConfig(
            project_name="Example",
            project_path="/private/path/not-needed",
            description="A CLI tool",
            project_type="cli",
            target_platforms=["cachyos-linux"],
        )
        prompt = build_advisor_prompt(config)
        self.assertIn("CachyOS", prompt)
        self.assertIn("standard library", prompt)
        self.assertNotIn(config.project_path, prompt)


    def test_manual_wizard_reaches_generation_review(self) -> None:
        answers = iter(
            [
                "new",
                "Wizard Project",
                "",
                "",
                "Build a small CLI program.",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "manual",
                "python",
                "none",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        output: list[str] = []
        result = run_wizard(
            initial_path="./wizard-project-test",
            input_fn=self.wizard_input(list(answers)),
            output_fn=output.append,
            skip_agent_setup=True,
        )
        self.assertEqual(result.config.project_name, "Wizard Project")
        self.assertEqual(result.config.languages, ["python"])
        self.assertEqual(result.config.database, "none")
        self.assertTrue(result.config.git_enabled)
        self.assertFalse(result.config.github_actions)
        self.assertEqual(result.config.github_remote, "none")
        self.assertFalse(result.launch_after_generation)
        self.assertTrue(any("Generation preserves existing files" in line for line in output))
        self.assertTrue(any("License quick guide" in line for line in output))
        self.assertTrue(any("AGPL-3.0-or-later is the default" in line for line in output))
        self.assertTrue(any("AGPL has network-service source-sharing obligations" in line for line in output))
        self.assertTrue(any("Local-first recommendation" in line for line in output))

    def test_new_project_defaults_to_toolchain_sandbox(self) -> None:
        answers = iter(
            [
                "new",
                "Sandbox Wizard",
                "",
                "",
                "Build a small CLI program.",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "manual",
                "python",
                "none",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        result = run_wizard(
            initial_path="./sandbox-wizard-test",
            input_fn=self.wizard_input(list(answers)),
            output_fn=lambda _line: None,
            skip_agent_setup=True,
        )
        self.assertTrue(result.config.sandbox.enabled)
        self.assertEqual(result.config.sandbox.mode, "toolchain")
        self.assertFalse(result.config.sandbox.codex_inside_container)
        self.assertFalse(result.config.sandbox.first_run_autonomous_prompt)

    def test_game_wizard_offers_gui_passthrough_after_stack_selection(self) -> None:
        answers = iter(
            [
                "new",
                "Godot Wizard",
                "",
                "",
                "Build a small Godot game.",
                "game",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "manual",
                "godot",
                "none",
                "",
                "",
                "",
                "y",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        output: list[str] = []
        result = run_wizard(
            initial_path="./godot-wizard-test",
            input_fn=self.wizard_input(list(answers)),
            output_fn=output.append,
            skip_agent_setup=True,
        )
        self.assertTrue(result.config.sandbox.enabled)
        self.assertTrue(result.config.sandbox.gui_passthrough)
        self.assertTrue(any("GPU/audio/controller passthrough" in line for line in output))

    def test_existing_project_defaults_to_no_sandbox(self) -> None:
        answers = iter(
            [
                "existing",
                ".",
                "Existing Project",
                "Renovate safely.",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "manual",
                "python",
                "none",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        result = run_wizard(
            initial_path=".",
            input_fn=self.wizard_input(list(answers)),
            output_fn=lambda _line: None,
            skip_agent_setup=True,
        )
        self.assertFalse(result.config.sandbox.enabled)
        self.assertEqual(result.config.sandbox.mode, "none")

    def test_prompter_rejects_credential_like_input(self) -> None:
        answers = iter(["password=hunter2", "safe note"])
        output: list[str] = []
        prompter = Prompter(lambda _: next(answers), output.append)
        self.assertEqual(prompter.ask("Notes"), "safe note")
        self.assertTrue(any("credential" in line for line in output))


if __name__ == "__main__":
    unittest.main()
