"""Typed, plan-only deployment target contracts.

This module defines vocabulary and authority boundaries. It deliberately does
not build artifacts, execute plans, contact remote systems, or handle secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class DeploymentTarget(str, Enum):
    STATIC_SITE = "static-site"
    OCI_IMAGE = "oci-image"
    LINUX_SERVICE_BUNDLE = "linux-service-bundle"
    SSH_RSYNC = "ssh-rsync"


class DeploymentOperation(str, Enum):
    PLAN = "plan"
    CHECK = "check"
    BUILD = "build"
    PUSH = "push"
    APPLY = "apply"


@dataclass(frozen=True, slots=True)
class DeploymentContractIssue:
    path: str
    code: str
    explanation: str
    remedy: str


class DeploymentContractError(ValueError):
    def __init__(self, issue: DeploymentContractIssue):
        self.issue = issue
        super().__init__(f"{issue.path}: {issue.explanation}")


@dataclass(frozen=True, slots=True)
class DeploymentTargetContract:
    target: DeploymentTarget
    display_label: str
    artifact_kind: str
    summary: str
    enabled_operations: tuple[DeploymentOperation, ...]
    reviewed_future_operations: tuple[DeploymentOperation, ...]
    required_plan_sections: tuple[str, ...]
    allows_network: bool = False
    allows_remote_writes: bool = False
    allows_secret_values: bool = False
    disposable_staging_rehearsal: bool = False
    production_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, non-secret presentation form."""

        return {
            "target": self.target.value,
            "display_label": self.display_label,
            "artifact_kind": self.artifact_kind,
            "summary": self.summary,
            "enabled_operations": [item.value for item in self.enabled_operations],
            "reviewed_future_operations": [item.value for item in self.reviewed_future_operations],
            "required_plan_sections": list(self.required_plan_sections),
            "allows_network": self.allows_network,
            "allows_remote_writes": self.allows_remote_writes,
            "allows_secret_values": self.allows_secret_values,
            "disposable_staging_rehearsal": self.disposable_staging_rehearsal,
            "production_ready": self.production_ready,
        }


_REQUIRED_PLAN_SECTIONS = (
    "source revision and dirty state",
    "environment and exact target identity",
    "artifact inputs and expected outputs",
    "artifact provenance and digest",
    "local and remote filesystem effects",
    "exact commands for separate human review",
    "network destinations and purpose",
    "credential mechanism by reference only",
    "health checks and success evidence",
    "rollback and recovery",
    "monitoring, log locations, and maintenance ownership",
)


def _contract(
    target: DeploymentTarget,
    label: str,
    artifact_kind: str,
    summary: str,
    future: tuple[DeploymentOperation, ...],
    *,
    local_zip_build: bool = False,
    disposable_staging_rehearsal: bool = False,
) -> DeploymentTargetContract:
    enabled = (DeploymentOperation.PLAN, DeploymentOperation.CHECK)
    if local_zip_build:
        enabled += (DeploymentOperation.BUILD,)
    return DeploymentTargetContract(
        target=target,
        display_label=label,
        artifact_kind=artifact_kind,
        summary=summary,
        enabled_operations=enabled,
        reviewed_future_operations=tuple(operation for operation in future if operation not in enabled),
        required_plan_sections=_REQUIRED_PLAN_SECTIONS,
        disposable_staging_rehearsal=disposable_staging_rehearsal,
    )


DEPLOYMENT_TARGET_CONTRACTS: Mapping[DeploymentTarget, DeploymentTargetContract] = MappingProxyType({
    DeploymentTarget.STATIC_SITE: _contract(
        DeploymentTarget.STATIC_SITE,
        "Static-site artifact",
        "immutable static-site directory or archive",
        "Plan a locally reproducible static-site artifact; no hosting adapter is implied.",
        (DeploymentOperation.CHECK, DeploymentOperation.BUILD),
        local_zip_build=True,
        disposable_staging_rehearsal=True,
    ),
    DeploymentTarget.OCI_IMAGE: _contract(
        DeploymentTarget.OCI_IMAGE,
        "OCI image artifact",
        "OCI-compatible image",
        "Plan a local image build and inspection; registry push is not supported.",
        (DeploymentOperation.CHECK, DeploymentOperation.BUILD),
    ),
    DeploymentTarget.LINUX_SERVICE_BUNDLE: _contract(
        DeploymentTarget.LINUX_SERVICE_BUNDLE,
        "Linux service bundle",
        "reviewable Linux service bundle",
        "Plan a host-neutral service bundle; installation and service changes are not supported.",
        (DeploymentOperation.CHECK, DeploymentOperation.BUILD),
        local_zip_build=True,
    ),
    DeploymentTarget.SSH_RSYNC: _contract(
        DeploymentTarget.SSH_RSYNC,
        "SSH/rsync transfer plan",
        "reviewable file-transfer manifest",
        "Plan an explicit SSH/rsync transfer; connection and remote writes are not supported.",
        (DeploymentOperation.CHECK,),
    ),
})


def parse_deployment_target(value: object, *, path: str = "deployment.target") -> DeploymentTarget:
    """Strictly parse an exact supported target identifier."""

    choices = ", ".join(target.value for target in DeploymentTarget)
    if not isinstance(value, str):
        raise DeploymentContractError(DeploymentContractIssue(
            path=path,
            code="invalid_deployment_target_type",
            explanation="Deployment target must be an exact string identifier.",
            remedy=f"Use one of: {choices}.",
        ))
    try:
        return DeploymentTarget(value)
    except ValueError as exc:
        raise DeploymentContractError(DeploymentContractIssue(
            path=path,
            code="unsupported_deployment_target",
            explanation=f"Deployment target {value!r} has no reviewed adapter contract.",
            remedy=f"Use one of: {choices}.",
        )) from exc


def deployment_contract(value: object) -> DeploymentTargetContract:
    """Return the immutable contract for one strictly parsed target."""

    return DEPLOYMENT_TARGET_CONTRACTS[parse_deployment_target(value)]


def list_deployment_contracts() -> tuple[DeploymentTargetContract, ...]:
    """Return contracts in stable public-enum order."""

    return tuple(DEPLOYMENT_TARGET_CONTRACTS[target] for target in DeploymentTarget)
