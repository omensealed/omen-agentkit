"""Plan-only deployment CLI registration and presentation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ..deployment_build import build_artifact, render_build_json, render_build_text
from ..deployment_check import check_deployment, load_immutable_plan, render_check_json, render_check_text
from ..deployment_plan import (
    DeploymentPlanError,
    confined_output_path,
    build_deployment_plan,
    inspect_source_state,
    load_plan_project_config,
    load_target_profile,
    render_plan_json,
    render_plan_text,
)
from ..generation import atomic_create


def _deployment_root(value: str, *, operation: str) -> Path:
    requested_root = Path(value).expanduser()
    if requested_root.is_symlink():
        raise ValueError(f"Deployment {operation} refuses a symlinked project root.")
    root = requested_root.resolve()
    if root == Path(root.anchor) or not root.is_dir():
        raise ValueError(f"Deployment {operation} requires an existing non-root generated project directory.")
    return root


def command_deployment_plan(args: argparse.Namespace) -> int:
    root = _deployment_root(args.project, operation="planning")
    config = load_plan_project_config(root)
    profile = load_target_profile(root, Path(args.profile))
    source = inspect_source_state(root)
    destination = confined_output_path(root, Path(args.output)) if args.output else None
    plan = build_deployment_plan(
        config,
        profile,
        source,
        plan_output=destination.relative_to(root).as_posix() if destination is not None else None,
    )
    rendered = render_plan_json(plan) if args.format == "json" else render_plan_text(plan)
    if destination is not None:
        try:
            atomic_create(destination, rendered.encode("utf-8"), mode=0o644)
        except FileExistsError as exc:
            raise ValueError("Immutable plan output already exists; choose a new project-relative path.") from exc
        print(f"Wrote immutable deployment plan: {destination.relative_to(root)}")
        print(f"Plan digest (SHA-256): {plan.digest}")
    else:
        sys.stdout.write(rendered)
    return 0


def command_deployment_check(args: argparse.Namespace) -> int:
    root = _deployment_root(args.project, operation="checking")
    plan = load_immutable_plan(root, Path(args.plan))
    report = check_deployment(root, plan)
    sys.stdout.write(render_check_json(report) if args.format == "json" else render_check_text(report))
    return report.exit_code


def command_deployment_build(args: argparse.Namespace) -> int:
    root = _deployment_root(args.project, operation="building")
    plan = load_immutable_plan(root, Path(args.plan))
    report = build_artifact(root, plan, Path(args.source), plan_reference=Path(args.plan).as_posix())
    sys.stdout.write(render_build_json(report) if args.format == "json" else render_build_text(report))
    return 0


def register_deployment_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    deployment = subparsers.add_parser(
        "deployment",
        help="Create reviewed deployment plans without builds, network access, or remote changes.",
    )
    deployment_sub = deployment.add_subparsers(dest="deployment_command", required=True)
    plan = deployment_sub.add_parser("plan", help="Render a digest-bound immutable deployment plan.")
    plan.add_argument("project", nargs="?", default=".", help="Generated project root.")
    plan.add_argument("--profile", required=True, help="Project-relative reviewed target-profile JSON path.")
    plan.add_argument("--format", choices=("text", "json"), default="text")
    plan.add_argument("--output", help="New project-relative output path; existing files are never replaced.")
    plan.set_defaults(func=command_deployment_plan)

    check = deployment_sub.add_parser("check", help="Check local plan evidence without target contact or writes.")
    check.add_argument("project", nargs="?", default=".", help="Generated project root.")
    check.add_argument("--plan", required=True, help="Project-relative immutable JSON plan path.")
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.set_defaults(func=command_deployment_check)

    build = deployment_sub.add_parser("build", help="Assemble a deterministic local artifact without running project commands.")
    build.add_argument("project", nargs="?", default=".", help="Generated project root.")
    build.add_argument("--plan", required=True, help="Project-relative immutable JSON plan path.")
    build.add_argument("--source", required=True, help="Reviewed project-relative artifact-input file or directory.")
    build.add_argument("--format", choices=("text", "json"), default="text")
    build.set_defaults(func=command_deployment_build)
