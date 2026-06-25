"""Safe project-file generation and validation.

The generator treats an existing repository as valuable user data.  It never
silently replaces a file: unchanged files are left alone, conflicts are written
under ``.agent-starter/proposals/``, and ``--force`` creates timestamped backups
before replacement.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

from . import templates
from .models import ProjectConfig


REQUIRED_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "FIRST_PROMPT.md",
    "NEXT_STEPS.md",
    "README.md",
    ".agent-starter/rsync-excludes",
    ".agent-starter/project.json",
    "docs/README.md",
    "docs/00-PROJECT-BRIEF.md",
    "docs/01-REQUIREMENTS.md",
    "docs/02-ARCHITECTURE.md",
    "docs/03-TECH-STACK.md",
    "docs/04-DEVELOPMENT-ENVIRONMENT.md",
    "docs/05-TESTING.md",
    "docs/06-SECURITY.md",
    "docs/07-UX-ACCESSIBILITY.md",
    "docs/08-IMPLEMENTATION-PLAN.md",
    "docs/09-PROGRESS.md",
    "docs/10-DECISIONS.md",
    "docs/11-IMPLEMENTATION-NOTES.md",
    "docs/12-RELEASE-CHECKLIST.md",
    "docs/13-OPERATIONS.md",
    "docs/14-AGENT-HANDOFF.md",
    "docs/15-OPEN-QUESTIONS.md",
    "docs/AI-STACK-RECOMMENDATION.md",
    "scripts/bootstrap-dev.sh",
    "scripts/doctor.sh",
    "scripts/build.sh",
    "scripts/test.sh",
    "scripts/lint.sh",
    "scripts/check.sh",
    "scripts/run.sh",
    "scripts/setup-agent.sh",
    "scripts/agent-status.sh",
    "scripts/new-implementation-note.sh",
    "START_AGENT.sh",
)

EXECUTABLE_FILES: tuple[str, ...] = (
    "START_AGENT.sh",
    "scripts/bootstrap-dev.sh",
    "scripts/doctor.sh",
    "scripts/build.sh",
    "scripts/test.sh",
    "scripts/lint.sh",
    "scripts/check.sh",
    "scripts/run.sh",
    "scripts/setup-agent.sh",
    "scripts/agent-status.sh",
    "scripts/new-implementation-note.sh",
)


@dataclass(slots=True)
class GenerationReport:
    root: Path
    created: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    proposals: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    git_initialized: bool = False
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.validation_errors


@dataclass(slots=True)
class ValidationReport:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+:-]*$")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    rel = PurePosixPath(value)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError(f"Unsafe generated path: {value!r}")
    return rel



def _validate_config_safety(config: ProjectConfig) -> None:
    if config.primary_agent != "codex":
        raise ValueError("primary_agent must be codex.")
    for package in config.cachyos_packages:
        if not PACKAGE_NAME_RE.fullmatch(package) or package.startswith("-"):
            raise ValueError(f"Unsafe or invalid CachyOS package name: {package!r}")

def _assert_safe_root(root: Path) -> None:
    resolved = root.expanduser().resolve()
    home = Path.home().resolve()
    if resolved == Path("/"):
        raise ValueError("Refusing to generate files in the filesystem root.")
    if resolved == home:
        raise ValueError("Refusing to generate files directly in the home directory; choose a project subdirectory.")


def _assert_no_symlink_parent(root: Path, destination: Path) -> None:
    current = root
    try:
        relative = destination.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Generated path escaped the project root: {destination}") from exc
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing to write through symlinked directory: {current}")


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _redacted_config_dict(config: ProjectConfig) -> dict[str, object]:
    """Serialize configuration without model transcripts or credentials."""

    data = config.to_dict()
    advisor = data.get("advisor")
    if isinstance(advisor, dict):
        advisor["raw_output"] = ""
    return data


def _codex_scripts() -> tuple[str, str]:
    setup = templates.clean(
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        INSTALL_URL='https://chatgpt.com/codex/install.sh'
        if ! command -v codex >/dev/null 2>&1; then
          if [[ "${1:-}" != "--install" ]]; then
            printf '%s\n' 'Codex is not installed.'
            printf 'Review the official installer, then run: %s --install\n' "$0"
            printf 'Installer source: %s\n' "$INSTALL_URL"
            exit 2
          fi
          printf '%s\n' 'Running the vendor-published Codex installer after explicit approval.'
          curl -fsSL "$INSTALL_URL" | sh
          export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
        fi

        printf '%s\n' 'Starting the official Codex account authorization flow.'
        printf '%s\n' 'This script never reads or stores the OAuth token.'
        codex login
        codex login status
        """
    )
    status = templates.clean(
        r"""
        #!/usr/bin/env bash
        set -u
        if ! command -v codex >/dev/null 2>&1; then
          printf '%s\n' '[missing] OpenAI Codex CLI'
          exit 1
        fi
        codex --version || true
        if codex login status; then
          printf '%s\n' '[ok] Codex reports an authorized account.'
        else
          printf '%s\n' '[not authorized] Run ./scripts/setup-agent.sh'
          exit 2
        fi
        """
    )
    return setup, status

def _new_note_script() -> str:
    return templates.clean(
        r"""
        #!/usr/bin/env bash
        set -euo pipefail
        ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
        FILE="$ROOT/docs/11-IMPLEMENTATION-NOTES.md"
        AGENT_NAME=${1:-human-or-agent}
        OBJECTIVE=${2:-Describe the objective}
        NOW=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

        cat >>"$FILE" <<EOF

        ## $NOW — $AGENT_NAME

        - Objective/phase: $OBJECTIVE
        - Files/subsystems changed: Pending
        - Behavior/design decisions: Pending
        - Commands and tests run: Pending
        - Results: Pending
        - Security/data/performance/UX implications: Pending
        - Unresolved problems: Pending
        - Exact next step: Pending
        EOF

        printf 'Appended an implementation-note template to %s\n' "$FILE"
        """
    )


def build_file_map(config: ProjectConfig) -> dict[str, str]:
    """Render every managed file for a configured project."""

    setup_agent, agent_status = _codex_scripts()
    data: dict[str, str] = {
        "AGENTS.md": templates.agents_md(config),
        "FIRST_PROMPT.md": templates.first_prompt(config),
        "NEXT_STEPS.md": templates.next_steps(config),
        "README.md": templates.project_readme(config),
        ".gitignore": templates.gitignore(config),
        ".agent-starter/rsync-excludes": templates.rsync_excludes(config),
        ".env.example": templates.env_example(config),
        ".editorconfig": templates.editorconfig(),
        ".codex/config.toml": templates.codex_config(),
        "CONTRIBUTING.md": templates.contributing(config),
        "SECURITY.md": templates.security_policy(config),
        "docs/README.md": templates.docs_index(config),
        "docs/00-PROJECT-BRIEF.md": templates.project_brief(config),
        "docs/01-REQUIREMENTS.md": templates.requirements_doc(config),
        "docs/02-ARCHITECTURE.md": templates.architecture_doc(config),
        "docs/03-TECH-STACK.md": templates.tech_stack_doc(config),
        "docs/04-DEVELOPMENT-ENVIRONMENT.md": templates.development_environment_doc(config),
        "docs/05-TESTING.md": templates.testing_doc(config),
        "docs/06-SECURITY.md": templates.security_doc(config),
        "docs/07-UX-ACCESSIBILITY.md": templates.ux_doc(config),
        "docs/08-IMPLEMENTATION-PLAN.md": templates.implementation_plan(config),
        "docs/09-PROGRESS.md": templates.progress_doc(config),
        "docs/10-DECISIONS.md": templates.decisions_doc(config),
        "docs/11-IMPLEMENTATION-NOTES.md": templates.implementation_notes(config),
        "docs/12-RELEASE-CHECKLIST.md": templates.release_checklist(config),
        "docs/13-OPERATIONS.md": templates.operations_doc(config),
        "docs/14-AGENT-HANDOFF.md": templates.handoff_doc(config),
        "docs/15-OPEN-QUESTIONS.md": templates.open_questions_doc(config),
        "docs/AI-STACK-RECOMMENDATION.md": templates.advisor_doc(config),
        "scripts/bootstrap-dev.sh": templates.bootstrap_script(config),
        "scripts/doctor.sh": templates.doctor_script(config),
        "scripts/build.sh": templates.command_script(config, "build"),
        "scripts/test.sh": templates.command_script(config, "test"),
        "scripts/lint.sh": templates.command_script(config, "lint"),
        "scripts/check.sh": templates.check_script(config),
        "scripts/run.sh": templates.run_script(config),
        "scripts/setup-agent.sh": setup_agent,
        "scripts/agent-status.sh": agent_status,
        "scripts/new-implementation-note.sh": _new_note_script(),
        "START_AGENT.sh": templates.start_agent_script(config),
    }
    if config.github_actions:
        data[".github/workflows/ci.yml"] = templates.github_ci(config)
    license_name = config.license_name.strip().lower()
    if license_name == "mit":
        data["LICENSE"] = templates.mit_license()
    elif license_name in {"apache-2.0", "apache2"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="Apache License 2.0",
            spdx="Apache-2.0",
            url="https://www.apache.org/licenses/LICENSE-2.0.html",
            summary="This project is licensed under the Apache License, Version 2.0.",
        )
    elif license_name in {"bsd-3-clause", "bsd3"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="BSD 3-Clause License",
            spdx="BSD-3-Clause",
            url="https://opensource.org/license/bsd-3-clause",
            summary="This project is licensed under the BSD 3-Clause License.",
        )
    elif license_name in {"gpl-3.0-or-later", "gplv3-or-later", "gpl-3.0+"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="GNU General Public License v3.0 or later",
            spdx="GPL-3.0-or-later",
            url="https://www.gnu.org/licenses/gpl-3.0.html",
            summary=(
                "This project is licensed under the GNU General Public License, version 3 "
                "or any later version published by the Free Software Foundation."
            ),
        )
    elif license_name in {"agpl-3.0-or-later", "agplv3-or-later", "agpl-3.0+"}:
        data["LICENSE"] = templates.agpl_3_or_later_license()
    elif license_name in {"mpl-2.0", "mpl2"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="Mozilla Public License 2.0",
            spdx="MPL-2.0",
            url="https://www.mozilla.org/MPL/2.0/",
            summary="This project is licensed under the Mozilla Public License, version 2.0.",
        )

    config_json = json.dumps(_redacted_config_dict(config), indent=2, sort_keys=True) + "\n"
    data[".agent-starter/project.json"] = config_json
    data[".agent-starter/README.md"] = templates.clean(
        """
        # Agent Starter metadata

        `project.json` records non-secret wizard choices so future humans and agents can understand how this
        workspace was initialized. Do not put credentials, API keys, access tokens, database passwords, private
        customer data, or model authentication artifacts in this directory.

        `manifest.json` lists the intended generated files and their hashes. Existing-file conflicts are preserved
        under timestamped `proposals/`; forced replacements are copied to timestamped `backups/` first.
        """
    )
    return data


def _manifest(config: ProjectConfig, files: dict[str, str]) -> str:
    payload = {
        "schema_version": 1,
        "kit_version": config.kit_version,
        "generated_at": config.created_at,
        "project_name": config.project_name,
        "files": {
            path: {"sha256": _sha256(content.encode("utf-8")), "executable": path in EXECUTABLE_FILES}
            for path, content in sorted(files.items())
            if path != ".agent-starter/manifest.json"
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def generate_project(
    config: ProjectConfig,
    *,
    force: bool = False,
    initialize_git: bool | None = None,
    dry_run: bool = False,
) -> GenerationReport:
    root = config.root
    _validate_config_safety(config)
    _assert_safe_root(root)
    report = GenerationReport(root=root)
    files = build_file_map(config)
    files[".agent-starter/manifest.json"] = _manifest(config, files)
    stamp = _timestamp()

    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)

    for relative_name, content in sorted(files.items()):
        rel = _safe_relative(relative_name)
        destination = root.joinpath(*rel.parts)
        _assert_no_symlink_parent(root, destination)
        data = content.encode("utf-8")
        mode = 0o755 if relative_name in EXECUTABLE_FILES else 0o644

        if not destination.exists() and not destination.is_symlink():
            report.created.append(relative_name)
            if not dry_run:
                _atomic_write(destination, data, mode)
            continue

        if destination.is_symlink() or not destination.is_file():
            report.conflicts.append(relative_name)
            report.warnings.append(f"Skipped non-regular existing path: {relative_name}")
            if not dry_run:
                proposal = root / ".agent-starter" / "proposals" / stamp / relative_name
                _assert_no_symlink_parent(root, proposal)
                _atomic_write(proposal, data, mode)
                report.proposals.append(str(proposal.relative_to(root)))
            continue

        existing = destination.read_bytes()
        if existing == data:
            report.unchanged.append(relative_name)
            if not dry_run and relative_name in EXECUTABLE_FILES:
                destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            continue

        if force:
            report.overwritten.append(relative_name)
            if not dry_run:
                backup = root / ".agent-starter" / "backups" / stamp / relative_name
                _assert_no_symlink_parent(root, backup)
                original_mode = stat.S_IMODE(destination.stat().st_mode)
                _atomic_write(backup, existing, original_mode)
                report.backups.append(str(backup.relative_to(root)))
                _atomic_write(destination, data, mode)
        else:
            report.conflicts.append(relative_name)
            if not dry_run:
                proposal = root / ".agent-starter" / "proposals" / stamp / relative_name
                _assert_no_symlink_parent(root, proposal)
                _atomic_write(proposal, data, mode)
                report.proposals.append(str(proposal.relative_to(root)))

    should_init = config.git_enabled if initialize_git is None else initialize_git
    if should_init and not dry_run and not (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "init", "-b", config.default_branch],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "init"], cwd=root, text=True, capture_output=True, check=False, timeout=30
                )
                if result.returncode == 0:
                    subprocess.run(
                        ["git", "branch", "-M", config.default_branch],
                        cwd=root,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
            report.git_initialized = result.returncode == 0
            if result.returncode != 0:
                report.warnings.append(f"Could not initialize Git: {(result.stderr or result.stdout).strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            report.warnings.append(f"Could not initialize Git: {exc}")

    if not dry_run:
        validation = validate_project(root)
        report.validation_errors.extend(validation.errors)
        report.validation_warnings.extend(validation.warnings)
    return report


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
            if data.get("schema_version") != 1:
                report.warnings.append("Unknown project.json schema version.")
            serialized = json.dumps(data).lower()
            for suspicious in ("access_token", "refresh_token", "client_secret", "api_key\": \"sk-", "password\":"):
                if suspicious in serialized:
                    report.errors.append("project.json appears to contain secret material; remove it and rotate exposed credentials.")
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
