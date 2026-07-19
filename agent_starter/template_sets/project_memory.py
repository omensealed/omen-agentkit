"""Durable generated project progress, decision, work, and handoff templates."""

from __future__ import annotations

from ..models import ProjectConfig
from .common import clean, inline_list, md_list


def render_progress_doc(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Progress

        ## Current status

        - Current phase: **Phase 0 — Discovery and executable baseline**
        - Overall state: **Not started by implementation agent**
        - Last updated: {config.created_at}
        - Coding agent: OpenAI Codex CLI
        - Next milestone: reproducible setup, baseline tests, verified architecture map

        ## Milestones

        - [ ] Phase 0 — Discovery and executable baseline
        - [ ] Phase 1 — Architecture and core vertical slice
        - [ ] Phase 2 — Reliability, security, and data lifecycle
        - [ ] Phase 3 — User experience, accessibility, and performance
        - [ ] Phase 4 — Packaging, CI, and release readiness

        ## Active tasks

        - [ ] Run the initial prompt in `FIRST_PROMPT.md`.
        - [ ] Verify or correct the generated project assumptions.
        - [ ] Establish real setup/build/test/lint commands.
        - [ ] Record the first implementation-note entry and handoff.

        ## Blockers

        {md_list(config.open_questions, empty="- No blocker has been verified yet; unresolved choices are tracked in `15-OPEN-QUESTIONS.md`.")}

        ## Update rule

        Keep this file concise. Detailed chronology belongs in `11-IMPLEMENTATION-NOTES.md`; durable choices belong
        in `10-DECISIONS.md`. Every status claim should point to a test, command, artifact, or human decision.
        """
    )


def render_decisions_doc(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Architecture and project decisions

        Use append-only Architecture Decision Record entries. A later decision may supersede an earlier one but must
        not erase its historical context.

        ## ADR-0001 — Initial project workflow

        - Date: {config.created_at}
        - Status: Accepted
        - Context: The project needs a repeatable, beginner-friendly workflow across CLI coding-agent sessions.
        - Decision: Use `AGENTS.md` as canonical agent policy and `docs/` as durable project memory. Require a stable
          `./scripts/check.sh` gate, implementation-note ledger, progress file, decision log, and handoff.
        - Consequences: Agents spend a small amount of time maintaining docs, reducing repeated discovery and hidden state.

        ## ADR-0002 — Initial stack direction

        - Date: {config.created_at}
        - Status: Proposed; verify during Phase 0
        - Context: User answers and any advisor output suggest {inline_list(config.languages)} with `{config.database}`.
        - Decision: Begin discovery with this stack and minimal dependencies. Do not create a broad rewrite until the
          first vertical slice and toolchain are validated.
        - Consequences: The choice may be superseded if measured requirements or existing-code compatibility demand it.

        ## ADR template

        ```text
        ## ADR-NNNN — Title
        - Date:
        - Status: Proposed | Accepted | Superseded by ADR-NNNN | Rejected
        - Context:
        - Options considered:
        - Decision:
        - Security/data/UX/operations impact:
        - Consequences and rollback:
        - Verification:
        ```
        """
    )


def render_implementation_notes(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Implementation notes

        This is the append-only work ledger. Add the newest entry at the top below this introduction or consistently
        at the bottom; do not mix ordering. Never replace history with a summary.

        ## {config.created_at} — Starter kit generation

        - Agent/client: CLI AI Agent Starter Kit {config.kit_version}
        - Objective/phase: Initialize project governance, documentation, safe agent launch, and CachyOS tooling notes.
        - Files/subsystems: `AGENTS.md`, `.codex/config.toml`, `docs/`, scripts, optional CI, and Codex launch helpers.
        - Decisions: Canonical instructions live in `AGENTS.md`; progress and technical memory live in version control.
        - Verification: Generator validation must confirm required files, executable scripts, and no unresolved tokens.
        - Security/data impact: No credentials were requested or stored. Codex owns its OAuth authorization.
        - Problems/assumptions: Stack and requirements remain provisional until Phase 0 inspection.
        - Next step: Run `FIRST_PROMPT.md` with Codex and append the first implementation session.

        ## Entry template

        ```text
        ## YYYY-MM-DDTHH:MM:SSZ — concise title
        - Agent/client:
        - Objective/phase:
        - Starting state/baseline:
        - Files/subsystems changed:
        - Implementation and decisions:
        - Commands/tests and exact results:
        - Security/data/migration/performance/UX impact:
        - Problems, failed approaches, and evidence:
        - Remaining work and exact next step:
        ```
        """
    )


def render_handoff_doc(config: ProjectConfig) -> str:
    unresolved = "\n".join(
        f"  {line}" for line in md_list(config.open_questions, empty="- None explicitly recorded; do not invent one.").splitlines()
    )
    return clean(
        f"""
        # Agent handoff

        ## Current state

        - Phase: Phase 0 has not yet been executed by the implementation agent.
        - Workspace: {config.project_path}
        - Coding agent: OpenAI Codex CLI
        - Stack hypothesis: {inline_list(config.languages)} / {config.database}
        - Last known check result: Not run on the target machine.

        ## Continuation delta

        - Current objective: Complete Phase 0 discovery and establish the executable baseline.
        - Changes since last handoff: The starter workspace was generated; implementation work has not been verified yet.
        - Current failures: No target-machine check result is recorded yet.
        - Exact relevant docs/modules: `docs/AGENT-INDEX.md`, `AGENTS.md`, and the Baseline/discovery row's files.
        - Acceptance checks: Run the documented safe checks, replace placeholders with verified commands, and record exact results.
        - Unresolved decisions:
        {unresolved}

        ## Next agent instructions

        1. Read `docs/AGENT-INDEX.md` first, then `AGENTS.md` and the Baseline/discovery row's relevant files.
        2. Run `./scripts/doctor.sh`, inspect the repository, and record the actual baseline.
        3. Complete only Phase 0 unless the user explicitly expands scope.
        4. Update this handoff, progress, decisions, open questions, and implementation notes before stopping.

        ## Do not assume

        - Generated stack recommendations are final.
        - Placeholder commands prove the application builds or runs.
        - A missing test means behavior is unimportant.
        - Existing files are obsolete merely because they look old.
        - Authorization to edit the workspace implies authorization to access unrelated paths, services, or credentials.

        ## Handoff template

        ```text
        Phase and task:
        Working branch/commit:
        Current objective:
        Changes since last handoff:
        Current failures and exact command/output summary:
        Exact relevant docs/modules:
        Acceptance checks:
        Unresolved decisions and ADR links:
        What is complete/partially complete:
        Data/schema/API compatibility impact:
        Security/UX/performance concerns:
        Best next action:
        Human decision required:
        ```
        """
    )


def render_open_questions_doc(config: ProjectConfig) -> str:
    initial = config.open_questions or [
        "What is the smallest end-to-end user journey that proves the project is useful?",
        "Which requirements are release blockers versus later ideas?",
        "What existing data, interfaces, saves, or URLs require backward compatibility?",
        "Which target platform and package format is the first release priority?",
    ]
    return clean(
        f"""
        # Open questions

        Resolve only questions that change architecture, safety, acceptance criteria, or near-term implementation.
        Record a decision and remove/supersede the question when answered.

        {md_list(initial)}

        ## Question template

        ```text
        - Question:
        - Why it matters now:
        - Options/evidence:
        - Owner:
        - Needed by phase/date:
        - Resolution and linked ADR:
        ```
        """
    )
