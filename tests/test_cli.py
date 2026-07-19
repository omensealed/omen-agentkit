from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter import __version__
from agent_starter.cli import (
    AI_LOCAL_IGNORE_PATTERNS,
    ContinuationDelta,
    GitReadiness,
    OllamaModelAssessment,
    PROMPT_TEMPLATES,
    SANDBOX_FINGERPRINT_INPUTS,
    _codex_status_summary,
    _git_readiness,
    _git_status_summary,
    _github_workflow_summary,
    _report_generation,
    _validate_noninteractive_config,
    _ignored_ai_artifacts_summary,
    _looks_like_remote_rsync_target,
    _best_ollama_assessment,
    _coding_score,
    _ensure_agent_authorized,
    _find_context_length,
    _parse_ollama_list,
    _podman_image_id,
    _podman_rootless_summary,
    _prompt_interactive_choice,
    _prompt_interactive_value,
    _prompt_template_section,
    _rsync_command,
    _run_local_check,
    _sandbox_status_lines,
    _sha256_file,
    _show_ollama_model,
    _validate_rsync_target,
    _write_sandbox_preflight_stamp,
    _xdg_runtime_summary,
    build_parser,
    build_continuation_delta,
    command_audit_context,
    command_example,
    command_audit_structure,
    command_auth,
    command_codex_install_skill,
    command_codex_skill_status,
    command_codex_uninstall_skill,
    command_codex_update_skill,
    command_github_ready,
    command_launch,
    command_generate,
    command_new,
    command_ollama_check,
    command_prompt,
    command_rsync_plan,
    command_sandbox_clean,
    command_sandbox_doctor,
    command_sandbox_preflight,
    command_status,
    command_doctor,
    command_toolchains,
    command_validate,
    collect_interactive_prompt_request,
    collect_interactive_task_packet,
    load_answers,
    launch_agent,
    main,
    assess_ollama_model,
    render_continuation_prompt,
    render_local_model_handoff_prompt,
    sandbox_fingerprint,
    sandbox_preflight,
    sandbox_preflight_state,
)
from agent_starter.cli_app import information_commands
from agent_starter.cli_app import inspection_commands
from agent_starter.cli_app import skill_commands
from agent_starter.cli_app import sandbox_commands
from agent_starter.cli_app import sandbox_orchestration
from agent_starter.cli_app import readiness_commands
from agent_starter.cli_app import prompt_commands
from agent_starter.cli_app import local_model_commands
from agent_starter.cli_app import agent_commands
from agent_starter.cli_app import generation_commands
from agent_starter.codex_skill import SKILL_MD
from agent_starter.generator import generate_project
from agent_starter.models import ProjectConfig


class CliTests(unittest.TestCase):
    def test_generation_command_family_preserves_exports_and_dispatch(self) -> None:
        exports = (
            (load_answers, generation_commands.load_answers),
            (_validate_noninteractive_config, generation_commands._validate_noninteractive_config),
            (_report_generation, generation_commands._report_generation),
            (command_new, generation_commands.command_new),
            (command_generate, generation_commands.command_generate),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

        parser = build_parser()
        self.assertIs(parser.parse_args(["new", "--answers", "answers.json"]).func, generation_commands.command_new)
        self.assertIs(parser.parse_args(["init", "--answers", "answers.json"]).func, generation_commands.command_new)
        self.assertIs(parser.parse_args(["generate", "--answers", "answers.json"]).func, generation_commands.command_generate)

    def test_agent_command_family_preserves_exports_dispatch_and_auth_safety(self) -> None:
        self.assertIs(_ensure_agent_authorized, agent_commands._ensure_agent_authorized)
        self.assertIs(launch_agent, agent_commands.launch_agent)
        self.assertIs(command_auth, agent_commands.command_auth)
        self.assertIs(command_launch, agent_commands.command_launch)
        parser = build_parser()
        self.assertIs(parser.parse_args(["auth", "--status"]).func, agent_commands.command_auth)
        self.assertIs(parser.parse_args(["launch"]).func, agent_commands.command_launch)

        adapter = mock.Mock()
        adapter.exists.return_value = True
        adapter.version.return_value = "codex test"
        adapter.auth_status.return_value = True
        output = io.StringIO()
        with (
            mock.patch("agent_starter.cli_app.agent_commands.get_adapter", return_value=adapter),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["auth", "--status"]), 0)
        self.assertEqual(output.getvalue(), "Detected: codex test\nauthorized\n")
        adapter.install.assert_not_called()
        adapter.login.assert_not_called()

        missing = mock.Mock()
        missing.display_name = "OpenAI Codex CLI"
        missing.install_command = "reviewed installer"
        missing.exists.return_value = False
        output = io.StringIO()
        with (
            mock.patch("agent_starter.cli_app.agent_commands.get_adapter", return_value=missing),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["auth"]), 2)
        self.assertIn("Re-run with --install only after reviewing", output.getvalue())
        missing.install.assert_not_called()
        missing.login.assert_not_called()

    def test_local_model_command_family_preserves_exports_dispatch_and_bytes(self) -> None:
        exports = (
            (OllamaModelAssessment, local_model_commands.OllamaModelAssessment),
            (_parse_ollama_list, local_model_commands._parse_ollama_list),
            (_find_context_length, local_model_commands._find_context_length),
            (_coding_score, local_model_commands._coding_score),
            (_show_ollama_model, local_model_commands._show_ollama_model),
            (assess_ollama_model, local_model_commands.assess_ollama_model),
            (_best_ollama_assessment, local_model_commands._best_ollama_assessment),
            (render_local_model_handoff_prompt, local_model_commands.render_local_model_handoff_prompt),
            (command_ollama_check, local_model_commands.command_ollama_check),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)
        self.assertIs(build_parser().parse_args(["ollama-check"]).func, local_model_commands.command_ollama_check)

        config = ProjectConfig(
            project_name="Local Hash",
            project_mode="existing",
            project_stage="maintenance",
            project_type="cli",
            languages=["python"],
            database="sqlite",
            target_platforms=["linux"],
            tests=["unit"],
        )
        assessment = OllamaModelAssessment(
            "qwen2.5-coder:32b",
            131_072,
            4,
            "suitable",
            ["Confirmed context.", "Coding model."],
        )
        prompt = render_local_model_handoff_prompt(
            config,
            request="Review the import path",
            assessment=assessment,
            override=False,
        )
        self.assertEqual(
            hashlib.sha256(prompt.encode()).hexdigest(),
            "aa927f83d0c315c1deeacbe2d20e53a26b31641d4519d166f29379f893bb53ef",
        )

    def test_prompt_command_family_preserves_exports_dispatch_and_bytes(self) -> None:
        exports = (
            (ContinuationDelta, prompt_commands.ContinuationDelta),
            (PROMPT_TEMPLATES, prompt_commands.PROMPT_TEMPLATES),
            (_prompt_template_section, prompt_commands._prompt_template_section),
            (render_continuation_prompt, prompt_commands.render_continuation_prompt),
            (_prompt_interactive_value, prompt_commands._prompt_interactive_value),
            (_prompt_interactive_choice, prompt_commands._prompt_interactive_choice),
            (collect_interactive_task_packet, prompt_commands.collect_interactive_task_packet),
            (build_continuation_delta, prompt_commands.build_continuation_delta),
            (collect_interactive_prompt_request, prompt_commands.collect_interactive_prompt_request),
            (command_prompt, prompt_commands.command_prompt),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)
        self.assertIs(build_parser().parse_args(["prompt"]).func, prompt_commands.command_prompt)

        config = ProjectConfig(
            project_name="Hash Prompt",
            project_mode="existing",
            project_stage="maintenance",
            project_type="cli",
            languages=["python", "javascript"],
            database="sqlite",
            target_platforms=["linux", "web"],
            tests=["unit", "integration"],
        )
        prompt = render_continuation_prompt(
            config,
            request="Preserve the import contract",
            phase="compatibility review",
            template="bug",
        )
        self.assertEqual(
            hashlib.sha256(prompt.encode()).hexdigest(),
            "511919a06035661e670081927f40fe47f12589121b1a03cfa6726ad56f555d9c",
        )
        self.assertLessEqual(len(prompt.split()), 500)

    def test_continuation_delta_is_complete_bounded_and_secret_safe(self) -> None:
        config = ProjectConfig(project_name="Delta", open_questions=["Keep the legacy alias?"])
        delta = build_continuation_delta(
            config,
            request="Finish the parser migration.",
            changes="Parser ownership moved.",
            failures="Malformed rows still fail.",
            relevant_references=("agent_starter/parser.py", "tests/test_parser.py"),
            acceptance_checks="Focused and full checks pass.",
        )
        self.assertEqual(delta.current_objective, "Finish the parser migration.")
        self.assertEqual(delta.unresolved_decisions, ("Keep the legacy alias?",))
        self.assertEqual(delta.relevant_references[-2:], ("agent_starter/parser.py", "tests/test_parser.py"))
        with self.assertRaisesRegex(ValueError, "project-relative"):
            build_continuation_delta(config, request="Continue", relevant_references=("../outside",))
        with self.assertRaisesRegex(ValueError, "credential"):
            build_continuation_delta(config, request="Continue", failures="password=do-not-store")

    def test_readiness_command_family_preserves_direct_cli_exports_and_dispatch(self) -> None:
        exports = (
            (AI_LOCAL_IGNORE_PATTERNS, readiness_commands.AI_LOCAL_IGNORE_PATTERNS),
            (GitReadiness, readiness_commands.GitReadiness),
            (_git_status_summary, readiness_commands._git_status_summary),
            (_git_readiness, readiness_commands._git_readiness),
            (_ignored_ai_artifacts_summary, readiness_commands._ignored_ai_artifacts_summary),
            (_codex_status_summary, readiness_commands._codex_status_summary),
            (_podman_rootless_summary, readiness_commands._podman_rootless_summary),
            (_xdg_runtime_summary, readiness_commands._xdg_runtime_summary),
            (_sandbox_status_lines, readiness_commands._sandbox_status_lines),
            (_github_workflow_summary, readiness_commands._github_workflow_summary),
            (_run_local_check, readiness_commands._run_local_check),
            (_looks_like_remote_rsync_target, readiness_commands._looks_like_remote_rsync_target),
            (_validate_rsync_target, readiness_commands._validate_rsync_target),
            (_rsync_command, readiness_commands._rsync_command),
            (command_status, readiness_commands.command_status),
            (command_github_ready, readiness_commands.command_github_ready),
            (command_rsync_plan, readiness_commands.command_rsync_plan),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)
        parser = build_parser()
        self.assertIs(parser.parse_args(["status"]).func, readiness_commands.command_status)
        self.assertIs(parser.parse_args(["github-ready"]).func, readiness_commands.command_github_ready)
        self.assertIs(
            parser.parse_args(["rsync-plan", ".", "../mirror"]).func,
            readiness_commands.command_rsync_plan,
        )

    def test_sandbox_orchestration_preserves_direct_cli_exports(self) -> None:
        exports = (
            (SANDBOX_FINGERPRINT_INPUTS, sandbox_orchestration.SANDBOX_FINGERPRINT_INPUTS),
            (_sha256_file, sandbox_orchestration._sha256_file),
            (sandbox_fingerprint, sandbox_orchestration.sandbox_fingerprint),
            (_podman_image_id, sandbox_orchestration._podman_image_id),
            (_write_sandbox_preflight_stamp, sandbox_orchestration._write_sandbox_preflight_stamp),
            (sandbox_preflight_state, sandbox_orchestration.sandbox_preflight_state),
            (sandbox_preflight, sandbox_orchestration.sandbox_preflight),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

    def test_sandbox_command_family_preserves_direct_dispatch(self) -> None:
        commands = {
            "doctor": (command_sandbox_doctor, sandbox_commands.command_sandbox_doctor),
            "preflight": (command_sandbox_preflight, sandbox_commands.command_sandbox_preflight),
            "clean": (command_sandbox_clean, sandbox_commands.command_sandbox_clean),
        }
        parser = build_parser()
        for command, (legacy, moved) in commands.items():
            self.assertIs(legacy, moved)
            self.assertIs(parser.parse_args(["sandbox", command]).func, moved)

    def test_skill_command_family_preserves_dispatch_confirmation_and_safety(self) -> None:
        commands = {
            "skill-status": (command_codex_skill_status, skill_commands.command_codex_skill_status),
            "install-agentkit-skill": (command_codex_install_skill, skill_commands.command_codex_install_skill),
            "update-agentkit-skill": (command_codex_update_skill, skill_commands.command_codex_update_skill),
            "uninstall-agentkit-skill": (command_codex_uninstall_skill, skill_commands.command_codex_uninstall_skill),
        }
        parser = build_parser()
        for command, (legacy, moved) in commands.items():
            self.assertIs(legacy, moved)
            self.assertIs(parser.parse_args(["codex", command]).func, moved)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["codex", "skill-status", str(root)]), 0)
            self.assertIn("Installed: no", stdout.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["codex", "install-agentkit-skill", str(root), "--yes"]), 0)
            skill_path = root / SKILL_MD
            before = skill_path.read_bytes()
            stdout = io.StringIO()
            with mock.patch("builtins.input", return_value="n"), contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["codex", "update-agentkit-skill", str(root)]), 2)
            self.assertIn("No changes made.", stdout.getvalue())
            self.assertEqual(skill_path.read_bytes(), before)

            custom = Path(temp) / "custom"
            custom_skill = custom / SKILL_MD
            custom_skill.parent.mkdir(parents=True)
            custom_skill.write_text("custom\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["codex", "uninstall-agentkit-skill", str(custom)]), 2)
            self.assertIn("refusing to delete user-owned content", stdout.getvalue())
            self.assertEqual(custom_skill.read_text(encoding="utf-8"), "custom\n")

    def test_inspection_command_family_preserves_direct_dispatch_and_invalid_exit(self) -> None:
        expected = {
            "validate": (command_validate, inspection_commands.command_validate),
            "audit-structure": (command_audit_structure, inspection_commands.command_audit_structure),
            "audit-context": (command_audit_context, inspection_commands.command_audit_context),
            "doctor": (command_doctor, inspection_commands.command_doctor),
        }
        parser = build_parser()
        for command, (legacy, moved) in expected.items():
            self.assertIs(legacy, moved)
            self.assertIs(parser.parse_args([command]).func, moved)
        with tempfile.TemporaryDirectory() as temp:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["validate", temp])
            self.assertEqual(code, 2)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("[error] Missing required file: .agent-starter/project.json", stdout.getvalue())

    def test_information_command_family_preserves_dispatch_exit_and_streams(self) -> None:
        self.assertIs(command_example, information_commands.command_example)
        self.assertIs(command_toolchains, information_commands.command_toolchains)
        parser = build_parser()
        self.assertIs(parser.parse_args(["example-answers"]).func, information_commands.command_example)
        self.assertIs(parser.parse_args(["toolchains"]).func, information_commands.command_toolchains)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["toolchains"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            hashlib.sha256(stdout.getvalue().encode()).hexdigest(),
            "d3f85b3d200cd868157add3a1ffe91f41d8c5bb1b82a1bdf15b10d12a9e37c3d",
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["example-answers"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        example = json.loads(stdout.getvalue())
        self.assertEqual(example["schema_version"], 2)
        self.assertEqual(example["primary_agent"], "codex")
        self.assertEqual(example["model_policy"]["model_id"], "gpt-5.6-sol")

        with tempfile.TemporaryDirectory() as temp:
            existing = Path(temp) / "answers.json"
            existing.write_text("preserve me\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["example-answers", "--output", str(existing)])
            self.assertEqual(code, 2)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(stdout.getvalue(), f"Refusing to replace {existing}; add --force.\n")
            self.assertEqual(existing.read_text(encoding="utf-8"), "preserve me\n")

    def test_version_and_toolchains(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(__version__, output.getvalue())

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
            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["model_policy"]["model_id"], "gpt-5.6-sol")

    def test_new_command_exposes_guided_and_advanced_modes_without_changing_answers_flow(self) -> None:
        guided = build_parser().parse_args(["new", "--mode", "guided"])
        advanced = build_parser().parse_args(["init", "--mode", "advanced"])
        answers = build_parser().parse_args(["new", "--answers", "answers.json"])
        self.assertEqual(guided.entry_mode, "guided")
        self.assertEqual(advanced.entry_mode, "advanced")
        self.assertEqual(answers.entry_mode, "advanced")
        with mock.patch(
            "agent_starter.cli_app.generation_commands.run_wizard",
            side_effect=RuntimeError("stop after wiring"),
        ) as wizard:
            with self.assertRaisesRegex(RuntimeError, "stop after wiring"):
                main(["new", "--mode", "guided", "--skip-agent-setup"])
        wizard.assert_called_once_with(
            initial_path=None,
            skip_agent_setup=True,
            entry_mode="guided",
        )

    def test_doctor_accepts_only_reviewed_platform_provider_overrides(self) -> None:
        args = build_parser().parse_args(["doctor", "--platform-provider", "ubuntu"])
        self.assertEqual(args.platform_provider, "ubuntu")
        self.assertFalse(args.json)
        json_args = build_parser().parse_args(["doctor", "--json"])
        self.assertTrue(json_args.json)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            build_parser().parse_args(["doctor", "--platform-provider", "fedora"])
        self.assertEqual(raised.exception.code, 2)

    def test_doctor_json_is_redacted_and_provider_appropriate(self) -> None:
        from agent_starter.platforms import CommandResult, DebianFamilyProvider, detect_platform

        available = {"apt-get", "bash", "git", "curl"}
        lookup = lambda name: f"/synthetic/{name}" if name in available else None
        detection = detect_platform(
            'ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu"\n',
            architecture="x86_64",
            executable_lookup=lookup,
        )
        provider = DebianFamilyProvider(
            "ubuntu", runner=lambda argv: CommandResult(0, "install ok installed")
        )
        adapter = mock.Mock()
        adapter.exists.return_value = True
        adapter.version.return_value = "codex test"
        adapter.auth_status.return_value = True
        output = io.StringIO()
        with (
            mock.patch("agent_starter.cli_app.inspection_commands.detect_host", return_value=detection),
            mock.patch("agent_starter.cli_app.inspection_commands.provider_for_detection", return_value=provider),
            mock.patch("agent_starter.cli_app.inspection_commands.get_adapter", return_value=adapter),
            mock.patch("agent_starter.cli_app.inspection_commands.shutil.which", side_effect=lookup),
            contextlib.redirect_stdout(output),
        ):
            code = main(["doctor", "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["provider"]["id"], "ubuntu")
        encoded = json.dumps(payload)
        self.assertIn("apt-get", encoded)
        self.assertNotIn("pacman", encoded)
        self.assertNotIn("/synthetic", encoded)

    def test_public_entry_point_and_config_command_remain_importable(self) -> None:
        from agent_starter.cli_app.config_command import command_config_migrate

        self.assertTrue(callable(main))
        self.assertTrue(callable(build_parser))
        self.assertTrue(callable(command_config_migrate))
        args = build_parser().parse_args(["config", "migrate", "--input", "answers.json"])
        self.assertIs(args.func, command_config_migrate)

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
            self.assertTrue((root / "START_HERE.md").is_file())
            self.assertTrue((root / "NEXT_STEPS.md").is_file())
            self.assertIn("START_HERE.md", output.getvalue())

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

    def test_answers_file_accepts_sandbox_config_and_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "answers.json"
            data = {
                "project_name": "Sandbox Answers",
                "project_path": str(Path(temp) / "project"),
                "project_mode": "new",
                "description": "test",
                "primary_agent": "codex",
                "database": "none",
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            old_loaded = load_answers(path, path_override=None, allow_custom_commands=False)
            self.assertFalse(old_loaded.sandbox.enabled)
            self.assertEqual(old_loaded.sandbox.mode, "none")

            data["sandbox"] = {
                "enabled": True,
                "engine": "podman",
                "mode": "codex",
                "codex_inside_container": True,
                "rootless_required": True,
                "install_agentkit_skill": True,
                "first_run_autonomous_prompt": True,
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_answers(path, path_override=None, allow_custom_commands=False)
            self.assertTrue(loaded.sandbox.enabled)
            self.assertEqual(loaded.sandbox.mode, "codex")
            self.assertTrue(loaded.sandbox.codex_inside_container)

    def test_sandbox_doctor_cli_reports_missing_podman(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Sandbox CLI",
                project_path=str(root),
                git_enabled=False,
            )
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)
            output = io.StringIO()
            with mock.patch("agent_starter.sandbox.shutil.which", return_value=None), contextlib.redirect_stdout(output):
                code = main(["sandbox", "doctor", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("[missing] podman", output.getvalue())
            self.assertIn("Review on CachyOS", output.getvalue())

    def test_sandbox_preflight_runs_generated_scripts_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="Sandbox Preflight",
                project_path=str(root),
                git_enabled=False,
            )
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)

            calls: list[str] = []

            def fake_run(root_arg: Path, command: list[Path], **kwargs: object) -> int:
                self.assertEqual(root_arg, root.resolve())
                calls.append(command[0].name)
                self.assertIn("label", kwargs)
                self.assertIn("log_path", kwargs)
                return 0

            output = io.StringIO()
            with (
                mock.patch("agent_starter.cli_app.sandbox_orchestration._run_project_command_logged", side_effect=fake_run),
                mock.patch("agent_starter.cli_app.sandbox_orchestration._podman_image_id", return_value="sha256:test"),
                contextlib.redirect_stdout(output),
            ):
                code = main(["sandbox", "preflight", str(root)])
            self.assertEqual(code, 0)
            self.assertEqual(calls, ["doctor", "build", "check"])
            self.assertIn("Sandbox preflight passed", output.getvalue())
            stamp = json.loads((root / ".agent-starter/sandbox/preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(stamp["status"], "passed")
            self.assertEqual(stamp["mode"], "toolchain")
            self.assertEqual(stamp["image_id"], "sha256:test")
            self.assertIn("sandbox_fingerprint", stamp)
            self.assertIn("inputs", stamp)
            self.assertIn("scripts/sandbox/preflight", stamp["inputs"])
            self.assertEqual(stamp["steps"], ["sandbox doctor", "sandbox build", "sandbox check"])
            self.assertIn("contains no credentials", stamp["note"])

    def test_sandbox_preflight_state_detects_missing_valid_stale_and_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="State Check", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)

            state, reason, _ = sandbox_preflight_state(root)
            self.assertEqual(state, "missing")
            self.assertIn("missing", reason)

            with mock.patch("agent_starter.cli_app.sandbox_orchestration._podman_image_id", return_value="sha256:test"):
                _write_sandbox_preflight_stamp(
                    root,
                    config,
                    status="passed",
                    run_check=True,
                    steps=["sandbox doctor", "sandbox build", "sandbox check"],
                )
            state, reason, _ = sandbox_preflight_state(root)
            self.assertEqual(state, "valid")
            self.assertIn("current", reason)

            check = root / "scripts/sandbox/check"
            check.write_text(check.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
            state, reason, _ = sandbox_preflight_state(root)
            self.assertEqual(state, "stale")
            self.assertIn("scripts/sandbox/check", reason)

            _write_sandbox_preflight_stamp(
                root,
                config,
                status="failed",
                run_check=True,
                steps=["sandbox doctor", "sandbox build", "sandbox check"],
                failed_step="sandbox build",
            )
            state, reason, _ = sandbox_preflight_state(root)
            self.assertEqual(state, "failed")
            self.assertIn("sandbox build", reason)

    def test_sandbox_fingerprint_matches_generated_shell_algorithm(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Fingerprint Match", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)
            fingerprint, inputs = sandbox_fingerprint(root)

            import hashlib

            expected = hashlib.sha256()
            for relative in (
                ".agent-starter/project.json",
                ".agent-starter/sandbox/Containerfile",
                ".agent-starter/sandbox/sandbox.json",
                "scripts/sandbox/doctor",
                "scripts/sandbox/preflight",
                "scripts/sandbox/build",
                "scripts/sandbox/check",
            ):
                expected.update(f"{inputs[relative]}  {relative}\n".encode("utf-8"))
            self.assertEqual(fingerprint, expected.hexdigest())

    def test_sandbox_clean_delegates_to_generated_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Sandbox Clean", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)

            calls: list[list[str]] = []

            def fake_run(root_arg: Path, command: list[object], **kwargs: object) -> int:
                self.assertEqual(root_arg, root.resolve())
                calls.append([str(item) for item in command])
                self.assertEqual(kwargs.get("label"), "sandbox clean")
                return 0

            with mock.patch("agent_starter.cli._run_project_command", side_effect=fake_run):
                code = main(["sandbox", "clean", str(root), "--all", "--yes"])
            self.assertEqual(code, 0)
            self.assertEqual(calls, [[str(root / "scripts/sandbox/clean"), "--all", "--yes"]])

    def test_launch_runs_sandbox_preflight_before_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Launch Preflight", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)

            output = io.StringIO()
            with (
                mock.patch("agent_starter.cli_app.agent_commands.sandbox_preflight", return_value=2) as preflight,
                mock.patch("agent_starter.cli_app.agent_commands.get_adapter") as get_adapter,
                contextlib.redirect_stdout(output),
            ):
                code = main(["launch", str(root), "--kickoff"])
            self.assertEqual(code, 2)
            preflight.assert_called_once()
            get_adapter.assert_not_called()

    def test_launch_validation_errors_block_preflight_and_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Blocked Launch", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)
            (root / "AGENTS.md").unlink()

            output = io.StringIO()
            with (
                mock.patch("agent_starter.cli_app.agent_commands.sandbox_preflight") as preflight,
                mock.patch("agent_starter.cli_app.agent_commands.get_adapter") as get_adapter,
                contextlib.redirect_stdout(output),
            ):
                code = main(["launch", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("Launch blocked by project validation", output.getvalue())
            self.assertIn("Missing required file: AGENTS.md", output.getvalue())
            preflight.assert_not_called()
            get_adapter.assert_not_called()

    def test_codex_inside_container_kickoff_uses_sandbox_codex_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Container Kickoff", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "codex"
            config.sandbox.codex_inside_container = True
            config.sandbox.first_run_autonomous_prompt = True
            self.assertTrue(generate_project(config).ok)

            calls: list[list[str]] = []

            def fake_run(root_arg: Path, command: list[object], **_: object) -> int:
                self.assertEqual(root_arg, root.resolve())
                calls.append([str(item) for item in command])
                return 0

            adapter = mock.Mock()
            output = io.StringIO()
            with (
                mock.patch("agent_starter.cli_app.agent_commands.sandbox_preflight", return_value=0),
                mock.patch("agent_starter.cli_app.agent_commands.get_adapter", return_value=adapter),
                mock.patch("agent_starter.cli_app.agent_commands._run_project_command", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["launch", str(root), "--kickoff"])
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0][0].endswith("scripts/sandbox/codex-exec"))
            self.assertEqual(calls[0][1], "FIRST_RUN_AUTONOMOUS.md")
            adapter.auth_status.assert_not_called()

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
                code = main([
                    "prompt", str(root),
                    "--request", "Add an import command",
                    "--changes", "CSV parsing was characterized.",
                    "--failures", "Invalid rows still crash.",
                    "--relevant-reference", "agent_starter/imports.py",
                    "--relevant-reference", "tests/test_imports.py",
                    "--acceptance", "The regression and full checks pass.",
                    "--unresolved-decision", "Keep partial imports atomic?",
                ])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("User request", text)
            self.assertIn("Add an import command", text)
            self.assertLess(text.index("docs/AGENT-INDEX.md"), text.index("AGENTS.md"))
            self.assertIn("Read `AGENTS.md` completely", text)
            self.assertIn("only the task-relevant files", text)
            self.assertIn("## Canonical policy references", text)
            self.assertIn("AGENTS.md#canonical-policy-registry", text)
            self.assertNotIn("Do not run `sudo`", text)
            self.assertIn("docs/11-IMPLEMENTATION-NOTES.md", text)
            self.assertIn("## Continuation delta", text)
            self.assertIn("Changes since last handoff: CSV parsing was characterized.", text)
            self.assertIn("Current failures: Invalid rows still crash.", text)
            self.assertIn("`agent_starter/imports.py`", text)
            self.assertIn("Acceptance checks: The regression and full checks pass.", text)
            self.assertIn("Keep partial imports atomic?", text)
            self.assertIn("Do not reread every historical implementation-note entry", text)

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
                    "Import a CSV containing an invalid row",
                    "The import command crashes",
                    "It should report the invalid row and preserve existing files",
                    "ValueError: invalid row",
                    "consistent",
                    "approve",
                ]
            )

            output = io.StringIO()
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)), contextlib.redirect_stdout(output):
                code = main(["prompt", str(root), "--interactive"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Guided Codex continuation prompt", text)
            self.assertIn("Task type: Fix a problem", text)
            self.assertIn("Bug Fix Template", text)
            self.assertIn("The import command crashes", text)
            self.assertIn("preserve existing files", text)
            self.assertIn("What Codex will attempt", text)
            self.assertIn("What it must not change", text)
            self.assertIn("Approve prompt", text)
            self.assertIn("Current phase focus: fix continuation", text)

    def test_cli_and_gui_task_composers_produce_equivalent_packets(self) -> None:
        from agent_starter.gui.bridge import GuiBridge

        answers = {
            "current": "The command replaces the report.",
            "desired": "The command should merge the report.",
            "compatibility": "Existing flags and report files must remain compatible.",
        }
        cli_answers = iter(["3", *answers.values()])
        with mock.patch("builtins.input", side_effect=lambda _prompt: next(cli_answers)), contextlib.redirect_stdout(io.StringIO()):
            cli_packet = collect_interactive_task_packet()
        gui_result = GuiBridge().compose_task({"kind": "change", "answers": answers})
        self.assertTrue(gui_result["ok"], gui_result)
        self.assertEqual(cli_packet.to_dict(), gui_result["packet"])

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
                    "A person imports one sample CSV",
                    "",
                    "A focused import test passes",
                    "approve",
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

    def test_interactive_contract_can_be_edited_before_approval(self) -> None:
        answers = iter([
            "feature",
            "Export every report.",
            "Export all findings.",
            "Preserve existing CLI flags.",
            "The export test passes.",
            "edit",
            "feature",
            "Export a filtered report.",
            "Export unresolved findings only.",
            "Preserve existing CLI flags.",
            "Focused export and trusted checks pass.",
            "approve",
        ])
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)), contextlib.redirect_stdout(output):
            request, phase, template = collect_interactive_prompt_request()
        self.assertIn("Export a filtered report", request)
        self.assertNotIn("Export every report", request)
        self.assertEqual(phase, "feature continuation")
        self.assertEqual(template, "feature")
        self.assertEqual(output.getvalue().count("Task contract — review required"), 2)

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
            with mock.patch("agent_starter.cli_app.readiness_commands.get_adapter", return_value=adapter), contextlib.redirect_stdout(output):
                code = main(["status", str(root)])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Workspace status:", text)
            self.assertIn("[ok] Metadata: Status Project", text)
            self.assertIn("[ok] Generated files:", text)
            self.assertIn("[ok] Codex: codex 1.2.3; authorized account reported", text)
            self.assertIn("AI-local notes, prompts, sessions, skill metadata, and proposals are ignored", text)
            self.assertIn("Next action:", text)

    def test_status_command_reports_sandbox_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(project_name="Sandbox Status", project_path=str(root), git_enabled=False)
            config.sandbox.enabled = True
            config.sandbox.mode = "toolchain"
            self.assertTrue(generate_project(config).ok)

            adapter = mock.Mock()
            adapter.display_name = "OpenAI Codex CLI"
            adapter.exists.return_value = False

            output = io.StringIO()
            with (
                mock.patch("agent_starter.cli_app.readiness_commands.get_adapter", return_value=adapter),
                mock.patch("agent_starter.cli_app.readiness_commands.shutil.which", return_value=None),
                contextlib.redirect_stdout(output),
            ):
                code = main(["status", str(root)])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Sandbox mode: toolchain", text)
            self.assertIn("Sandbox engine: podman", text)
            self.assertIn("Sandbox preflight: missing", text)
            self.assertIn("Sandbox preflight reason: preflight stamp is missing", text)
            self.assertIn("Sandbox image:", text)
            self.assertIn("Rootless Podman: podman missing", text)
            self.assertIn("agent-starter sandbox preflight .", text)

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
                mock.patch("agent_starter.cli_app.readiness_commands.shutil.which", return_value="/usr/bin/rsync"),
                mock.patch("agent_starter.cli_app.readiness_commands.subprocess.run", side_effect=fake_run),
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
                mock.patch("agent_starter.cli_app.local_model_commands.shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("agent_starter.cli_app.local_model_commands.subprocess.run", side_effect=fake_run),
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
                mock.patch("agent_starter.cli_app.local_model_commands.shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("agent_starter.cli_app.local_model_commands.subprocess.run", side_effect=fake_run),
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
                mock.patch("agent_starter.cli_app.local_model_commands.shutil.which", return_value="/usr/bin/ollama"),
                mock.patch("agent_starter.cli_app.local_model_commands.subprocess.run", side_effect=fake_run),
                contextlib.redirect_stdout(output),
            ):
                code = main(["ollama-check", str(root), "--model", "llama3.2:3b", "--override"])
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Manual override accepted", text)
            self.assertIn("## Local Model Handoff Prompt", text)


if __name__ == "__main__":
    unittest.main()
