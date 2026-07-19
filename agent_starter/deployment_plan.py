"""Strict, deterministic deployment-plan data with no execution authority."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
from typing import Any, Mapping

from .deployment import DeploymentContractError, DeploymentTarget, deployment_contract, parse_deployment_target
from .deployment_secrets import CREDENTIAL_MECHANISMS, valid_secret_reference_name
from .models import ProjectConfig


PROFILE_LIMIT = 128_000
PROJECT_CONFIG_LIMIT = 1_000_000
PROFILE_FIELDS = {
    "schema_version", "target", "environment", "target_identifier", "artifact_output",
    "local_writes", "remote_writes", "commands", "network_destinations",
    "credential_references", "health_checks", "rollback_steps",
}
ENVIRONMENTS = {"development", "staging", "production"}
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9._-]{0,79}$")
_DESTINATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}$")
_SENSITIVE_RE = re.compile(
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|token)\s*[:=]\s*\S+)|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}\b"
)


@dataclass(frozen=True, slots=True)
class DeploymentPlanIssue:
    path: str
    code: str
    explanation: str
    remedy: str


class DeploymentPlanError(ValueError):
    def __init__(self, issues: list[DeploymentPlanIssue] | tuple[DeploymentPlanIssue, ...]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.path}: {issue.explanation}" for issue in self.issues))


@dataclass(frozen=True, slots=True)
class CredentialReference:
    name: str
    mechanism: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "mechanism": self.mechanism}


@dataclass(frozen=True, slots=True)
class DeploymentTargetProfile:
    target: DeploymentTarget
    environment: str
    target_identifier: str
    artifact_output: str
    local_writes: tuple[str, ...]
    remote_writes: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...]
    network_destinations: tuple[str, ...]
    credential_references: tuple[CredentialReference, ...]
    health_checks: tuple[str, ...]
    rollback_steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceState:
    repository: str
    revision: str | None
    dirty: bool | None
    changed_entry_count: int
    project_is_repository_root: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "revision": self.revision,
            "dirty": self.dirty,
            "changed_entry_count": self.changed_entry_count,
            "project_is_repository_root": self.project_is_repository_root,
        }


@dataclass(frozen=True, slots=True)
class DeploymentPlan:
    canonical_payload: str
    digest: str

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.canonical_payload)


def _issue(path: str, code: str, explanation: str, remedy: str) -> DeploymentPlanIssue:
    return DeploymentPlanIssue(path, code, explanation, remedy)


def _text(value: object, path: str, issues: list[DeploymentPlanIssue], *, limit: int = 500) -> str:
    if not isinstance(value, str):
        issues.append(_issue(path, "invalid_string", "Expected text.", "Use a JSON string."))
        return ""
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        issues.append(_issue(path, "invalid_text", f"Text must be 1–{limit} printable characters.", "Use short printable text without control characters."))
        return ""
    if _SENSITIVE_RE.search(value):
        issues.append(_issue(path, "secret_value_forbidden", "A secret-like value is forbidden in a target profile.", "Use a credential reference name and mechanism, never a value."))
        return ""
    return value


def _relative_path(value: object, path: str, issues: list[DeploymentPlanIssue]) -> str:
    text = _text(value, path, issues, limit=240)
    if not text:
        return ""
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or ".." in candidate.parts or text in {".", ""}:
        issues.append(_issue(path, "unsafe_relative_path", "Path must stay relative to the project root.", "Use a project-relative path without '..'."))
        return ""
    return candidate.as_posix()


def _text_list(value: object, path: str, issues: list[DeploymentPlanIssue], *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        issues.append(_issue(path, "invalid_list", "Expected a JSON list of strings.", "Use an explicit JSON array, including [] when none apply."))
        return ()
    if len(value) > 30:
        issues.append(_issue(path, "list_too_long", "At most 30 items are allowed.", "Remove unrelated entries."))
    result = tuple(text for index, item in enumerate(value[:30]) if (text := _text(item, f"{path}[{index}]", issues, limit=1000)))
    if required and not result:
        issues.append(_issue(path, "required_plan_evidence", "At least one reviewed item is required.", "Add a concrete health check or rollback step."))
    return result


def _commands(value: object, issues: list[DeploymentPlanIssue]) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        issues.append(_issue("commands", "invalid_list", "Commands must be a JSON list of argv arrays.", "Use [] when no commands apply."))
        return ()
    if len(value) > 30:
        issues.append(_issue("commands", "list_too_long", "At most 30 commands are allowed.", "Remove unrelated commands."))
    result: list[tuple[str, ...]] = []
    for index, command in enumerate(value[:30]):
        if not isinstance(command, list) or not command or len(command) > 32:
            issues.append(_issue(f"commands[{index}]", "invalid_argv", "Each command must be a non-empty JSON argv array of at most 32 strings.", "Use [\"program\", \"argument\"] data; it will be displayed, never executed."))
            continue
        argv = tuple(text for arg_index, arg in enumerate(command) if (text := _text(arg, f"commands[{index}][{arg_index}]", issues)))
        if len(argv) == len(command):
            result.append(argv)
    return tuple(result)


def _credentials(value: object, issues: list[DeploymentPlanIssue]) -> tuple[CredentialReference, ...]:
    if not isinstance(value, list):
        issues.append(_issue("credential_references", "invalid_list", "Expected a list of credential references.", "Use [] when no credentials apply."))
        return ()
    result: list[CredentialReference] = []
    for index, item in enumerate(value[:20]):
        if not isinstance(item, dict) or set(item) != {"name", "mechanism"}:
            issues.append(_issue(f"credential_references[{index}]", "invalid_credential_reference", "Credential references require exactly name and mechanism.", "Use a reference name plus an approved mechanism, never a value."))
            continue
        name = _text(item.get("name"), f"credential_references[{index}].name", issues, limit=80)
        mechanism = _text(item.get("mechanism"), f"credential_references[{index}].mechanism", issues, limit=40)
        if name and not valid_secret_reference_name(name):
            issues.append(_issue(f"credential_references[{index}].name", "invalid_identifier", "Credential reference name is invalid.", "Use a lowercase non-secret reference identifier."))
        if mechanism not in CREDENTIAL_MECHANISMS:
            issues.append(_issue(f"credential_references[{index}].mechanism", "invalid_credential_mechanism", "Credential mechanism is not supported.", "Use none, environment-file, os-keyring, ci-secret-store, target-secret-manager, or ssh-agent."))
        if name and valid_secret_reference_name(name) and mechanism in CREDENTIAL_MECHANISMS:
            result.append(CredentialReference(name, mechanism))
    if len(value) > 20:
        issues.append(_issue("credential_references", "list_too_long", "At most 20 credential references are allowed.", "Remove unrelated references."))
    return tuple(result)


def parse_target_profile(data: object) -> DeploymentTargetProfile:
    issues: list[DeploymentPlanIssue] = []
    if not isinstance(data, dict):
        raise DeploymentPlanError([_issue("profile", "invalid_object", "Target profile must be a JSON object.", "Use the documented closed target-profile schema.")])
    for field in sorted(set(data) - PROFILE_FIELDS):
        issues.append(_issue(field, "unknown_field", "Unknown target-profile field.", "Remove the field or use the documented schema."))
    for field in sorted(PROFILE_FIELDS - set(data)):
        issues.append(_issue(field, "missing_field", "Required target-profile field is missing.", "Add the field explicitly; use [] where no effects apply."))

    version = data.get("schema_version")
    if type(version) is not int or version != 1:
        issues.append(_issue("schema_version", "unsupported_schema_version", "Target profile schema_version must be integer 1.", "Set schema_version to 1 without quotes."))
    try:
        target = parse_deployment_target(data.get("target"), path="target")
    except DeploymentContractError as exc:
        target = DeploymentTarget.STATIC_SITE
        source_issue = exc.issue
        issues.append(_issue(source_issue.path, source_issue.code, source_issue.explanation, source_issue.remedy))
    environment = _text(data.get("environment"), "environment", issues, limit=20)
    if environment not in ENVIRONMENTS:
        issues.append(_issue("environment", "invalid_environment", "Environment must be explicit and supported.", "Use development, staging, or production; there is no default."))
    target_identifier = _text(data.get("target_identifier"), "target_identifier", issues, limit=80)
    if target_identifier and not _IDENTIFIER_RE.fullmatch(target_identifier):
        issues.append(_issue("target_identifier", "invalid_identifier", "Target identifier has unsafe or ambiguous characters.", "Use a lowercase identifier beginning with a letter and containing letters, digits, '.', '_', or '-'."))
    artifact_output = _relative_path(data.get("artifact_output"), "artifact_output", issues)

    local_value = data.get("local_writes")
    if isinstance(local_value, list):
        local_writes = tuple(path for index, item in enumerate(local_value[:30]) if (path := _relative_path(item, f"local_writes[{index}]", issues)))
        if len(local_value) > 30:
            issues.append(_issue("local_writes", "list_too_long", "At most 30 local writes are allowed.", "Remove unrelated paths."))
    else:
        issues.append(_issue("local_writes", "invalid_list", "Expected a JSON list of project-relative paths.", "Use [] when no local writes apply."))
        local_writes = ()
    remote_writes = _text_list(data.get("remote_writes"), "remote_writes", issues)
    for index, destination in enumerate(remote_writes):
        if not _DESTINATION_RE.fullmatch(destination):
            issues.append(_issue(f"remote_writes[{index}]", "invalid_remote_write", "Remote write must be a bounded target/path identifier without credentials or shell syntax.", "Use a reviewed host:path, URI-like path, or target-native identifier."))
    network_destinations = _text_list(data.get("network_destinations"), "network_destinations", issues)
    for index, destination in enumerate(network_destinations):
        if not _DESTINATION_RE.fullmatch(destination):
            issues.append(_issue(f"network_destinations[{index}]", "invalid_network_destination", "Network destination must be a host/port or reviewed URI-like identifier without credentials or query data.", "Use a bounded hostname, host:port, or scheme://host/path reference."))

    commands = _commands(data.get("commands"), issues)
    credentials = _credentials(data.get("credential_references"), issues)

    health_checks = _text_list(data.get("health_checks"), "health_checks", issues, required=True)
    rollback_steps = _text_list(data.get("rollback_steps"), "rollback_steps", issues, required=True)
    if issues:
        raise DeploymentPlanError(issues)
    return DeploymentTargetProfile(
        target, environment, target_identifier, artifact_output, local_writes, remote_writes, commands,
        network_destinations, credentials, health_checks, rollback_steps,
    )


def _confined_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    if relative.is_absolute():
        raise DeploymentPlanError([_issue("path", "absolute_path_forbidden", "Path must be project-relative.", "Use a relative path inside the generated project.")])
    if ".." in relative.parts:
        raise DeploymentPlanError([_issue("path", "path_traversal", "Parent traversal is forbidden even when it would resolve inside the project.", "Use a normalized project-relative path without '..'.")])
    candidate = root / relative
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise DeploymentPlanError([_issue("path", "path_escape", "Path leaves the project root.", "Use a path confined to the generated project.")]) from exc
    current = root
    for part in relative.parts[:-1] if must_exist else relative.parts:
        current /= part
        if current.is_symlink():
            raise DeploymentPlanError([_issue("path", "symlink_path_forbidden", "Symlinked path components are refused.", "Use a regular project-local path without symlinks.")])
    if candidate.is_symlink():
        raise DeploymentPlanError([_issue("path", "symlink_path_forbidden", "Symlinked files are refused.", "Use a regular project-local file.")])
    return candidate


def load_target_profile(root: Path, relative: Path) -> DeploymentTargetProfile:
    root = root.expanduser().resolve()
    path = _confined_path(root, relative, must_exist=True)
    if not path.is_file():
        raise DeploymentPlanError([_issue("profile", "profile_not_found", "Target profile is not a regular file.", "Create a reviewed project-local JSON target profile.")])
    if path.stat().st_size > PROFILE_LIMIT:
        raise DeploymentPlanError([_issue("profile", "profile_too_large", "Target profile exceeds 128000 bytes.", "Remove unrelated or embedded data.")])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DeploymentPlanError([_issue("profile", "invalid_profile_json", "Target profile is not valid bounded UTF-8 JSON.", "Correct the JSON without adding secret values.")]) from exc
    return parse_target_profile(data)


def load_plan_project_config(root: Path) -> ProjectConfig:
    root = root.expanduser().resolve()
    path = _confined_path(root, Path(".agent-starter/project.json"), must_exist=True)
    if not path.is_file() or path.stat().st_size > PROJECT_CONFIG_LIMIT:
        raise DeploymentPlanError([_issue("project", "invalid_project_metadata", "Generated project metadata is missing, non-regular, or oversized.", "Regenerate or repair the project metadata before planning.")])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(data)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise DeploymentPlanError([_issue("project", "invalid_project_metadata", "Generated project metadata is invalid.", "Validate and repair the generated workspace before planning.")]) from exc
    if config.primary_agent != "codex":
        raise DeploymentPlanError([_issue("project.primary_agent", "incompatible_agent", "Project metadata is not Codex-only.", "Use metadata generated by this Codex-only AgentKit edition.")])
    return config


def confined_output_path(root: Path, relative: Path) -> Path:
    root = root.expanduser().resolve()
    path = _confined_path(root, relative, must_exist=False)
    if path.exists():
        raise DeploymentPlanError([_issue("output", "output_exists", "Immutable plan output already exists.", "Choose a new project-relative output path; existing plans are never replaced.")])
    return path


def inspect_source_state(root: Path) -> SourceState:
    root = root.expanduser().resolve()
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(root), *arguments],
            text=True, capture_output=True, check=False, timeout=5, env=environment,
        )

    try:
        top = run("rev-parse", "--show-toplevel")
        if top.returncode != 0:
            return SourceState("not-versioned", None, None, 0, False)
        project_is_root = Path(top.stdout.strip()).resolve() == root
        revision_result = run("rev-parse", "HEAD")
        revision_text = revision_result.stdout.strip()
        revision = revision_text if revision_result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", revision_text) else None
        status = run("status", "--porcelain=v1", "--untracked-files=normal")
        if status.returncode != 0:
            return SourceState("git-status-unavailable", revision, None, 0, project_is_root)
        changed_count = len(status.stdout.splitlines())
        return SourceState("git", revision, changed_count > 0, changed_count, project_is_root)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return SourceState("git-unavailable", None, None, 0, False)


def build_deployment_plan(
    config: ProjectConfig,
    profile: DeploymentTargetProfile,
    source: SourceState,
    *,
    plan_output: str | None = None,
) -> DeploymentPlan:
    contract = deployment_contract(profile.target.value)
    payload: dict[str, object] = {
        "schema_version": 1,
        "authority": {
            "operation": "plan",
            "apply_authorized": False,
            "build_or_check_performed": False,
            "remote_changes_performed": False,
            "credentials_accessed": False,
            "plan_document_output": plan_output or "stdout",
            "local_plan_write_performed": plan_output is not None,
        },
        "project": {"name": config.project_name, "slug": config.project_slug, "root": "."},
        "source": source.to_dict(),
        "target": {
            "id": profile.target.value,
            "display_label": contract.display_label,
            "environment": profile.environment,
            "target_identifier": profile.target_identifier,
            "artifact_kind": contract.artifact_kind,
            "artifact_output": profile.artifact_output,
        },
        "effects": {
            "local_writes": list(profile.local_writes),
            "remote_writes": list(profile.remote_writes),
            "commands": [list(command) for command in profile.commands],
            "network_destinations": list(profile.network_destinations),
            "credential_references": [item.to_dict() for item in profile.credential_references],
        },
        "health_checks": list(profile.health_checks),
        "rollback_steps": list(profile.rollback_steps),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return DeploymentPlan(canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest())


def render_plan_json(plan: DeploymentPlan) -> str:
    return json.dumps({"digest_algorithm": "sha256", "plan_digest": plan.digest, "plan": plan.payload}, indent=2, sort_keys=True) + "\n"


def _items(values: list[object], *, empty: str = "None declared") -> list[str]:
    return [f"- {value}" for value in values] or [f"- {empty}"]


def render_plan_text(plan: DeploymentPlan) -> str:
    data = plan.payload
    source = data["source"]
    target = data["target"]
    effects = data["effects"]
    commands = [shlex.join(command) for command in effects["commands"]]
    credentials = [f"{item['name']} ({item['mechanism']})" for item in effects["credential_references"]]
    lines = [
        "# Immutable deployment plan", "", f"Plan digest (SHA-256): {plan.digest}",
        "Authority: plan only; no build/check, credential access, network request, remote write, or apply occurred.", "",
        f"Plan document output: {data['authority']['plan_document_output']}", "",
        "## Project and source", f"- Project: {data['project']['name']} ({data['project']['slug']})",
        f"- Repository state: {source['repository']}", f"- Revision: {source['revision'] or 'unavailable'}",
        f"- Dirty: {source['dirty']}", f"- Changed entry count: {source['changed_entry_count']}",
        f"- Project is repository root: {source['project_is_repository_root']}", "",
        "## Target and artifact", f"- Target: {target['id']} — {target['display_label']}",
        f"- Environment: {target['environment']}", f"- Target identifier: {target['target_identifier']}",
        f"- Artifact kind: {target['artifact_kind']}", f"- Artifact output: {target['artifact_output']}", "",
        "## Local writes (advertised, not performed)", *_items(effects["local_writes"]), "",
        "## Remote writes (advertised, not performed)", *_items(effects["remote_writes"]), "",
        "## Commands (display only; never executed)", *_items(commands), "",
        "## Network destinations (advertised, not contacted)", *_items(effects["network_destinations"]), "",
        "## Credential references (names/mechanisms only)", *_items(credentials), "",
        "## Health checks", *_items(data["health_checks"]), "", "## Rollback steps", *_items(data["rollback_steps"]), "",
    ]
    return "\n".join(str(line) for line in lines)
