"""Answers loading and project-generation CLI lifecycle."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config_schema import has_custom_commands
from ..generator import GenerationReport, generate_project
from ..models import ProjectConfig
from ..toolchains import normalize_language, unique
from ..wizard import run_wizard, slugify
from .agent_commands import launch_agent


SENSITIVE_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\s*[:=]\s*\S+)|"
    r"\bsk-[A-Za-z0-9_-]{16,}\b"
)


def _recursive_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_recursive_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(_recursive_strings(item))
        return result
    return []


def _validate_noninteractive_config(config: ProjectConfig, *, allow_custom_commands: bool) -> None:
    if not config.project_name.strip():
        raise ValueError("project_name is required in the answers file.")
    if not config.project_path.strip():
        raise ValueError("project_path is required in the answers file or via --path.")

    for value in _recursive_strings(config.to_dict()):
        if SENSITIVE_RE.search(value):
            raise ValueError("Answers appear to contain a credential or private key. Remove it and rotate it if it was real.")

    if has_custom_commands(config) and not allow_custom_commands:
        raise ValueError(
            "The answers file contains executable custom commands. Review it, then re-run with --allow-custom-commands."
        )


def load_answers(path: Path, *, path_override: str | None, allow_custom_commands: bool) -> ProjectConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read answers file {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Answers JSON must contain one object.")

    config = ProjectConfig.from_dict(raw)
    if path_override:
        config.project_path = str(Path(path_override).expanduser().resolve())
    elif config.project_path:
        config.project_path = str(Path(config.project_path).expanduser().resolve())
    config.project_slug = config.project_slug or slugify(config.project_name)
    config.languages = unique(normalize_language(item) for item in config.languages)
    config.database = config.database.strip().lower()
    config.advisor.raw_output = ""
    _validate_noninteractive_config(config, allow_custom_commands=allow_custom_commands)
    return config


def _report_generation(report: GenerationReport, *, dry_run: bool = False) -> None:
    verb = "Would create" if dry_run else "Created"
    print(f"\nWorkspace: {report.root}")
    print(f"{verb}: {len(report.created)} file(s)")
    if report.unchanged:
        print(f"Unchanged: {len(report.unchanged)} file(s)")
    if report.overwritten:
        print(f"Replaced with backups: {len(report.overwritten)} file(s)")
    if report.conflicts:
        print(f"Preserved conflicts: {len(report.conflicts)} file(s)")
    if report.proposals:
        print("Generated alternatives were placed under .agent-starter/proposals/ for manual merging.")
    if report.backups:
        print("Original replaced files were copied under .agent-starter/backups/.")
    if report.git_initialized:
        print("Initialized a local Git repository; no commit or remote push was made.")
    for warning in [*report.warnings, *report.validation_warnings]:
        print(f"[warning] {warning}")
    for error in report.validation_errors:
        print(f"[error] {error}")
    if not dry_run and report.ok:
        print("Starter workspace validation passed.")
        print("Start with START_HERE.md in the generated workspace.")


def _github_remote(root: Path, config: ProjectConfig) -> int:
    visibility = "private" if config.github_remote == "create-private" else "public"
    if shutil.which("gh") is None:
        print("GitHub CLI is not installed. On CachyOS, review: sudo pacman -S --needed github-cli")
        return 2
    if not (root / ".git").exists():
        print("Cannot create a GitHub remote before the local Git repository exists.")
        return 2
    existing = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=root, text=True, capture_output=True, check=False
    )
    if existing.returncode == 0:
        print(f"An origin remote already exists: {existing.stdout.strip()}")
        return 0
    auth = subprocess.run(["gh", "auth", "status"], cwd=root, check=False)
    if auth.returncode != 0:
        print("Starting GitHub CLI authorization. Credentials remain managed by gh.")
        if subprocess.run(["gh", "auth", "login"], cwd=root, check=False).returncode != 0:
            return 3
    command = [
        "gh",
        "repo",
        "create",
        config.project_slug,
        f"--{visibility}",
        "--source",
        str(root),
        "--remote",
        "origin",
    ]
    result = subprocess.run(command, cwd=root, check=False)
    if result.returncode == 0:
        print("Created the GitHub repository and origin remote. No code was pushed.")
    return result.returncode


def command_new(args: argparse.Namespace) -> int:
    if args.answers:
        config = load_answers(
            Path(args.answers), path_override=args.path, allow_custom_commands=args.allow_custom_commands
        )
        launch = not args.no_launch
        kickoff = args.kickoff
        interactive = False
    else:
        result = run_wizard(
            initial_path=args.path,
            skip_agent_setup=args.skip_agent_setup,
            entry_mode=args.entry_mode,
        )
        config = result.config
        launch = result.launch_after_generation and not args.no_launch
        kickoff = args.kickoff or result.kickoff_mode
        interactive = True

    report = generate_project(config, force=args.force, dry_run=args.dry_run)
    _report_generation(report, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    if not report.ok:
        print("Resolve validation errors before launching an agent.")
        return 2

    if interactive and config.github_remote in {"create-private", "create-public"}:
        remote_code = _github_remote(config.root, config)
        if remote_code != 0:
            print("GitHub remote setup did not complete; the local project remains usable.")

    print("\nNext local checks:")
    print(f"  cd {config.root}")
    print("  less START_HERE.md")
    print("  less NEXT_STEPS.md")
    print("  ./scripts/doctor.sh")
    print("  ./scripts/bootstrap-dev.sh        # review only")
    print("  ./scripts/bootstrap-dev.sh --install  # installs after sudo approval")
    print("  ./scripts/check.sh")
    if config.sandbox.enabled:
        print("  agent-starter sandbox preflight .")
        if config.sandbox.codex_inside_container:
            print("  scripts/sandbox/codex-login")
            print("  scripts/sandbox/codex")
    print("  ./START_AGENT.sh")

    if launch:
        return launch_agent(config.root, kickoff=kickoff)
    return 0


def command_generate(args: argparse.Namespace) -> int:
    config = load_answers(
        Path(args.answers), path_override=args.path, allow_custom_commands=args.allow_custom_commands
    )
    report = generate_project(config, force=args.force, dry_run=args.dry_run)
    _report_generation(report, dry_run=args.dry_run)
    return 0 if (args.dry_run or report.ok) else 2


def register_generation_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    new = subparsers.add_parser(
        "new",
        aliases=["init"],
        help="Run the interactive project wizard or consume an answers file.",
    )
    new.add_argument("--path", help="Project directory (overrides answers-file path).")
    new.add_argument("--answers", help="Use JSON answers instead of interactive questions.")
    new.add_argument("--force", action="store_true", help="Back up and replace conflicting managed files.")
    new.add_argument("--dry-run", action="store_true", help="Report intended writes without changing files.")
    new.add_argument("--skip-agent-setup", action="store_true", help="Defer Codex installation/account authorization.")
    new.add_argument(
        "--mode",
        dest="entry_mode",
        choices=("guided", "advanced"),
        default="advanced",
        help="Interactive presentation: guided safe defaults or the compatibility-preserved full advanced flow.",
    )
    new.add_argument("--no-launch", action="store_true", help="Do not launch Codex after generation.")
    new.add_argument("--kickoff", action="store_true", help="Run the first prompt as a one-shot Codex task.")
    new.add_argument(
        "--allow-custom-commands",
        action="store_true",
        help="Allow explicitly supplied answers-file commands to become executable project scripts.",
    )
    new.set_defaults(func=command_new)

    generate = subparsers.add_parser(
        "generate",
        help="Generate deterministically from a JSON answers file without launching an agent.",
    )
    generate.add_argument("--answers", required=True)
    generate.add_argument("--path")
    generate.add_argument("--force", action="store_true")
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument("--allow-custom-commands", action="store_true")
    generate.set_defaults(func=command_generate)
