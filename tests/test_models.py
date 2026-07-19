from __future__ import annotations

import unittest

from agent_starter.models import (
    AdvisorCapability,
    AdvisorRecommendation,
    CapabilityDecision,
    CapabilityDecisionState,
    ProjectConfig,
)


class ProjectConfigTests(unittest.TestCase):
    def test_advisor_review_mode_never_mislabels_local_or_unknown_data_as_ai_reviewed(self) -> None:
        self.assertEqual(
            AdvisorRecommendation(source="local-fallback").review_label,
            "Local deterministic default — not AI-reviewed",
        )
        self.assertEqual(
            AdvisorRecommendation(source="manual-seed").review_label,
            "Local manual selection — not AI-reviewed",
        )
        self.assertEqual(
            AdvisorRecommendation(source="saved").review_label,
            "Saved recommendation — AI review not established",
        )
        self.assertEqual(
            AdvisorRecommendation(source="codex").review_label,
            "AI-reviewed structured recommendation",
        )

    def test_round_trip_preserves_timestamps_advisor_and_codex_default(self) -> None:
        config = ProjectConfig(
            project_name="Example",
            project_path="/tmp/example",
            languages=["python"],
            advisor=AdvisorRecommendation(
                summary="Small stack",
                recommended_capabilities=[AdvisorCapability(
                    "language.python", "Run Python", "required", "Matches the project", "high"
                )],
                architecture_notes=["Keep modules cohesive."],
                toolchain_capabilities=["language.python"],
                toolchain_packages=["legacy-arch-package"],
                source="test",
            ),
            capability_decisions=[
                CapabilityDecision(
                    "language.python", CapabilityDecisionState.ACCEPTED, "required", ""
                ),
                CapabilityDecision(
                    "optional.shellcheck", CapabilityDecisionState.REJECTED, "optional", ""
                ),
            ],
        )
        loaded = ProjectConfig.from_dict(config.to_dict())
        self.assertEqual(loaded.created_at, config.created_at)
        self.assertEqual(loaded.updated_at, config.updated_at)
        self.assertEqual(loaded.advisor.summary, "Small stack")
        self.assertEqual(loaded.advisor.toolchain_capabilities, ["language.python"])
        self.assertEqual(loaded.advisor.recommended_capabilities[0].capability_id, "language.python")
        self.assertEqual(loaded.advisor.architecture_notes, ["Keep modules cohesive."])
        self.assertEqual(loaded.advisor.toolchain_packages, ["legacy-arch-package"])
        self.assertEqual(loaded.capability_decisions, config.capability_decisions)
        self.assertEqual(
            loaded.capability_decisions[0].decision,
            CapabilityDecisionState.ACCEPTED,
        )
        self.assertEqual(loaded.primary_agent, "codex")
        self.assertEqual(loaded.license_name, "AGPL-3.0-or-later")

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
                    "image_profile": "debian-toolchain",
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
        self.assertEqual(loaded.sandbox.image_profile, "debian-toolchain")
        self.assertTrue(loaded.sandbox.codex_inside_container)
        self.assertTrue(loaded.sandbox.first_run_autonomous_prompt)
        self.assertTrue(loaded.sandbox.gui_passthrough)
        self.assertEqual(loaded.to_dict()["sandbox"]["engine"], "podman")
        self.assertEqual(loaded.to_dict()["sandbox"]["image_profile"], "debian-toolchain")


if __name__ == "__main__":
    unittest.main()
