"""Read-only example-answers and toolchain information commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..model_policy import DEFAULT_CODEX_MODEL_POLICY
from ..toolchains import TOOLCHAINS


def command_example(args: argparse.Namespace) -> int:
    example = {
        "schema_version": 2,
        "project_name": "My Project",
        "project_slug": "my-project",
        "project_path": str(Path("./my-project").resolve()),
        "project_mode": "new",
        "project_stage": "idea",
        "project_type": "cli",
        "description": "Describe the program, game, site, or service to build.",
        "goals": ["Deliver one reliable end-to-end workflow", "Keep setup understandable"],
        "non_goals": [],
        "target_users": "Intended users",
        "target_platforms": ["cachyos-linux"],
        "packaging_targets": ["source checkout"],
        "stack_strategy": "manual",
        "languages": ["python"],
        "database": "sqlite",
        "network_access": False,
        "user_accounts": False,
        "handles_personal_data": False,
        "handles_payments": False,
        "primary_agent": "codex",
        "model_policy": DEFAULT_CODEX_MODEL_POLICY.to_dict(),
        "setup_agent_now": False,
        "git_enabled": True,
        "github_actions": False,
        "github_remote": "later",
        "default_branch": "main",
        "license_name": "AGPL-3.0-or-later",
        "tests": ["unit", "integration"],
        "browser_tests": False,
        "codex_agentkit_skill": True,
        "sandbox": {
            "enabled": True,
            "engine": "podman",
            "mode": "toolchain",
            "image_profile": "arch-toolchain",
            "codex_inside_container": False,
            "rootless_required": True,
            "install_agentkit_skill": True,
            "first_run_autonomous_prompt": False,
            "gui_passthrough": False,
        },
    }
    text = json.dumps(example, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists() and not args.force:
            print(f"Refusing to replace {path}; add --force.")
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path}")
    else:
        sys.stdout.write(text)
    return 0


def command_toolchains(args: argparse.Namespace) -> int:
    del args
    for toolchain in TOOLCHAINS:
        print(f"{toolchain.key:12} {toolchain.display:24} CachyOS: {', '.join(toolchain.packages)}")
    return 0


def register_information_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    example = subparsers.add_parser("example-answers", help="Print or write an answers JSON example.")
    example.add_argument("--output")
    example.add_argument("--force", action="store_true")
    example.set_defaults(func=command_example)

    toolchains = subparsers.add_parser("toolchains", help="List built-in CachyOS toolchain mappings.")
    toolchains.set_defaults(func=command_toolchains)
