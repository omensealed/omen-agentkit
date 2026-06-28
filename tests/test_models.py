from __future__ import annotations

import unittest

from agent_starter.models import AdvisorRecommendation, ProjectConfig


class ProjectConfigTests(unittest.TestCase):
    def test_round_trip_preserves_timestamps_advisor_and_codex_default(self) -> None:
        config = ProjectConfig(
            project_name="Example",
            project_path="/tmp/example",
            languages=["python"],
            advisor=AdvisorRecommendation(summary="Small stack", source="test"),
        )
        loaded = ProjectConfig.from_dict(config.to_dict())
        self.assertEqual(loaded.created_at, config.created_at)
        self.assertEqual(loaded.updated_at, config.updated_at)
        self.assertEqual(loaded.advisor.summary, "Small stack")
        self.assertEqual(loaded.primary_agent, "codex")

    def test_unknown_saved_fields_are_ignored_by_model_loader(self) -> None:
        loaded = ProjectConfig.from_dict({"project_name": "Example", "retired_field": "ignored"})
        self.assertEqual(loaded.project_name, "Example")
        self.assertEqual(loaded.primary_agent, "codex")

    def test_missing_sandbox_defaults_to_disabled(self) -> None:
        loaded = ProjectConfig.from_dict({"project_name": "Example"})
        self.assertFalse(loaded.sandbox.enabled)
        self.assertEqual(loaded.sandbox.mode, "none")
        self.assertEqual(loaded.sandbox.engine, "podman")

    def test_sandbox_config_round_trip(self) -> None:
        loaded = ProjectConfig.from_dict(
            {
                "project_name": "Sandboxed",
                "sandbox": {
                    "enabled": True,
                    "engine": "podman",
                    "mode": "codex",
                    "codex_inside_container": True,
                    "rootless_required": True,
                    "install_agentkit_skill": True,
                    "first_run_autonomous_prompt": True,
                    "gui_passthrough": True,
                },
            }
        )
        self.assertTrue(loaded.sandbox.enabled)
        self.assertEqual(loaded.sandbox.mode, "codex")
        self.assertTrue(loaded.sandbox.codex_inside_container)
        self.assertTrue(loaded.sandbox.first_run_autonomous_prompt)
        self.assertTrue(loaded.sandbox.gui_passthrough)
        self.assertEqual(loaded.to_dict()["sandbox"]["engine"], "podman")


if __name__ == "__main__":
    unittest.main()
