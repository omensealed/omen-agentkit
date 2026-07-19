from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.gui.bridge import GuiBridge
from agent_starter.ui_schema import GUI_PAGES, config_from_gui_payload
from agent_starter.config_schema import ConfigValidationError
from agent_starter.task_composer import compose_task_packet
from agent_starter.draft_sessions import DraftStore
from agent_starter.diagnostics import DiagnosticLog
from agent_starter.agents import AgentError
from agent_starter.generator import generate_project
from agent_starter.model_policy import CodexModelPolicy


class GuiTests(unittest.TestCase):
    def payload(self, root: Path) -> dict[str, object]:
        return {
            "project_name": "GUI Test",
            "project_path": str(root),
            "project_mode": "new",
            "project_stage": "idea",
            "project_type": "cli",
            "description": "A GUI-generated project.",
            "languages": "python",
            "database": "sqlite",
            "target_platforms": "cachyos-linux",
            "codex_agentkit_skill": True,
            "sandbox_enabled": True,
            "sandbox_mode": "toolchain",
            "sandbox_image_profile": "debian-toolchain",
            "gui_passthrough": False,
            "git_enabled": False,
        }

    def test_gui_pages_cover_expected_flow(self) -> None:
        ids = [str(page["id"]) for page in GUI_PAGES]
        for expected in ("welcome", "project", "codex", "sandbox", "stack", "task", "generate", "result"):
            self.assertIn(expected, ids)

    def test_gui_task_composer_uses_the_same_packet_as_the_cli_domain(self) -> None:
        answers = {
            "current": "CSV import replaces the destination file.",
            "desired": "Merge valid rows and report conflicts.",
            "compatibility": "Keep the CLI flags and existing CSV files compatible.",
        }
        bridge = GuiBridge()
        schema = bridge.task_composer_schema()
        self.assertEqual(schema[0]["label"], "Add a feature")
        result = bridge.compose_task({"kind": "change", "answers": answers})
        expected = compose_task_packet("change", answers).to_dict()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["packet"], expected)
        self.assertEqual(result["template"], "feature")
        self.assertEqual(result["state"], "review-required")
        self.assertNotIn("request", result)
        self.assertIn("What Codex will attempt", result["contract_text"])
        self.assertIn("What it must not change", result["contract_text"])
        self.assertIn("Files/areas likely involved", result["contract_text"])
        self.assertIn("Tests/acceptance checks", result["contract_text"])
        self.assertIn("Risks/approvals", result["contract_text"])
        approved = bridge.approve_task({"kind": "change", "answers": answers})
        self.assertTrue(approved["ok"], approved)
        self.assertEqual(approved["state"], "approved")
        self.assertIn("Task type: Change existing behavior", approved["request"])
        self.assertNotIn("launch", approved)
        invalid = bridge.compose_task({"kind": "change", "answers": {**answers, "extra": "no"}})
        self.assertFalse(invalid["ok"])
        self.assertNotIn("Traceback", invalid["error"])
        self.assertEqual(invalid["diagnostic"]["code"], "task_invalid")
        self.assertFalse(invalid["diagnostic"]["project_changed"])
        self.assertEqual(
            set(invalid["diagnostic"]),
            {
                "code", "severity", "title", "explanation", "project_changed",
                "safe_next_action", "technical_details",
            },
        )

    def test_gui_draft_save_resume_export_and_discard_use_shared_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = DraftStore(root / "drafts")
            payload = {
                "project": {
                    "entry_mode": "guided",
                    "project_name": "Partial GUI Draft",
                    "project_path": str(root / "project"),
                    "sandbox_enabled": True,
                },
                "task": {
                    "kind": "fix",
                    "answers": {"steps": "Open it.", "observed": "Blank page."},
                },
            }
            bridge = GuiBridge()
            with (
                mock.patch("agent_starter.gui.bridge.get_draft_store", return_value=store),
                mock.patch("agent_starter.gui.bridge.generate_project") as generate,
                mock.patch("agent_starter.gui.bridge.approve_task_contract") as approve,
                mock.patch("agent_starter.cli.launch_agent") as launch,
            ):
                saved = bridge.save_draft(payload)
                self.assertTrue(saved["ok"], saved)
                draft_id = saved["draft"]["draft_id"]
                self.assertEqual(saved["draft"]["selected_project"], str(root / "project"))
                self.assertTrue(saved["draft"]["updated_at"])
                listed = bridge.list_drafts()
                self.assertEqual(listed["drafts"][0]["draft_id"], draft_id)
                resumed = bridge.load_draft(draft_id)
                self.assertEqual(resumed["draft"]["project"]["project_name"], "Partial GUI Draft")
                self.assertEqual(resumed["draft"]["task"]["kind"], "fix")
                exported = root / "exported.json"
                self.assertTrue(bridge.export_draft(draft_id, str(exported))["ok"])
                self.assertTrue(exported.is_file())
                self.assertTrue(bridge.discard_draft(draft_id)["ok"])
                self.assertEqual(bridge.list_drafts()["drafts"], [])
                rejected = bridge.save_draft({
                    "project": {**payload["project"], "description": "password=do-not-store"},
                    "task": None,
                })
                self.assertFalse(rejected["ok"])
                self.assertEqual(rejected["diagnostic"]["code"], "draft_invalid")
                self.assertFalse(rejected["diagnostic"]["project_changed"])
                self.assertNotIn("do-not-store", str(rejected))
                generate.assert_not_called()
                approve.assert_not_called()
                launch.assert_not_called()

    def test_config_from_gui_payload_builds_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = config_from_gui_payload(self.payload(root))
            self.assertEqual(config.project_name, "GUI Test")
            self.assertEqual(config.primary_agent, "codex")
            self.assertEqual(config.languages, ["python"])
            self.assertEqual(config.database, "sqlite")
            self.assertEqual(config.license_name, "AGPL-3.0-or-later")
            self.assertTrue(config.codex_agentkit_skill)
            self.assertTrue(config.sandbox.enabled)
            self.assertEqual(config.sandbox.mode, "toolchain")
            self.assertEqual(config.sandbox.image_profile, "debian-toolchain")
            self.assertFalse(config.sandbox.gui_passthrough)

    def test_gui_entry_modes_share_config_validation_and_are_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            guided_payload = self.payload(Path(temp) / "guided")
            guided_payload["entry_mode"] = "guided"
            advanced_payload = self.payload(Path(temp) / "advanced")
            advanced_payload["entry_mode"] = "advanced"
            guided = config_from_gui_payload(guided_payload).to_dict()
            advanced = config_from_gui_payload(advanced_payload).to_dict()
            guided["project_path"] = "normalized"
            advanced["project_path"] = "normalized"
            self.assertEqual(guided, advanced)
            self.assertNotIn("entry_mode", guided)
            guided_payload["entry_mode"] = "unsupported"
            with self.assertRaises(ValueError):
                config_from_gui_payload(guided_payload)

    def test_gui_payload_rejects_secret_like_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = self.payload(Path(temp) / "project")
            payload["description"] = "api_key=sk-secret-value"
            with self.assertRaises(ValueError):
                config_from_gui_payload(payload)

            result = GuiBridge().preview_config(payload)
            self.assertFalse(result["ok"])
            self.assertEqual(result["diagnostic"]["code"], "configuration_invalid")
            self.assertFalse(result["diagnostic"]["project_changed"])
            self.assertNotIn("password=bad", str(result))

    def test_gui_payload_uses_strict_canonical_boolean_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = self.payload(Path(temp) / "project")
            payload["network_access"] = "false"
            with self.assertRaises(ValueError):
                config_from_gui_payload(payload)

    def test_bridge_generates_and_validates_without_display(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()
            result = bridge.generate(self.payload(root))
            self.assertTrue(result["ok"], result)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / ".agents/skills/agentkit/SKILL.md").is_file())
            validation = bridge.validate(str(root))
            self.assertTrue(validation["ok"], validation)

    def test_non_coder_gui_flow_creates_project_and_bug_fix_prompt_without_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "friendly-project"
            bridge = GuiBridge()
            with mock.patch("agent_starter.cli.launch_agent") as launch:
                generated = bridge.generate(self.payload(root))
                composed = bridge.compose_task({
                    "kind": "fix",
                    "answers": {
                        "steps": "Open the generated application and select Import.",
                        "observed": "The import summary stays blank.",
                        "expected": "The summary should show imported and rejected rows.",
                        "error_text": "",
                        "frequency": "consistent",
                    },
                })
                approved = bridge.approve_task({
                    "kind": "fix",
                    "answers": {
                        "steps": "Open the generated application and select Import.",
                        "observed": "The import summary stays blank.",
                        "expected": "The summary should show imported and rejected rows.",
                        "error_text": "",
                        "frequency": "consistent",
                    },
                })

            self.assertTrue(generated["ok"], generated)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue(composed["ok"], composed)
            self.assertEqual(composed["state"], "review-required")
            self.assertNotIn("request", composed)
            self.assertTrue(approved["ok"], approved)
            self.assertEqual(approved["state"], "approved")
            self.assertIn("Task type: Fix a problem", approved["request"])
            launch.assert_not_called()

    def test_bridge_codex_status_does_not_start_login(self) -> None:
        adapter = mock.Mock()
        adapter.exists.return_value = True
        adapter.auth_status.return_value = False
        adapter.version.return_value = "codex test"
        adapter.install_command = "review installer"
        with mock.patch("agent_starter.gui.bridge.get_adapter", return_value=adapter):
            result = GuiBridge().codex_status()
        self.assertFalse(result["ok"])
        self.assertEqual(result["diagnostic"]["code"], "codex_not_authorized")
        self.assertFalse(result["diagnostic"]["project_changed"])
        adapter.login.assert_not_called()

    def test_bridge_launch_codex_closes_window_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()
            self.assertTrue(bridge.generate(self.payload(root))["ok"])
            preview = bridge.launch_preview(str(root))
            self.assertTrue(preview["ok"], preview)
            with (
                mock.patch.object(bridge, "close_window", return_value={"ok": True}) as close_window,
                mock.patch("agent_starter.cli.launch_agent", return_value=0) as launch_agent,
            ):
                result = bridge.launch_codex(str(root), preview["preview_id"])
            self.assertTrue(result["ok"])
            close_window.assert_called_once_with()
            launch_agent.assert_called_once_with(root, kickoff=False)

            close_failure = {
                "ok": False,
                "error": "Window close failed.",
                "diagnostic": {"code": "optional_component_missing", "project_changed": False},
            }
            with (
                mock.patch.object(bridge, "close_window", return_value=close_failure),
                mock.patch("agent_starter.cli.launch_agent") as blocked_launch,
            ):
                preview = bridge.launch_preview(str(root))
                blocked = bridge.launch_codex(str(root), preview["preview_id"])
            self.assertEqual(blocked, close_failure)
            blocked_launch.assert_not_called()

    def test_launch_preview_identifies_exact_policy_sandbox_network_and_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = config_from_gui_payload(self.payload(root))
            generated = generate_project(config)
            self.assertTrue(generated.ok, generated.validation_errors)

            bridge = GuiBridge()
            ready = bridge.launch_preview(str(root))
            self.assertTrue(ready["ok"], ready)
            self.assertTrue(ready["preview_id"])
            preview = ready["preview"]
            self.assertEqual(preview["target_project"], str(root))
            self.assertEqual(preview["model_policy"]["provider"], "openai")
            self.assertEqual(preview["model_policy"]["selection"], "explicit")
            self.assertEqual(preview["model_policy"]["exact_model_id"], "gpt-5.6-sol")
            self.assertEqual(preview["model_policy"]["display_label"], "GPT-5.6-SOL")
            self.assertEqual(preview["model_policy"]["reasoning_effort"], "medium")
            self.assertFalse(preview["model_policy"]["allow_task_routing"])
            self.assertEqual(preview["model_policy"]["fallback_behavior"], "ask")
            self.assertEqual(preview["sandbox"]["project_mode"], "toolchain")
            self.assertEqual(preview["sandbox"]["codex_mode"], "workspace-write")
            self.assertEqual(preview["sandbox"]["agent_policy"], "builtin-safe")
            self.assertEqual(preview["network"]["command_network_access"], "off")
            self.assertEqual(preview["network"]["web_search"], "cached")
            self.assertFalse(preview["network"]["project_requires_network"])

            with (
                mock.patch.object(bridge, "close_window", return_value={"ok": True}) as close_window,
                mock.patch("agent_starter.cli.launch_agent", return_value=0) as launch_agent,
            ):
                launched = bridge.launch_codex(str(root), ready["preview_id"])
            self.assertTrue(launched["ok"], launched)
            self.assertEqual(launched["preview"], preview)
            close_window.assert_called_once_with()
            launch_agent.assert_called_once_with(root, kickoff=False)

    def test_launch_preview_preserves_reviewed_override_and_inherited_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            policies = (
                (
                    CodexModelPolicy(
                        model_id="reviewed-model",
                        display_label="Reviewed Model",
                        reasoning_effort="high",
                    ),
                    "reviewed-model",
                    "high",
                ),
                (CodexModelPolicy(selection="inherit"), None, None),
            )
            for index, (policy, expected_id, expected_effort) in enumerate(policies):
                root = base / f"project-{index}"
                config = config_from_gui_payload(self.payload(root))
                config.model_policy = policy
                self.assertTrue(generate_project(config).ok)
                preview = GuiBridge().launch_preview(str(root))["preview"]["model_policy"]
                self.assertEqual(preview["selection"], policy.selection)
                self.assertEqual(preview["exact_model_id"], expected_id)
                self.assertEqual(preview["reasoning_effort"], expected_effort)

    def test_launch_requires_current_successful_preview_and_revalidation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(GuiBridge().generate(self.payload(root))["ok"])
            bridge = GuiBridge()

            with mock.patch("agent_starter.cli.launch_agent") as launch_agent:
                missing = bridge.launch_codex(str(root), "")
            self.assertEqual(missing["diagnostic"]["code"], "launch_preview_required")
            self.assertFalse(missing["diagnostic"]["project_changed"])
            launch_agent.assert_not_called()

            ready = bridge.launch_preview(str(root))
            failed_validation = mock.Mock(
                ok=False,
                root=root,
                errors=["Missing required file: AGENTS.md"],
                warnings=[],
                checked=[],
            )
            with (
                mock.patch("agent_starter.gui.bridge.validate_project", return_value=failed_validation),
                mock.patch.object(bridge, "close_window") as close_window,
                mock.patch("agent_starter.cli.launch_agent") as launch_agent,
            ):
                blocked = bridge.launch_codex(str(root), ready["preview_id"])
            self.assertEqual(blocked["diagnostic"]["code"], "launch_validation_failed")
            self.assertFalse(blocked["diagnostic"]["project_changed"])
            close_window.assert_not_called()
            launch_agent.assert_not_called()

    def test_launch_preview_blocks_codex_policy_drift_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(GuiBridge().generate(self.payload(root))["ok"])
            codex_config = root / ".codex" / "config.toml"
            original = codex_config.read_text(encoding="utf-8")
            codex_config.write_text(original.replace("network_access = false", "network_access = true"), encoding="utf-8")

            drifted = GuiBridge().launch_preview(str(root))
            self.assertFalse(drifted["ok"])
            self.assertEqual(drifted["diagnostic"]["code"], "launch_policy_invalid")
            self.assertFalse(drifted["diagnostic"]["project_changed"])
            self.assertNotIn("preview_id", drifted)

            target = root / ".codex" / "reviewed-config.toml"
            target.write_text(original, encoding="utf-8")
            codex_config.unlink()
            codex_config.symlink_to(target.name)
            symlinked = GuiBridge().launch_preview(str(root))
            self.assertFalse(symlinked["ok"])
            self.assertEqual(symlinked["diagnostic"]["code"], "launch_policy_invalid")
            self.assertFalse(symlinked["diagnostic"]["project_changed"])

    def test_bridge_maps_backend_failures_logs_safely_and_preserves_path_confinement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            logger = DiagnosticLog(base / "diagnostics")
            bridge = GuiBridge(diagnostic_logger=logger)
            self.assertTrue(bridge.generate(self.payload(root))["ok"])

            adapter = mock.Mock()
            adapter.exists.side_effect = AgentError("api_key=do-not-log")
            with mock.patch("agent_starter.gui.bridge.get_adapter", return_value=adapter):
                status = bridge.codex_status()
            self.assertFalse(status["ok"])
            self.assertEqual(status["diagnostic"]["code"], "codex_operation_failed")
            self.assertFalse(status["diagnostic"]["project_changed"])

            adapter = mock.Mock()
            adapter.exists.return_value = True
            adapter.auth_status.return_value = True
            adapter.version.return_value = "password=do-not-display"
            adapter.install_command = "Authorization: Bearer do-not-display"
            with mock.patch("agent_starter.gui.bridge.get_adapter", return_value=adapter):
                safe_status = bridge.codex_status()
            self.assertNotIn("do-not-display", str(safe_status))

            with mock.patch("agent_starter.gui.bridge.validate_project", side_effect=PermissionError("/private/path")):
                validation = bridge.validate(str(root))
            self.assertEqual(validation["diagnostic"]["code"], "permission_denied")
            self.assertFalse(validation["diagnostic"]["project_changed"])

            traversal = bridge.read_text_file(str(root), "../outside.txt")
            self.assertEqual(traversal["diagnostic"]["code"], "path_outside_project")
            self.assertFalse(traversal["diagnostic"]["project_changed"])

            outside_file = base / "outside.txt"
            outside_file.write_text("outside", encoding="utf-8")
            linked = root / "linked.txt"
            linked.symlink_to(outside_file)
            try:
                linked_result = bridge.read_text_file(str(root), "linked.txt")
                self.assertEqual(linked_result["diagnostic"]["code"], "path_outside_project")
            finally:
                outside_file.unlink(missing_ok=True)

            with mock.patch("agent_starter.gui.bridge.webbrowser.open", side_effect=OSError("token=do-not-log")):
                opened = bridge.open_project_folder(str(root))
            self.assertEqual(opened["diagnostic"]["code"], "system_io_error")

            failing_store = mock.Mock()
            failing_store.list_summaries.side_effect = OSError("password=do-not-log")
            with mock.patch("agent_starter.gui.bridge.get_draft_store", return_value=failing_store):
                drafts = bridge.list_drafts()
            self.assertEqual(drafts["diagnostic"]["code"], "system_io_error")

            with mock.patch.dict(sys.modules, {"webview": None}):
                closed = bridge.close_window()
            self.assertEqual(closed["diagnostic"]["code"], "optional_component_missing")

            preview = bridge.launch_preview(str(root))
            with (
                mock.patch.object(bridge, "close_window", return_value={"ok": True}),
                mock.patch("agent_starter.cli.launch_agent", side_effect=AgentError("token=do-not-log")),
            ):
                launch_failure = bridge.launch_codex(str(root), preview["preview_id"])
            self.assertEqual(launch_failure["diagnostic"]["code"], "codex_operation_failed")

            log_text = (base / "diagnostics" / "gui-diagnostics.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("do-not-log", log_text)
            self.assertNotIn("/private/path", log_text)
            self.assertNotIn("Traceback", log_text)

    def test_generate_failure_reports_observed_project_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()

            def fail_after_write(_config, **kwargs):
                kwargs["_mutation_observer"]()
                raise OSError("write failed")

            with mock.patch("agent_starter.gui.bridge.generate_project", side_effect=fail_after_write):
                failed = bridge.generate(self.payload(root))
            self.assertFalse(failed["ok"])
            self.assertTrue(failed["diagnostic"]["project_changed"])

            invalid = self.payload(root)
            invalid["network_access"] = "false"
            before_write = bridge.generate(invalid)
            self.assertFalse(before_write["diagnostic"]["project_changed"])

    def test_failed_results_and_launch_status_use_stable_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()
            self.assertTrue(bridge.generate(self.payload(root))["ok"])
            validation_report = mock.Mock(
                ok=False,
                root=root,
                errors=["Missing required file: AGENTS.md"],
                warnings=[],
                checked=[],
            )
            with mock.patch("agent_starter.gui.bridge.validate_project", return_value=validation_report):
                validation = bridge.validate(str(root))
            self.assertEqual(validation["diagnostic"]["code"], "project_validation_failed")
            self.assertFalse(validation["diagnostic"]["project_changed"])

            generation_report = mock.Mock(
                ok=False,
                root=root,
                created=["AGENTS.md"],
                unchanged=[],
                overwritten=[],
                conflicts=[],
                proposals=[],
                backups=[],
                warnings=[],
                validation_errors=["Generated validation failed"],
                validation_warnings=[],
            )

            def changed_result(_config, **kwargs):
                kwargs["_mutation_observer"]()
                return generation_report

            with mock.patch("agent_starter.gui.bridge.generate_project", side_effect=changed_result):
                generated = bridge.generate(self.payload(root))
            self.assertEqual(generated["diagnostic"]["code"], "generation_validation_failed")
            self.assertTrue(generated["diagnostic"]["project_changed"])

            preview = bridge.launch_preview(str(root))
            with (
                mock.patch.object(bridge, "close_window", return_value={"ok": True}),
                mock.patch("agent_starter.cli.launch_agent", return_value=7),
            ):
                launched = bridge.launch_codex(str(root), preview["preview_id"])
            self.assertEqual(launched["diagnostic"]["code"], "codex_launch_failed")
            self.assertTrue(launched["diagnostic"]["project_changed"])
            self.assertEqual(launched["code"], 7)

    def test_gui_app_imports_without_pywebview(self) -> None:
        from agent_starter.gui import app

        self.assertEqual(app.static_path().name, "index.html")
        html = app.static_path().read_text(encoding="utf-8")
        script = app.static_path().with_name("app.js").read_text(encoding="utf-8")
        self.assertIn('name="entry_mode"', html)
        self.assertIn('data-advanced-only', html)
        self.assertIn('setEntryMode', script)
        self.assertIn('advanceGuidedDecision', script)
        self.assertIn('Next decision', script)
        self.assertIn('id="task-composer"', html)
        self.assertIn('initializeTaskComposer', script)
        self.assertIn('id="edit-task"', html)
        self.assertIn('id="approve-task"', html)
        self.assertIn('api().approve_task', script)
        self.assertIn('document.createElement("details")', script)
        self.assertIn('diagnostic.technical_details', script)
        self.assertIn('Project files changed:', script)
        for control_id in ("save-draft", "draft-list", "resume-draft", "discard-draft", "export-draft"):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn('id="start-here"', html)
        self.assertIn('read_text_file(lastProjectPath, "START_HERE.md")', script)
        self.assertIn('api().save_draft', script)
        self.assertIn('api().load_draft', script)
        app_source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertIn('GuiBridge(diagnostic_logger=get_diagnostic_log())', app_source)

    def test_gui_console_entry_help_needs_no_display_or_optional_dependency(self) -> None:
        from agent_starter.gui import app

        with mock.patch.object(app, "run_gui") as run_gui, mock.patch("sys.stdout") as stdout:
            self.assertEqual(app.main(["--help"]), 0)
        run_gui.assert_not_called()
        self.assertIn("agent-starter-gui", "".join(call.args[0] for call in stdout.write.call_args_list))

    def test_gui_accessibility_contract_is_keyboard_complete_and_explicit(self) -> None:
        from agent_starter.gui import app

        html = app.static_path().read_text(encoding="utf-8")
        script = app.static_path().with_name("app.js").read_text(encoding="utf-8")
        styles = app.static_path().with_name("app.css").read_text(encoding="utf-8")

        self.assertIn('class="skip-link" href="#wizard-panel"', html)
        self.assertIn('id="wizard-panel"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-label="Generation status"', html)
        self.assertIn('aria-label="Result status"', html)
        self.assertIn('function focusActivePage', script)
        self.assertIn('document.createElement("button")', script)
        self.assertIn('aria-current', script)
        self.assertIn('Current step', script)
        self.assertIn('function renderRemediationCommand', script)
        self.assertIn('Copy remediation command', script)
        self.assertIn('navigator.clipboard.writeText', script)
        self.assertIn('This command is displayed for review only', script)
        self.assertIn('function confirmationText', script)
        self.assertIn('.slice(0, 300)', script)
        self.assertIn('This permanently deletes only the selected local draft file', script)
        self.assertIn('This writes Agent Kit files under', script)
        self.assertIn('This releases prompt text in the GUI only', script)
        self.assertIn(':focus-visible', styles)
        self.assertIn('.step-state', styles)
        self.assertIn('.skip-link:focus', styles)
        self.assertIn('api().launch_preview', script)
        self.assertIn('pendingLaunchPreviewId', script)
        self.assertIn('Exact model ID', script)
        self.assertIn('Confirm and launch Codex', script)

    def test_pywebview_smoke_when_available(self) -> None:
        if importlib.util.find_spec("webview") is None:
            self.skipTest("pywebview is not installed")
        import agent_starter.gui.app as app

        self.assertTrue(app.static_path().is_file())


if __name__ == "__main__":
    unittest.main()
