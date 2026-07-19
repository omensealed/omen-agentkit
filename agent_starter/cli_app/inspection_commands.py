"""Read-only workspace validation, structure audit, and host doctor commands."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

from .. import __version__
from ..agents import get_adapter
from ..context_budget import audit_context, render_context_audit
from ..doctor import CodexDoctorState, build_doctor_report, provider_for_detection, render_doctor_text
from ..generator import validate_project
from ..platforms import PROVIDER_IDS, detect_host
from ..structure.audit import audit_project, render_audit_text


def command_validate(args: argparse.Namespace) -> int:
    report = validate_project(Path(args.project))
    for checked in report.checked:
        if args.verbose:
            print(f"[ok] {checked}")
    for warning in report.warnings:
        print(f"[warning] {warning}")
    for error in report.errors:
        print(f"[error] {error}")
    if report.ok:
        print(f"Validated starter workspace: {report.root}")
        return 0
    return 2


def command_audit_structure(args: argparse.Namespace) -> int:
    baseline = Path(args.baseline) if args.baseline is not None else None
    report = audit_project(Path(args.project), baseline_path=baseline)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_audit_text(report))
    return 0


def command_audit_context(args: argparse.Namespace) -> int:
    report = audit_context(Path(args.project))
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_context_audit(report))
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    detection = detect_host(override=args.platform_provider)
    adapter = get_adapter()
    installed = adapter.exists()
    raw_version = adapter.version() if installed else "not installed"
    codex_version = "".join(character for character in raw_version if ord(character) >= 32)[:500] or "version unavailable"
    report = build_doctor_report(
        kit_version=__version__,
        python_version=platform.python_version(),
        detection=detection,
        provider=provider_for_detection(detection),
        executable_lookup=shutil.which,
        codex=CodexDoctorState(
            installed=installed,
            version=codex_version,
            authorized=adapter.auth_status() if installed else False,
        ),
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True) if args.json else render_doctor_text(report))
    return report.exit_code


def register_validation_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    validate = subparsers.add_parser("validate", help="Validate a generated starter workspace.")
    validate.add_argument("project", nargs="?", default=".")
    validate.add_argument("--verbose", action="store_true")
    validate.set_defaults(func=command_validate)

    audit_structure = subparsers.add_parser(
        "audit-structure",
        help="Report advisory Python source-structure hotspots without changing the project.",
    )
    audit_structure.add_argument("project", nargs="?", default=".")
    audit_structure.add_argument(
        "--baseline",
        help="Project-confined baseline JSON; defaults to .agent-starter/structure-baseline.json when present.",
    )
    audit_structure.add_argument("--json", action="store_true", help="Emit the structured advisory report as JSON.")
    audit_structure.set_defaults(func=command_audit_structure)

    audit_context_parser = subparsers.add_parser(
        "audit-context",
        help="Report advisory generated-context budgets without changing the project.",
    )
    audit_context_parser.add_argument("project", nargs="?", default=".")
    audit_context_parser.add_argument("--json", action="store_true", help="Emit the structured advisory report as JSON.")
    audit_context_parser.set_defaults(func=command_audit_context)


def register_doctor_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    doctor = subparsers.add_parser("doctor", help="Inspect the host and Codex CLI without changing anything.")
    doctor.add_argument(
        "--platform-provider",
        choices=PROVIDER_IDS,
        help="Explicit provider override; requires its package-manager executable and warns on OS contradiction.",
    )
    doctor.add_argument("--json", action="store_true", help="Emit the structured, redacted doctor report as JSON.")
    doctor.set_defaults(func=command_doctor)
