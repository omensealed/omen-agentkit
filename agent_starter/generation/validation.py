"""Read-only validation for generated AgentKit workspaces."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..deployment_ci import validate_github_action_references
from .registry import EXECUTABLE_FILES, REQUIRED_FILES


@dataclass(slots=True)
class ValidationReport:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _shell_files(root: Path) -> Iterable[Path]:
    for relative in EXECUTABLE_FILES:
        path = root / relative
        if path.is_file() and not path.is_symlink():
            yield path


def validate_project(root: Path) -> ValidationReport:
    root = root.expanduser().resolve()
    report = ValidationReport(root=root)
    if not root.is_dir():
        report.errors.append(f"Project directory does not exist: {root}")
        return report

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            report.errors.append(f"Missing required file: {relative}")
            continue
        report.checked.append(relative)
        if path.stat().st_size == 0:
            report.errors.append(f"Required file is empty: {relative}")

    config_path = root / ".agent-starter/project.json"
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("root JSON value must be an object")
            if data.get("schema_version") not in {1, 2}:
                report.warnings.append("Unknown project.json schema version.")
            serialized = json.dumps(data).lower()
            for suspicious in ("access_token", "refresh_token", "client_secret", "api_key\": \"sk-", "password\":"):
                if suspicious in serialized:
                    report.errors.append(
                        "project.json appears to contain secret material; remove it and rotate exposed credentials."
                    )
                    break
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            report.errors.append(f"Invalid .agent-starter/project.json: {exc}")

    required_agent_text = root / "AGENTS.md"
    if required_agent_text.is_file():
        text = required_agent_text.read_text(encoding="utf-8", errors="replace")
        for phrase in (
            "docs/11-IMPLEMENTATION-NOTES.md",
            "docs/09-PROGRESS.md",
            "docs/14-AGENT-HANDOFF.md",
            "./scripts/check.sh",
        ):
            if phrase not in text:
                report.errors.append(f"AGENTS.md is missing required workflow reference: {phrase}")

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        text = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        if ".env" not in text:
            report.errors.append(".gitignore must ignore .env files.")
    else:
        report.warnings.append("No .gitignore was found.")

    for shell_file in _shell_files(root):
        relative = str(shell_file.relative_to(root))
        if not os.access(shell_file, os.X_OK):
            report.errors.append(f"Script is not executable: {relative}")
        try:
            result = subprocess.run(
                ["bash", "-n", str(shell_file)],
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
            if result.returncode != 0:
                report.errors.append(f"Shell syntax error in {relative}: {result.stderr.strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            report.warnings.append(f"Could not syntax-check {relative}: {exc}")

    workflow = root / ".github/workflows/ci.yml"
    if workflow.is_file():
        workflow_text = workflow.read_text(encoding="utf-8", errors="replace")
        if "permissions:\n  contents: read" not in workflow_text:
            report.warnings.append("CI workflow does not appear to set read-only default contents permissions.")
        if "./scripts/check.sh" not in workflow_text:
            report.errors.append("CI workflow does not call the stable ./scripts/check.sh entry point.")
        for issue in validate_github_action_references(workflow_text):
            report.errors.append(f"CI workflow action pin [{issue.code}]: {issue.explanation} {issue.remedy}")

    manifest_path = root / ".agent-starter/manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest.get("files"), dict):
                report.errors.append("manifest.json has no file map.")
        except (json.JSONDecodeError, OSError) as exc:
            report.errors.append(f"Invalid manifest.json: {exc}")

    proposals = root / ".agent-starter/proposals"
    if proposals.exists():
        count = sum(1 for path in proposals.rglob("*") if path.is_file())
        if count:
            report.warnings.append(
                f"There are {count} generated proposal file(s) awaiting manual merge under .agent-starter/proposals/."
            )
    return report
