"""Disposable static-site staging rehearsal with mandatory rollback.

The adapter is intentionally in-memory and library-only. It executes no plan
command, opens no artifact or credential, contacts no target, and exposes no
CLI or generated-script entry point. Its only mutation is disposable adapter
state used to prove partial-failure recovery and exact rollback behavior.
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .deployment import deployment_contract
from .deployment_build import ArtifactBuildReport
from .deployment_check import DeploymentCheckReport
from .deployment_gate import REQUIRED_APPLY_CHECK_IDS
from .deployment_plan import DeploymentPlan


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TARGET_RE = re.compile(r"^[a-z][a-z0-9._-]{0,79}$")


class RehearsalFailurePoint(str, Enum):
    NONE = "none"
    AFTER_INSTALL = "after-install"
    HEALTH_CHECK = "health-check"


class StagingRehearsalState(str, Enum):
    VERIFIED = "verified"
    ROLLED_BACK = "rolled-back"


class StagingRehearsalError(ValueError):
    def __init__(self, code: str, explanation: str, remedy: str):
        self.code = code
        self.explanation = explanation
        self.remedy = remedy
        super().__init__(explanation)


@dataclass(frozen=True, slots=True)
class StagingRehearsalEvidence:
    reviewed_plan_digest: str
    check_report: DeploymentCheckReport
    artifact_report: ArtifactBuildReport
    reviewed_artifact_digest: str


@dataclass(frozen=True, slots=True)
class StagingAuditEvent:
    event: str
    plan_digest: str
    artifact_digest: str
    target_identifier: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "event": self.event,
            "plan_digest": self.plan_digest,
            "artifact_digest": self.artifact_digest,
            "environment": "staging",
            "target_identifier": self.target_identifier,
            "redacted": True,
        }


@dataclass(frozen=True, slots=True)
class StagingRehearsalAuthority:
    disposable_staging_changed: bool = True
    production_apply_performed: bool = False
    remote_changes_performed: bool = False
    network_accessed: bool = False
    credentials_accessed: bool = False
    commands_executed: bool = False

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "operation": "disposable-staging-rehearsal",
            "disposable_staging_changed": self.disposable_staging_changed,
            "production_apply_performed": self.production_apply_performed,
            "remote_changes_performed": self.remote_changes_performed,
            "network_accessed": self.network_accessed,
            "credentials_accessed": self.credentials_accessed,
            "commands_executed": self.commands_executed,
        }


@dataclass(frozen=True, slots=True)
class StagingRehearsalResult:
    state: StagingRehearsalState
    plan_digest: str
    artifact_digest: str
    target_identifier: str
    health_passed: bool
    rollback_proven: bool
    failure_code: str | None
    audit_events: tuple[StagingAuditEvent, ...]
    authority: StagingRehearsalAuthority = StagingRehearsalAuthority()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": "disposable-staging-rehearsal",
            "state": self.state.value,
            "plan_digest": self.plan_digest,
            "artifact_digest": self.artifact_digest,
            "environment": "staging",
            "target_identifier": self.target_identifier,
            "health_passed": self.health_passed,
            "rollback_proven": self.rollback_proven,
            "failure_code": self.failure_code,
            "authority": self.authority.to_dict(),
            "audit_events": [event.to_dict() for event in self.audit_events],
        }


class DisposableStaticSiteStagingAdapter:
    """In-memory exact-target state for deterministic rehearsal tests."""

    adapter_id = "disposable-static-site-staging-v1"

    def __init__(self, target_identifier: str, current_artifact_digest: str | None = None):
        if not isinstance(target_identifier, str) or _TARGET_RE.fullmatch(target_identifier) is None:
            raise ValueError("disposable staging target identifier is invalid")
        if current_artifact_digest is not None and not _valid_digest(current_artifact_digest):
            raise ValueError("disposable staging artifact digest is invalid")
        self.target_identifier = target_identifier
        self.current_artifact_digest = current_artifact_digest

    def install(self, artifact_digest: str) -> None:
        if not _valid_digest(artifact_digest):
            raise ValueError("disposable staging artifact digest is invalid")
        self.current_artifact_digest = artifact_digest

    def restore(self, artifact_digest: str | None) -> None:
        if artifact_digest is not None and not _valid_digest(artifact_digest):
            raise ValueError("disposable staging rollback digest is invalid")
        self.current_artifact_digest = artifact_digest


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST_RE.fullmatch(value) is not None


def _reject(code: str, explanation: str, remedy: str) -> None:
    raise StagingRehearsalError(code, explanation, remedy)


def _validate_plan(plan: DeploymentPlan, adapter: DisposableStaticSiteStagingAdapter) -> dict[str, Any]:
    target = plan.payload.get("target", {})
    source = plan.payload.get("source", {})
    if not isinstance(target, dict) or not isinstance(source, dict):
        _reject("malformed_rehearsal_plan", "Staging plan identity or source evidence is malformed.", "Use an immutable plan produced by the current AgentKit version.")
    if target.get("environment") == "production":
        _reject("production_rehearsal_forbidden", "Disposable rehearsal cannot select production.", "Generate an explicit staging plan for a disposable target.")
    if target.get("id") != "static-site" or not deployment_contract("static-site").disposable_staging_rehearsal:
        _reject("unsupported_staging_adapter", "The disposable adapter supports static-site staging only.", "Use a static-site staging plan; other targets remain plan/check/build-only.")
    if target.get("environment") != "staging":
        _reject("staging_environment_required", "The rehearsal requires the exact staging environment.", "Generate and review a staging plan.")
    if target.get("target_identifier") != adapter.target_identifier:
        _reject("staging_target_mismatch", "The adapter target does not match the reviewed plan.", "Use a disposable adapter with the exact planned staging identifier.")
    if source.get("dirty") is not False or source.get("project_is_repository_root") is not True:
        _reject("dirty_source_blocked", "Staging rehearsal requires an exact clean repository-root source state.", "Commit or otherwise clean reviewed source, then generate a new immutable plan.")
    if not plan.payload.get("health_checks"):
        _reject("health_check_missing", "Staging rehearsal requires a declared health check.", "Generate a new plan with a concrete non-mutating staging health check.")
    if not plan.payload.get("rollback_steps"):
        _reject("rollback_missing", "Staging rehearsal requires declared rollback steps.", "Generate a new plan with concrete staging rollback steps.")
    return target


def _validate_evidence(plan: DeploymentPlan, evidence: StagingRehearsalEvidence) -> str:
    if (
        not _valid_digest(plan.digest)
        or not _valid_digest(evidence.reviewed_plan_digest)
        or not hmac.compare_digest(evidence.reviewed_plan_digest, plan.digest)
    ):
        _reject("stale_plan_evidence", "Reviewed plan evidence is stale or malformed.", "Review the exact current immutable plan digest and start a new rehearsal.")
    check_ids = {item.check_id for item in evidence.check_report.findings}
    if (
        evidence.check_report.plan_digest != plan.digest
        or not evidence.check_report.ready
        or check_ids != REQUIRED_APPLY_CHECK_IDS
    ):
        _reject("required_checks_not_passing", "Every required digest-bound check must pass before rehearsal.", "Resolve failed, unverified, stale, or missing checks and create a new report.")
    artifact = evidence.artifact_report
    artifact_valid = (
        artifact.plan_digest == plan.digest
        and _valid_digest(artifact.artifact_digest)
        and artifact.reproducible is True
        and artifact.reproduction_runs == 2
        and artifact.provenance.get("plan_digest") == plan.digest
        and artifact.source_revision == plan.payload["source"].get("revision")
        and _valid_digest(evidence.reviewed_artifact_digest)
        and hmac.compare_digest(evidence.reviewed_artifact_digest, artifact.artifact_digest)
    )
    if not artifact_valid:
        _reject("stale_artifact_evidence", "Artifact evidence is stale, non-reproducible, or unreviewed.", "Rebuild and review the exact digest-bound artifact before rehearsal.")
    return artifact.artifact_digest


def _event(name: str, plan: DeploymentPlan, artifact_digest: str, target_identifier: str) -> StagingAuditEvent:
    return StagingAuditEvent(name, plan.digest, artifact_digest, target_identifier)


def rehearse_static_site_staging(
    plan: DeploymentPlan,
    evidence: StagingRehearsalEvidence,
    adapter: DisposableStaticSiteStagingAdapter,
    *,
    failure_point: RehearsalFailurePoint = RehearsalFailurePoint.NONE,
) -> StagingRehearsalResult:
    """Install into disposable state, evaluate fixed health state, and always roll back."""

    if not isinstance(failure_point, RehearsalFailurePoint):
        raise TypeError("failure_point must be a RehearsalFailurePoint")
    target = _validate_plan(plan, adapter)
    artifact_digest = _validate_evidence(plan, evidence)
    previous = adapter.current_artifact_digest
    events = [_event("staging-rehearsal-started", plan, artifact_digest, adapter.target_identifier)]
    adapter.install(artifact_digest)
    events.append(_event("staging-artifact-installed", plan, artifact_digest, adapter.target_identifier))
    failure_code = None
    health_passed = failure_point is RehearsalFailurePoint.NONE
    if failure_point is RehearsalFailurePoint.AFTER_INSTALL:
        failure_code = "injected_staging_install_failure"
    elif failure_point is RehearsalFailurePoint.HEALTH_CHECK:
        failure_code = "injected_staging_health_failure"
    events.append(_event("staging-health-passed" if health_passed else "staging-health-failed", plan, artifact_digest, adapter.target_identifier))
    adapter.restore(previous)
    rollback_proven = adapter.current_artifact_digest == previous
    if not rollback_proven:
        _reject("staging_rollback_failed", "Disposable staging did not return to its exact prior state.", "Disable the adapter and repair rollback before any further rehearsal.")
    events.append(_event("staging-rollback-passed", plan, artifact_digest, adapter.target_identifier))
    state = StagingRehearsalState.VERIFIED if health_passed else StagingRehearsalState.ROLLED_BACK
    return StagingRehearsalResult(
        state, plan.digest, artifact_digest, target["target_identifier"], health_passed,
        rollback_proven, failure_code, tuple(events),
    )
