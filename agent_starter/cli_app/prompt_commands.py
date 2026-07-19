"""Codex continuation-prompt rendering and interactive CLI presentation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Sequence

from ..models import ProjectConfig
from ..policy_fragments import render_prompt_policy_references
from ..task_composer import (
    TASK_DEFINITIONS,
    TASK_SECRET_RE,
    TaskKind,
    TaskPacket,
    approve_task_contract,
    build_task_contract,
    compose_task_packet,
    render_task_contract,
)
from ..wizard import CancelledByUser
from .project_runtime import load_generated_config


PROMPT_TEMPLATES: dict[str, tuple[str, tuple[str, ...]]] = {
    "feature": (
        "Feature Implementation Template",
        (
            "Identify the smallest vertical slice that proves the feature works.",
            "Update or add acceptance criteria before implementing broad behavior.",
            "Add focused tests around the new user-visible behavior and important failure paths.",
            "Keep compatibility and migration notes explicit when data, CLI, API, or file formats change.",
        ),
    ),
    "bug": (
        "Bug Fix Template",
        (
            "Reproduce or characterize the bug before changing implementation code.",
            "Add a regression test that fails on the current behavior when practical.",
            "Fix the narrowest cause, then check for adjacent cases without broad rewrites.",
            "Document the root cause, affected versions or flows, and verification result.",
        ),
    ),
    "cleanup": (
        "Cleanup Template",
        (
            "Preserve behavior first; avoid mixing cleanup with feature changes.",
            "Use existing tests or add characterization coverage before risky rewrites.",
            "Keep the diff small enough to review and explain any abstraction added.",
            "Remove dead code only after confirming it has no documented or tested use.",
        ),
    ),
    "docs": (
        "Documentation Template",
        (
            "Verify behavior from code, tests, scripts, and generated files before documenting it.",
            "Update the nearest user-facing and maintainer-facing docs together when workflow changes.",
            "Keep examples copy/pasteable and aligned with safe approval boundaries.",
            "Record any durable decisions or changed assumptions in the project memory docs.",
        ),
    ),
    "test-baseline": (
        "Test Baseline Template",
        (
            "Inventory current build, lint, test, and run commands before adding tools.",
            "Prefer deterministic local tests with temporary directories and synthetic data.",
            "Replace placeholder scripts with the smallest real commands that prove the baseline.",
            "Document skipped, missing, or intentionally deferred coverage with exact follow-up tasks.",
        ),
    ),
    "release-prep": (
        "Release Preparation Template",
        (
            "Run the full local check suite and inspect release, security, and operations docs.",
            "Confirm version, changelog, license, packaging, and generated artifacts are consistent.",
            "Check for secrets, local AI artifacts, debug files, caches, and uncommitted changes.",
            "Do not publish, push, tag, deploy, or create external resources without explicit approval.",
        ),
    ),
}

_DEFAULT_DELTA_REFERENCES = (
    "docs/AGENT-INDEX.md",
    "AGENTS.md",
    "docs/14-AGENT-HANDOFF.md",
    "docs/09-PROGRESS.md",
    "docs/15-OPEN-QUESTIONS.md",
)
_DELTA_TEXT_LIMIT = 4000
_DELTA_ITEM_LIMIT = 20
_REFERENCE_RE = re.compile(r"[A-Za-z0-9_./-]+")


@dataclass(frozen=True, slots=True)
class ContinuationDelta:
    current_objective: str
    changes_since_handoff: str
    current_failures: str
    relevant_references: tuple[str, ...]
    acceptance_checks: str
    unresolved_decisions: tuple[str, ...]


def _delta_text(value: str, *, field: str, default: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Continuation {field} must be text.")
    cleaned = re.sub(r"\s+", " ", value).strip() or default
    if len(cleaned) > _DELTA_TEXT_LIMIT:
        raise ValueError(f"Continuation {field} exceeds {_DELTA_TEXT_LIMIT} characters.")
    if TASK_SECRET_RE.search(cleaned):
        raise ValueError(f"Continuation {field} appears to contain a credential or private key. Remove it and rotate it if it was real.")
    return cleaned


def _delta_references(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or len(values) > _DELTA_ITEM_LIMIT:
        raise ValueError(f"Continuation relevant references must contain at most {_DELTA_ITEM_LIMIT} paths or modules.")
    result: list[str] = list(_DEFAULT_DELTA_REFERENCES)
    for value in values:
        cleaned = _delta_text(value, field="relevant reference", default="")
        pure = PurePosixPath(cleaned)
        if not cleaned or pure.is_absolute() or ".." in pure.parts or _REFERENCE_RE.fullmatch(cleaned) is None:
            raise ValueError("Continuation relevant references must be safe project-relative paths or dotted module names.")
        if cleaned not in result:
            result.append(cleaned)
    return tuple(result)


def _delta_decisions(config: ProjectConfig, values: Sequence[str]) -> tuple[str, ...]:
    source = values or tuple(config.open_questions)
    if isinstance(source, (str, bytes)) or len(source) > _DELTA_ITEM_LIMIT:
        raise ValueError(f"Continuation unresolved decisions must contain at most {_DELTA_ITEM_LIMIT} items.")
    decisions: list[str] = []
    for value in source:
        cleaned = _delta_text(value, field="unresolved decision", default="")
        if cleaned:
            decisions.append(cleaned)
    return tuple(decisions) or ("None explicitly supplied; do not invent one. Consult `docs/15-OPEN-QUESTIONS.md` only when the current task or handoff links it.",)


def build_continuation_delta(
    config: ProjectConfig,
    *,
    request: str,
    changes: str = "",
    failures: str = "",
    relevant_references: Sequence[str] = (),
    acceptance_checks: str = "",
    unresolved_decisions: Sequence[str] = (),
) -> ContinuationDelta:
    return ContinuationDelta(
        current_objective=_delta_text(request, field="objective", default="Continue the next documented project phase."),
        changes_since_handoff=_delta_text(
            changes,
            field="changes since handoff",
            default="No explicit delta supplied; inspect `docs/14-AGENT-HANDOFF.md` and the working tree for changes since the last handoff.",
        ),
        current_failures=_delta_text(
            failures,
            field="current failures",
            default="No current failure supplied; verify the latest recorded check in `docs/14-AGENT-HANDOFF.md` before editing.",
        ),
        relevant_references=_delta_references(relevant_references),
        acceptance_checks=_delta_text(
            acceptance_checks,
            field="acceptance checks",
            default="Run focused checks for affected behavior, then `./scripts/check.sh`; record exact results or the blocker.",
        ),
        unresolved_decisions=_delta_decisions(config, unresolved_decisions),
    )


def _render_continuation_delta(delta: ContinuationDelta) -> str:
    references = "\n".join(f"  - `{item}`" for item in delta.relevant_references)
    decisions = "\n".join(f"  - {item}" for item in delta.unresolved_decisions)
    return (
        "## Continuation delta\n\n"
        f"- Current objective: {delta.current_objective}\n"
        f"- Changes since last handoff: {delta.changes_since_handoff}\n"
        f"- Current failures: {delta.current_failures}\n"
        "- Exact relevant docs/modules:\n"
        f"{references}\n"
        f"- Acceptance checks: {delta.acceptance_checks}\n"
        "- Unresolved decisions:\n"
        f"{decisions}\n"
        "- Context boundary: Do not reread every historical implementation-note entry. Read older ledger history only "
        "when the selected task references it or current evidence is insufficient.\n\n"
    )


def _prompt_template_section(template: str) -> str:
    if not template:
        return ""
    try:
        title, items = PROMPT_TEMPLATES[template]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt template: {template}") from exc
    lines = [f"## {title}", ""]
    lines.extend(f"- {item}" for item in items)
    return "\n".join(lines) + "\n\n"


def render_continuation_prompt(
    config: ProjectConfig,
    *,
    request: str,
    phase: str,
    template: str = "",
    changes: str = "",
    failures: str = "",
    relevant_references: Sequence[str] = (),
    acceptance_checks: str = "",
    unresolved_decisions: Sequence[str] = (),
) -> str:
    request = request.strip() or "Continue the next documented project phase."
    phase = phase.strip() or "next safe phase"
    if TASK_SECRET_RE.search(request) or TASK_SECRET_RE.search(phase):
        raise ValueError("The prompt request appears to contain a credential or private key. Remove it and rotate it if it was real.")
    stack = ", ".join(item for item in config.languages if item.strip()) or "not decided"
    platforms = ", ".join(item for item in config.target_platforms if item.strip()) or "not decided"
    tests = ", ".join(item for item in config.tests if item.strip()) or "not decided"
    delta = build_continuation_delta(
        config,
        request=request,
        changes=changes,
        failures=failures,
        relevant_references=relevant_references,
        acceptance_checks=acceptance_checks,
        unresolved_decisions=unresolved_decisions,
    )
    return (
        f"You are continuing work on **{config.project_name or 'this project'}** in the repository root.\n\n"
        "Read `docs/AGENT-INDEX.md` first. Use its matching task row and read only the task-relevant files it "
        "links. Read `AGENTS.md` completely and follow it.\n\n"
        "Do not assume the documents are fully current. Inspect the actual files and behavior before changing code.\n\n"
        "## Project Snapshot\n\n"
        f"- Project type: {config.project_type or 'not recorded'}\n"
        f"- Starting mode/stage: {config.project_mode or 'not recorded'} / {config.project_stage or 'not recorded'}\n"
        f"- Stack hypothesis: {stack}\n"
        f"- Database: {config.database or 'not decided'}\n"
        f"- Target platforms: {platforms}\n"
        f"- Expected test layers: {tests}\n"
        f"- Current phase focus: {phase}\n\n"
        f"{_render_continuation_delta(delta)}"
        "## User request\n\n"
        f"{request}\n\n"
        f"{_prompt_template_section(template)}"
        "## Work Method\n\n"
        "1. Inspect the relevant code, docs, scripts, tests, and generated metadata before editing.\n"
        "2. Restate the smallest safe interpretation of the request and identify risks or missing decisions.\n"
        "3. Add or update a regression test first where practical; otherwise document why inspection/manual verification is appropriate.\n"
        "4. Make the smallest coherent change that satisfies the request without unrelated refactors or dependency churn.\n"
        "5. Run targeted checks during work, then run `./scripts/check.sh` before finishing unless a blocker prevents it.\n"
        "6. Apply `AGENTS.md`'s Required documentation procedure and canonical policy registry before stopping.\n\n"
        f"{render_prompt_policy_references()}\n"
        "## Final Response Requirements\n\n"
        "Report the baseline discovered, files changed, behavior changed, tests/checks run with exact results, docs updated, risks or decisions, and the exact next task.\n"
    )


def _prompt_interactive_value(label: str, *, default: str = "", required: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            value = input(f"{label}{suffix}: ").strip() or default
        except (EOFError, KeyboardInterrupt) as exc:
            print("")
            raise CancelledByUser("Prompt generation cancelled.") from exc
        if required and not value:
            print("Please enter a value.")
            continue
        if value and TASK_SECRET_RE.search(value):
            print("That entry resembles a credential. Do not put passwords, tokens, API keys, or private keys in prompts.")
            continue
        return value


def _prompt_interactive_choice(label: str, options: dict[str, str], *, default: str) -> str:
    print(label)
    keys = list(options)
    for index, key in enumerate(keys, start=1):
        print(f"  {index}. {options[key]}")
    lookup = {str(index): key for index, key in enumerate(keys, start=1)}
    lookup.update({key: key for key in keys})
    while True:
        value = _prompt_interactive_value("Choice", default=default).lower()
        if value in lookup:
            return lookup[value]
        print("Choose a listed number or name.")


def collect_interactive_task_packet() -> TaskPacket:
    print("Guided Codex continuation prompt")
    choices = {kind.value: definition.label for kind, definition in TASK_DEFINITIONS.items()}
    task_type = _prompt_interactive_choice("What kind of work is next?", choices, default=TaskKind.FEATURE.value)
    definition = TASK_DEFINITIONS[TaskKind(task_type)]
    answers: dict[str, str] = {}
    for question in definition.questions:
        if question.choices:
            answers[question.key] = _prompt_interactive_choice(
                question.prompt,
                dict(question.choices),
                default=question.default,
            )
        else:
            answers[question.key] = _prompt_interactive_value(
                question.prompt,
                default=question.default,
                required=question.required,
            )
    return compose_task_packet(task_type, answers)


def collect_interactive_prompt_request() -> tuple[str, str, str]:
    while True:
        packet = collect_interactive_task_packet()
        contract = build_task_contract(packet)
        print("")
        print(render_task_contract(contract))
        action = _prompt_interactive_choice(
            "Review action",
            {"edit": "Edit answers", "approve": "Approve prompt"},
            default="edit",
        )
        if action == "edit":
            print("Re-enter the task answers. Nothing has been approved or launched.")
            continue
        approved = approve_task_contract(contract)
        definition = TASK_DEFINITIONS[packet.kind]
        return approved.prompt, f"{packet.kind.value} continuation", definition.prompt_template


def command_prompt(args: argparse.Namespace) -> int:
    config = load_generated_config(Path(args.project))
    if args.interactive:
        request, phase, template = collect_interactive_prompt_request()
    else:
        request, phase, template = args.request or "", args.phase, args.template or ""
    prompt = render_continuation_prompt(
        config,
        request=request,
        phase=phase,
        template=template,
        changes=args.changes,
        failures=args.failures,
        relevant_references=args.relevant_reference,
        acceptance_checks=args.acceptance,
        unresolved_decisions=args.unresolved_decision,
    )
    if args.output:
        path = Path(args.output)
        if path.exists() and not args.force:
            print(f"Refusing to replace {path}; add --force.")
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt, encoding="utf-8")
        print(f"Wrote {path}")
    else:
        sys.stdout.write(prompt)
    return 0


def register_prompt_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    prompt = subparsers.add_parser("prompt", help="Generate a copy/paste Codex continuation prompt for a generated project.")
    prompt.add_argument("project", nargs="?", default=".")
    prompt.add_argument("--request", "-r", default="", help="Feature, fix, or next-step request for Codex.")
    prompt.add_argument("--phase", default="next safe phase", help="Phase or work focus to name in the prompt.")
    prompt.add_argument("--changes", default="", help="Concise changes since the last handoff.")
    prompt.add_argument("--failures", default="", help="Current failing command/result summary, with secrets removed.")
    prompt.add_argument(
        "--relevant-reference",
        action="append",
        default=[],
        help="Exact project-relative file or dotted module relevant to this continuation; repeat as needed.",
    )
    prompt.add_argument("--acceptance", default="", help="Focused acceptance checks for this continuation.")
    prompt.add_argument(
        "--unresolved-decision",
        action="append",
        default=[],
        help="Unresolved decision that may block or redirect this task; repeat as needed.",
    )
    prompt.add_argument(
        "--template",
        choices=sorted(PROMPT_TEMPLATES),
        help="Add task-specific guidance to the generated prompt.",
    )
    prompt.add_argument("--interactive", "-i", action="store_true", help="Ask guided questions before generating the prompt.")
    prompt.add_argument("--output", "-o", help="Write the prompt to a file instead of stdout.")
    prompt.add_argument("--force", action="store_true", help="Replace an existing --output file.")
    prompt.set_defaults(func=command_prompt)
