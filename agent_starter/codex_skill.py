"""Managed repo-local Agent Kit Codex skill files."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SKILL_NAME = "agentkit"
SKILL_VERSION = "0.1.0"
AGENT_STARTER_MIN_VERSION = "0.3.0"
SKILL_DIR = Path(".agents") / "skills" / SKILL_NAME
SKILL_MD = SKILL_DIR / "SKILL.md"
SKILL_META = SKILL_DIR / "agentkit-skill.json"


@dataclass(slots=True)
class SkillStatus:
    root: Path
    exists: bool
    managed: bool
    installed_version: str | None
    bundled_version: str
    update_available: bool
    path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_skill_md() -> str:
    return f"""---
name: agentkit
description: Use Agent Kit to turn short feature, fix, planning, review, test, refactor, or docs requests into full safe Codex implementation prompts for this generated project.
---

# Agent Kit skill

Agent Kit skill version: {SKILL_VERSION}

Use this skill when the user invokes `$agentkit ...` or asks Agent Kit to plan, implement, fix, review, test, refactor, or document work in this repository.

Treat the user's short request as an idea, not as the complete task brief.

## Workflow

1. Inspect the current repository state.
2. Read `AGENTS.md`.
3. Read `.agent-starter/project.json` if present.
4. Read `docs/11-IMPLEMENTATION-NOTES.md` if present.
5. Parse the user request into a mode and idea.
6. Run Agent Kit's prompt builder with safe argument handling, not shell interpolation:
   `agent-starter idea-prompt --from-codex --arguments <user request> --json`
7. Read the generated prompt file from the returned `prompt_path`.
8. Follow that generated prompt as the authoritative task brief.

## Safety

- Do not inspect Codex credentials.
- Do not start `codex login`.
- Do not bypass approvals or sandboxing.
- Do not push to GitHub or create remote resources without explicit user approval.
- Do not overwrite user work.
- Do not run package installs unless the generated project allows it and the user approves.
- Always update implementation notes after meaningful work.

## Final response

Report generated prompt path, files changed, tests run, result, documentation updated, and unresolved decisions.
"""


def render_skill_metadata(*, installed_at: str | None = None, updated_at: str | None = None) -> str:
    now = utc_now()
    payload = {
        "name": SKILL_NAME,
        "skill_version": SKILL_VERSION,
        "agent_starter_min_version": AGENT_STARTER_MIN_VERSION,
        "installed_by": "agent-starter",
        "managed": True,
        "installed_at": installed_at or now,
        "updated_at": updated_at or now,
        "prompt_builder_command": "agent-starter idea-prompt",
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def skill_files(*, installed_at: str | None = None, updated_at: str | None = None) -> dict[str, str]:
    return {
        str(SKILL_MD): render_skill_md(),
        str(SKILL_META): render_skill_metadata(installed_at=installed_at, updated_at=updated_at),
    }


def _atomic_write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def inspect_skill(root: Path) -> SkillStatus:
    root = root.expanduser().resolve()
    directory = root / SKILL_DIR
    metadata = root / SKILL_META
    exists = directory.exists()
    managed = False
    installed_version: str | None = None
    if metadata.is_file():
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            managed = data.get("name") == SKILL_NAME and data.get("installed_by") == "agent-starter" and data.get("managed") is True
            version = data.get("skill_version")
            installed_version = str(version) if version is not None else None
    update_available = managed and installed_version != SKILL_VERSION
    return SkillStatus(
        root=root,
        exists=exists,
        managed=managed,
        installed_version=installed_version,
        bundled_version=SKILL_VERSION,
        update_available=update_available,
        path=directory,
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup_skill(root: Path) -> Path | None:
    directory = root / SKILL_DIR
    if not directory.exists():
        return None
    destination = root / ".agent-starter" / "backups" / _timestamp() / str(SKILL_DIR)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if directory.is_dir() and not directory.is_symlink():
        shutil.copytree(directory, destination)
    else:
        shutil.copy2(directory, destination)
    return destination


def write_skill(root: Path, *, preserve_installed_at: bool = True) -> list[Path]:
    root = root.expanduser().resolve()
    current_installed_at: str | None = None
    metadata = root / SKILL_META
    if preserve_installed_at and metadata.is_file():
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("installed_at"), str):
                current_installed_at = data["installed_at"]
        except (OSError, json.JSONDecodeError):
            current_installed_at = None
    written: list[Path] = []
    for relative, content in skill_files(installed_at=current_installed_at).items():
        path = root / relative
        _atomic_write(path, content)
        written.append(path)
    return written


def install_skill(root: Path, *, yes: bool = False, force: bool = False) -> tuple[str, list[Path], Path | None]:
    status = inspect_skill(root)
    if status.exists and not status.managed and not force:
        raise ValueError("A non-managed .agents/skills/agentkit skill already exists. Refusing to overwrite it without --force.")
    if status.exists and status.managed:
        if not yes:
            raise ValueError("Agent Kit skill is already installed. Re-run with --yes to update managed files.")
        backup = backup_skill(status.root)
        return "updated", write_skill(status.root), backup
    if status.exists and force:
        backup = backup_skill(status.root)
        return "replaced", write_skill(status.root, preserve_installed_at=False), backup
    return "installed", write_skill(status.root, preserve_installed_at=False), None


def update_skill(root: Path, *, yes: bool = False) -> tuple[str, list[Path], Path | None]:
    status = inspect_skill(root)
    if not status.exists:
        raise ValueError("Agent Kit skill is not installed.")
    if not status.managed:
        raise ValueError("Existing agentkit skill is not Agent Kit-managed; refusing to update user-owned content.")
    if not yes:
        raise ValueError("Updating managed skill files requires --yes.")
    backup = backup_skill(status.root)
    return "updated", write_skill(status.root), backup


def uninstall_skill(root: Path, *, force: bool = False) -> tuple[str, Path | None]:
    status = inspect_skill(root)
    if not status.exists:
        return "missing", None
    if not status.managed and not force:
        raise ValueError("Existing agentkit skill is not Agent Kit-managed; refusing to delete user-owned content.")
    backup = backup_skill(status.root)
    target = status.root / SKILL_DIR
    if force and target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    elif force:
        target.unlink()
    else:
        for relative in (SKILL_MD, SKILL_META):
            path = status.root / relative
            if path.exists() and not path.is_dir():
                path.unlink()
        try:
            target.rmdir()
        except OSError:
            pass
    return "removed", backup
