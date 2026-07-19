"""Codex authorization and validated project-launch command family."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..agents import get_adapter
from ..generator import validate_project
from ..models import ProjectConfig
from .project_runtime import _run_project_command
from .sandbox_orchestration import sandbox_preflight


def _ensure_agent_authorized(*, allow_login: bool = True) -> bool:
    adapter = get_adapter()
    if not adapter.exists():
        print(f"{adapter.display_name} is not installed.")
        print(f"Review and run: {adapter.install_command}")
        return False
    status = adapter.auth_status()
    if status is True or status is None:
        return True
    if not allow_login:
        return False
    print(f"Starting {adapter.display_name}'s official account authorization flow.")
    return adapter.login(device_auth=False)


def launch_agent(
    root: Path,
    *,
    kickoff: bool = False,
    allow_login: bool = True,
    sandbox_preflight_enabled: bool = True,
) -> int:
    root = root.expanduser().resolve()
    config_path = root / ".agent-starter/project.json"
    if not config_path.is_file():
        print(f"No generated project metadata found at {config_path}")
        return 2
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"Could not load project metadata: {exc}")
        return 2
    if config.primary_agent != "codex":
        print("This workspace metadata was not created for the Codex-only starter kit.")
        return 2
    validation = validate_project(root)
    if not validation.ok:
        print("Launch blocked by project validation:")
        for error in validation.errors:
            print(f"  - {error}")
        print("Correct the errors and run validation again before launching Codex.")
        return 2
    if sandbox_preflight_enabled and config.sandbox.enabled and config.sandbox.mode in {"toolchain", "codex"}:
        preflight_code = sandbox_preflight(root, run_check=True)
        if preflight_code != 0:
            return preflight_code
    adapter = get_adapter()
    prompt_path = root / "FIRST_PROMPT.md"
    if not prompt_path.is_file():
        print("FIRST_PROMPT.md is missing.")
        return 2
    if kickoff and config.sandbox.codex_inside_container:
        prompt_name = "FIRST_RUN_AUTONOMOUS.md" if (root / "FIRST_RUN_AUTONOMOUS.md").is_file() else "FIRST_PROMPT.md"
        codex_exec = root / "scripts/sandbox/codex-exec"
        if not codex_exec.is_file():
            print("Codex-inside-container kickoff requested, but scripts/sandbox/codex-exec is missing.")
            return 2
        print("Launching autonomous Codex inside the project sandbox.")
        print("If this fails for authorization, run scripts/sandbox/codex-login explicitly; host Codex auth is not mounted.")
        return _run_project_command(root, [codex_exec, prompt_name], label="sandbox codex exec", timeout=3600)
    if not _ensure_agent_authorized(allow_login=allow_login):
        print("Agent authorization was not confirmed. Run the generated ./scripts/setup-agent.sh helper.")
        return 3
    prompt = prompt_path.read_text(encoding="utf-8")
    if kickoff:
        code = adapter.launch_kickoff(root, prompt)
    else:
        code = adapter.launch_interactive(root, prompt)
    if code != 0 and config.model_policy.selection == "explicit":
        print(config.model_policy.launch_failure_message())
    return code


def command_auth(args: argparse.Namespace) -> int:
    adapter = get_adapter()
    if not adapter.exists():
        print(f"{adapter.display_name} is not installed.")
        print(f"Official installer: {adapter.install_command}")
        if not args.install:
            print("Re-run with --install only after reviewing that vendor-published command.")
            return 2
        if not adapter.install():
            print("Installation did not complete or the command is not on PATH yet.")
            return 3
    print(f"Detected: {adapter.version()}")
    status = adapter.auth_status()
    if args.status:
        print("authorized" if status is True else "not authorized" if status is False else "status unavailable")
        return 0 if status is not False else 3
    if status is True and not args.relogin:
        print("The CLI reports an authorized account. Use --relogin to switch/re-authorize through the official flow.")
        return 0
    ok = adapter.login(device_auth=args.device_auth)
    return 0 if ok else 3


def command_launch(args: argparse.Namespace) -> int:
    return launch_agent(
        Path(args.project),
        kickoff=args.kickoff,
        allow_login=not args.no_login,
        sandbox_preflight_enabled=not args.skip_sandbox_preflight,
    )


def register_agent_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    auth = subparsers.add_parser("auth", help="Install or authorize Codex through its official CLI flow.")
    auth.add_argument("--install", action="store_true", help="Run the displayed vendor installer when missing.")
    auth.add_argument("--status", action="store_true", help="Only report status.")
    auth.add_argument("--relogin", action="store_true", help="Run authorization even if currently authorized.")
    auth.add_argument("--device-auth", action="store_true", help="Use Codex device-code authorization.")
    auth.set_defaults(func=command_auth)

    launch = subparsers.add_parser("launch", help="Launch Codex in a generated project.")
    launch.add_argument("project", nargs="?", default=".")
    launch.add_argument("--kickoff", action="store_true", help="Run FIRST_PROMPT.md as a one-shot task.")
    launch.add_argument("--no-login", action="store_true", help="Do not start authorization automatically.")
    launch.add_argument(
        "--skip-sandbox-preflight",
        action="store_true",
        help="Do not run generated sandbox doctor/build/check before launching Codex.",
    )
    launch.set_defaults(func=command_launch)
