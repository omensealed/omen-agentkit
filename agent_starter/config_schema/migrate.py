"""Ordered, non-destructive configuration migrations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

CURRENT_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class MigrationResult:
    data: dict[str, Any]
    source_version: int
    target_version: int
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _v1_to_v2(data: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    migrated = deepcopy(data)
    warnings: list[str] = []
    old_packages = migrated.pop("cachyos_packages", [])
    if old_packages:
        existing = migrated.get("extra_packages_by_provider", {})
        if not isinstance(existing, dict):
            existing = {}
        arch = existing.get("arch", [])
        if not isinstance(arch, list):
            arch = []
        existing["arch"] = list(dict.fromkeys([*arch, *old_packages]))
        migrated["extra_packages_by_provider"] = existing
        warnings.append(
            "v1 cachyos_packages were preserved only as extra_packages_by_provider.arch; "
            "they were not translated to another distribution."
        )
    migrated.setdefault("model_policy", {})
    migrated["schema_version"] = 2
    return migrated, tuple(warnings)


MIGRATIONS: dict[int, Callable[[dict[str, Any]], tuple[dict[str, Any], tuple[str, ...]]]] = {1: _v1_to_v2}


def migrate_config(data: dict[str, Any]) -> MigrationResult:
    """Return a migrated copy. The caller owns any explicit output write."""

    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object.")
    raw_version = data.get("schema_version", 1)
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise ValueError("schema_version must be an integer.")
    if raw_version < 1:
        raise ValueError("schema_version must be at least 1.")
    if raw_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version {raw_version} is newer than this AgentKit supports ({CURRENT_SCHEMA_VERSION})."
        )
    migrated = deepcopy(data)
    warnings: list[str] = []
    version = raw_version
    while version < CURRENT_SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No ordered migration is registered for schema version {version}.")
        migrated, step_warnings = migration(migrated)
        warnings.extend(step_warnings)
        version += 1
    return MigrationResult(migrated, raw_version, version, tuple(warnings))
