"""Canonical generated-policy ownership and prompt references.

Durable policy statements live in this registry and are rendered once into the
binding generated workspace contract. Task prompts link to the owning files
instead of carrying independent copies that can drift.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CanonicalPolicy:
    key: str
    title: str
    owners: tuple[str, ...]
    statement: str


@dataclass(frozen=True, slots=True)
class PolicyConflict:
    path: str
    code: str
    explanation: str
    remedy: str


CODEX_DEPLOYMENT_BOUNDARY = (
    "Codex may prepare code, documentation, tests, and deployment plans.",
    "Codex may run local deployment plan, check, and build operations inside the configured sandbox.",
    "Codex must stop before remote apply, repository push, release publication, database migration, or secret access "
    "unless a separate human-approved tool operation is invoked.",
    'A prompt saying "deploy it" is not sufficient production authorization.',
)


CANONICAL_POLICIES: dict[str, CanonicalPolicy] = {
    "model": CanonicalPolicy(
        key="model",
        title="Model selection",
        owners=(".agent-starter/project.json", ".codex/config.toml"),
        statement=(
            "The project metadata owns the reviewed selection and the Codex TOML owns the effective project-local "
            "keys. Prompts never select, rename, route around, or silently downgrade the model; launch validation "
            "must stop on unavailable explicit policy."
        ),
    ),
    "command-network": CanonicalPolicy(
        key="command-network",
        title="Command network",
        owners=(".codex/config.toml", "docs/06-SECURITY.md"),
        statement=(
            "Codex command network access is controlled only by the reviewed project TOML and defaults off. A "
            "project's application-level network requirement is separate and never enables command networking."
        ),
    ),
    "deployment": CanonicalPolicy(
        key="deployment",
        title="Deployment and external actions",
        owners=("AGENTS.md#canonical-policy-registry", "docs/16-DEPLOYMENT.md", "docs/13-OPERATIONS.md", "docs/12-RELEASE-CHECKLIST.md"),
        statement=(
            " ".join(CODEX_DEPLOYMENT_BOUNDARY)
            + " These permissions grant no package-installation, remote-resource, credential-value, or "
            "production-data authority."
        ),
    ),
    "progress-ledger": CanonicalPolicy(
        key="progress-ledger",
        title="Current progress",
        owners=("docs/09-PROGRESS.md",),
        statement=(
            "This is the only current-status ledger. Update it when task or phase state changes; chronology belongs "
            "in implementation notes."
        ),
    ),
    "implementation-notes": CanonicalPolicy(
        key="implementation-notes",
        title="Implementation notes",
        owners=("docs/11-IMPLEMENTATION-NOTES.md",),
        statement=(
            "This is the append-only meaningful-session ledger for objectives, changes, exact checks/results, "
            "decisions, implications, unresolved problems, and next steps."
        ),
    ),
}


DEPLOYMENT_SCOPE_BOUNDARY = "Scope boundary: planning only."
DEPLOYMENT_ACTION_BOUNDARY = (
    "Codex must not deploy, publish, push, create remote resources, or change production data."
)


def render_canonical_policy_registry() -> str:
    lines = ["## Canonical policy registry", ""]
    for policy in CANONICAL_POLICIES.values():
        owners = ", ".join(f"`{owner}`" for owner in policy.owners)
        lines.append(f"- **{policy.title}** (`{policy.key}`; owners: {owners}): {policy.statement}")
    return "\n".join(lines)


def render_prompt_policy_references() -> str:
    """Render owner references only; detailed policy remains in its owner."""

    return (
        "## Canonical policy references\n\n"
        "- Model selection: `.agent-starter/project.json` and `.codex/config.toml`.\n"
        "- Command network: `.codex/config.toml`; project security context: `docs/06-SECURITY.md`.\n"
        "- Security, approvals, and deployment: `AGENTS.md#canonical-policy-registry`, `docs/16-DEPLOYMENT.md`, "
        "`docs/13-OPERATIONS.md`, and `docs/12-RELEASE-CHECKLIST.md`.\n"
        "- Current status: `docs/09-PROGRESS.md`; append-only work record: "
        "`docs/11-IMPLEMENTATION-NOTES.md`.\n\n"
        "This prompt does not override those owners or grant an exception to their policies.\n"
    )


_CONFLICT_RULES: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "model.outdated-baseline",
        re.compile(r"(?:gpt[- ]?5\.5.{0,80}recommended|recommended.{0,80}gpt[- ]?5\.5)", re.IGNORECASE),
        "An obsolete GPT-5.5 recommendation conflicts with the reviewed project model policy.",
        "Remove the copied recommendation and reference .agent-starter/project.json plus .codex/config.toml.",
    ),
    (
        "command-network.enabled",
        re.compile(r"\bnetwork_access\s*=\s*true\b", re.IGNORECASE),
        "Command network access is enabled contrary to the conservative workspace policy.",
        "Keep command network access false unless a separately reviewed canonical policy explicitly changes it.",
    ),
    (
        "deployment.prompt-authority",
        re.compile(r"\bdeployment\s+is\s+authorized\s+by\s+this\s+prompt\b", re.IGNORECASE),
        "A task prompt claims deployment authority that prompts cannot grant.",
        "Reference the canonical deployment policy and require separate human approval for external actions.",
    ),
    (
        "deployment.deploy-it-authority",
        re.compile(r"\bprompt\s+saying\s+[\"']?deploy\s+it[\"']?\s+is\s+sufficient\s+production\s+authorization\b", re.IGNORECASE),
        "A prompt incorrectly treats free-form deploy wording as production authorization.",
        "State that deploy wording is insufficient and require a separate human-approved tool operation.",
    ),
    (
        "progress-ledger.conflicting-path",
        re.compile(r"docs/10-PROGRESS\.md", re.IGNORECASE),
        "A second progress-ledger path conflicts with docs/09-PROGRESS.md.",
        "Use docs/09-PROGRESS.md as the only current-status ledger.",
    ),
    (
        "implementation-notes.conflicting-path",
        re.compile(r"docs/12-IMPLEMENTATION-NOTES\.md", re.IGNORECASE),
        "A second implementation-notes path conflicts with docs/11-IMPLEMENTATION-NOTES.md.",
        "Use docs/11-IMPLEMENTATION-NOTES.md as the append-only work ledger.",
    ),
)


def find_policy_conflicts(documents: Mapping[str, str]) -> list[PolicyConflict]:
    """Return deterministic policy conflicts without interpreting document text as instructions."""

    issues: list[PolicyConflict] = []
    for path in sorted(documents):
        text = documents[path]
        for code, pattern, explanation, remedy in _CONFLICT_RULES:
            if pattern.search(text):
                issues.append(PolicyConflict(path=path, code=code, explanation=explanation, remedy=remedy))
    return issues
