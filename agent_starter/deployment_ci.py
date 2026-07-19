"""Typed CI identity, permission, and provenance policy for deployment work.

This module is policy data plus rendering helpers.  It does not authenticate,
contact GitHub or a deployment target, create workflow jobs, or apply changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Mapping


ACTION_PIN_REVIEW_DATE = "2026-07-18"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
_USES_RE = re.compile(r"^\s*uses:\s*(\S+)(?:\s+#\s*(\S+))?\s*$")


@dataclass(frozen=True, slots=True)
class GitHubActionPin:
    action: str
    version: str
    commit_sha: str
    reviewed_on: str
    source_url: str


@dataclass(frozen=True, slots=True)
class GitHubActionPinIssue:
    path: str
    code: str
    explanation: str
    remedy: str


@dataclass(frozen=True, slots=True)
class ContainerImagePin:
    image: str
    digest: str
    platform: str
    reviewed_on: str
    source_url: str

    @property
    def reference(self) -> str:
        return f"{self.image}@{self.digest}"


@dataclass(frozen=True, slots=True)
class DeploymentCIPolicy:
    deployment_enabled: bool
    identity_mode: str
    long_lived_credentials_allowed: bool
    build_permissions: tuple[str, ...]
    future_deploy_permissions: tuple[str, ...]
    separate_build_and_deploy_jobs: bool
    separate_environments: bool
    production_protected_environment: bool
    production_manual_approval: bool
    artifact_evidence: tuple[str, ...]


def _pin(
    action: str,
    version: str,
    commit_sha: str,
    *,
    reviewed_on: str = ACTION_PIN_REVIEW_DATE,
) -> GitHubActionPin:
    return GitHubActionPin(
        action, version, commit_sha, reviewed_on,
        f"https://github.com/{action}/commit/{commit_sha}",
    )


GITHUB_ACTION_PINS: Mapping[str, GitHubActionPin] = MappingProxyType({
    "actions/checkout": _pin(
        "actions/checkout",
        "v7.0.0",
        "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        reviewed_on="2026-07-19",
    ),
    "actions/setup-python": _pin("actions/setup-python", "v6.3.0", "ece7cb06caefa5fff74198d8649806c4678c61a1"),
    "actions/setup-node": _pin("actions/setup-node", "v6.5.0", "249970729cb0ef3589644e2896645e5dc5ba9c38"),
    "actions/setup-go": _pin("actions/setup-go", "v6.4.0", "4a3601121dd01d1626a1e23e37211e3254c1c06c"),
    "actions/setup-java": _pin("actions/setup-java", "v5.2.0", "be666c2fcd27ec809703dec50e508c2fdc7f6654"),
    "actions/dependency-review-action": _pin("actions/dependency-review-action", "v5.0.0", "a1d282b36b6f3519aa1f3fc636f609c47dddb294"),
    "actions/upload-artifact": _pin("actions/upload-artifact", "v7.0.1", "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"),
    "actions/attest": _pin("actions/attest", "v4.2.0", "f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"),
    "actions/download-artifact": _pin("actions/download-artifact", "v8.0.1", "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"),
})


CI_PROVIDER_IMAGES: Mapping[str, ContainerImagePin] = MappingProxyType({
    "arch": ContainerImagePin(
        "docker.io/library/archlinux",
        "sha256:d5ae80f3489764be5c8e27fe19b7ebfe876b35d7b42aaa5ab99aff2bf7438c34",
        "linux/amd64",
        ACTION_PIN_REVIEW_DATE,
        "https://hub.docker.com/_/archlinux",
    ),
    "debian": ContainerImagePin(
        "docker.io/library/debian",
        "sha256:4cc40147060d766a649b100b175ac0a346a5b5c8fbcc5677c2f471854ee4e55c",
        "linux/amd64",
        ACTION_PIN_REVIEW_DATE,
        "https://hub.docker.com/_/debian",
    ),
})


DEPLOYMENT_CI_POLICY = DeploymentCIPolicy(
    deployment_enabled=False,
    identity_mode="github-oidc",
    long_lived_credentials_allowed=False,
    build_permissions=("contents: read",),
    future_deploy_permissions=("contents: read", "id-token: write"),
    separate_build_and_deploy_jobs=True,
    separate_environments=True,
    production_protected_environment=True,
    production_manual_approval=True,
    artifact_evidence=("sha256-checksum", "artifact-attestation"),
)


def github_action_reference(action: str) -> str:
    """Return a reviewable immutable workflow reference for a known action."""

    try:
        pin = GITHUB_ACTION_PINS[action]
    except KeyError as exc:
        raise ValueError(f"GitHub action has no reviewed immutable pin: {action}") from exc
    return f"{pin.action}@{pin.commit_sha} # {pin.version}"


def _issue(line: int, code: str, explanation: str, remedy: str) -> GitHubActionPinIssue:
    return GitHubActionPinIssue(f"workflow.line[{line}].uses", code, explanation, remedy)


def validate_github_action_references(workflow_text: str) -> tuple[GitHubActionPinIssue, ...]:
    """Validate managed workflow action references without network access."""

    if not isinstance(workflow_text, str):
        raise TypeError("workflow_text must be a string")
    issues: list[GitHubActionPinIssue] = []
    for line_number, line in enumerate(workflow_text.splitlines(), start=1):
        if not line.lstrip().startswith("uses:"):
            continue
        match = _USES_RE.fullmatch(line)
        if match is None or "@" not in match.group(1):
            issues.append(_issue(
                line_number, "malformed_action_reference",
                "GitHub Action reference is malformed.",
                "Use `owner/action@<40-character-sha> # vMAJOR.MINOR.PATCH`.",
            ))
            continue
        reference, version = match.groups()
        action, commit_sha = reference.rsplit("@", 1)
        if _SHA_RE.fullmatch(commit_sha) is None:
            issues.append(_issue(
                line_number, "mutable_action_reference",
                "GitHub Action reference is not pinned to a full lowercase 40-character commit SHA.",
                "Resolve the reviewed release through official GitHub pages and pin its exact full commit SHA.",
            ))
            continue
        if version is None or _VERSION_RE.fullmatch(version) is None:
            issues.append(_issue(
                line_number, "missing_action_version_comment",
                "Immutable action pin lacks a human-readable semantic release comment.",
                "Add `# vMAJOR.MINOR.PATCH` matching the reviewed release.",
            ))
            continue
        reviewed = GITHUB_ACTION_PINS.get(action)
        if reviewed is None:
            issues.append(_issue(
                line_number, "unreviewed_action",
                "Action is not present in the reviewed generated-workflow pin registry.",
                "Complete the maintainer action review and add one typed registry entry before generating it.",
            ))
        elif reviewed.commit_sha != commit_sha or reviewed.version != version:
            issues.append(_issue(
                line_number, "reviewed_action_pin_mismatch",
                "Action SHA and version comment do not match the reviewed registry entry.",
                "Update the registry, source evidence, version comment, templates, tests, and implementation note together.",
            ))
    return tuple(issues)
