"""Data models for the CLI AI Agent Starter Kit.

The package intentionally uses only the Python standard library so a stock
CachyOS Python installation can run it without bootstrapping dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .model_policy import CodexModelPolicy

SCHEMA_VERSION = 2


def utc_now_iso() -> str:
    """Return a stable, timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AdvisorCapability:
    """Untrusted capability intent returned by an advisor; never executable."""

    capability_id: str
    purpose: str
    requirement: str
    rationale: str
    confidence: str


@dataclass(slots=True)
class AdvisorRecommendation:
    """A structured stack recommendation returned by an AI agent or fallback."""

    summary: str = ""
    languages: list[str] = field(default_factory=list)
    database: str = "undecided"
    architecture: str = ""
    recommended_capabilities: list[AdvisorCapability] = field(default_factory=list)
    architecture_notes: list[str] = field(default_factory=list)
    toolchain_capabilities: list[str] = field(default_factory=list)
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

    @property
    def review_mode(self) -> str:
        """Classify provenance conservatively without inferring AI review."""

        source = self.source.strip().lower()
        if source == "local-fallback":
            return "local-default"
        if source == "codex-cache":
            return "ai-reviewed-cache"
        if source in {"", "none", "manual-seed"}:
            return "local-manual"
        if source == "saved":
            return "saved-unknown"
        return "ai-reviewed"

    @property
    def review_label(self) -> str:
        return {
            "local-default": "Local deterministic default — not AI-reviewed",
            "local-manual": "Local manual selection — not AI-reviewed",
            "saved-unknown": "Saved recommendation — AI review not established",
            "ai-reviewed": "AI-reviewed structured recommendation",
            "ai-reviewed-cache": "Cached AI-reviewed structured recommendation",
        }[self.review_mode]

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

        def capability_list() -> list[AdvisorCapability]:
            value = data.get("recommended_capabilities", [])
            if not isinstance(value, list):
                return []
            result: list[AdvisorCapability] = []
            for item in value[:30]:
                if not isinstance(item, dict):
                    continue
                capability_id = clean_text(item.get("capability_id", ""), 80)
                if not capability_id:
                    continue
                result.append(AdvisorCapability(
                    capability_id=capability_id,
                    purpose=clean_text(item.get("purpose", ""), 500),
                    requirement=clean_text(item.get("requirement", "optional"), 20),
                    rationale=clean_text(item.get("rationale", ""), 2000),
                    confidence=clean_text(item.get("confidence", "low"), 20),
                ))
            return result

        return cls(
            summary=clean_text(data.get("summary", ""), 2000),
            languages=string_list("languages", item_limit=80, count_limit=10),
            database=clean_text(data.get("database", "undecided"), 80) or "undecided",
            architecture=clean_text(data.get("architecture", ""), 6000),
            recommended_capabilities=capability_list(),
            architecture_notes=string_list("architecture_notes", item_limit=2000, count_limit=20),
            toolchain_capabilities=string_list("toolchain_capabilities", item_limit=80),
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


class CapabilityDecisionState(str, Enum):
    """Human decision state; never an instruction to install or execute."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CHALLENGED = "challenged"


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    """Project-owned capability choice kept separate from advisor output."""

    capability_id: str
    decision: CapabilityDecisionState
    requirement: str
    limitation: str = ""

    def __post_init__(self) -> None:
        from .capabilities import CAPABILITY_CATALOG

        if self.capability_id not in CAPABILITY_CATALOG:
            raise ValueError("capability decision must use a canonical capability ID.")
        if not isinstance(self.decision, CapabilityDecisionState):
            raise TypeError("capability decision must be a CapabilityDecisionState.")
        if self.requirement not in {"required", "optional"}:
            raise ValueError("capability decision requirement must be required or optional.")
        if not isinstance(self.limitation, str) or "\x00" in self.limitation or len(self.limitation) > 1000:
            raise ValueError("capability decision limitation must be bounded text without NUL bytes.")
        if self.requirement == "required" and self.decision is CapabilityDecisionState.REJECTED:
            raise ValueError("required capabilities must be accepted or challenged.")
        if self.requirement == "optional" and self.decision is CapabilityDecisionState.CHALLENGED:
            raise ValueError("optional capabilities must be accepted or rejected.")
        if self.decision is CapabilityDecisionState.CHALLENGED and not self.limitation.strip():
            raise ValueError("a challenged required capability must explain the resulting limitation.")
        if self.decision is not CapabilityDecisionState.CHALLENGED and self.limitation:
            raise ValueError("only challenged capabilities may carry a limitation.")



@dataclass(slots=True)
class SandboxConfig:
    """Optional rootless Podman sandbox configuration for generated projects."""

    enabled: bool = False
    engine: str = "podman"
    mode: str = "none"  # none | toolchain | codex | files-only
    image_profile: str = "arch-toolchain"  # arch-toolchain | debian-toolchain
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
        for name in (
            "enabled", "codex_inside_container", "rootless_required", "install_agentkit_skill",
            "first_run_autonomous_prompt", "gui_passthrough",
        ):
            if name in kwargs and not isinstance(kwargs[name], bool):
                raise ValueError(f"sandbox.{name} must be a JSON boolean.")
        config = cls(**kwargs)
        config.engine = str(config.engine or "podman").strip().lower()
        config.mode = str(config.mode or "none").strip().lower()
        config.image_profile = str(config.image_profile or "arch-toolchain").strip().lower()
        if config.mode not in {"none", "toolchain", "codex", "files-only"}:
            config.mode = "none"
        if config.engine != "podman":
            config.engine = "podman"
        if config.image_profile not in {"arch-toolchain", "debian-toolchain"}:
            config.image_profile = "arch-toolchain"
        config.enabled = config.enabled and config.mode != "none"
        config.codex_inside_container = config.codex_inside_container or config.mode == "codex"
        if config.codex_inside_container:
            config.mode = "codex"
            config.enabled = True
        return config


@dataclass(slots=True)
class ProjectConfig:
    """Answers collected by the wizard and persisted with generated projects."""

    schema_version: int = SCHEMA_VERSION
    kit_version: str = "0.5.5"
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
    model_policy: CodexModelPolicy = field(default_factory=CodexModelPolicy)

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
    extra_packages_by_provider: dict[str, list[str]] = field(default_factory=dict)

    open_questions: list[str] = field(default_factory=list)
    advisor: AdvisorRecommendation = field(default_factory=AdvisorRecommendation)
    capability_decisions: list[CapabilityDecision] = field(default_factory=list)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        from .config_schema import parse_config

        return parse_config(data).config

    @property
    def arch_extra_packages(self) -> list[str]:
        """Return Arch-family-only extras, including the deprecated v1 field."""

        return list(dict.fromkeys([*self.extra_packages_by_provider.get("arch", []), *self.cachyos_packages]))

    @property
    def root(self) -> Path:
        return Path(self.project_path).expanduser().resolve()
