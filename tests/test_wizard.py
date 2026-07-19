from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from agent_starter.models import AdvisorCapability, AdvisorRecommendation, CapabilityDecisionState, ProjectConfig
from agent_starter.generator import generate_project, validate_project
from agent_starter.recommendation import RecommendationReview, RecommendationSource, ReviewedCapability
from agent_starter.recommendation_cache import CachedRecommendation
from agent_starter.platforms import ExecutableFact, HostProfile, PrerequisiteCheck, PrerequisiteStatus, RootlessPodmanStatus
from agent_starter.wizard import (
    CancelledByUser,
    Prompter,
    _choose_database,
    _collect_capability_decisions,
    _local_recommendation,
    _looks_sensitive,
    _manual_languages,
    _normalize_database,
    _prepare_agent,
    _print_recommendation,
    _split_list,
    build_advisor_host_snapshot,
    build_advisor_prompt,
    render_advisor_host_snapshot,
    run_wizard,
    slugify,
)
from agent_starter.guided import advisor
from agent_starter.guided import questions


class WizardHelpersTests(unittest.TestCase):
    def test_advisor_support_exports_and_prompt_bytes_remain_compatible(self) -> None:
        exports = (
            (build_advisor_host_snapshot, advisor.build_advisor_host_snapshot),
            (render_advisor_host_snapshot, advisor.render_advisor_host_snapshot),
            (build_advisor_prompt, advisor.build_advisor_prompt),
            (_print_recommendation, advisor._print_recommendation),
            (_collect_capability_decisions, advisor._collect_capability_decisions),
            (_local_recommendation, advisor._local_recommendation),
            (_prepare_agent, advisor._prepare_agent),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

        config = ProjectConfig(
            project_name="Boundary",
            project_mode="new",
            project_stage="idea",
            project_type="cli",
            description="A deterministic CLI.",
            goals=["Ship safely"],
            non_goals=["Network service"],
            target_users="Maintainers",
            target_platforms=["linux"],
            packaging_targets=["source checkout"],
            network_access=False,
            user_accounts=False,
            handles_personal_data=False,
            handles_payments=False,
        )
        rendered = build_advisor_prompt(config)
        self.assertEqual(len(rendered), 2149)
        self.assertEqual(
            hashlib.sha256(rendered.encode()).hexdigest(),
            "06265295727ee8136ff0675b1bfd84c054277345989bd5964823df0cc634ac58",
        )

    def test_question_group_exports_and_transcript_remain_compatible(self) -> None:
        exports = (
            (CancelledByUser, questions.CancelledByUser),
            (Prompter, questions.Prompter),
            (slugify, questions.slugify),
            (_split_list, questions._split_list),
            (_looks_sensitive, questions._looks_sensitive),
            (_normalize_database, questions._normalize_database),
            (_manual_languages, questions._manual_languages),
            (_choose_database, questions._choose_database),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

        output: list[str] = []
        answers = iter(["1, javascript, Custom Lang", "2"])
        prompt = Prompter(input_fn=lambda _: next(answers), output_fn=output.append)
        self.assertEqual(_manual_languages(prompt), ["python", "javascript", "custom-lang"])
        self.assertEqual(_choose_database(prompt, default="postgres"), "sqlite")
        self.assertEqual(
            output,
            [
                "Select one or more implementation languages/toolchains. Custom names are allowed but receive no automatic commands:",
                "  1. Python",
                "  2. JavaScript / Node.js",
                "  3. Rust",
                "  4. Go",
                "  5. PHP",
                "  6. C / C++",
                "  7. Java",
                "  8. Godot / GDScript",
                "  9. POSIX shell / Bash",
                "Persistence/database plan:",
                "  1. No database",
                "  2. SQLite file database (simple local/default choice)",
                "  3. MariaDB service",
                "  4. PostgreSQL service",
                "  5. An existing database must be discovered safely",
                "  6. Leave as an explicit Phase 0 decision",
            ],
        )

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

    def test_guided_mode_uses_safe_defaults_and_hides_nonessential_questions(self) -> None:
        prompts: list[str] = []
        output: list[str] = []

        def guided_input(prompt: str) -> str:
            prompts.append(prompt)
            if prompt.startswith("Project name"):
                return "Guided Project"
            if prompt.startswith("Describe what"):
                return "Build a small local CLI."
            if prompt.startswith("Create a rootless"):
                return "n"
            if prompt.startswith("Choice") and any("How should the first stack" in line for line in output[-4:]):
                return "manual"
            if prompt.startswith("After generation"):
                return "n"
            return ""

        result = run_wizard(
            initial_path="./guided-project-test",
            input_fn=guided_input,
            output_fn=output.append,
            skip_agent_setup=True,
            entry_mode="guided",
        )
        asked = "\n".join(prompts)
        self.assertEqual(result.config.project_stage, "idea")
        self.assertEqual(result.config.packaging_targets, ["source checkout", "documented local development build"])
        self.assertEqual(result.config.tests, ["unit", "integration"])
        self.assertFalse(result.config.github_actions)
        self.assertEqual(result.config.default_branch, "main")
        self.assertNotIn("Current stage", asked)
        self.assertNotIn("Desired deliverables", asked)
        self.assertNotIn("Stack/architecture constraints", asked)
        self.assertNotIn("Expected test layers", asked)
        self.assertNotIn("GitHub Actions", asked)
        self.assertTrue(any("Guided mode" in line for line in output))
        self.assertTrue(any("--mode advanced" in line for line in output))

    def test_advisor_prompt_contains_constraints_not_tokens(self) -> None:
        config = ProjectConfig(
            project_name="Example",
            project_path="/private/path/not-needed",
            description="A CLI tool",
            project_type="cli",
            target_platforms=["cachyos-linux"],
        )
        prompt = build_advisor_prompt(config)
        self.assertIn("recommended_capabilities", prompt)
        self.assertIn("language.python", prompt)
        self.assertNotIn("CachyOS package names", prompt)
        self.assertNotIn("setup_commands", prompt)
        self.assertNotIn("build_commands", prompt)
        self.assertNotIn("install commands", prompt.lower())
        self.assertIn("standard library", prompt)
        self.assertNotIn(config.project_path, prompt)

    def test_per_item_decisions_reject_optional_and_explain_required_challenge(self) -> None:
        output: list[str] = []
        answers = iter(["n", "n"])
        prompt = Prompter(input_fn=lambda _: next(answers), output_fn=output.append)
        review = RecommendationReview(
            provider_id="debian",
            provider_label="Debian",
            items=(
                ReviewedCapability(
                    "language.python", "Python toolchain", "Run and test Python.", "required",
                    (RecommendationSource.DETERMINISTIC,), confidence="high", provider_id="debian",
                ),
                ReviewedCapability(
                    "optional.shellcheck", "ShellCheck", "Check shell helpers.", "optional",
                    (RecommendationSource.AI_SUGGESTED,), confidence="medium", provider_id="debian",
                ),
            ),
        )
        decisions = _collect_capability_decisions(prompt, review)
        self.assertEqual(
            [item.decision for item in decisions],
            [CapabilityDecisionState.CHALLENGED, CapabilityDecisionState.REJECTED],
        )
        self.assertIn("Run and test Python", decisions[0].limitation)
        self.assertEqual(decisions[1].limitation, "")
        self.assertTrue(any("limitation" in line.lower() for line in output))

    def test_advisor_host_snapshot_is_exactly_rendered_and_forbidden_fields_are_absent(self) -> None:
        config = ProjectConfig(
            project_name="Snapshot",
            project_path="/private/project/path",
            languages=["python"],
            target_platforms=["linux", "browser"],
        )
        profile = HostProfile(
            os_id="ubuntu",
            os_id_like=("debian",),
            pretty_name="Ubuntu 24.04 LTS",
            version_id="24.04",
            architecture="x86_64",
            package_provider="ubuntu",
            executables=(ExecutableFact("apt-get", True, "2.7"),),
            rootless_podman=RootlessPodmanStatus(
                executable_available=True,
                rootless_usable=True,
                checks=(PrerequisiteCheck("subuid", PrerequisiteStatus.SATISFIED, "Configured."),),
            ),
        )
        snapshot = build_advisor_host_snapshot(config, profile=profile)
        rendered = render_advisor_host_snapshot(snapshot)
        prompt = build_advisor_prompt(config, host_snapshot=snapshot)
        self.assertIn(rendered, prompt)
        self.assertEqual(snapshot["selected_languages"], ["python"])
        self.assertEqual(snapshot["selected_targets"], ["linux", "browser"])
        self.assertEqual(snapshot["executables"], [{"name": "apt-get", "available": True, "version": "2.7"}])
        self.assertNotIn(config.project_path, rendered)

        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return {str(key).lower() for key in value} | set().union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value), set())
            return set()

        snapshot_keys = keys(snapshot)
        for forbidden in (
            "username", "hostname", "home_path", "ip_address", "environment", "history",
            "token", "cookie", "browser_state", "ssh_configuration", "unrelated_packages",
        ):
            self.assertNotIn(forbidden, snapshot_keys)

    def test_wizard_discloses_exact_snapshot_before_advisor_call(self) -> None:
        profile = HostProfile(
            os_id="debian",
            os_id_like=(),
            pretty_name="Debian GNU/Linux 12",
            version_id="12",
            architecture="x86_64",
            package_provider="debian",
            executables=(ExecutableFact("apt-get", True),),
        )
        output: list[str] = []
        adapter = mock.Mock()
        adapter.display_name = "Test Codex"
        adapter.account_description = "Official test account boundary"
        adapter.exists.return_value = True
        adapter.version.return_value = "codex test"
        adapter.auth_status.return_value = True

        def advise(config: ProjectConfig, prompt: str) -> AdvisorRecommendation:
            snapshot = build_advisor_host_snapshot(config, profile=profile)
            rendered = render_advisor_host_snapshot(snapshot)
            self.assertIn(rendered, output)
            self.assertIn(rendered, prompt)
            self.assertLess(output.index(rendered), len(output))
            return AdvisorRecommendation(
                summary="Test recommendation",
                languages=["python"],
                database="sqlite",
                architecture="Small package",
                recommended_capabilities=[AdvisorCapability(
                    "optional.shellcheck", "Check generated shell helpers.", "optional",
                    "The workspace contains shell helpers.", "medium",
                )],
                source="test",
                raw_output='{"untrusted":"advisor payload"}',
            )

        adapter.advise.side_effect = advise
        answers = [
            "new", "Advisor Disclosure", "", "", "Build a CLI.", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "",
        ]
        cache = mock.Mock()
        cache.load.return_value = None
        with mock.patch("agent_starter.wizard.get_adapter", return_value=adapter), mock.patch(
            "agent_starter.wizard.detect_host", return_value=SimpleNamespace(profile=profile)
        ), mock.patch("agent_starter.wizard.provider_for_detection", return_value=None), mock.patch(
            "agent_starter.wizard.get_recommendation_cache", return_value=cache
        ):
            result = run_wizard(
                initial_path="./advisor-disclosure-test",
                input_fn=self.wizard_input(answers),
                output_fn=output.append,
                skip_agent_setup=True,
            )
        self.assertEqual(result.config.advisor.source, "test")
        self.assertEqual(
            result.config.advisor.toolchain_capabilities,
            [
                "base.tooling", "language.python", "database.sqlite",
                "sandbox.rootless-podman", "optional.shellcheck",
            ],
        )
        self.assertEqual(result.config.advisor.raw_output, "")
        self.assertEqual(len(result.config.capability_decisions), 5)
        self.assertTrue(all(
            item.decision is CapabilityDecisionState.ACCEPTED
            for item in result.config.capability_decisions
        ))
        self.assertTrue(any("No package or command was executed" in line for line in output))
        self.assertNotIn("host_profile", result.config.to_dict())
        self.assertNotIn("host_snapshot", result.config.to_dict())
        adapter.advise.assert_called_once()
        cache.store.assert_called_once()
        disclosure_index = output.index("The advisor will receive this exact redacted host snapshot:")
        request_index = output.index("Requesting a structured recommendation in a temporary, read-only advisory workspace...")
        self.assertLess(disclosure_index, request_index)

    def test_current_cache_hit_offers_visible_refresh_and_skips_advisor(self) -> None:
        profile = HostProfile(
            os_id="debian",
            os_id_like=(),
            pretty_name="Debian GNU/Linux 12",
            version_id="12",
            architecture="x86_64",
            package_provider="debian",
            executables=(ExecutableFact("apt-get", True),),
        )
        adapter = mock.Mock()
        adapter.display_name = "Test Codex"
        adapter.account_description = "Official account boundary"
        adapter.exists.return_value = True
        adapter.version.return_value = "codex test"
        adapter.auth_status.return_value = True
        cached = AdvisorRecommendation(
            summary="Cached recommendation",
            languages=["python"],
            database="sqlite",
            recommended_capabilities=[AdvisorCapability(
                "language.python", "Run Python.", "required", "Matches the CLI.", "high"
            )],
            architecture_notes=["Small package."],
            source="codex-cache",
        )
        cache = mock.Mock()
        cache.load.return_value = CachedRecommendation("a" * 64, "2026-07-14T00:00:00+00:00", cached)
        output: list[str] = []
        answers = [
            "new", "Cached Advisor", "", "", "Build a CLI.", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "",
        ]
        with mock.patch("agent_starter.wizard.get_adapter", return_value=adapter), mock.patch(
            "agent_starter.wizard.detect_host", return_value=SimpleNamespace(profile=profile)
        ), mock.patch("agent_starter.wizard.provider_for_detection", return_value=None), mock.patch(
            "agent_starter.wizard.get_recommendation_cache", return_value=cache
        ):
            result = run_wizard(
                initial_path="./cached-advisor-test",
                input_fn=self.wizard_input(answers),
                output_fn=output.append,
                skip_agent_setup=True,
            )
        self.assertEqual(result.config.advisor.source, "codex-cache")
        self.assertTrue(any("cached structured recommendation" in line.lower() for line in output))
        self.assertTrue(any("Refresh this cached recommendation" in line for line in output))
        self.assertFalse(any("advisor will receive" in line.lower() for line in output))
        adapter.advise.assert_not_called()
        cache.store.assert_not_called()

    def test_offline_default_completes_review_generation_and_validation_without_codex(self) -> None:
        profile = HostProfile(
            os_id="fedora",
            os_id_like=(),
            pretty_name="Unsupported offline test host",
            version_id="42",
            architecture="x86_64",
            package_provider=None,
        )
        adapter = mock.Mock()
        adapter.display_name = "Unavailable Codex"
        adapter.account_description = "Official Codex account boundary"
        adapter.install_command = "official-installer-placeholder"
        adapter.exists.return_value = False
        output: list[str] = []
        answers = [
            "new", "Offline Complete", "", "", "Build a CLI offline.", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "",
        ]
        with tempfile.TemporaryDirectory() as temp, mock.patch(
            "agent_starter.wizard.get_adapter", return_value=adapter
        ), mock.patch(
            "agent_starter.wizard.detect_host", return_value=SimpleNamespace(profile=profile)
        ), mock.patch("agent_starter.wizard.provider_for_detection", return_value=None):
            root = Path(temp) / "offline-project"
            result = run_wizard(
                initial_path=str(root),
                input_fn=self.wizard_input(answers),
                output_fn=output.append,
                skip_agent_setup=True,
            )
            report = generate_project(result.config)
            self.assertTrue(report.ok, report.validation_errors)
            self.assertTrue(validate_project(root).ok)
            generated = (root / "docs/AI-STACK-RECOMMENDATION.md").read_text(encoding="utf-8")

        self.assertEqual(result.config.advisor.source, "local-fallback")
        self.assertTrue(result.config.languages)
        self.assertTrue(result.config.capability_decisions)
        self.assertEqual(result.config.advisor.raw_output, "")
        self.assertTrue(any("Local deterministic default — not AI-reviewed" in line for line in output))
        self.assertIn("Local deterministic default — not AI-reviewed", generated)
        adapter.advise.assert_not_called()
        adapter.install.assert_not_called()


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
        self.assertEqual(result.config.sandbox.image_profile, "arch-toolchain")
        self.assertFalse(result.config.sandbox.codex_inside_container)
        self.assertFalse(result.config.sandbox.first_run_autonomous_prompt)

    def test_sandbox_image_profile_is_an_explicit_host_independent_choice(self) -> None:
        answers = [
            "new", "Debian Image Wizard", "", "", "Build a small CLI program.", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "", "", "manual", "python", "none",
            "", "", "", "", "", "", "", "", "", "",
        ]
        answers[19] = "2"
        output: list[str] = []
        result = run_wizard(
            initial_path="./debian-image-wizard-test",
            input_fn=self.wizard_input(answers),
            output_fn=output.append,
            skip_agent_setup=True,
        )
        self.assertEqual(result.config.sandbox.image_profile, "debian-toolchain")
        self.assertTrue(any("does not have to match the host distribution" in line for line in output))

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
