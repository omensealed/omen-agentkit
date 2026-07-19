"""Generated sandbox CLI registration and presentation boundary."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from ..sandbox import doctor_lines as sandbox_doctor_lines


def command_sandbox_doctor(args: argparse.Namespace) -> int:
    code, lines = sandbox_doctor_lines(Path(args.project))
    for line in lines:
        print(line)
    return code


def command_sandbox_preflight(args: argparse.Namespace) -> int:
    return args._sandbox_preflight(Path(args.project), run_check=not args.no_check)


def command_sandbox_clean(args: argparse.Namespace) -> int:
    root = Path(args.project).expanduser().resolve()
    script = root / "scripts" / "sandbox" / "clean"
    if not script.is_file():
        print(f"[fail] Missing generated sandbox clean script: {script}")
        return 2
    command: list[object] = [script]
    for enabled, flag in (
        (args.image, "--image"),
        (args.volumes, "--volumes"),
        (args.all, "--all"),
        (args.dry_run, "--dry-run"),
        (args.force, "--force"),
        (args.yes, "--yes"),
    ):
        if enabled:
            command.append(flag)
    return args._run_project_command(root, command, label="sandbox clean")


def register_sandbox_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    sandbox_preflight: Callable[..., int],
    run_project_command: Callable[..., int],
) -> None:
    sandbox = subparsers.add_parser("sandbox", help="Inspect generated rootless Podman sandbox support.")
    sandbox_sub = sandbox.add_subparsers(dest="sandbox_command", required=True)

    doctor = sandbox_sub.add_parser("doctor", help="Check generated sandbox readiness without changing host setup.")
    doctor.add_argument("project", nargs="?", default=".")
    doctor.set_defaults(func=command_sandbox_doctor)

    preflight = sandbox_sub.add_parser(
        "preflight",
        help="Run generated host-side sandbox doctor/build/check before launching Codex.",
    )
    preflight.add_argument("project", nargs="?", default=".")
    preflight.add_argument("--no-check", action="store_true", help="Run doctor/build only, skipping sandbox check.")
    preflight.set_defaults(func=command_sandbox_preflight, _sandbox_preflight=sandbox_preflight)

    clean = sandbox_sub.add_parser("clean", help="Run the generated project sandbox cleanup helper.")
    clean.add_argument("project", nargs="?", default=".")
    clean.add_argument("--dry-run", action="store_true", help="Show matching sandbox resources without removing them.")
    clean.add_argument("--image", action="store_true", help="Also remove the generated project image.")
    clean.add_argument("--volumes", action="store_true", help="Also remove project Codex-home/database volumes; requires --force or --yes.")
    clean.add_argument("--all", action="store_true", help="Remove containers, image, and volumes; volumes require --force or --yes.")
    clean.add_argument("--force", action="store_true", help="Remove matching generated sandbox resources.")
    clean.add_argument("--yes", action="store_true", help="Backward-compatible alias to confirm project volume removal.")
    clean.set_defaults(func=command_sandbox_clean, _run_project_command=run_project_command)
