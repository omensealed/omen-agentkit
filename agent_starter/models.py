"""Data models for the CLI AI Agent Starter Kit.

The package intentionally uses only the Python standard library so a stock
CachyOS Python installation can run it without bootstrapping dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    """Return a stable, timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AdvisorRecommendation:
    """A structured stack recommendation returned by an AI agent or fallback."""

    summary: str = ""
    languages: list[str] = field(default_factory=list)
    database: str = "undecided"
    architecture: str = ""
    toolchain_packages: list[str] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    lint_commands: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    source: str = "none"
    raw_output: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source: str, raw_output: str = "") -> "AdvisorRecommendation":
        def clean_text(value: Any, limit: int = 4000) -> str:
            text = str(value).replace("\x00", "").strip()
            text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
            return text[:limit]

        def string_list(name: str, *, item_limit: int = 1000, count_limit: int = 30) -> list[str]:
            value = data.get(name, [])
            raw_items = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            result: list[str] = []
            for item in raw_items[:count_limit]:
                cleaned = clean_text(item, item_limit)
                if cleaned:
                    result.append(cleaned)
            return result

        return cls(
            summary=clean_text(data.get("summary", ""), 2000),
            languages=string_list("languages", item_limit=80, count_limit=10),
            database=clean_text(data.get("database", "undecided"), 80) or "undecided",
            architecture=clean_text(data.get("architecture", ""), 6000),
            toolchain_packages=string_list("toolchain_packages", item_limit=160),
            setup_commands=string_list("setup_commands", item_limit=1000),
            build_commands=string_list("build_commands", item_limit=1000),
            test_commands=string_list("test_commands", item_limit=1000),
            lint_commands=string_list("lint_commands", item_limit=1000),
            rationale=string_list("rationale", item_limit=2000),
            risks=string_list("risks", item_limit=2000),
            questions=string_list("questions", item_limit=2000),
            source=clean_text(source, 100),
            raw_output=raw_output[:100_000],
        )



@dataclass(slots=True)
class SandboxConfig:
    """Optional rootless Podman sandbox configuration for generated projects."""

    enabled: bool = False
    engine: str = "podman"
    mode: str = "none"  # none | toolchain | codex | files-only
    codex_inside_container: bool = False
    rootless_required: bool = True
    install_agentkit_skill: bool = True
    first_run_autonomous_prompt: bool = False
    gui_passthrough: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SandboxConfig":
        if not isinstance(data, dict):
            return cls()
        allowed = cls.__dataclass_fields__
        kwargs = {name: data[name] for name in allowed if name in data}
        config = cls(**kwargs)
        config.engine = str(config.engine or "podman").strip().lower()
        config.mode = str(config.mode or "none").strip().lower()
        if config.mode not in {"none", "toolchain", "codex", "files-only"}:
            config.mode = "none"
        if config.engine != "podman":
            config.engine = "podman"
        config.enabled = bool(config.enabled and config.mode != "none")
        config.codex_inside_container = bool(config.codex_inside_container or config.mode == "codex")
        if config.codex_inside_container:
            config.mode = "codex"
            config.enabled = True
        return config


@dataclass(slots=True)
class ProjectConfig:
    """Answers collected by the wizard and persisted with generated projects."""

    schema_version: int = SCHEMA_VERSION
    kit_version: str = "0.4.8"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    project_name: str = ""
    project_slug: str = ""
    project_path: str = ""
    project_mode: str = "new"  # new | existing
    project_stage: str = "idea"  # idea | prototype | active | renovation
    project_type: str = "other"
    description: str = ""
    goals: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    target_users: str = ""
    target_platforms: list[str] = field(default_factory=list)
    packaging_targets: list[str] = field(default_factory=list)

    stack_strategy: str = "manual"  # manual | ai
    languages: list[str] = field(default_factory=list)
    stack_notes: str = ""
    minimal_dependencies: bool = True
    database: str = "none"
    database_notes: str = ""
    network_access: bool = False
    user_accounts: bool = False
    handles_personal_data: bool = False
    handles_payments: bool = False
    security_notes: str = ""

    primary_agent: str = "codex"
    setup_agent_now: bool = True
    agent_sandbox: str = "builtin-safe"
    use_ai_advisor: bool = False
    codex_agentkit_skill: bool = True

    git_enabled: bool = True
    github_actions: bool = False
    github_remote: str = "later"  # none | later | create-private | create-public
    default_branch: str = "main"
    license_name: str = "AGPL-3.0-or-later"

    tests: list[str] = field(default_factory=lambda: ["unit", "integration"])
    browser_tests: bool = False
    quality_checks: list[str] = field(default_factory=lambda: ["format", "lint", "tests"])
    custom_setup_commands: list[str] = field(default_factory=list)
    custom_build_commands: list[str] = field(default_factory=list)
    custom_test_commands: list[str] = field(default_factory=list)
    custom_lint_commands: list[str] = field(default_factory=list)
    cachyos_packages: list[str] = field(default_factory=list)

    open_questions: list[str] = field(default_factory=list)
    advisor: AdvisorRecommendation = field(default_factory=AdvisorRecommendation)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        fields = cls.__dataclass_fields__
        kwargs: dict[str, Any] = {}
        for name in fields:
            if name == "advisor":
                advisor_data = data.get("advisor", {})
                if isinstance(advisor_data, dict):
                    kwargs[name] = AdvisorRecommendation.from_dict(
                        advisor_data,
                        source=str(advisor_data.get("source", "saved")),
                        raw_output=str(advisor_data.get("raw_output", "")),
                    )
                continue
            if name == "sandbox":
                kwargs[name] = SandboxConfig.from_dict(data.get("sandbox"))
                continue
            if name in data:
                kwargs[name] = data[name]
        return cls(**kwargs)

    @property
    def root(self) -> Path:
        return Path(self.project_path).expanduser().resolve()
