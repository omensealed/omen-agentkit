"""Human project-entry and next-action document templates."""

from __future__ import annotations

import shlex

from ..models import ProjectConfig
from .common import clean, inline_list
from .shared_sections import agentkit_skill_note, sandbox_note


def render_project_readme(config: ProjectConfig) -> str:
    return clean(
        f"""
        # {config.project_name}

        {config.description or "Project description is being refined during discovery."}

        ## Status

        This repository was initialized with the CLI AI Agent Starter Kit. The authoritative project brief,
        requirements, architecture notes, implementation plan, progress ledger, and agent handoff are in `docs/`.

        ## Start here

        Read `START_HERE.md` first for the short project/status/action summary. Continue with `NEXT_STEPS.md` for
        the full beginner-safe local sequence and an explanation of checks that Phase 0 still needs to verify.

        ```bash
        ./scripts/doctor.sh
        ./scripts/bootstrap-dev.sh
        ./scripts/check.sh
        ```

        Then launch Codex:

        ```bash
        ./START_AGENT.sh
        ```

        The first agent task is stored in `FIRST_PROMPT.md`. Contributors and agents must follow `AGENTS.md`.

        {sandbox_note(config)}

        {agentkit_skill_note(config)}

        ## Selected direction

        - Type: {config.project_type}
        - Stage: {config.project_stage}
        - Stack: {inline_list(config.languages)}
        - Database: {config.database}
        - Platforms: {inline_list(config.target_platforms)}
        - Coding agent: OpenAI Codex CLI
        - Architecture posture: keep files responsibility-focused; avoid god files that collect unrelated UI,
          domain, persistence, networking, state, configuration, and test code.

        ## Documentation

        See [`docs/README.md`](docs/README.md) for the complete documentation map and current phase.
        """
    )


def render_start_here(config: ProjectConfig) -> str:
    if config.project_mode == "existing":
        status = (
            "AgentKit prepared a generated review layer for an existing project. Verify its description, "
            "commands, tests, and architecture against the actual repository before changing behavior."
        )
        next_action = (
            "Open `NEXT_STEPS.md`, then compare the generated brief and implementation plan with the existing "
            "code. Record corrections before the first implementation change."
        )
    else:
        status = (
            "This is a generated starting point, not proof that the application or its test harness is complete. "
            "Phase 0 should establish the smallest real local baseline."
        )
        next_action = (
            "Open `NEXT_STEPS.md`, then establish the smallest real build, check, and test baseline before adding "
            "a broad feature set."
        )
    return clean(
        f"""
        # Start here

        ## Project summary

        **{config.project_name}** — {config.description or "The project purpose is still being refined."}

        - Type/stage: {config.project_type} / {config.project_stage}
        - Stack: {inline_list(config.languages)}
        - Data: {config.database}

        ## Current status

        {status}

        ## First safe local commands

        These inspect or check local state. The bootstrap command prints a plan and changes nothing by default.

        ```bash
        ./scripts/doctor.sh
        ./scripts/bootstrap-dev.sh
        ./scripts/check.sh
        ```

        ## Next action

        {next_action}

        ## Help and detail

        - `NEXT_STEPS.md` — full guided setup and Codex handoff.
        - `docs/README.md` — documentation map.
        - `AGENTS.md` — safety and contribution boundaries.
        """
    )


def render_next_steps(config: ProjectConfig) -> str:
    root = shlex.quote(str(config.root))
    github_note = (
        "A GitHub Actions workflow was generated because you explicitly enabled it. Keep GitHub remote creation "
        "and pushes paused until local checks and Phase 0 documentation are useful."
        if config.github_actions
        else "GitHub Actions were deferred by default. Keep the project local until `./scripts/check.sh` and Phase 0 prove there is a useful baseline to publish or back up remotely."
    )
    check_note = (
        "For a new project, the generated `build`, `lint`, and `test` scripts may still be placeholders. That is "
        "intentional. Phase 0 should replace them with the smallest real build, static check, and test harness for "
        "the app being created."
        if config.project_mode == "new"
        else "For an existing project, the generated `build`, `lint`, and `test` scripts are starting guesses based "
        "on the selected stack. Phase 0 should verify them against the actual codebase before refactoring."
    )
    return clean(
        f"""
        # Next steps

        This file is the first thing to read after generation. It keeps the first session local, reviewable,
        and focused on getting a real Codex-ready project baseline.

        ## 1. Enter the project

        ```bash
        cd {root}
        ```

        ## 2. Inspect the generated contract

        Read these before asking Codex to change code:

        - `AGENTS.md`
        - `FIRST_PROMPT.md`
        - `docs/00-PROJECT-BRIEF.md`
        - `docs/08-IMPLEMENTATION-PLAN.md`
        - `docs/11-IMPLEMENTATION-NOTES.md`

        ## 3. Check the local environment

        ```bash
        ./scripts/doctor.sh
        ./scripts/bootstrap-dev.sh
        ```

        `bootstrap-dev.sh` detects CachyOS/Arch, Debian, or Ubuntu, checks installed packages, and prints the
        provider-specific plan. It changes nothing by default. APT index refresh and package installation are
        separate explicit actions that require your review and normal sudo approval.

        ## 4. Run the current checks

        ```bash
        ./scripts/check.sh
        agent-starter status .
        ```

        {check_note}

        ## 5. Start Codex when ready

        ```bash
        ./START_AGENT.sh
        ```

        If the rootless Podman sandbox is active, `START_AGENT.sh` and `agent-starter launch .` run
        `agent-starter sandbox preflight .` before Codex starts. Fix any preflight failure from this host
        terminal instead of asking Codex for full host permissions.

        If Codex is missing or not authorized, use:

        ```bash
        ./scripts/setup-agent.sh
        ./scripts/agent-status.sh
        ```

        Authorization belongs to the official `codex` CLI. Do not paste OAuth tokens, API keys, cookies,
        browser-profile data, or keyring data into project files or prompts.

        {sandbox_note(config)}

        ## 6. Keep GitHub local-first

        {github_note}

        Before enabling CI or creating a remote repository, complete the Phase 0 baseline, inspect `.gitignore`,
        and confirm local AI/runtime artifacts are not part of the project source:

        ```bash
        agent-starter github-ready {root}
        ```

        ## 7. Continue later without losing context

        From outside the generated project, the starter can produce a copy/paste continuation prompt:

        ```bash
        agent-starter prompt {root} --request "Describe the next feature or fix"
        ```

        Add `--template feature`, `--template bug`, `--template cleanup`, `--template docs`,
        `--template test-baseline`, or `--template release-prep` for task-specific guidance.

        For guided prompt writing:

        ```bash
        agent-starter prompt {root} --interactive
        ```

        The task composer starts with Add a feature, Fix a problem, Change existing behavior,
        Review or improve code, Improve tests/documentation, or Prepare a deployment plan, then asks
        only questions relevant to that choice. Deployment output is planning-only and cannot deploy.

        {agentkit_skill_note(config)}

        If you are considering a local Ollama model, assess it first instead of switching blindly:

        ```bash
        agent-starter ollama-check {root} --request "Continue the next project phase"
        ```

        Treat any local-model handoff as a warning-rich assessment. Codex remains the configured agent for this
        workspace unless a human deliberately changes the architecture.

        ## 8. Optional local mirror

        To review a local or SSH rsync mirror without running it:

        ```bash
        agent-starter rsync-plan {root} /path/to/project-mirror
        ```

        The plan uses `.agent-starter/rsync-excludes` and does nothing unless you rerun it with `--run`.
        """
    )
