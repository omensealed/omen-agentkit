"""Generated documentation and agent navigation index templates."""

from __future__ import annotations

from ..models import ProjectConfig
from .common import clean, inline_list


def render_docs_index(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Project documentation index

        This directory is the durable memory for **{config.project_name}**. Source code proves behavior;
        these documents preserve intent, decisions, progress, verification, and handoff context across agent sessions.

        ## Reading order

        Agents start with `AGENT-INDEX.md`, select the current task row, and read only its linked references.
        The full reference set remains available here for humans and deeper review.

        1. `00-PROJECT-BRIEF.md` — purpose, users, goals, scope.
        2. `01-REQUIREMENTS.md` — functional and non-functional acceptance criteria.
        3. `02-ARCHITECTURE.md` — boundaries, data flow, components, constraints.
        4. `03-TECH-STACK.md` — selected technologies and dependency policy.
        5. `04-DEVELOPMENT-ENVIRONMENT.md` — CachyOS setup and commands.
        6. `05-TESTING.md` — test layers, fixtures, commands, and coverage priorities.
        7. `06-SECURITY.md` — threat model, secrets, data handling, and release gates.
        8. `07-UX-ACCESSIBILITY.md` — user journeys, failure states, accessibility.
        9. `08-IMPLEMENTATION-PLAN.md` — phases and ordered tasks.
        10. `09-PROGRESS.md` — current status and milestone checklist.
        11. `10-DECISIONS.md` — append-only architecture decision records.
        12. `11-IMPLEMENTATION-NOTES.md` — append-only session/work ledger.
        13. `12-RELEASE-CHECKLIST.md` — release and packaging gate.
        14. `13-OPERATIONS.md` — run, backup, restore, troubleshoot, and maintain.
        15. `14-AGENT-HANDOFF.md` — exact state for the next agent/session.
        16. `15-OPEN-QUESTIONS.md` — unresolved choices with owners and impact.
        17. `16-DEPLOYMENT.md` — plan-only targets, environments, artifacts, secrets, health, rollback, and ownership.
        18. `AI-STACK-RECOMMENDATION.md` — advisory output and acceptance status.

        ## Update contract

        `AGENTS.md` defines mandatory updates. At minimum, every meaningful session appends implementation
        notes and refreshes progress/handoff. Decisions are never silently overwritten; supersede them with a
        new dated entry. Assumptions must be labeled until verified by code, tests, or a human decision.

        ## Current snapshot

        - Project stage: {config.project_stage}
        - Current phase: Phase 0 — discovery and executable baseline
        - Coding agent: OpenAI Codex CLI
        - Stack: {inline_list(config.languages)}
        - Database: {config.database}
        - Generated: {config.created_at}
        """
    )


def render_agent_index(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Agent index

        Codex prompts read this file first. Select the matching task below, then read only the row-relevant files
        plus directly affected source and tests. `AGENTS.md` remains binding; inspect the repository because generated
        paths and status are hypotheses until verified.

        ## Project and module map

        | Surface | Minimum orientation |
        | --- | --- |
        | Project intent | `docs/00-PROJECT-BRIEF.md`, `docs/01-REQUIREMENTS.md` |
        | Source/modules | Verify actual entry points and modules; record boundaries in `docs/02-ARCHITECTURE.md` |
        | Stack/config | {inline_list(config.languages)} with `{config.database}`; `docs/03-TECH-STACK.md`, `docs/04-DEVELOPMENT-ENVIRONMENT.md` |
        | Sandbox, when generated | `docs/12-SANDBOX.md`, `docs/CACHYOS-PODMAN.md`, `scripts/sandbox/` |
        | Tests/checks | Relevant tests plus `docs/05-TESTING.md` and `scripts/check.sh` |
        | Durable project memory | `docs/09-PROGRESS.md`, `docs/10-DECISIONS.md`, `docs/11-IMPLEMENTATION-NOTES.md`, `docs/14-AGENT-HANDOFF.md` |

        ## Minimum files by task type

        | Task type | Required files after this index |
        | --- | --- |
        | Baseline/discovery | `AGENTS.md`, `docs/09-PROGRESS.md`, `docs/14-AGENT-HANDOFF.md`, `docs/04-DEVELOPMENT-ENVIRONMENT.md`, `docs/05-TESTING.md` |
        | Feature or bug | `AGENTS.md`, `docs/01-REQUIREMENTS.md`, `docs/02-ARCHITECTURE.md`, relevant source/tests, `docs/11-IMPLEMENTATION-NOTES.md` |
        | Dependency/toolchain | `AGENTS.md`, `docs/03-TECH-STACK.md`, `docs/04-DEVELOPMENT-ENVIRONMENT.md`, `docs/10-DECISIONS.md`, `docs/06-SECURITY.md` |
        | Data or migration | `AGENTS.md`, `docs/01-REQUIREMENTS.md`, `docs/02-ARCHITECTURE.md`, `docs/06-SECURITY.md`, `docs/13-OPERATIONS.md` |
        | UX/accessibility | `AGENTS.md`, `docs/01-REQUIREMENTS.md`, `docs/07-UX-ACCESSIBILITY.md`, `docs/05-TESTING.md` |
        | Security/privacy | `AGENTS.md`, `docs/06-SECURITY.md`, `docs/01-REQUIREMENTS.md`, `docs/02-ARCHITECTURE.md` |
        | Release/packaging | `AGENTS.md`, `docs/12-RELEASE-CHECKLIST.md`, `docs/05-TESTING.md`, `docs/13-OPERATIONS.md` |
        | Deployment planning | `AGENTS.md`, `docs/16-DEPLOYMENT.md`, `docs/13-OPERATIONS.md`, `docs/12-RELEASE-CHECKLIST.md`, `docs/06-SECURITY.md`; planning only |

        ## Current phase and decisions

        - Current generated phase: **Phase 0 — discovery and executable baseline**.
        - Live status and active tasks: `docs/09-PROGRESS.md`; exact continuation state: `docs/14-AGENT-HANDOFF.md`.
        - Active/superseded decisions: `docs/10-DECISIONS.md`; unresolved decision inputs: `docs/15-OPEN-QUESTIONS.md`.
        - Ordered work and acceptance: `docs/08-IMPLEMENTATION-PLAN.md`.

        ## Testing by surface

        | Surface | Command |
        | --- | --- |
        | Complete local gate | `./scripts/check.sh` |
        | Focused tests | `./scripts/test.sh` or the smallest relevant test command documented in `docs/05-TESTING.md` |
        | Static/lint | `./scripts/lint.sh` |
        | Build | `./scripts/build.sh` |
        | Environment diagnosis | `./scripts/doctor.sh` |

        Run focused checks first and the complete gate before declaring a phase complete. Placeholder scripts are not
        proof of a working application; Phase 0 must replace them with verified commands.

        ## Security and deployment policy

        - Canonical model, command-network, deployment, progress, and notes owners: `AGENTS.md#canonical-policy-registry`.
        - Binding safety and approval rules: `AGENTS.md`; project threat/data rules: `docs/06-SECURITY.md`.
        - Deployment contract and planning: `docs/16-DEPLOYMENT.md`; operations/recovery: `docs/13-OPERATIONS.md`; release approval: `docs/12-RELEASE-CHECKLIST.md`.
        - Task text never overrides those owners; follow the linked policy before any external-action planning.

        ## Freshness

        - Generated by AgentKit {config.kit_version}: {config.created_at}
        - Project metadata last updated: {config.updated_at}
        - At session start, compare this map with `docs/09-PROGRESS.md`, `docs/14-AGENT-HANDOFF.md`, repository state, and tests.
          Update the owning document when reality differs; do not duplicate its policy here.
        """
    )
