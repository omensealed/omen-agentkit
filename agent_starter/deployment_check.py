"""Read-only local deployment checks with explicit unverified boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .deployment_build import verify_built_artifact
from .deployment import deployment_contract
from .deployment_plan import (
    CredentialReference,
    DeploymentPlan,
    DeploymentPlanError,
    DeploymentPlanIssue,
    _confined_path,
    inspect_source_state,
    load_plan_project_config,
    parse_target_profile,
)
from .deployment_secrets import check_secret_references
from .generator import validate_project


PLAN_LIMIT = 2_000_000
ARTIFACT_FILE_LIMIT = 10_000
ARTIFACT_BYTE_LIMIT = 512 * 1024 * 1024
STATUSES = {"passed", "failed", "unverified"}


@dataclass(frozen=True, slots=True)
class DeploymentCheckFinding:
    check_id: str
    status: str
    summary: str
    remedy: str
    evidence: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "summary": self.summary,
            "remedy": self.remedy,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class DeploymentCheckReport:
    plan_digest: str
    findings: tuple[DeploymentCheckFinding, ...]

    @property
    def ready(self) -> bool:
        return all(item.status == "passed" for item in self.findings)

    @property
    def exit_code(self) -> int:
        return 0 if self.ready else 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": "deployment-check",
            "plan_digest": self.plan_digest,
            "ready": self.ready,
            "authority": {
                "operation": "check",
                "apply_authorized": False,
                "artifact_built": False,
                "credentials_accessed": False,
                "network_accessed": False,
                "project_commands_executed": False,
                "remote_changes_performed": False,
                "target_contacted": False,
                "writes_performed": False,
            },
            "findings": [item.to_dict() for item in self.findings],
        }


def _error(path: str, code: str, explanation: str, remedy: str) -> DeploymentPlanError:
    return DeploymentPlanError([DeploymentPlanIssue(path, code, explanation, remedy)])


def _exact_keys(value: object, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise _error(path, "invalid_plan_shape", "Immutable plan fields do not match the supported schema.", "Regenerate the plan with this AgentKit version and do not edit it.")
    return value


def _validate_plan_payload(payload: object) -> dict[str, Any]:
    plan = _exact_keys(payload, {"schema_version", "authority", "project", "source", "target", "effects", "health_checks", "rollback_steps"}, "plan")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise _error("plan.schema_version", "unsupported_plan_schema", "Plan schema must be integer 1.", "Regenerate the immutable plan with this AgentKit version.")
    authority = _exact_keys(plan["authority"], {
        "operation", "apply_authorized", "build_or_check_performed", "remote_changes_performed",
        "credentials_accessed", "plan_document_output", "local_plan_write_performed",
    }, "plan.authority")
    expected_false = ("apply_authorized", "build_or_check_performed", "remote_changes_performed", "credentials_accessed")
    if authority["operation"] != "plan" or any(authority[name] is not False for name in expected_false):
        raise _error("plan.authority", "invalid_plan_authority", "Input does not retain plan-only authority.", "Use an unmodified plan produced by `deployment plan`.")
    if type(authority["local_plan_write_performed"]) is not bool or not isinstance(authority["plan_document_output"], str):
        raise _error("plan.authority", "invalid_plan_authority", "Plan output authority metadata is malformed.", "Regenerate the immutable plan.")

    project = _exact_keys(plan["project"], {"name", "slug", "root"}, "plan.project")
    if project["root"] != "." or not all(isinstance(project[name], str) and project[name] for name in ("name", "slug")):
        raise _error("plan.project", "invalid_project_identity", "Plan project identity is invalid.", "Regenerate the plan from the generated project root.")
    source = _exact_keys(plan["source"], {"repository", "revision", "dirty", "changed_entry_count", "project_is_repository_root"}, "plan.source")
    if source["repository"] not in {"git", "not-versioned", "git-status-unavailable", "git-unavailable"} or source["dirty"] is not None and type(source["dirty"]) is not bool or type(source["changed_entry_count"]) is not int or source["changed_entry_count"] < 0 or type(source["project_is_repository_root"]) is not bool:
        raise _error("plan.source", "invalid_source_state", "Recorded source state is malformed.", "Regenerate the plan from the current project source.")
    revision = source["revision"]
    if revision is not None and (not isinstance(revision, str) or len(revision) not in range(40, 65) or any(character not in "0123456789abcdefABCDEF" for character in revision)):
        raise _error("plan.source.revision", "invalid_source_revision", "Recorded revision is malformed.", "Regenerate the plan from a supported Git checkout.")

    target = _exact_keys(plan["target"], {"id", "display_label", "environment", "target_identifier", "artifact_kind", "artifact_output"}, "plan.target")
    effects = _exact_keys(plan["effects"], {"local_writes", "remote_writes", "commands", "network_destinations", "credential_references"}, "plan.effects")
    profile = parse_target_profile({
        "schema_version": 1,
        "target": target["id"],
        "environment": target["environment"],
        "target_identifier": target["target_identifier"],
        "artifact_output": target["artifact_output"],
        "local_writes": effects["local_writes"],
        "remote_writes": effects["remote_writes"],
        "commands": effects["commands"],
        "network_destinations": effects["network_destinations"],
        "credential_references": effects["credential_references"],
        "health_checks": plan["health_checks"],
        "rollback_steps": plan["rollback_steps"],
    })
    contract = deployment_contract(profile.target.value)
    if target["display_label"] != contract.display_label or target["artifact_kind"] != contract.artifact_kind:
        raise _error("plan.target", "target_contract_mismatch", "Target labels do not match the reviewed adapter contract.", "Regenerate the plan instead of editing target metadata.")
    return plan


def load_immutable_plan(root: Path, relative: Path) -> DeploymentPlan:
    root = root.expanduser().resolve()
    path = _confined_path(root, relative, must_exist=True)
    if not path.is_file() or path.stat().st_size > PLAN_LIMIT:
        raise _error("plan", "invalid_plan_file", "Plan must be a regular project-local JSON file no larger than 2000000 bytes.", "Use a bounded immutable plan produced by `deployment plan`.")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error("plan", "invalid_plan_json", "Plan is not valid bounded UTF-8 JSON.", "Regenerate the immutable JSON plan.") from exc
    wrapper = _exact_keys(document, {"digest_algorithm", "plan_digest", "plan"}, "document")
    if wrapper["digest_algorithm"] != "sha256" or not isinstance(wrapper["plan_digest"], str):
        raise _error("document", "invalid_digest_metadata", "Plan digest metadata is invalid.", "Use SHA-256 output produced by `deployment plan`.")
    payload = _validate_plan_payload(wrapper["plan"])
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if wrapper["plan_digest"] != digest:
        raise _error("plan_digest", "plan_digest_mismatch", "Plan content does not match its immutable digest.", "Discard the edited file and generate a new reviewed plan.")
    return DeploymentPlan(canonical, digest)


def _finding(check_id: str, status: str, summary: str, remedy: str, evidence: str = "") -> DeploymentCheckFinding:
    if status not in STATUSES:
        raise ValueError("invalid deployment-check status")
    return DeploymentCheckFinding(check_id, status, summary, remedy, evidence)


def _artifact_checksum(root: Path, relative: str) -> str:
    path = _confined_path(root, Path(relative), must_exist=True)
    if not path.exists() or path.is_symlink():
        raise ValueError("planned artifact is missing or symlinked")
    if path.is_file():
        digest = hashlib.sha256()
        _update_regular_file(digest, path, ARTIFACT_BYTE_LIMIT, b"")
        return digest.hexdigest()
    digest = hashlib.sha256()
    entries = list(path.rglob("*"))
    if any(item.is_symlink() or not (item.is_file() or item.is_dir()) for item in entries):
        raise ValueError("planned artifact contains a symlink or special file")
    files = sorted((item for item in entries if item.is_file()), key=lambda item: item.relative_to(path).as_posix())
    if not path.is_dir():
        raise ValueError("planned artifact is not a regular file or directory")
    if len(files) > ARTIFACT_FILE_LIMIT:
        raise ValueError("planned artifact exceeds the 10000-file inspection limit")
    reported_total = 0
    actual_total = 0
    for item in files:
        if item.is_symlink() or not item.is_file():
            raise ValueError("planned artifact contains a symlink or special file")
        relative_name = item.relative_to(path).as_posix()
        prefix = b"file\0" + relative_name.encode("utf-8") + b"\0"
        consumed, declared = _update_regular_file(digest, item, ARTIFACT_BYTE_LIMIT - actual_total, prefix)
        actual_total += consumed
        reported_total += declared
        if reported_total > ARTIFACT_BYTE_LIMIT:
            raise ValueError("planned artifact exceeds the 512 MiB inspection limit")
    return digest.hexdigest()


def _update_regular_file(digest: Any, path: Path, limit: int, prefix: bytes) -> tuple[int, int]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError("planned artifact contains an unsafe or oversized file")
        if prefix:
            digest.update(prefix + str(metadata.st_size).encode("ascii") + b"\0")
        consumed = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            consumed += len(chunk)
            if consumed > limit:
                raise ValueError("planned artifact exceeds the 512 MiB inspection limit")
            digest.update(chunk)
    return consumed, metadata.st_size


def _source_finding(planned: dict[str, Any], current: Any) -> DeploymentCheckFinding:
    if planned["repository"] != "git" or planned["revision"] is None:
        return _finding("source_state", "unverified", "The plan has no immutable Git revision to compare.", "Create the plan from a Git checkout with a readable HEAD.")
    if current.repository != "git" or current.revision != planned["revision"] or not current.project_is_repository_root:
        return _finding("source_state", "failed", "Current Git identity does not match the plan.", "Return to the recorded revision and repository root, then create a new plan for any intended change.")
    if current.dirty is None:
        return _finding("source_state", "unverified", "Current Git dirty state could not be read.", "Restore local Git status inspection and rerun the check.")
    if planned["dirty"] is False and current.dirty:
        return _finding("source_state", "failed", "Source became dirty after a clean plan was recorded.", "Review the changes and generate a new immutable plan.")
    summary = "Current clean source matches the recorded revision." if not current.dirty else "Current dirty source is explicitly recorded at the same revision."
    return _finding("source_state", "passed", summary, "No action required.", current.revision or "")


def check_deployment(root: Path, plan: DeploymentPlan) -> DeploymentCheckReport:
    root = root.expanduser().resolve()
    data = plan.payload
    findings: list[DeploymentCheckFinding] = [
        _finding("plan_integrity", "passed", "Plan schema and SHA-256 digest are valid.", "No action required.", plan.digest),
    ]
    config = load_plan_project_config(root)
    planned_project = data["project"]
    project_matches = config.project_name == planned_project["name"] and config.project_slug == planned_project["slug"]
    findings.append(_finding(
        "project_identity", "passed" if project_matches else "failed",
        "Project metadata matches the plan." if project_matches else "Project metadata does not match the plan.",
        "No action required." if project_matches else "Use the plan with its original project or generate a new plan.",
    ))
    validation = validate_project(root)
    findings.append(_finding(
        "project_validation", "passed" if validation.ok else "failed",
        "AgentKit structural validation passed." if validation.ok else "AgentKit structural validation reported errors.",
        "No action required." if validation.ok else "Run `agent-starter validate` and resolve every error before deployment.",
        f"checked={len(validation.checked)}; errors={len(validation.errors)}; warnings={len(validation.warnings)}",
    ))
    findings.append(_finding(
        "project_tests", "unverified", "Project test commands were not executed by this read-only check.",
        "Run the trusted project test entry point separately under explicit human approval and bind its result to the planned revision.",
    ))
    findings.append(_source_finding(data["source"], inspect_source_state(root)))
    artifact_reproducibility = _finding(
        "artifact_reproducibility", "unverified", "One local checksum does not prove reproducibility.",
        "Use the reviewed artifact-build gate to produce and verify two equal deterministic assemblies.",
    )
    try:
        checksum = _artifact_checksum(root, data["target"]["artifact_output"])
        findings.append(_finding("artifact_checksum", "passed", "The planned local artifact has a deterministic SHA-256 checksum.", "No action required.", f"sha256:{checksum}"))
        artifact_path = _confined_path(root, Path(data["target"]["artifact_output"]), must_exist=True)
        verification = verify_built_artifact(artifact_path, plan_digest=plan.digest)
        if verification.ok:
            artifact_reproducibility = _finding(
                "artifact_reproducibility", "passed", "Embedded provenance verifies two equal deterministic assemblies and every payload checksum.",
                "No action required.", verification.content_root_digest or "",
            )
    except (OSError, ValueError, DeploymentPlanError):
        findings.append(_finding("artifact_checksum", "failed", "The planned local artifact could not be safely checksummed.", "Create the artifact through the later reviewed build gate or correct its confined path.", "artifact_unavailable_or_unsafe"))
    findings.append(artifact_reproducibility)
    findings.append(_finding(
        "target_identity", "unverified", "The target identifier is declared but the target was not contacted.",
        "Verify identity through a reviewed read-only target adapter when one is available.", data["target"]["target_identifier"],
    ))
    credentials = data["effects"]["credential_references"]
    secret_findings = check_secret_references(
        root,
        tuple(CredentialReference(item["name"], item["mechanism"]) for item in credentials),
    )
    credential_status = (
        "passed" if not secret_findings or all(item.status == "passed" for item in secret_findings)
        else "failed" if any(item.status == "failed" for item in secret_findings)
        else "unverified"
    )
    credential_summary = {
        "passed": "Required credential references are present through value-free metadata checks.",
        "failed": "One or more required credential references are missing or unsafe.",
        "unverified": "One or more external credential references require a reviewed metadata adapter.",
    }[credential_status]
    findings.append(_finding(
        "credential_references", credential_status,
        "No credential references are required." if not credentials else credential_summary,
        "No action required." if credential_status == "passed" else "Resolve each named reference through its mechanism without reading, printing, or storing a value.",
        ", ".join(f"{item.name}:{item.code}" for item in secret_findings),
    ))
    remote_effects = bool(data["effects"]["remote_writes"])
    findings.append(_finding(
        "backup_migration_readiness", "passed" if not remote_effects else "unverified",
        "No remote write requires backup or migration readiness." if not remote_effects else "Rollback is declared, but target backup or migration readiness was not contacted or changed.",
        "No action required." if not remote_effects else "Verify a restorable backup and migration prerequisites through a reviewed read-only adapter.",
    ))
    complete = bool(data["health_checks"]) and bool(data["rollback_steps"])
    findings.append(_finding(
        "health_rollback_completeness", "passed" if complete else "failed",
        "Health-check and rollback instructions are present." if complete else "Health-check or rollback instructions are missing.",
        "No action required." if complete else "Generate a new plan with concrete health-check and rollback steps.",
    ))
    privileged = bool(credentials or data["effects"]["network_destinations"] or data["effects"]["remote_writes"])
    findings.append(_finding(
        "least_privilege", "passed" if not privileged else "unverified",
        "The plan declares no network, credential, or remote-write capability." if not privileged else "Declared access is visible, but target-side least privilege was not queried.",
        "No action required." if not privileged else "Review the declared destinations and verify narrowly scoped target permissions without reading secret values.",
    ))
    return DeploymentCheckReport(plan.digest, tuple(findings))


def render_check_json(report: DeploymentCheckReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_check_text(report: DeploymentCheckReport) -> str:
    lines = [
        "# Read-only deployment check", "", f"Plan digest (SHA-256): {report.plan_digest}",
        f"Ready: {str(report.ready).lower()}",
        "Authority: check only; no project command, build, credential access, network request, target contact, write, or apply occurred.", "",
    ]
    for finding in report.findings:
        lines.extend((f"[{finding.status}] {finding.check_id}: {finding.summary}", f"  Remedy: {finding.remedy}"))
        if finding.evidence:
            lines.append(f"  Evidence: {finding.evidence}")
    return "\n".join(lines) + "\n"
