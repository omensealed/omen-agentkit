from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.cli import _write_sandbox_preflight_stamp
from agent_starter.generator import generate_project
from agent_starter.models import ProjectConfig, SandboxConfig
from agent_starter.sandbox import doctor_lines


HOST_SIDE_MESSAGE = "This is a host-side sandbox command. Exit the container and run it from the project root on the host."


class SandboxGenerationTests(unittest.TestCase):
    def make_config(self, root: Path, **overrides: object) -> ProjectConfig:
        values: dict[str, object] = {
            "project_name": "Sandbox Test",
            "project_slug": "sandbox-test",
            "project_path": str(root),
            "project_mode": "new",
            "project_type": "cli",
            "languages": ["python"],
            "database": "sqlite",
            "git_enabled": False,
            "sandbox": SandboxConfig(enabled=True, mode="toolchain"),
        }
        values.update(overrides)
        return ProjectConfig(**values)

    def test_sandbox_enabled_generates_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            report = generate_project(self.make_config(root))
            self.assertTrue(report.ok, report.validation_errors)
            for relative in (
                ".agent-starter/sandbox/Containerfile",
                ".agent-starter/sandbox/sandbox.json",
                ".agent-starter/sandbox/README.md",
                "docs/agent-prompts/create-container-handoff.md",
                "docs/CACHYOS-PODMAN.md",
                "docs/12-SANDBOX.md",
                "scripts/sandbox/doctor",
                "scripts/sandbox/preflight",
                "scripts/sandbox/status",
                "scripts/sandbox/build",
                "scripts/sandbox/shell",
                "scripts/sandbox/exec",
                "scripts/sandbox/check",
                "scripts/sandbox/logs",
                "scripts/sandbox/clean",
            ):
                self.assertTrue((root / relative).is_file(), relative)

    def test_sandbox_json_and_scripts_are_safe_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            sandbox = json.loads((root / ".agent-starter/sandbox/sandbox.json").read_text(encoding="utf-8"))
            self.assertEqual(sandbox["engine"], "podman")
            self.assertEqual(sandbox["workspace_mount"], "/workspace")
            self.assertEqual(sandbox["mode"], "toolchain")
            self.assertEqual(sandbox["image_profile"], "arch-toolchain")
            self.assertEqual(sandbox["user_namespace"], "keep-id")
            self.assertIn("id -u/id -g", sandbox["runtime_user"])
            self.assertIn("none", sandbox["network_default"])
            self.assertIn(".agent-starter/container-home", sandbox["project_local_paths"]["container_home"])
            self.assertIn(".agent-starter/cache", sandbox["project_local_paths"]["cache"])

            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (root / "scripts/sandbox").iterdir()
                if path.is_file()
            )
            self.assertIn("/workspace", combined)
            self.assertNotIn("~/.codex", combined)
            self.assertNotIn("$HOME/.codex", combined)
            self.assertNotIn("~/.ssh", combined)
            self.assertNotIn("$HOME/.ssh", combined)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", combined)
            self.assertNotIn("-v $HOME", combined)
            self.assertNotIn("--volume $HOME", combined)
            self.assertNotIn("/run/podman/podman.sock", combined)
            self.assertNotIn("--privileged", combined)
            self.assertNotIn("useradd -m -u 1000", (root / ".agent-starter/sandbox/Containerfile").read_text(encoding="utf-8"))
            self.assertNotIn("chmod 0777 /home/codex", (root / ".agent-starter/sandbox/Containerfile").read_text(encoding="utf-8"))
            for relative in ("scripts/sandbox/check", "scripts/sandbox/exec", "scripts/sandbox/shell"):
                text = (root / relative).read_text(encoding="utf-8")
                self.assertIn("HOST_UID=$(id -u)", text, relative)
                self.assertIn("HOST_GID=$(id -g)", text, relative)
                self.assertIn("--userns=keep-id", text, relative)
                self.assertIn('--user "$HOST_UID:$HOST_GID"', text, relative)
                self.assertIn('SANDBOX_NETWORK=${AGENTKIT_SANDBOX_NETWORK:-none}', text, relative)
                self.assertIn('--network "$SANDBOX_NETWORK"', text, relative)
                self.assertIn("--security-opt=no-new-privileges", text, relative)
                self.assertIn("--cap-drop=all", text, relative)
                self.assertIn("--pids-limit", text, relative)
                self.assertIn('--env HOME="$CONTAINER_HOME"', text, relative)
                self.assertIn('XDG_CACHE_HOME="$CONTAINER_CACHE/xdg-cache"', text, relative)
                self.assertIn('NPM_CONFIG_CACHE="$CONTAINER_CACHE/npm"', text, relative)
                self.assertIn('PIP_CACHE_DIR="$CONTAINER_CACHE/pip"', text, relative)
                self.assertIn('CARGO_HOME="$CONTAINER_CACHE/cargo"', text, relative)
                self.assertIn('GOPATH="$CONTAINER_CACHE/go"', text, relative)
                self.assertIn('"$HOST_CONTAINER_HOME:$CONTAINER_HOME:Z"', text, relative)
                self.assertIn('"$HOST_CACHE:$CONTAINER_CACHE:Z"', text, relative)
                self.assertNotIn("$CACHE_VOLUME:$CONTAINER_HOME/.cache:Z,U", text, relative)

            docs = "\n".join(
                (root / relative).read_text(encoding="utf-8")
                for relative in ("README.md", "NEXT_STEPS.md", "FIRST_PROMPT.md", "AGENTS.md", "docs/12-SANDBOX.md", "docs/CACHYOS-PODMAN.md")
            )
            normalized_docs = " ".join(docs.split())
            self.assertIn("rootless Podman sandbox", docs)
            self.assertIn("scripts/sandbox/check", docs)
            self.assertIn("Inside-container project commands", docs)
            self.assertIn("./scripts/check.sh", docs)
            self.assertIn("BLOCKED_ENVIRONMENT", docs)
            self.assertIn("do not ask for codex full permissions", docs.lower())
            self.assertIn("normal host terminal before launching Codex", docs)
            self.assertIn(".agent-starter/sandbox/preflight.json", docs)
            self.assertIn("valid/current", docs)
            self.assertIn("AGENTKIT_SANDBOX_NETWORK=default", docs)
            self.assertIn("../agent-starter", docs)
            self.assertIn("scripts/sandbox/status", docs)
            self.assertIn("CachyOS rootless Podman troubleshooting", docs)
            self.assertIn("should not rerun", docs)
            self.assertIn("do not silently fall back to host build/test commands", normalized_docs.lower())
            self.assertIn("Codex still edits this project directory from the host", docs)
            self.assertIn("Image profile: `arch-toolchain`", docs)
            self.assertIn("independent of the host distribution", docs)
            self.assertIn("Do not mount host secrets", docs)
            self.assertNotIn("codex --sandbox danger-full-access", docs)
            self.assertNotIn("do not let sandbox setup block", docs.lower())

    def test_explicit_sandbox_image_profiles_are_independent_from_host_target(self) -> None:
        cases = (
            ("debian-toolchain", ["cachyos-linux"], "debian:stable-slim", "apt-get install", "python3-venv", "pacman -Syu"),
            ("arch-toolchain", ["linux"], "archlinux:base-devel", "pacman -Syu", "python", "apt-get install"),
        )
        for profile, target_platforms, base_image, installer, package, absent in cases:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "project"
                config = self.make_config(
                    root,
                    target_platforms=target_platforms,
                    sandbox=SandboxConfig(enabled=True, mode="toolchain", image_profile=profile),
                )
                report = generate_project(config)
                self.assertTrue(report.ok, report.validation_errors)
                text = (root / ".agent-starter/sandbox/Containerfile").read_text(encoding="utf-8")
                sandbox = json.loads((root / ".agent-starter/sandbox/sandbox.json").read_text(encoding="utf-8"))
                self.assertIn(base_image, text)
                self.assertIn(installer, text)
                self.assertIn(package, text)
                self.assertNotIn(absent, text)
                self.assertEqual(sandbox["image_profile"], profile)
                self.assertNotIn("chmod 0777", text)

    def test_project_container_scripts_set_inside_sandbox_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(
                root,
                database="mariadb",
                project_type="web",
                sandbox=SandboxConfig(enabled=True, mode="codex", codex_inside_container=True),
            )
            generate_project(config)
            for relative in (
                "scripts/sandbox/check",
                "scripts/sandbox/exec",
                "scripts/sandbox/shell",
                "scripts/sandbox/web",
                "scripts/sandbox/codex",
                "scripts/sandbox/codex-login",
                "scripts/sandbox/resume",
                "scripts/sandbox/codex-exec",
            ):
                self.assertIn("AGENTKIT_INSIDE_SANDBOX=1", (root / relative).read_text(encoding="utf-8"), relative)

    def test_inside_container_check_runs_project_check_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            env = os.environ.copy()
            env["AGENTKIT_INSIDE_SANDBOX"] = "1"
            completed = subprocess.run(
                [str(root / "scripts/sandbox/check")],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Already inside the Agent Kit sandbox. Running ./scripts/check.sh directly.", completed.stdout)
            self.assertIn("Documentation invariants", completed.stdout)
            self.assertNotIn("podman", completed.stderr.lower())

    def test_inside_container_exec_runs_command_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            env = os.environ.copy()
            env["AGENTKIT_INSIDE_SANDBOX"] = "1"
            completed = subprocess.run(
                [str(root / "scripts/sandbox/exec"), "printf", "inside-exec"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "inside-exec")
            self.assertNotIn("podman", completed.stderr.lower())

    def test_noninteractive_toolchain_commands_do_not_request_tty_or_fixed_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            for relative in ("scripts/sandbox/exec", "scripts/sandbox/check"):
                text = (root / relative).read_text(encoding="utf-8")
                self.assertNotIn("--name agentkit-sandbox-test-dev", text)
                self.assertIn("podman run --rm \\", text)
                self.assertNotIn("podman run --rm -it", text)

    def test_build_reuses_existing_image_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            text = (root / "scripts/sandbox/build").read_text(encoding="utf-8")
            self.assertIn("podman image exists agentkit-sandbox-test:dev", text)
            self.assertIn("scripts/sandbox/build --rebuild", text)
            self.assertIn("--label agentkit.project=sandbox-test", text)
            self.assertIn("--label agentkit.generated=true", text)

    def test_preflight_script_uses_adjacent_agent_starter_and_writes_fingerprint_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            text = (root / "scripts/sandbox/preflight").read_text(encoding="utf-8")
            self.assertIn('if [ -x "$ROOT/../agent-starter" ]; then', text)
            self.assertIn('"$ROOT/../agent-starter"', text)
            self.assertIn("sandbox_fingerprint()", text)
            self.assertIn('"sandbox_fingerprint"', text)
            self.assertIn('"inputs"', text)
            self.assertIn(".agent-starter/logs", text)
            self.assertIn("sandbox-preflight-doctor.log", text)
            self.assertIn("sandbox-build.log", text)
            self.assertIn("sandbox-check.log", text)

    def test_status_script_delegates_or_validates_preflight_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            generate_project(config)
            text = (root / "scripts/sandbox/status").read_text(encoding="utf-8")
            self.assertIn('exec "$AGENT_STARTER" status "$ROOT"', text)
            self.assertIn('"$ROOT/../agent-starter"', text)
            self.assertIn("sandbox_fingerprint()", text)
            self.assertIn("Sandbox preflight: missing", text)
            self.assertIn("Sandbox preflight: stale", text)
            self.assertIn("Sandbox preflight: valid", text)
            self.assertIn("Do not rerun scripts/sandbox/doctor", text)
            _write_sandbox_preflight_stamp(
                root,
                config,
                status="passed",
                run_check=True,
                steps=["sandbox doctor", "sandbox build", "sandbox check"],
            )
            completed = subprocess.run(
                [str(root / "scripts/sandbox/status")],
                cwd=root,
                env={**os.environ, "PATH": "/usr/bin:/bin"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Sandbox preflight: valid", completed.stdout)

    def test_sandbox_shell_remains_interactive_without_fixed_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            text = (root / "scripts/sandbox/shell").read_text(encoding="utf-8")
            self.assertNotIn("--name agentkit-sandbox-test-dev", text)
            self.assertIn("podman run --rm -it", text)
            self.assertIn("--label agentkit.project=sandbox-test", text)
            self.assertIn("--label agentkit.generated=true", text)
            self.assertIn("if inside_agentkit_sandbox; then\n  exec /bin/sh\nfi", text)
            self.assertIn("run_interactive_project_container /bin/sh", text)

    def test_clean_script_can_dry_run_and_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            text = (root / "scripts/sandbox/clean").read_text(encoding="utf-8")
            self.assertIn("Usage: scripts/sandbox/clean [--dry-run] [--image] [--volumes] [--all] [--force|--yes]", text)
            self.assertIn("podman ps -aq --filter label=agentkit.project=sandbox-test", text)
            self.assertIn("--filter label=agentkit.generated=true", text)
            self.assertIn("podman image rm agentkit-sandbox-test:dev", text)
            self.assertIn("Dry run: would remove matching generated sandbox resources only.", text)
            self.assertIn("Refusing to remove project volumes without --force", text)
            self.assertIn("podman image exists agentkit-sandbox-test:dev", text)
            self.assertIn('podman volume exists "$volume"', text)
            self.assertIn("Volume not found:", text)
            self.assertIn("agentkit_sandbox-test_codex_home", text)

    def test_codex_mode_generates_codex_scripts_and_project_volume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(
                root,
                sandbox=SandboxConfig(enabled=True, mode="codex", codex_inside_container=True),
            )
            generate_project(config)
            for relative in (
                "scripts/sandbox/codex",
                "scripts/sandbox/codex-login",
                "scripts/sandbox/resume",
                "scripts/sandbox/codex-exec",
            ):
                self.assertTrue((root / relative).is_file(), relative)
            codex_script = (root / "scripts/sandbox/codex").read_text(encoding="utf-8")
            self.assertIn("agentkit_sandbox-test_codex_home", codex_script)
            self.assertIn("/home/codex", codex_script)
            self.assertIn("/workspace", codex_script)
            self.assertIn("AGENTKIT_INSIDE_SANDBOX=1", codex_script)
            self.assertIn("--userns=keep-id", codex_script)
            self.assertIn('--user "$HOST_UID:$HOST_GID"', codex_script)
            self.assertIn("--label agentkit.generated=true", codex_script)
            self.assertIn("--env HOME=/home/codex", codex_script)
            self.assertIn("$CODEX_HOME_VOLUME:/home/codex:Z,U", codex_script)
            self.assertIn(HOST_SIDE_MESSAGE, codex_script)
            self.assertNotIn("~/.codex", codex_script)

    def test_host_only_sandbox_scripts_refuse_inside_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(
                root,
                database="mariadb",
                sandbox=SandboxConfig(enabled=True, mode="codex", codex_inside_container=True),
            )
            generate_project(config)
            for relative in (
                "scripts/sandbox/build",
                "scripts/sandbox/codex",
                "scripts/sandbox/codex-login",
                "scripts/sandbox/resume",
                "scripts/sandbox/codex-exec",
                "scripts/sandbox/db-up",
                "scripts/sandbox/db-down",
                "scripts/sandbox/db-shell",
                "scripts/sandbox/db-logs",
            ):
                self.assertIn(HOST_SIDE_MESSAGE, (root / relative).read_text(encoding="utf-8"), relative)

    def test_database_projects_generate_db_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root, database="mariadb"))
            for relative in (
                "scripts/sandbox/db-up",
                "scripts/sandbox/db-down",
                "scripts/sandbox/db-shell",
                "scripts/sandbox/db-logs",
                ".env.sandbox.example",
            ):
                self.assertTrue((root / relative).is_file(), relative)
            db_up = (root / "scripts/sandbox/db-up").read_text(encoding="utf-8")
            self.assertIn("agentkit_sandbox-test_db_data", db_up)
            self.assertIn("127.0.0.1", db_up)
            self.assertIn("dev_password_change_me", (root / ".env.sandbox.example").read_text(encoding="utf-8"))

    def test_postgresql_sandbox_uses_postgres_port_and_data_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root, database="postgresql"))
            db_up = (root / "scripts/sandbox/db-up").read_text(encoding="utf-8")
            self.assertIn("docker.io/library/postgres", db_up)
            self.assertIn("5432", db_up)
            self.assertIn("/var/lib/postgresql/data", db_up)
            self.assertIn("POSTGRES_PASSWORD", db_up)
            self.assertNotIn("/var/lib/mysql", db_up)

    def test_game_projects_generate_headless_and_host_playtest_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(
                self.make_config(root, project_type="game", languages=["godot"], sandbox=SandboxConfig(enabled=True, mode="toolchain"))
            )
            self.assertTrue((root / "scripts/sandbox/headless-test").is_file())
            self.assertTrue((root / "scripts/playtest-host").is_file())
            self.assertTrue((root / "docs/GODOT-SANDBOX.md").is_file())
            self.assertFalse((root / "scripts/sandbox/playtest-gui").exists())
            headless = (root / "scripts/sandbox/headless-test").read_text(encoding="utf-8")
            self.assertIn("scripts/godot-headless-test.sh", headless)
            self.assertIn("artifacts/headless", headless)
            self.assertIn("No scripts/godot-headless-test.sh hook exists", headless)
            sandbox_doc = (root / "docs/12-SANDBOX.md").read_text(encoding="utf-8")
            godot_doc = (root / "docs/GODOT-SANDBOX.md").read_text(encoding="utf-8")
            self.assertIn("Interactive GPU/audio/controller playtesting is usually better on the host", sandbox_doc)
            self.assertIn("sandbox.gui_passthrough: true", sandbox_doc)
            self.assertIn("scripts/godot-headless-test.sh", sandbox_doc)
            self.assertIn("scripts/sandbox/headless-test", godot_doc)
            self.assertIn("artifacts/headless/", godot_doc)
            self.assertIn("Screenshot or visual smoke tests are project-specific", godot_doc)
            self.assertIn("Do not promise visual", godot_doc)
            self.assertNotIn("GUI forwarding is enabled", sandbox_doc)

    def test_game_gui_passthrough_is_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(
                self.make_config(
                    root,
                    project_type="game",
                    languages=["godot"],
                    sandbox=SandboxConfig(enabled=True, mode="toolchain", gui_passthrough=True),
                )
            )
            script = (root / "scripts/sandbox/playtest-gui").read_text(encoding="utf-8")
            sandbox_doc = (root / "docs/12-SANDBOX.md").read_text(encoding="utf-8")
            sandbox_json = json.loads((root / ".agent-starter/sandbox/sandbox.json").read_text(encoding="utf-8"))
            self.assertTrue(sandbox_json["advanced_passthrough"]["gpu_audio_controller"])
            self.assertIn("Wayland socket not found", script)
            self.assertIn("--device /dev/dri", script)
            self.assertIn("--device /dev/input", script)
            self.assertIn("--userns=keep-id", script)
            self.assertIn('--user "$USER_ID:$(id -g)"', script)
            self.assertIn("pipewire-0", script)
            self.assertIn("selected host display/audio/input interfaces", script)
            self.assertNotIn("~/.codex", script)
            self.assertNotIn("$HOME", script)
            self.assertNotIn("/run/podman/podman.sock", script)
            self.assertIn("Advanced GUI passthrough is enabled", sandbox_doc)
            self.assertIn("Headless checks remain the preferred autonomous Codex path", sandbox_doc)

    def test_autonomous_prompt_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            self.assertFalse((root / "FIRST_RUN_AUTONOMOUS.md").exists())

            enabled = Path(temp) / "autonomous"
            generate_project(
                self.make_config(
                    enabled,
                    sandbox=SandboxConfig(enabled=True, mode="codex", codex_inside_container=True, first_run_autonomous_prompt=True),
                )
            )
            prompt = (enabled / "FIRST_RUN_AUTONOMOUS.md").read_text(encoding="utf-8")
            self.assertIn("COMPLETE", prompt)
            self.assertIn("BLOCKED_PERMISSION", prompt)
            self.assertIn("BLOCKED_ENVIRONMENT", prompt)
            self.assertIn("scripts/sandbox/doctor", prompt)
            self.assertIn("scripts/sandbox/build", prompt)
            self.assertIn("scripts/sandbox/check", prompt)
            self.assertIn("Do not ask for Codex `danger-full-access`", prompt)
            self.assertIn(".agent-starter/sandbox/preflight.json", prompt)
            self.assertIn("do not rerun `scripts/sandbox/doctor`", prompt)
            self.assertIn("Do not silently fall back to host build/test commands", prompt)
            self.assertIn("Do not install host packages", prompt)
            self.assertIn("Do not deploy", prompt)

    def test_handoff_prompt_forbids_raw_session_and_auth_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            prompt = (root / "docs/agent-prompts/create-container-handoff.md").read_text(encoding="utf-8")
            self.assertIn("docs/CODEX-HANDOFF.md", prompt)
            self.assertIn("Do not copy raw Codex session transcripts", prompt)
            self.assertIn("Do not include OAuth tokens", prompt)

    def test_source_sandbox_doctor_reports_missing_podman_without_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))
            with mock.patch("agent_starter.sandbox.shutil.which", return_value=None), mock.patch(
                "agent_starter.sandbox.subprocess.run"
            ) as run:
                code, lines = doctor_lines(root)
            self.assertEqual(code, 2)
            self.assertIn("[missing] podman", "\n".join(lines))
            self.assertIn("sudo pacman -S --needed podman passt fuse-overlayfs", "\n".join(lines))
            run.assert_not_called()

    def test_source_sandbox_doctor_reports_userns_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            generate_project(self.make_config(root))

            def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                if args[:3] == ["podman", "info", "--format"]:
                    return subprocess.CompletedProcess(args, 0, stdout="true\n", stderr="")
                if args == ["podman", "run", "--help"]:
                    return subprocess.CompletedProcess(args, 0, stdout="Usage: podman run [options]\n      --userns string\n", stderr="")
                if args == ["id", "-un"]:
                    return subprocess.CompletedProcess(args, 0, stdout="tester\n", stderr="")
                if args[:3] == ["podman", "image", "exists"]:
                    return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
                raise AssertionError(f"unexpected command: {args!r}")

            with mock.patch("agent_starter.sandbox.shutil.which", return_value="/usr/bin/podman"), mock.patch(
                "agent_starter.sandbox.subprocess.run", side_effect=fake_run
            ):
                code, lines = doctor_lines(root)
            self.assertEqual(code, 0)
            self.assertIn("[ok] Podman supports --userns=keep-id for host-owned workspace files", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
