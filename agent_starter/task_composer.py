"""Strict, non-executing task-specific question composer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Mapping

from .policy_fragments import CODEX_DEPLOYMENT_BOUNDARY, DEPLOYMENT_ACTION_BOUNDARY, DEPLOYMENT_SCOPE_BOUNDARY


TASK_TEXT_LIMIT = 4000
TASK_SECRET_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\s*[:=]\s*\S+)|"
    r"\bsk-[A-Za-z0-9_-]{16,}\b"
)


class TaskValidationError(ValueError):
    """Raised when task-composer input is unsafe or malformed."""


class TaskKind(str, Enum):
    FEATURE = "feature"
    FIX = "fix"
    CHANGE = "change"
    REVIEW = "review"
    TESTS_DOCS = "tests-docs"
    DEPLOYMENT_PLAN = "deployment-plan"


@dataclass(frozen=True, slots=True)
class TaskQuestion:
    key: str
    prompt: str
    required: bool = True
    default: str = ""
    choices: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class TaskDefinition:
    kind: TaskKind
    label: str
    questions: tuple[TaskQuestion, ...]
    prompt_template: str


@dataclass(frozen=True, slots=True)
class TaskPacket:
    kind: TaskKind
    label: str
    answers: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "answers": dict(self.answers),
            "codex_deployment_boundary": list(CODEX_DEPLOYMENT_BOUNDARY),
        }


@dataclass(frozen=True, slots=True)
class TaskContract:
    """Review-required interpretation of one validated task packet."""

    packet: TaskPacket
    attempt: str
    must_not_change: str
    likely_areas: str
    acceptance_checks: str
    risks_and_approvals: str
    state: str = "review-required"

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "packet": self.packet.to_dict(),
            "attempt": self.attempt,
            "must_not_change": self.must_not_change,
            "likely_areas": self.likely_areas,
            "acceptance_checks": self.acceptance_checks,
            "risks_and_approvals": self.risks_and_approvals,
        }


@dataclass(frozen=True, slots=True)
class ApprovedTaskPrompt:
    """Prompt data released by an explicit approval action; never a launch instruction."""

    contract: TaskContract
    prompt: str
    state: str = "approved"

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "contract": self.contract.to_dict(),
            "prompt": self.prompt,
        }


TASK_DEFINITIONS: dict[TaskKind, TaskDefinition] = {
    TaskKind.FEATURE: TaskDefinition(
        TaskKind.FEATURE,
        "Add a feature",
        (
            TaskQuestion("outcome", "What should a person be able to do afterward?"),
            TaskQuestion("example", "Give one concrete example."),
            TaskQuestion(
                "preserve",
                "What existing behavior must remain unchanged?",
                default="Preserve existing documented behavior and public interfaces.",
            ),
            TaskQuestion("acceptance", "How will you know it works?"),
        ),
        "feature",
    ),
    TaskKind.FIX: TaskDefinition(
        TaskKind.FIX,
        "Fix a problem",
        (
            TaskQuestion("steps", "What did you do?"),
            TaskQuestion("observed", "What happened?"),
            TaskQuestion("expected", "What should have happened?"),
            TaskQuestion("error_text", "Include the exact error text, with secrets removed.", required=False),
            TaskQuestion(
                "frequency",
                "Is it consistent or intermittent?",
                default="unknown",
                choices=(("consistent", "Consistent"), ("intermittent", "Intermittent"), ("unknown", "Not known yet")),
            ),
        ),
        "bug",
    ),
    TaskKind.CHANGE: TaskDefinition(
        TaskKind.CHANGE,
        "Change existing behavior",
        (
            TaskQuestion("current", "What behavior exists now?"),
            TaskQuestion("desired", "What should replace it?"),
            TaskQuestion("compatibility", "Which users, data, or interfaces must remain compatible?"),
        ),
        "feature",
    ),
    TaskKind.REVIEW: TaskDefinition(
        TaskKind.REVIEW,
        "Review or improve code",
        (
            TaskQuestion("focus", "What code or behavior should be reviewed?"),
            TaskQuestion("concern", "What concern or improvement matters most?"),
            TaskQuestion("preserve", "What behavior or interface must remain unchanged?"),
            TaskQuestion("acceptance", "What evidence should the review produce?"),
        ),
        "cleanup",
    ),
    TaskKind.TESTS_DOCS: TaskDefinition(
        TaskKind.TESTS_DOCS,
        "Improve tests/documentation",
        (
            TaskQuestion("area", "Which behavior, test layer, or documentation area needs improvement?"),
            TaskQuestion("gap", "What is missing, unclear, flaky, or unverified today?"),
            TaskQuestion("preserve", "What existing workflow or wording must remain compatible?"),
            TaskQuestion("acceptance", "How will the improvement be verified?"),
        ),
        "docs",
    ),
    TaskKind.DEPLOYMENT_PLAN: TaskDefinition(
        TaskKind.DEPLOYMENT_PLAN,
        "Prepare a deployment plan",
        (
            TaskQuestion("target", "What environment is the plan for?"),
            TaskQuestion("current_state", "What is already built and verified locally?"),
            TaskQuestion("constraints", "What safety, data, downtime, or compatibility constraints apply?"),
            TaskQuestion("approvals", "Which remote or production actions require human approval?"),
            TaskQuestion("acceptance", "What must the reviewable plan contain to be useful?"),
        ),
        "release-prep",
    ),
}


def parse_task_kind(value: str | TaskKind) -> TaskKind:
    if isinstance(value, TaskKind):
        return value
    if not isinstance(value, str):
        raise TaskValidationError("Task kind must be one of the listed composer choices.")
    try:
        return TaskKind(value.strip().lower())
    except ValueError as exc:
        raise TaskValidationError("Task kind must be one of the listed composer choices.") from exc


def task_composer_schema() -> list[dict[str, object]]:
    return [
        {
            "kind": definition.kind.value,
            "label": definition.label,
            "questions": [
                {
                    "key": question.key,
                    "prompt": question.prompt,
                    "required": question.required,
                    "default": question.default,
                    "choices": [
                        {"value": value, "label": label} for value, label in question.choices
                    ],
                }
                for question in definition.questions
            ],
        }
        for definition in TASK_DEFINITIONS.values()
    ]


def _task_text(value: object, *, field: str, required: bool, default: str) -> str:
    if value is None or value == "":
        value = default
    if not isinstance(value, str):
        raise TaskValidationError(f"Task answer {field} must be text.")
    if "\x00" in value or any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise TaskValidationError(f"Task answer {field} contains unsupported control content.")
    cleaned = value.strip()
    if required and not cleaned:
        raise TaskValidationError(f"Task answer {field} is required.")
    if len(cleaned) > TASK_TEXT_LIMIT:
        raise TaskValidationError(f"Task answer {field} exceeds {TASK_TEXT_LIMIT} characters.")
    if TASK_SECRET_RE.search(cleaned):
        raise TaskValidationError(
            f"Task answer {field} appears to contain a credential or private key; remove it and rotate it if real."
        )
    return cleaned


def compose_task_packet(
    kind: str | TaskKind,
    answers: Mapping[str, object],
) -> TaskPacket:
    selected = parse_task_kind(kind)
    if not isinstance(answers, Mapping):
        raise TaskValidationError("Task answers must be an object keyed by the displayed questions.")
    definition = TASK_DEFINITIONS[selected]
    allowed = {question.key for question in definition.questions}
    unexpected = sorted(set(answers) - allowed)
    if unexpected:
        raise TaskValidationError(f"Task answers contain unexpected fields: {', '.join(unexpected)}.")
    normalized: list[tuple[str, str]] = []
    for question in definition.questions:
        value = _task_text(
            answers.get(question.key),
            field=question.key,
            required=question.required,
            default=question.default,
        )
        if question.choices and value not in {choice for choice, _ in question.choices}:
            raise TaskValidationError(
                f"Task answer {question.key} must be one of: "
                + ", ".join(choice for choice, _ in question.choices)
                + "."
            )
        normalized.append((question.key, value))
    return TaskPacket(selected, definition.label, tuple(normalized))


def render_task_request(packet: TaskPacket) -> str:
    definition = TASK_DEFINITIONS[packet.kind]
    answers = dict(packet.answers)
    lines = [
        "Read `docs/AGENT-INDEX.md` first, then only the task-relevant files linked by its matching row.",
        "Treat `AGENTS.md` as binding.",
        f"Task type: {packet.label}",
    ]
    for question in definition.questions:
        value = answers[question.key] or "Not provided."
        lines.append(f"{question.prompt.rstrip('?')}: {value}")
    lines.extend(CODEX_DEPLOYMENT_BOUNDARY)
    if packet.kind is TaskKind.DEPLOYMENT_PLAN:
        lines.extend((
            DEPLOYMENT_SCOPE_BOUNDARY,
            DEPLOYMENT_ACTION_BOUNDARY,
            "Canonical policy: `AGENTS.md#canonical-policy-registry` and `docs/13-OPERATIONS.md`.",
        ))
    lines.append("Ask concise clarifying questions only when repository evidence cannot resolve a blocking ambiguity.")
    return "\n".join(lines)


def build_task_contract(packet: TaskPacket) -> TaskContract:
    """Derive a complete review surface without inspecting a repository or executing work."""

    answers = dict(packet.answers)
    unknown_areas = (
        "Not identified in the answers; Codex should inspect the project and report likely files "
        "before making broad changes."
    )
    generic_risk = (
        "Stop for human approval before destructive changes, compatibility breaks, remote actions, "
        "or work outside this bounded task."
    )
    if packet.kind is TaskKind.FEATURE:
        attempt = f"{answers['outcome']} Example: {answers['example']}"
        must_not_change = answers["preserve"]
        acceptance = answers["acceptance"]
        risks = generic_risk
    elif packet.kind is TaskKind.FIX:
        attempt = (
            f"Reproduce these steps: {answers['steps']} Correct the observed behavior: "
            f"{answers['observed']} Expected behavior: {answers['expected']}"
        )
        must_not_change = "Preserve existing data, public interfaces, and unrelated behavior."
        acceptance = (
            f"Verify the expected behavior: {answers['expected']} Add or run a focused regression check; "
            f"reported frequency is {answers['frequency']}."
        )
        risks = generic_risk
    elif packet.kind is TaskKind.CHANGE:
        attempt = f"Replace this behavior: {answers['current']} Desired behavior: {answers['desired']}"
        must_not_change = answers["compatibility"]
        acceptance = f"Verify the desired behavior and compatibility boundary: {answers['desired']}"
        risks = f"Compatibility is the primary risk. {generic_risk}"
    elif packet.kind is TaskKind.REVIEW:
        attempt = f"Review {answers['focus']} with emphasis on {answers['concern']}"
        must_not_change = answers["preserve"]
        acceptance = answers["acceptance"]
        risks = generic_risk
    elif packet.kind is TaskKind.TESTS_DOCS:
        attempt = f"Improve {answers['area']} by closing this gap: {answers['gap']}"
        must_not_change = answers["preserve"]
        acceptance = answers["acceptance"]
        risks = generic_risk
    else:
        attempt = (
            f"Prepare a deployment plan for {answers['target']} based on this verified state: "
            f"{answers['current_state']}"
        )
        must_not_change = f"{DEPLOYMENT_SCOPE_BOUNDARY} {DEPLOYMENT_ACTION_BOUNDARY} Constraints: {answers['constraints']}"
        acceptance = answers["acceptance"]
        risks = f"Constraints: {answers['constraints']} Required approvals: {answers['approvals']}"
        unknown_areas = (
            "Deployment documentation, configuration, and workflow areas; identify exact files during review."
        )
    return TaskContract(
        packet=packet,
        attempt=attempt,
        must_not_change=must_not_change,
        likely_areas=unknown_areas,
        acceptance_checks=acceptance,
        risks_and_approvals=risks,
    )


def render_task_contract(contract: TaskContract) -> str:
    """Render the five plan-required review sections and explicit available actions."""

    return "\n\n".join((
        "Task contract — review required",
        f"What Codex will attempt\n{contract.attempt}",
        f"What it must not change\n{contract.must_not_change}",
        f"Files/areas likely involved\n{contract.likely_areas}",
        f"Tests/acceptance checks\n{contract.acceptance_checks}",
        f"Risks/approvals that may be encountered\n{contract.risks_and_approvals}",
        "Actions\n- Edit answers\n- Approve prompt",
    ))


def approve_task_contract(contract: TaskContract) -> ApprovedTaskPrompt:
    """Release prompt text after the caller records an explicit human approval action."""

    return ApprovedTaskPrompt(contract=contract, prompt=render_task_request(contract.packet))
