"""Shared beginner-facing UI metadata and GUI payload conversion."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import ProjectConfig, SandboxConfig
from .config_schema import parse_config
from .entry_modes import parse_entry_mode


SECRET_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\s*[:=]\s*\S+)|"
    r"\bsk-[A-Za-z0-9_-]{16,}\b"
)


GUI_PAGES: list[dict[str, object]] = [
    {"id": "welcome", "title": "Welcome"},
    {"id": "project", "title": "Project Mode And Folder"},
    {"id": "identity", "title": "Identity And Scope"},
    {"id": "targets", "title": "Users, Platforms, Packages"},
    {"id": "security", "title": "Security And Data"},
    {"id": "codex", "title": "Codex Setup"},
    {"id": "sandbox", "title": "Rootless Podman Sandbox"},
    {"id": "stack", "title": "Technology Stack"},
    {"id": "quality", "title": "Testing, Git, Automation"},
    {"id": "task", "title": "Task Composer"},
    {"id": "review", "title": "Review"},
    {"id": "generate", "title": "Generate"},
    {"id": "result", "title": "Result"},
]


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "agent-project"


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").replace("\n", ",").split(",")
    return [str(item).strip() for item in raw if str(item).strip()]


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("Boolean form fields must be true or false, not strings, numbers, lists, or objects.")


def _recursive_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_recursive_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(_recursive_strings(item))
        return result
    return []


def _reject_secrets(payload: dict[str, Any]) -> None:
    for value in _recursive_strings(payload):
        if SECRET_RE.search(value):
            raise ValueError("The GUI form appears to contain a credential or private key. Remove it and rotate it if it was real.")


def config_from_gui_payload(payload: dict[str, Any]) -> ProjectConfig:
    """Build a ProjectConfig from GUI form values without weakening CLI safety."""

    if not isinstance(payload, dict):
        raise ValueError("GUI payload must be an object.")
    parse_entry_mode(payload.get("entry_mode", "guided"))
    _reject_secrets(payload)
    project_name = str(payload.get("project_name") or "").strip()
    project_path = str(payload.get("project_path") or "").strip()
    if not project_name:
        raise ValueError("Project name is required.")
    if not project_path:
        raise ValueError("Project folder is required.")

    sandbox_mode = str(payload.get("sandbox_mode") or "toolchain").strip().lower()
    sandbox_image_profile = str(payload.get("sandbox_image_profile") or "arch-toolchain").strip().lower()
    if sandbox_image_profile not in {"arch-toolchain", "debian-toolchain"}:
        raise ValueError("Sandbox image profile must be arch-toolchain or debian-toolchain.")
    sandbox_enabled = _bool(payload.get("sandbox_enabled", True))
    if not sandbox_enabled:
        sandbox_mode = "none"
    if sandbox_mode not in {"none", "toolchain", "codex", "files-only"}:
        sandbox_mode = "toolchain" if sandbox_enabled else "none"
    sandbox = SandboxConfig.from_dict(
        {
            "enabled": sandbox_enabled and sandbox_mode != "none",
            "engine": "podman",
            "mode": sandbox_mode,
            "image_profile": sandbox_image_profile,
            "codex_inside_container": sandbox_mode == "codex",
            "rootless_required": True,
            "install_agentkit_skill": _bool(payload.get("codex_agentkit_skill", True)),
            "first_run_autonomous_prompt": _bool(payload.get("first_run_autonomous_prompt", False)),
            "gui_passthrough": _bool(payload.get("gui_passthrough", False)),
        }
    )
    arch_extra_packages = _string_list(payload.get("cachyos_packages"))

    config = ProjectConfig(
        project_name=project_name,
        project_slug=str(payload.get("project_slug") or _slugify(project_name)).strip(),
        project_path=str(Path(project_path).expanduser().resolve()),
        project_mode=str(payload.get("project_mode") or "new").strip().lower(),
        project_stage=str(payload.get("project_stage") or "idea").strip().lower(),
        project_type=str(payload.get("project_type") or "other").strip().lower(),
        description=str(payload.get("description") or "").strip(),
        goals=_string_list(payload.get("goals")),
        non_goals=_string_list(payload.get("non_goals")),
        target_users=str(payload.get("target_users") or "").strip(),
        target_platforms=_string_list(payload.get("target_platforms")) or ["cachyos-linux"],
        packaging_targets=_string_list(payload.get("packaging_targets")) or ["source checkout"],
        stack_strategy="manual",
        languages=_string_list(payload.get("languages")) or ["python"],
        stack_notes=str(payload.get("stack_notes") or "").strip(),
        minimal_dependencies=_bool(payload.get("minimal_dependencies", True)),
        database=str(payload.get("database") or "none").strip().lower(),
        database_notes=str(payload.get("database_notes") or "").strip(),
        network_access=_bool(payload.get("network_access", False)),
        user_accounts=_bool(payload.get("user_accounts", False)),
        handles_personal_data=_bool(payload.get("handles_personal_data", False)),
        handles_payments=_bool(payload.get("handles_payments", False)),
        security_notes=str(payload.get("security_notes") or "").strip(),
        primary_agent="codex",
        setup_agent_now=_bool(payload.get("setup_agent_now", False)),
        agent_sandbox="builtin-safe",
        use_ai_advisor=False,
        codex_agentkit_skill=_bool(payload.get("codex_agentkit_skill", True)),
        git_enabled=_bool(payload.get("git_enabled", True)),
        github_actions=_bool(payload.get("github_actions", False)),
        github_remote=str(payload.get("github_remote") or "later").strip().lower(),
        default_branch=str(payload.get("default_branch") or "main").strip() or "main",
        license_name=str(payload.get("license_name") or "AGPL-3.0-or-later").strip(),
        tests=_string_list(payload.get("tests")) or ["unit", "integration"],
        browser_tests=_bool(payload.get("browser_tests", False)),
        quality_checks=_string_list(payload.get("quality_checks")) or ["format", "lint", "tests"],
        extra_packages_by_provider={"arch": arch_extra_packages} if arch_extra_packages else {},
        open_questions=_string_list(payload.get("open_questions")),
        sandbox=sandbox,
    )
    if config.project_mode not in {"new", "existing"}:
        raise ValueError("Project mode must be new or existing.")
    if config.database not in {"none", "sqlite", "mariadb", "postgresql", "existing", "undecided"}:
        raise ValueError("Database must be none, sqlite, mariadb, postgresql, existing, or undecided.")
    return parse_config(config.to_dict()).config
