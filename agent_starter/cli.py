"""Command-line interface for the CLI AI Agent Starter Kit."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .agents import AgentError, get_adapter
from .codex_skill import inspect_skill, install_skill, uninstall_skill, update_skill
from .cli_app.config_command import register_config_command
from .cli_app.deployment_commands import command_deployment_build, command_deployment_check, command_deployment_plan, register_deployment_commands
from .cli_app.agent_commands import (
    _ensure_agent_authorized,
    command_auth,
    command_launch,
    launch_agent,
    register_agent_commands,
)
from .cli_app.information_commands import command_example, command_toolchains, register_information_commands
from .cli_app.generation_commands import (
    SENSITIVE_RE,
    _github_remote,
    _recursive_strings,
    _report_generation,
    _validate_noninteractive_config,
    command_generate,
    command_new,
    load_answers,
    register_generation_commands,
)
from .cli_app.inspection_commands import (
    command_audit_context,
    command_audit_structure,
    command_doctor,
    command_validate,
    register_doctor_command,
    register_validation_commands,
)
from .cli_app.skill_commands import (
    _print_skill_change,
    command_codex_install_skill,
    command_codex_skill_status,
    command_codex_uninstall_skill,
    command_codex_update_skill,
    register_skill_commands,
)
from .cli_app.sandbox_commands import (
    command_sandbox_clean,
    command_sandbox_doctor,
    command_sandbox_preflight,
    register_sandbox_commands,
)
from .cli_app.project_runtime import _run_project_command, _run_project_command_logged, load_generated_config
from .cli_app.local_model_commands import (
    OllamaModelAssessment,
    _best_ollama_assessment,
    _coding_score,
    _find_context_length,
    _parse_ollama_list,
    _show_ollama_model,
    assess_ollama_model,
    command_ollama_check,
    register_local_model_command,
    render_local_model_handoff_prompt,
)
from .cli_app.prompt_commands import (
    ContinuationDelta,
    PROMPT_TEMPLATES,
    _prompt_interactive_choice,
    _prompt_interactive_value,
    _prompt_template_section,
    build_continuation_delta,
    collect_interactive_prompt_request,
    collect_interactive_task_packet,
    command_prompt,
    register_prompt_command,
    render_continuation_prompt,
)
from .cli_app.readiness_commands import (
    AI_LOCAL_IGNORE_PATTERNS,
    GitReadiness,
    _codex_status_summary,
    _git_readiness,
    _git_status_summary,
    _github_workflow_summary,
    _ignored_ai_artifacts_summary,
    _looks_like_remote_rsync_target,
    _podman_rootless_summary,
    _rsync_command,
    _run_local_check,
    _sandbox_status_lines,
    _validate_rsync_target,
    _xdg_runtime_summary,
    command_github_ready,
    command_rsync_plan,
    command_status,
    register_readiness_commands,
)
from .cli_app.sandbox_orchestration import (
    SANDBOX_FINGERPRINT_INPUTS,
    _podman_image_id,
    _sha256_file,
    _write_sandbox_preflight_stamp,
    sandbox_fingerprint,
    sandbox_preflight,
    sandbox_preflight_state,
)
from .config_schema import has_custom_commands
from .doctor import CodexDoctorState, build_doctor_report, provider_for_detection, render_doctor_text
from .generator import GenerationReport, generate_project, validate_project
from .idea_prompts import MODES as IDEA_PROMPT_MODES
from .idea_prompts import result_to_json, write_idea_prompt
from .models import ProjectConfig
from .model_policy import DEFAULT_CODEX_MODEL_POLICY
from .platforms import PROVIDER_IDS, detect_host
from .sandbox import doctor_lines as sandbox_doctor_lines
from .structure.audit import audit_project, render_audit_text
from .toolchains import TOOLCHAINS, normalize_language, unique
from .wizard import CancelledByUser, run_wizard, slugify


def _print(message: str = "") -> None:
    print(message)


def command_idea_prompt(args: argparse.Namespace) -> int:
    result = write_idea_prompt(
        start=Path(args.project),
        mode=args.mode,
        idea=args.idea,
        arguments=args.arguments if args.from_codex else None,
    )
    if args.json:
        _print(json.dumps(result_to_json(result), indent=2, sort_keys=True))
    else:
        _print(str(result.prompt_path))
    if args.print:
        _print("")
        sys.stdout.write(result.body)
    return 0


def command_gui(args: argparse.Namespace) -> int:
    del args
    try:
        from .gui.app import run_gui
    except RuntimeError as exc:
        _print(f"Error: {exc}")
        return 3
    try:
        return run_gui()
    except RuntimeError as exc:
        _print(f"Error: {exc}")
        return 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-starter",
        description="Generate safe AGENTS.md + docs/ project workspaces for OpenAI Codex CLI on CachyOS.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    register_config_command(sub)

    register_generation_commands(sub)

    register_validation_commands(sub)

    register_readiness_commands(sub)

    register_deployment_commands(sub)

    register_doctor_command(sub)

    gui = sub.add_parser("gui", help="Open the optional beginner-friendly desktop wizard.")
    gui.set_defaults(func=command_gui)

    register_agent_commands(sub)

    register_prompt_command(sub)

    idea_prompt = sub.add_parser("idea-prompt", help="Write a full Agent Kit implementation prompt from a short idea.")
    idea_prompt.add_argument("--project", default=".", help="Generated project root; defaults to the current directory.")
    idea_prompt.add_argument("--mode", choices=IDEA_PROMPT_MODES, help="Task mode for non-interactive prompt generation.")
    idea_prompt.add_argument("--idea", help="Short user idea for non-interactive prompt generation.")
    idea_prompt.add_argument("--from-codex", action="store_true", help="Parse --arguments as a Codex skill invocation payload.")
    idea_prompt.add_argument("--arguments", default="", help="Raw $agentkit arguments such as 'implement Add SQLite support'.")
    idea_prompt.add_argument("--print", action="store_true", help="Also print the generated prompt body.")
    idea_prompt.add_argument("--json", action="store_true", help="Print machine-readable prompt metadata.")
    idea_prompt.set_defaults(func=command_idea_prompt)

    register_local_model_command(sub)

    register_skill_commands(sub)

    register_sandbox_commands(
        sub,
        sandbox_preflight=sandbox_preflight,
        run_project_command=_run_project_command,
    )

    register_information_commands(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    values = list(argv) if argv is not None else sys.argv[1:]
    if not values:
        values = ["new"]
    args = parser.parse_args(values)
    try:
        return int(args.func(args))
    except CancelledByUser as exc:
        _print(str(exc))
        return 130
    except (AgentError, ValueError) as exc:
        _print(f"Error: {exc}")
        return 2
    except KeyboardInterrupt:
        _print("\nCancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
