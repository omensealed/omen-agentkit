from __future__ import annotations

import unittest

from agent_starter.models import ProjectConfig
from agent_starter.wizard import Prompter, build_advisor_prompt, run_wizard, slugify


class WizardHelpersTests(unittest.TestCase):
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
                "n",
            ]
        )
        output: list[str] = []
        result = run_wizard(
            initial_path="./wizard-project-test",
            input_fn=lambda _: next(answers),
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
        self.assertTrue(any("AGPL has network-service source-sharing obligations" in line for line in output))
        self.assertTrue(any("Local-first recommendation" in line for line in output))

    def test_prompter_rejects_credential_like_input(self) -> None:
        answers = iter(["password=hunter2", "safe note"])
        output: list[str] = []
        prompter = Prompter(lambda _: next(answers), output.append)
        self.assertEqual(prompter.ask("Notes"), "safe note")
        self.assertTrue(any("credential" in line for line in output))


if __name__ == "__main__":
    unittest.main()
