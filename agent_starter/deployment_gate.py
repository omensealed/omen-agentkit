"""Pure, fail-closed deployment apply-gate state model.

The module evaluates exact evidence bindings. It has no command runner, target
adapter, credential access, network access, filesystem write, or apply path.
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .deployment import DeploymentOperation, deployment_contract
from .deployment_build import ArtifactBuildReport
from .deployment_check import DeploymentCheckReport
from .deployment_plan import DeploymentPlan


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TARGET_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9._-]{0,79}$")
_ENVIRONMENTS = {"development", "staging", "production"}
_HUMAN_INPUT_SOURCE = "local-tty-human"
_AUTHENTICATION_SOURCE = "target-tool-human-session"
_GATE_STATUSES = {"passed", "blocked", "pending"}
REQUIRED_APPLY_CHECK_IDS = frozenset({
    "plan_integrity", "project_identity", "project_validation", "project_tests", "source_state",
    "artifact_checksum", "artifact_reproducibility", "target_identity", "credential_references",
    "backup_migration_readiness", "health_rollback_completeness", "least_privilege",
})


class ApplyGateState(str, Enum):
    INVALIDATED = "invalidated"
    BLOCKED_ADAPTER = "blocked-adapter"
    BLOCKED_EVIDENCE = "blocked-evidence"
    AWAITING_AUTHENTICATION = "awaiting-authentication"
    AWAITING_CONFIRMATION = "awaiting-confirmation"
    AWAITING_AUDIT = "awaiting-audit"
    READY_FOR_SEPARATE_APPLY = "ready-for-separate-apply"


@dataclass(frozen=True, slots=True)
class TargetAuthenticationEvidence:
    adapter_id: str
    plan_digest: str
    environment: str
    target_identifier: str
    human_authenticated: bool
    source: str


@dataclass(frozen=True, slots=True)
class TypedHumanConfirmation:
    plan_digest: str
    artifact_digest: str
    environment: str
    target_identifier: str
    input_source: str


@dataclass(frozen=True, slots=True)
class RedactedApplyAuditEvent:
    plan_digest: str
    artifact_digest: str
    environment: str
    target_identifier: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "event": "deployment-apply-gate-reviewed",
            "plan_digest": self.plan_digest,
            "artifact_digest": self.artifact_digest,
            "environment": self.environment,
            "target_identifier": self.target_identifier,
            "redacted": True,
        }


@dataclass(frozen=True, slots=True)
class ApplyGateEvidence:
    reviewed_plan_digest: str
    check_report: DeploymentCheckReport | None
    artifact_report: ArtifactBuildReport | None
    reviewed_artifact_digest: str
    environment: str
    target_identifier: str
    authentication: TargetAuthenticationEvidence | None
    confirmation: TypedHumanConfirmation | None
    rollback_available: bool
    audit_event: RedactedApplyAuditEvent | None


@dataclass(frozen=True, slots=True)
class ApplyGateFinding:
    gate_id: str
    status: str
    code: str
    explanation: str
    remedy: str

    def to_dict(self) -> dict[str, str]:
        return {
            "gate_id": self.gate_id,
            "status": self.status,
            "code": self.code,
            "explanation": self.explanation,
            "remedy": self.remedy,
        }


@dataclass(frozen=True, slots=True)
class ApplyGateAuthority:
    apply_authorized: bool = False
    apply_performed: bool = False
    credentials_accessed: bool = False
    network_accessed: bool = False
    remote_changes_performed: bool = False
    target_contacted: bool = False
    writes_performed: bool = False

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "operation": "apply-gate-evaluation",
            "apply_authorized": self.apply_authorized,
            "apply_performed": self.apply_performed,
            "credentials_accessed": self.credentials_accessed,
            "network_accessed": self.network_accessed,
            "remote_changes_performed": self.remote_changes_performed,
            "target_contacted": self.target_contacted,
            "writes_performed": self.writes_performed,
        }


@dataclass(frozen=True, slots=True)
class ApplyGateResult:
    state: ApplyGateState
    plan_digest: str
    artifact_digest: str
    findings: tuple[ApplyGateFinding, ...]
    authority: ApplyGateAuthority

    @property
    def ready(self) -> bool:
        return self.state is ApplyGateState.READY_FOR_SEPARATE_APPLY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": "deployment-apply-gate",
            "state": self.state.value,
            "ready_for_separate_apply": self.ready,
            "plan_digest": self.plan_digest,
            "artifact_digest": self.artifact_digest,
            "authority": self.authority.to_dict(),
            "findings": [item.to_dict() for item in self.findings],
        }


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST_RE.fullmatch(value) is not None


def _valid_identity(environment: object, target_identifier: object) -> bool:
    return bool(
        isinstance(environment, str)
        and environment in _ENVIRONMENTS
        and isinstance(target_identifier, str)
        and _TARGET_IDENTIFIER_RE.fullmatch(target_identifier)
    )


def _finding(gate_id: str, status: str, code: str, explanation: str, remedy: str) -> ApplyGateFinding:
    if status not in _GATE_STATUSES:
        raise ValueError("invalid apply-gate status")
    return ApplyGateFinding(gate_id, status, code, explanation, remedy)


def expected_confirmation_text(
    *, plan_digest: str, artifact_digest: str, environment: str, target_identifier: str
) -> str:
    """Return the exact phrase a future local human-input adapter may request."""

    if not _valid_digest(plan_digest) or not _valid_digest(artifact_digest):
        raise ValueError("confirmation requires exact lowercase SHA-256 digests")
    if not _valid_identity(environment, target_identifier):
        raise ValueError("confirmation requires a supported environment and exact safe target identifier")
    return f"approve {environment} {target_identifier} plan {plan_digest} artifact {artifact_digest}"


def record_typed_human_confirmation(
    typed_text: object,
    *,
    input_source: str,
    plan_digest: str,
    artifact_digest: str,
    environment: str,
    target_identifier: str,
) -> TypedHumanConfirmation:
    """Validate exact local-TTY input and retain only its evidence binding."""

    if input_source != _HUMAN_INPUT_SOURCE or not isinstance(typed_text, str):
        raise ValueError("confirmation must come from a separate local human TTY input boundary")
    expected = expected_confirmation_text(
        plan_digest=plan_digest,
        artifact_digest=artifact_digest,
        environment=environment,
        target_identifier=target_identifier,
    )
    if not hmac.compare_digest(typed_text, expected):
        raise ValueError("typed confirmation did not exactly match the reviewed evidence binding")
    return TypedHumanConfirmation(plan_digest, artifact_digest, environment, target_identifier, input_source)


def create_redacted_audit_event(
    *, plan_digest: str, artifact_digest: str, environment: str, target_identifier: str
) -> RedactedApplyAuditEvent:
    """Create closed audit data in memory; this function never writes a log."""

    expected_confirmation_text(
        plan_digest=plan_digest,
        artifact_digest=artifact_digest,
        environment=environment,
        target_identifier=target_identifier,
    )
    return RedactedApplyAuditEvent(plan_digest, artifact_digest, environment, target_identifier)


def _bindings_match(item: object, evidence: ApplyGateEvidence, plan_digest: str) -> bool:
    artifact_digest = evidence.artifact_report.artifact_digest if evidence.artifact_report else ""
    return bool(
        item is not None
        and getattr(item, "plan_digest", None) == plan_digest
        and getattr(item, "artifact_digest", artifact_digest) == artifact_digest
        and getattr(item, "environment", None) == evidence.environment
        and getattr(item, "target_identifier", None) == evidence.target_identifier
    )


def _adapter_review_findings(
    plan: DeploymentPlan, target: dict[str, Any], evidence: ApplyGateEvidence
) -> tuple[tuple[ApplyGateFinding, ...], bool, bool]:
    contract = deployment_contract(target["id"])
    adapter_supported = DeploymentOperation.APPLY in contract.enabled_operations and contract.production_ready
    adapter = _finding(
        "supported_target_adapter", "passed" if adapter_supported else "blocked",
        "supported_target_adapter" if adapter_supported else "apply_adapter_unavailable",
        "A reviewed apply-capable target adapter is available." if adapter_supported else "No current target contract has a reviewed apply-capable adapter.",
        "No action required." if adapter_supported else "Wait for a separately reviewed target adapter with staging rollback evidence; do not substitute free-form commands.",
    )
    plan_reviewed = _valid_digest(evidence.reviewed_plan_digest) and evidence.reviewed_plan_digest == plan.digest
    reviewed = _finding(
        "reviewed_plan_digest", "passed" if plan_reviewed else "blocked",
        "reviewed_plan_digest" if plan_reviewed else "reviewed_plan_digest_mismatch",
        "The exact current plan digest was reviewed." if plan_reviewed else "The reviewed plan digest does not match the current plan; approval is invalidated.",
        "No action required." if plan_reviewed else "Review the new immutable plan and start a new gate session.",
    )
    return (adapter, reviewed), adapter_supported, not plan_reviewed


def _check_artifact_findings(
    plan: DeploymentPlan, evidence: ApplyGateEvidence
) -> tuple[tuple[ApplyGateFinding, ...], str, bool]:
    check_ids = {item.check_id for item in evidence.check_report.findings} if evidence.check_report else set()
    checks_pass = bool(
        evidence.check_report
        and evidence.check_report.plan_digest == plan.digest
        and evidence.check_report.ready
        and check_ids == REQUIRED_APPLY_CHECK_IDS
    )
    checks = _finding(
        "required_checks", "passed" if checks_pass else "blocked",
        "required_checks_passed" if checks_pass else "required_checks_not_passing",
        "Every digest-bound required check passed." if checks_pass else "Required checks are failed, unverified, missing, or bound to another plan.",
        "No action required." if checks_pass else "Resolve every failed/unverified check and produce a report bound to this plan digest.",
    )
    artifact = evidence.artifact_report
    artifact_digest = artifact.artifact_digest if artifact else ""
    artifact_bound = bool(
        artifact
        and _valid_digest(artifact_digest)
        and artifact.plan_digest == plan.digest
        and artifact.reproducible is True
        and artifact.reproduction_runs == 2
        and artifact.provenance.get("plan_digest") == plan.digest
        and evidence.reviewed_artifact_digest == artifact_digest
    )
    invalidated = artifact is not None and (
        evidence.reviewed_artifact_digest != artifact_digest or artifact.plan_digest != plan.digest
    )
    artifact_finding = _finding(
        "exact_artifact_digest", "passed" if artifact_bound else "blocked",
        "exact_artifact_digest" if artifact_bound else "reviewed_artifact_digest_mismatch",
        "The exact artifact digest is reviewed and bound to this plan." if artifact_bound else "Artifact evidence is malformed, stale, or differs from the reviewed digest.",
        "No action required." if artifact_bound else "Rebuild or re-review the exact artifact and start a new gate session after any digest change.",
    )
    return (checks, artifact_finding), artifact_digest, invalidated


def _identity_human_findings(
    plan: DeploymentPlan, target: dict[str, Any], evidence: ApplyGateEvidence
) -> tuple[tuple[ApplyGateFinding, ...], bool, bool, bool]:
    identity_matches = (
        evidence.environment == target["environment"]
        and evidence.target_identifier == target["target_identifier"]
        and bool(evidence.environment and evidence.target_identifier)
    )
    identity = _finding(
        "explicit_target_identity", "passed" if identity_matches else "blocked",
        "explicit_target_identity" if identity_matches else "target_identity_mismatch",
        "Environment and exact target identifier match the plan." if identity_matches else "Environment or target identity differs from the plan; approval is invalidated.",
        "No action required." if identity_matches else "Generate and review a new plan for the intended explicit environment and target.",
    )
    authentication = evidence.authentication
    authenticated = bool(
        _bindings_match(authentication, evidence, plan.digest)
        and authentication.human_authenticated
        and authentication.source == _AUTHENTICATION_SOURCE
        and authentication.adapter_id
    )
    authentication_finding = _finding(
        "human_authentication", "passed" if authenticated else "pending",
        "human_authentication_bound" if authenticated else "human_authentication_required",
        "Human target-tool authentication evidence is bound to this plan and target." if authenticated else "Bound human authentication through the reviewed target tool is missing.",
        "No action required." if authenticated else "Authenticate interactively through the future reviewed target adapter; never supply credentials to AgentKit or model output.",
    )
    confirmation = evidence.confirmation
    confirmed = bool(
        _bindings_match(confirmation, evidence, plan.digest)
        and confirmation.input_source == _HUMAN_INPUT_SOURCE
    )
    confirmation_finding = _finding(
        "typed_human_confirmation", "passed" if confirmed else "pending",
        "typed_human_confirmation_bound" if confirmed else ("confirmation_binding_mismatch" if confirmation else "typed_human_confirmation_required"),
        "Exact typed local-human confirmation is bound to the current evidence." if confirmed else "A fresh exact typed confirmation outside model output is required.",
        "No action required." if confirmed else "Use the future dedicated local human-input boundary after every other reviewed digest and identity is final.",
    )
    invalidated = (
        not identity_matches
        or authentication is not None and not authenticated
        or confirmation is not None and not confirmed
    )
    return (identity, authentication_finding, confirmation_finding), authenticated, confirmed, invalidated


def _rollback_audit_findings(
    plan: DeploymentPlan, evidence: ApplyGateEvidence
) -> tuple[tuple[ApplyGateFinding, ...], bool, bool]:
    payload = plan.payload
    rollback = evidence.rollback_available is True and bool(payload.get("rollback_steps"))
    rollback_finding = _finding(
        "rollback_available", "passed" if rollback else "blocked",
        "rollback_available" if rollback else "rollback_unavailable",
        "A concrete rollback is declared and separately reported available." if rollback else "Rollback is missing or has not been reported available.",
        "No action required." if rollback else "Prove rollback in staging and bind that evidence before apply can be considered.",
    )
    audit_bound = _bindings_match(evidence.audit_event, evidence, plan.digest)
    audit = _finding(
        "redacted_local_audit_event", "passed" if audit_bound else "pending",
        "redacted_audit_event_bound" if audit_bound else "redacted_audit_event_required",
        "Closed redacted audit metadata is bound to the current evidence." if audit_bound else "A bound redacted local audit event is missing or stale.",
        "No action required." if audit_bound else "Create the closed value-free audit event after final evidence review; persistence belongs to a later safe operation boundary.",
    )
    return (rollback_finding, audit), audit_bound, evidence.audit_event is not None and not audit_bound


def evaluate_apply_gate(plan: DeploymentPlan, evidence: ApplyGateEvidence) -> ApplyGateResult:
    """Evaluate every P6-007 prerequisite without performing any side effect."""

    target = plan.payload["target"]
    review_findings, adapter_supported, invalid_review = _adapter_review_findings(plan, target, evidence)
    artifact_findings, artifact_digest, invalid_artifact = _check_artifact_findings(plan, evidence)
    human_findings, authenticated, confirmed, invalid_human = _identity_human_findings(plan, target, evidence)
    final_findings, audit_bound, invalid_audit = _rollback_audit_findings(plan, evidence)
    findings = review_findings + artifact_findings + human_findings + final_findings
    invalidated = invalid_review or invalid_artifact or invalid_human or invalid_audit

    if invalidated:
        state = ApplyGateState.INVALIDATED
    elif not adapter_supported:
        state = ApplyGateState.BLOCKED_ADAPTER
    elif any(item.status == "blocked" for item in findings):
        state = ApplyGateState.BLOCKED_EVIDENCE
    elif not authenticated:
        state = ApplyGateState.AWAITING_AUTHENTICATION
    elif not confirmed:
        state = ApplyGateState.AWAITING_CONFIRMATION
    elif not audit_bound:
        state = ApplyGateState.AWAITING_AUDIT
    else:
        state = ApplyGateState.READY_FOR_SEPARATE_APPLY
    return ApplyGateResult(state, plan.digest, artifact_digest, tuple(findings), ApplyGateAuthority())
