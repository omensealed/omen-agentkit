"""Strict canonical parser shared by files, CLI, GUI, and generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..capabilities import select_capabilities, unknown_capability_ids
from ..model_policy import CodexModelPolicy
from ..models import (
    AdvisorRecommendation,
    CapabilityDecision,
    CapabilityDecisionState,
    ProjectConfig,
    SandboxConfig,
)
from .migrate import migrate_config


PACKAGE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+:-]{0,159}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")

BOOL_FIELDS = {
    "minimal_dependencies", "network_access", "user_accounts", "handles_personal_data",
    "handles_payments", "setup_agent_now", "use_ai_advisor", "codex_agentkit_skill",
    "git_enabled", "github_actions", "browser_tests",
}
LIST_FIELDS = {
    "goals", "non_goals", "target_platforms", "packaging_targets", "languages", "tests",
    "quality_checks", "custom_setup_commands", "custom_build_commands", "custom_test_commands",
    "custom_lint_commands", "cachyos_packages", "open_questions",
}
ENUM_FIELDS: dict[str, set[str]] = {
    "project_mode": {"new", "existing"},
    "project_stage": {"idea", "prototype", "active", "renovation"},
    "stack_strategy": {"manual", "ai"},
    "database": {"none", "sqlite", "mariadb", "postgresql", "existing", "undecided"},
    "primary_agent": {"codex"},
    "agent_sandbox": {"builtin-safe"},
    "github_remote": {"none", "later", "create-private", "create-public"},
}
SANDBOX_BOOL_FIELDS = {
    "enabled", "codex_inside_container", "rootless_required", "install_agentkit_skill",
    "first_run_autonomous_prompt", "gui_passthrough",
}
CUSTOM_COMMAND_FIELDS = {
    "custom_setup_commands", "custom_build_commands", "custom_test_commands", "custom_lint_commands"
}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    code: str
    message: str
    remedy: str
    severity: str = "error"


class ConfigValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))


@dataclass(frozen=True, slots=True)
class ConfigParseResult:
    config: ProjectConfig
    issues: tuple[ValidationIssue, ...] = ()
    source_version: int = 2


def validate_package_identifier(value: str, *, path: str = "package") -> ValidationIssue | None:
    if not PACKAGE_IDENTIFIER_RE.fullmatch(value) or value.startswith("-"):
        return ValidationIssue(
            path, "invalid_package_identifier", "Package identifiers may contain only safe package-name characters.",
            "Use the exact selected-provider package name without options, spaces, or shell syntax.",
        )
    return None


def validate_custom_command(value: str, *, path: str = "command") -> ValidationIssue | None:
    if not value.strip():
        return ValidationIssue(path, "empty_command", "Custom commands must not be empty.", "Remove the item or enter one reviewed command.")
    if "\x00" in value or len(value) > 2000:
        return ValidationIssue(path, "invalid_command", "Custom command text is malformed or too long.", "Use a reviewed command of at most 2000 characters without NUL bytes.")
    return None


def has_custom_commands(config: ProjectConfig) -> bool:
    return any(getattr(config, name) for name in CUSTOM_COMMAND_FIELDS)


def _issue(path: str, code: str, message: str, remedy: str) -> ValidationIssue:
    return ValidationIssue(path, code, message, remedy)


def _strict_bool(value: Any, path: str, issues: list[ValidationIssue]) -> bool:
    if isinstance(value, bool):
        return value
    issues.append(_issue(path, "invalid_boolean", "Expected a JSON boolean, not a string, number, list, or object.", "Use true or false without quotes."))
    return False


def _strict_string(value: Any, path: str, issues: list[ValidationIssue], *, limit: int = 10_000) -> str:
    if not isinstance(value, str):
        issues.append(_issue(path, "invalid_string", "Expected text.", "Use a JSON string."))
        return ""
    if "\x00" in value or len(value) > limit:
        issues.append(_issue(path, "invalid_string", f"Text must be at most {limit} characters and contain no NUL bytes.", "Shorten the value and remove binary/control content."))
        return ""
    return value.strip()


def _string_list(value: Any, path: str, issues: list[ValidationIssue], *, limit: int = 100) -> list[str]:
    if not isinstance(value, list):
        issues.append(_issue(path, "invalid_list", "Expected a JSON list of strings.", "Use an array such as [\"item\"]."))
        return []
    if len(value) > limit:
        issues.append(_issue(path, "list_too_long", f"At most {limit} items are allowed.", "Remove unnecessary items."))
    result: list[str] = []
    for index, item in enumerate(value[:limit]):
        text = _strict_string(item, f"{path}[{index}]", issues, limit=2000)
        if text:
            result.append(text)
    return result


def _parse_sandbox(value: Any, issues: list[ValidationIssue]) -> SandboxConfig:
    if not isinstance(value, dict):
        issues.append(_issue("sandbox", "invalid_object", "Sandbox configuration must be an object.", "Use a JSON object with documented sandbox fields."))
        return SandboxConfig()
    unknown = sorted(set(value) - set(SandboxConfig.__dataclass_fields__))
    for name in unknown:
        issues.append(ValidationIssue(f"sandbox.{name}", "unknown_field", "Unknown sandbox field was ignored.", "Remove it or use a documented field.", "warning"))
    parsed: dict[str, Any] = {}
    for name in SANDBOX_BOOL_FIELDS:
        if name in value:
            parsed[name] = _strict_bool(value[name], f"sandbox.{name}", issues)
    engine = _strict_string(value.get("engine", "podman"), "sandbox.engine", issues, limit=40)
    mode = _strict_string(value.get("mode", "none"), "sandbox.mode", issues, limit=40)
    image_profile = _strict_string(
        value.get("image_profile", "arch-toolchain"), "sandbox.image_profile", issues, limit=40
    )
    if engine != "podman":
        issues.append(_issue("sandbox.engine", "invalid_enum", "Only rootless Podman is supported.", "Set sandbox.engine to \"podman\"."))
    if mode not in {"none", "toolchain", "codex", "files-only"}:
        issues.append(_issue("sandbox.mode", "invalid_enum", "Unknown sandbox mode.", "Use none, toolchain, codex, or files-only."))
        mode = "none"
    if image_profile not in {"arch-toolchain", "debian-toolchain"}:
        issues.append(_issue(
            "sandbox.image_profile",
            "invalid_enum",
            "Unknown sandbox image profile.",
            "Use arch-toolchain or debian-toolchain; choose independently from the host provider.",
        ))
        image_profile = "arch-toolchain"
    parsed.update(engine="podman", mode=mode, image_profile=image_profile)
    config = SandboxConfig(**parsed)
    if config.codex_inside_container:
        config.mode = "codex"
        config.enabled = True
    elif config.mode == "none":
        config.enabled = False
    return config


def _parse_capability_decisions(
    value: Any,
    issues: list[ValidationIssue],
    *,
    required_capability_ids: tuple[str, ...],
) -> list[CapabilityDecision]:
    path = "capability_decisions"
    if not isinstance(value, list):
        issues.append(_issue(path, "invalid_list", "Capability decisions must be a JSON list.", "Use an array of documented decision objects."))
        return []
    if len(value) > 50:
        issues.append(_issue(path, "list_too_long", "At most 50 capability decisions are allowed.", "Remove duplicate or obsolete decisions."))
    result: list[CapabilityDecision] = []
    seen: set[str] = set()
    expected = {"capability_id", "decision", "requirement", "limitation"}
    for index, item in enumerate(value[:50]):
        item_path = f"{path}[{index}]"
        before = len(issues)
        if not isinstance(item, dict):
            issues.append(_issue(item_path, "invalid_object", "A capability decision must be an object.", "Use the documented capability decision fields."))
            continue
        for name in sorted(set(item) - expected):
            issues.append(_issue(f"{item_path}.{name}", "unknown_field", "Unknown capability decision field.", "Remove the field."))
        for name in sorted(expected - set(item)):
            issues.append(_issue(f"{item_path}.{name}", "missing_field", "Required capability decision field is missing.", f"Add {name}."))
        capability_id = _strict_string(item.get("capability_id", ""), f"{item_path}.capability_id", issues, limit=80)
        decision = _strict_string(item.get("decision", ""), f"{item_path}.decision", issues, limit=20)
        requirement = _strict_string(item.get("requirement", ""), f"{item_path}.requirement", issues, limit=20)
        limitation = _strict_string(item.get("limitation", ""), f"{item_path}.limitation", issues, limit=1000)
        if unknown_capability_ids((capability_id,)):
            issues.append(_issue(f"{item_path}.capability_id", "invalid_capability", f"Unknown capability {capability_id!r}.", "Use an ID from the canonical capability catalog."))
        if capability_id in seen:
            issues.append(_issue(f"{item_path}.capability_id", "duplicate_capability", "Capability decisions must be unique.", "Keep only the latest reviewed decision for this capability."))
        if decision not in {item.value for item in CapabilityDecisionState}:
            issues.append(_issue(f"{item_path}.decision", "invalid_decision", "Unknown capability decision state.", "Use accepted, rejected, or challenged."))
        if requirement not in {"required", "optional"}:
            issues.append(_issue(f"{item_path}.requirement", "invalid_enum", "Requirement must be required or optional.", "Use required or optional."))
        if capability_id in required_capability_ids and requirement != "required":
            issues.append(_issue(
                f"{item_path}.requirement",
                "invalid_requirement",
                "The deterministic project baseline marks this capability required.",
                "Mark it required, then use accepted or challenged so limitations stay visible.",
            ))
        if requirement == "required" and decision == "rejected":
            issues.append(_issue(f"{item_path}.decision", "invalid_decision", "A required capability must be accepted or challenged.", "Use challenged and record the resulting limitation."))
        if requirement == "optional" and decision == "challenged":
            issues.append(_issue(f"{item_path}.decision", "invalid_decision", "An optional capability must be accepted or rejected.", "Use accepted or rejected."))
        if decision == "challenged" and not limitation:
            issues.append(_issue(f"{item_path}.limitation", "missing_limitation", "A challenged required capability needs a limitation explanation.", "Explain what will not work without this capability."))
        if decision != "challenged" and limitation:
            issues.append(_issue(f"{item_path}.limitation", "unexpected_limitation", "Only a challenged capability may have a limitation.", "Clear the limitation or mark the required capability challenged."))
        if len(issues) == before:
            result.append(CapabilityDecision(
                capability_id,
                CapabilityDecisionState(decision),
                requirement,
                limitation,
            ))
            seen.add(capability_id)
    return result


def parse_config(data: dict[str, Any]) -> ConfigParseResult:
    """Migrate and strictly parse configuration, raising structured issues on errors."""

    try:
        migration = migrate_config(data)
    except ValueError as exc:
        raise ConfigValidationError([_issue("schema_version", "migration_error", str(exc), "Use a supported v1 or v2 answers object and write migrated output separately.")]) from exc
    raw = migration.data
    issues: list[ValidationIssue] = [
        ValidationIssue("schema_version", "migration_notice", warning, "Review the migrated output before using it.", "warning")
        for warning in migration.warnings
    ]
    fields = ProjectConfig.__dataclass_fields__
    for name in sorted(set(raw) - set(fields)):
        issues.append(ValidationIssue(name, "unknown_field", "Unknown configuration field was ignored.", "Remove it or retain it in an external extension document.", "warning"))
    kwargs: dict[str, Any] = {"schema_version": 2}
    for name in fields:
        if name not in raw or name in {
            "schema_version", "advisor", "capability_decisions", "sandbox", "model_policy",
            "extra_packages_by_provider",
        }:
            continue
        value = raw[name]
        if name in BOOL_FIELDS:
            kwargs[name] = _strict_bool(value, name, issues)
        elif name in LIST_FIELDS:
            kwargs[name] = _string_list(value, name, issues)
        elif name in {"kit_version", "created_at", "updated_at", "project_name", "project_slug", "project_path", "project_mode", "project_stage", "project_type", "description", "target_users", "stack_strategy", "stack_notes", "database", "database_notes", "security_notes", "primary_agent", "agent_sandbox", "github_remote", "default_branch", "license_name"}:
            kwargs[name] = _strict_string(value, name, issues)
        else:
            kwargs[name] = value
    for name, choices in ENUM_FIELDS.items():
        if name in kwargs and kwargs[name] not in choices:
            issues.append(_issue(name, "invalid_enum", f"Unsupported value {kwargs[name]!r}.", f"Use one of: {', '.join(sorted(choices))}."))
    if "default_branch" in kwargs and not BRANCH_RE.fullmatch(kwargs["default_branch"]):
        issues.append(_issue("default_branch", "invalid_identifier", "Default branch contains unsafe or unsupported characters.", "Use a simple Git branch name without spaces or shell syntax."))
    project_path = kwargs.get("project_path", "")
    if project_path and ("\x00" in project_path or not Path(project_path).parts):
        issues.append(_issue("project_path", "invalid_path", "Project path is malformed.", "Choose a normal project directory path."))

    kwargs["sandbox"] = _parse_sandbox(raw.get("sandbox", {}), issues)
    advisor_data = raw.get("advisor", {})
    if not isinstance(advisor_data, dict):
        issues.append(_issue("advisor", "invalid_object", "Advisor data must be an object.", "Use an object or remove advisor data."))
        advisor_data = {}
    advisor_capabilities = _string_list(
        advisor_data.get("toolchain_capabilities", []),
        "advisor.toolchain_capabilities",
        issues,
        limit=50,
    )
    legacy_advisor = AdvisorRecommendation.from_dict(
        advisor_data, source=str(advisor_data.get("source", "saved")), raw_output=str(advisor_data.get("raw_output", ""))
    )
    legacy_advisor.toolchain_capabilities = advisor_capabilities
    kwargs["advisor"] = legacy_advisor
    if "recommended_capabilities" in advisor_data and advisor_data.get("summary"):
        from ..agents import AgentError, parse_advisor_response

        live_fields = (
            "summary", "languages", "database", "recommended_capabilities",
            "architecture_notes", "questions", "risks",
        )
        payload = {name: advisor_data.get(name, []) for name in live_fields}
        try:
            parsed_advisor = parse_advisor_response(
                payload,
                source=str(advisor_data.get("source", "saved")),
                raw_output=str(advisor_data.get("raw_output", "")),
            )
        except AgentError as exc:
            issues.append(_issue(
                "advisor",
                "invalid_advisor_response",
                str(exc),
                "Use the documented bounded capability-first advisor fields or remove malformed advisor data.",
            ))
        else:
            parsed_advisor.toolchain_packages = legacy_advisor.toolchain_packages
            parsed_advisor.setup_commands = legacy_advisor.setup_commands
            parsed_advisor.build_commands = legacy_advisor.build_commands
            parsed_advisor.test_commands = legacy_advisor.test_commands
            parsed_advisor.lint_commands = legacy_advisor.lint_commands
            if not parsed_advisor.toolchain_capabilities:
                parsed_advisor.toolchain_capabilities = legacy_advisor.toolchain_capabilities
            if not parsed_advisor.architecture:
                parsed_advisor.architecture = legacy_advisor.architecture
            kwargs["advisor"] = parsed_advisor
    for index, capability_id in enumerate(kwargs["advisor"].toolchain_capabilities):
        if unknown_capability_ids((capability_id,)):
            issues.append(_issue(
                f"advisor.toolchain_capabilities[{index}]",
                "invalid_capability",
                f"Unknown toolchain capability {capability_id!r}.",
                "Use a capability ID from the canonical AgentKit catalog.",
            ))
    required_capability_ids = select_capabilities(
        kwargs.get("languages", []),
        kwargs.get("database", "none"),
        github=kwargs.get("github_actions", False),
        rootless_podman=kwargs["sandbox"].enabled,
    )
    kwargs["capability_decisions"] = _parse_capability_decisions(
        raw.get("capability_decisions", []),
        issues,
        required_capability_ids=required_capability_ids,
    )
    try:
        kwargs["model_policy"] = CodexModelPolicy.from_dict(raw.get("model_policy", {}))
    except (TypeError, ValueError) as exc:
        issues.append(_issue("model_policy", "invalid_model_policy", str(exc), "Use explicit Sol/medium, a reviewed explicit override, or selection=inherit."))
        kwargs["model_policy"] = CodexModelPolicy()

    extras = raw.get("extra_packages_by_provider", {})
    parsed_extras: dict[str, list[str]] = {}
    if not isinstance(extras, dict):
        issues.append(_issue("extra_packages_by_provider", "invalid_object", "Provider extras must be an object of string lists.", "Use {\"arch\": [\"package\"]}."))
    else:
        for provider, packages in extras.items():
            if not isinstance(provider, str) or not PROVIDER_RE.fullmatch(provider):
                issues.append(_issue("extra_packages_by_provider", "invalid_provider", "Provider keys must be safe lowercase identifiers.", "Use a key such as \"arch\"; provider implementations are added only in their planned phase."))
                continue
            parsed_extras[provider] = _string_list(packages, f"extra_packages_by_provider.{provider}", issues)
    kwargs["extra_packages_by_provider"] = parsed_extras

    package_entries = [
        (f"cachyos_packages[{index}]", package)
        for index, package in enumerate(kwargs.get("cachyos_packages", []))
    ]
    for provider, packages in parsed_extras.items():
        package_entries.extend(
            (f"extra_packages_by_provider.{provider}[{index}]", package)
            for index, package in enumerate(packages)
        )
    for package_path, package in package_entries:
        package_issue = validate_package_identifier(package, path=package_path)
        if package_issue:
            issues.append(package_issue)
    for field_name in CUSTOM_COMMAND_FIELDS:
        for index, command in enumerate(kwargs.get(field_name, [])):
            command_issue = validate_custom_command(command, path=f"{field_name}[{index}]")
            if command_issue:
                issues.append(command_issue)

    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ConfigValidationError(errors)
    return ConfigParseResult(ProjectConfig(**kwargs), tuple(issues), migration.source_version)
