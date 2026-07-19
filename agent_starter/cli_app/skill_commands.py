"""Repo-local Agent Kit skill status and lifecycle CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..codex_skill import inspect_skill, install_skill, uninstall_skill, update_skill


def command_codex_skill_status(args: argparse.Namespace) -> int:
    status = inspect_skill(Path(args.project))
    print(f"Agent Kit skill path: {status.path}")
    print(f"Installed: {'yes' if status.exists else 'no'}")
    print(f"Managed by Agent Kit: {'yes' if status.managed else 'no'}")
    print(f"Installed skill version: {status.installed_version or 'none'}")
    print(f"Bundled skill version: {status.bundled_version}")
    print(f"Update available: {'yes' if status.update_available else 'no'}")
    return 0


def _print_skill_change(action: str, written: list[Path], backup: Path | None) -> None:
    print(f"Agent Kit skill {action}.")
    for path in written:
        print(f"  wrote {path}")
    if backup is not None:
        print(f"  backup {backup}")
    print("Restart Codex if the skill does not appear immediately in /skills.")


def command_codex_install_skill(args: argparse.Namespace) -> int:
    status = inspect_skill(Path(args.project))
    yes = args.yes
    if status.exists and status.managed and not yes:
        print(f"Installed Agent Kit skill version: {status.installed_version or 'unknown'}")
        print(f"Bundled Agent Kit skill version: {status.bundled_version}")
        answer = input("Update managed Agent Kit skill files now? [y/N]: ").strip().lower()
        yes = answer in {"y", "yes"}
        if not yes:
            print("No changes made.")
            return 2
    action, written, backup = install_skill(Path(args.project), yes=yes, force=args.force)
    _print_skill_change(action, written, backup)
    return 0


def command_codex_update_skill(args: argparse.Namespace) -> int:
    yes = args.yes
    if not yes:
        status = inspect_skill(Path(args.project))
        print(f"Installed Agent Kit skill version: {status.installed_version or 'unknown'}")
        print(f"Bundled Agent Kit skill version: {status.bundled_version}")
        answer = input("Update managed Agent Kit skill files now? [y/N]: ").strip().lower()
        yes = answer in {"y", "yes"}
        if not yes:
            print("No changes made.")
            return 2
    action, written, backup = update_skill(Path(args.project), yes=yes)
    _print_skill_change(action, written, backup)
    return 0


def command_codex_uninstall_skill(args: argparse.Namespace) -> int:
    action, backup = uninstall_skill(Path(args.project), force=args.force)
    if action == "missing":
        print("Agent Kit skill is not installed.")
    else:
        print("Agent Kit skill removed.")
        if backup is not None:
            print(f"  backup {backup}")
    return 0


def register_skill_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    codex = subparsers.add_parser("codex", help="Manage repo-local Codex conveniences for generated projects.")
    codex_sub = codex.add_subparsers(dest="codex_command", required=True)

    skill_status = codex_sub.add_parser("skill-status", help="Report repo-local Agent Kit skill state.")
    skill_status.add_argument("project", nargs="?", default=".")
    skill_status.set_defaults(func=command_codex_skill_status)

    install_parser = codex_sub.add_parser("install-agentkit-skill", help="Install or update the repo-local $agentkit skill.")
    install_parser.add_argument("project", nargs="?", default=".")
    install_parser.add_argument("--yes", action="store_true", help="Allow non-interactive update of managed skill files.")
    install_parser.add_argument("--force", action="store_true", help="Replace a non-managed agentkit skill after backing it up.")
    install_parser.set_defaults(func=command_codex_install_skill)

    update_parser = codex_sub.add_parser("update-agentkit-skill", help="Update managed repo-local $agentkit skill files.")
    update_parser.add_argument("project", nargs="?", default=".")
    update_parser.add_argument("--yes", action="store_true", help="Confirm managed skill replacement.")
    update_parser.set_defaults(func=command_codex_update_skill)

    uninstall_parser = codex_sub.add_parser("uninstall-agentkit-skill", help="Remove the managed repo-local $agentkit skill.")
    uninstall_parser.add_argument("project", nargs="?", default=".")
    uninstall_parser.add_argument("--force", action="store_true", help="Remove a non-managed agentkit skill after backing it up.")
    uninstall_parser.set_defaults(func=command_codex_uninstall_skill)
