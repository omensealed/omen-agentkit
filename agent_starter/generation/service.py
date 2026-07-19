"""Confined project-generation orchestration with proposals and backups."""

from __future__ import annotations

import json
import stat
import subprocess
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

from ..config_schema import parse_config
from ..models import ProjectConfig
from .registry import EXECUTABLE_FILES, _manifest, build_file_map
from .safe_write import atomic_replace
from .validation import validate_project


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


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _safe_relative(value: str) -> PurePosixPath:
    rel = PurePosixPath(value)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError(f"Unsafe generated path: {value!r}")
    return rel


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


_atomic_write = atomic_replace


def _reuse_existing_generation_timestamps(config: ProjectConfig) -> ProjectConfig:
    """Keep regenerated managed files stable when only default timestamps differ."""

    metadata = config.root / ".agent-starter" / "project.json"
    if not metadata.is_file():
        return config
    try:
        data = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if not isinstance(data, dict):
        return config
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    if not isinstance(created_at, str) or not isinstance(updated_at, str):
        return config
    return replace(config, created_at=created_at, updated_at=updated_at)


def _apply_artifact(
    root: Path,
    relative_name: str,
    content: str,
    *,
    stamp: str,
    report: GenerationReport,
    force: bool,
    dry_run: bool,
    mark_mutated: Callable[[], None],
) -> None:
    rel = _safe_relative(relative_name)
    destination = root.joinpath(*rel.parts)
    _assert_no_symlink_parent(root, destination)
    data = content.encode("utf-8")
    mode = 0o755 if relative_name in EXECUTABLE_FILES else 0o644

    if not destination.exists() and not destination.is_symlink():
        report.created.append(relative_name)
        if not dry_run:
            _atomic_write(destination, data, mode)
            mark_mutated()
        return

    if destination.is_symlink() or not destination.is_file():
        report.conflicts.append(relative_name)
        report.warnings.append(f"Skipped non-regular existing path: {relative_name}")
        if not dry_run:
            proposal = root / ".agent-starter" / "proposals" / stamp / relative_name
            _assert_no_symlink_parent(root, proposal)
            _atomic_write(proposal, data, mode)
            mark_mutated()
            report.proposals.append(str(proposal.relative_to(root)))
        return

    existing = destination.read_bytes()
    if existing == data:
        report.unchanged.append(relative_name)
        if not dry_run and relative_name in EXECUTABLE_FILES:
            previous_mode = destination.stat().st_mode
            destination.chmod(previous_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if destination.stat().st_mode != previous_mode:
                mark_mutated()
        return

    if force:
        report.overwritten.append(relative_name)
        if not dry_run:
            backup = root / ".agent-starter" / "backups" / stamp / relative_name
            _assert_no_symlink_parent(root, backup)
            original_mode = stat.S_IMODE(destination.stat().st_mode)
            _atomic_write(backup, existing, original_mode)
            mark_mutated()
            report.backups.append(str(backup.relative_to(root)))
            _atomic_write(destination, data, mode)
            mark_mutated()
        return

    report.conflicts.append(relative_name)
    if not dry_run:
        proposal = root / ".agent-starter" / "proposals" / stamp / relative_name
        _assert_no_symlink_parent(root, proposal)
        _atomic_write(proposal, data, mode)
        mark_mutated()
        report.proposals.append(str(proposal.relative_to(root)))


def _initialize_git(
    root: Path,
    config: ProjectConfig,
    report: GenerationReport,
    mark_mutated: Callable[[], None],
) -> None:
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
    if (root / ".git").exists():
        mark_mutated()


def generate_project(
    config: ProjectConfig,
    *,
    force: bool = False,
    initialize_git: bool | None = None,
    dry_run: bool = False,
    _mutation_observer: Callable[[], None] | None = None,
) -> GenerationReport:
    def mark_mutated() -> None:
        if _mutation_observer is not None:
            try:
                _mutation_observer()
            except Exception:
                pass

    config = parse_config(config.to_dict()).config
    root = config.root
    _assert_safe_root(root)
    config = _reuse_existing_generation_timestamps(config)
    root = config.root
    report = GenerationReport(root=root)
    files = build_file_map(config)
    files[".agent-starter/manifest.json"] = _manifest(config, files)
    stamp = _timestamp()

    root_existed = root.exists() or root.is_symlink()
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
        if not root_existed:
            mark_mutated()

    for relative_name, content in sorted(files.items()):
        _apply_artifact(
            root,
            relative_name,
            content,
            stamp=stamp,
            report=report,
            force=force,
            dry_run=dry_run,
            mark_mutated=mark_mutated,
        )

    should_init = config.git_enabled if initialize_git is None else initialize_git
    if should_init and not dry_run and not (root / ".git").exists():
        _initialize_git(root, config, report, mark_mutated)

    if not dry_run:
        validation = validate_project(root)
        report.validation_errors.extend(validation.errors)
        report.validation_warnings.extend(validation.warnings)
    return report
