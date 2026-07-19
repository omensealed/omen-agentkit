"""Generated project scope, requirements, and phased implementation templates."""

from __future__ import annotations

from ..models import ProjectConfig
from ..toolchains import DATABASE_COMMANDS
from .common import clean, inline_list, md_list


def render_project_brief(config: ProjectConfig) -> str:
    default_goals = (
        "- Deliver a small, usable vertical slice with repeatable setup and tests.\n"
        "- Refine additional goals with the user during Phase 0."
    )
    return clean(
        f"""
        # Project brief

        ## One-sentence purpose

        {config.description or "To be refined with the user before feature implementation."}

        ## Project profile

        - Name: {config.project_name}
        - Type: {config.project_type}
        - Starting condition: {config.project_mode} project, stage `{config.project_stage}`
        - Intended users: {config.target_users or "To be clarified"}
        - Target platforms: {inline_list(config.target_platforms)}
        - Packaging/distribution targets: {inline_list(config.packaging_targets)}

        ## Goals

        {md_list(config.goals, empty=default_goals)}

        ## Non-goals

        {md_list(config.non_goals, empty="- Unbounded rewrites, speculative features, and premature scale work are out of scope until documented.")}

        ## Product principles

        - A new user can set up, run, test, and understand the project from checked-in instructions.
        - User-facing errors explain what happened and how to recover without exposing sensitive details.
        - The smallest maintainable stack that satisfies the requirements wins.
        - Security and privacy controls scale with actual risk; they are not postponed after architecture hardens.
        - Progress remains recoverable across CLI-agent sessions through the docs ledger.

        ## Success measures to refine

        - A documented happy-path user journey works end to end.
        - Setup succeeds on CachyOS from a clean account using documented commands.
        - The default test/check command is deterministic and passes locally and in CI.
        - Known limitations and next milestones are explicit rather than hidden in chat history.
        """
    )


def render_requirements_doc(config: ProjectConfig) -> str:
    security_flags = []
    if config.user_accounts:
        security_flags.append("authentication, authorization, session handling, and account recovery")
    if config.handles_personal_data:
        security_flags.append("personal-data minimization, retention, export, and deletion")
    if config.handles_payments:
        security_flags.append("payment-provider boundary and avoidance of raw payment data")
    if config.network_access:
        security_flags.append("network timeout, retry, offline, and untrusted-response handling")
    return clean(
        f"""
        # Requirements

        ## Requirement-writing rule

        Replace assumptions with numbered, testable statements. Each implementation phase must reference the
        requirement IDs it satisfies. Do not mark a requirement complete without a reproducible test or inspection.

        ## Functional requirements

        - **FR-001 — Executable baseline:** A developer can follow the documented setup and launch the application.
        - **FR-002 — Core journey:** Define and implement the smallest complete user journey for {config.project_type}.
        - **FR-003 — Validation:** Invalid, missing, or hostile input is rejected safely with actionable feedback.
        - **FR-004 — Persistence:** {DATABASE_COMMANDS.get(config.database, DATABASE_COMMANDS['undecided'])}
        - **FR-005 — Recovery:** Expected failures do not corrupt durable state and expose a documented recovery path.
        - **FR-006 — Observability:** Important failures are diagnosable without logging secrets or personal data.

        ## Non-functional requirements

        - **NFR-001 — Maintainability:** Keep modules cohesive, interfaces explicit, and dependencies minimal.
        - **NFR-002 — Testability:** Core behavior is testable without GUI, live network, or production services.
        - **NFR-003 — Portability:** Primary development support targets CachyOS; target runtime platforms are
          {inline_list(config.target_platforms)}.
        - **NFR-004 — Performance:** Establish measurable budgets only after profiling the representative workflow.
        - **NFR-005 — Accessibility:** Keyboard use, readable contrast, clear focus/error states, and reduced-motion
          behavior apply wherever the project has a visual interface.
        - **NFR-006 — Security:** Apply least privilege, safe defaults, dependency review, secret isolation, and
          abuse-case tests appropriate to the project's exposure.

        ## Risk-specific requirements

        {md_list(security_flags, empty="- No elevated risk category was selected; the agent must still complete a basic threat model.")}

        ## Acceptance criteria template

        For every feature, document:

        1. Given/when/then happy path.
        2. Boundary and invalid-input behavior.
        3. Permission and data-access behavior.
        4. Persistence/migration behavior when applicable.
        5. Automated tests and manual verification.
        6. User-facing documentation and recovery steps.
        """
    )


def render_implementation_plan(config: ProjectConfig) -> str:
    existing_extra = "characterize current behavior, identify dead/legacy paths, and preserve user data compatibility" if config.project_mode == "existing" else "confirm the smallest vertical slice and create only the structure needed for it"
    return clean(
        f"""
        # Implementation plan

        The agent may refine tasks after discovery but must preserve phase intent and update this file before broad work.

        ## Phase 0 — Discovery and executable baseline

        - [ ] Read all project instructions/docs and inventory the workspace.
        - [ ] Verify the project brief with concrete acceptance criteria and resolve blocking open questions.
        - [ ] {existing_extra.capitalize()}.
        - [ ] Run `./scripts/doctor.sh`; document exact versions and missing CachyOS packages.
        - [ ] Establish setup, run, build, lint, and test commands in scripts and docs.
        - [ ] Add a deterministic smoke test and capture the baseline result.
        - [ ] Map entry points, data flow, trust boundaries, persistent formats, and external services.
        - [ ] Update progress, decisions, implementation notes, and handoff.

        **Exit gate:** a clean checkout can be set up and checked from documentation, or every blocker is reproduced and recorded.

        ## Phase 1 — Architecture and core vertical slice

        - [ ] Approve architecture boundaries and the first end-to-end user journey.
        - [ ] Implement the smallest useful slice through UI/entry, domain logic, persistence/adapters, and output.
        - [ ] Keep files responsibility-focused; avoid creating or extending a single god file that owns unrelated concerns.
        - [ ] Add unit and integration tests for success, validation, and failure paths.
        - [ ] Keep public interfaces and persistent formats explicit and versionable.

        **Exit gate:** the core journey is demonstrable, tested, and documented without relying on hidden manual steps.

        ## Phase 2 — Reliability, security, and data lifecycle

        - [ ] Complete the threat model and abuse cases.
        - [ ] Harden validation, permissions, timeouts, error recovery, logging, and secret handling.
        - [ ] Implement migrations/backups/restore or saved-state compatibility where applicable.
        - [ ] Add regression tests for high-impact failure and corruption scenarios.

        **Exit gate:** risk controls are verified and destructive/data-changing paths have tested recovery.

        ## Phase 3 — User experience, accessibility, and performance

        - [ ] Test the full journey as a new user on CachyOS.
        - [ ] Complete empty/loading/error/offline/permission states.
        - [ ] Perform accessibility checks appropriate to CLI or visual UI.
        - [ ] Profile representative workloads before optimizing; record before/after measurements.

        **Exit gate:** the project is understandable, responsive, and recoverable for its intended user.

        ## Phase 4 — Packaging, CI, and release readiness

        - [ ] Make local and GitHub CI gates equivalent.
        - [ ] Produce target packages/artifacts from documented commands.
        - [ ] Verify fresh-install, upgrade/migration, uninstall/cleanup, and rollback paths.
        - [ ] Complete security, license, documentation, and release checklists.

        **Exit gate:** a reproducible release candidate passes all checks from a clean environment.
        """
    )
