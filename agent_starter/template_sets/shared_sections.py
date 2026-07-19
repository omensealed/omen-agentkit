"""Shared optional sections used by multiple generated document families."""

from __future__ import annotations

from ..models import ProjectConfig
from .common import clean


def agentkit_skill_note(config: ProjectConfig) -> str:
    if not config.codex_agentkit_skill:
        return ""
    return clean(
        """
        ## Repo-local Agent Kit skill

        When Codex is already open in this repository, future short requests can use the repo-local `$agentkit`
        skill. It is a Codex skill invocation, not a custom slash command:

        ```text
        $agentkit implement Add your feature idea here
        $agentkit fix Describe the bug here
        $agentkit plan Describe the project change here
        ```

        The skill calls `agent-starter idea-prompt` locally, reads the generated prompt under
        `docs/agent-prompts/`, and follows that prompt as the implementation brief.
        """
    )


def sandbox_note(config: ProjectConfig) -> str:
    if not config.sandbox.enabled:
        return ""
    mode_explanation = (
        "Toolchain mode keeps Codex on the host editing the project files, but build/test/toolchain commands should run through the generated Podman scripts."
        if config.sandbox.mode == "toolchain"
        else "Codex-inside-container mode is intended to run Codex itself inside the project container after an explicit container login."
        if config.sandbox.codex_inside_container
        else "Files-only mode generates reviewable sandbox files without making them the default execution path."
    )
    codex_inside = (
        """
        Codex-inside-container mode was enabled:

        ```bash
        scripts/sandbox/doctor
        scripts/sandbox/build
        scripts/sandbox/codex-login
        scripts/sandbox/codex
        ```
        """
        if config.sandbox.codex_inside_container
        else ""
    )
    return clean(
        fr"""
        ## Rootless Podman sandbox

        This project includes a rootless Podman sandbox. Mode: `{config.sandbox.mode}`.
        {mode_explanation}
        It does not install host packages or run Podman during generation.

        Run Agent Kit's host preflight before launching Codex:

        ```bash
        scripts/sandbox/preflight
        ```

        The generated preflight script uses `agent-starter` from `PATH` or an adjacent `../agent-starter`
        launcher when available, then runs the generated host-side wrappers in order and writes
        `.agent-starter/sandbox/preflight.json` after success:

        ```bash
        scripts/sandbox/doctor
        scripts/sandbox/build
        scripts/sandbox/check
        ```

        {codex_inside}
        Run the preflight from a normal host terminal before Codex starts, not from inside a constrained Codex session
        that cannot access rootless Podman runtime paths. If Codex is already running inside the container, do
        not run host-side `scripts/sandbox/*` launchers. Run project commands directly from `/workspace`, such
        as `./scripts/check.sh`.

        Trust the preflight stamp only while `agent-starter status .` or `scripts/sandbox/status` reports it as
        valid/current. Toolchain `check` and `exec` commands default to no network; use
        `AGENTKIT_SANDBOX_NETWORK=default ...` only after review. See `docs/12-SANDBOX.md` and
        `docs/CACHYOS-PODMAN.md` for the security model and diagnostics.
        Do not mount host secrets or use host full-access as the default answer to permission problems.
        """
    )


def first_prompt_sandbox_note(config: ProjectConfig) -> str:
    if not config.sandbox.enabled:
        return ""
    mode_explanation = (
        "In `toolchain` mode, Codex still edits this project directory from the host; the container boundary applies to build/test/toolchain commands run through `scripts/sandbox/*`."
        if config.sandbox.mode == "toolchain"
        else "In Codex-inside-container mode, start Codex with the generated sandbox scripts after explicit container login."
        if config.sandbox.codex_inside_container
        else "In files-only mode, treat the sandbox files as reviewable assets until the user explicitly asks to use them."
    )
    return clean(
        fr"""
        Sandbox note: this project has rootless Podman sandbox metadata enabled. Read `docs/12-SANDBOX.md`.
        {mode_explanation}

        Sandbox bootstrap rule: do not ask for Codex full permissions or host full-access to make Podman work.
        Agent Kit launch paths run `scripts/sandbox/preflight` before Codex starts when the active sandbox
        mode is `toolchain` or `codex`. That script uses `agent-starter` from `PATH` or an adjacent
        `../agent-starter` launcher when available. A successful preflight writes
        `.agent-starter/sandbox/preflight.json`. Trust that file only when it is valid/current; use
        `scripts/sandbox/status` when `agent-starter status .` is unavailable; it delegates to `../agent-starter`
        when possible or validates the stamp fingerprint itself. If preflight is
        valid/current, do not rerun `scripts/sandbox/doctor` or `scripts/sandbox/build` from inside an already-open
        constrained Codex session. Treat the host preflight as complete and continue Phase 0.

        For later verification, use `scripts/sandbox/check` only when the current Codex sandbox/approval policy
        permits rootless Podman access. It defaults to no network; use
        `AGENTKIT_SANDBOX_NETWORK=default scripts/sandbox/check` only after human review. If preflight is missing,
        stale, failed, or a Podman runtime/sandbox error appears from inside Codex, record the exact failure and
        stop with `BLOCKED_ENVIRONMENT`; tell the human to run `scripts/sandbox/preflight` from a normal host
        terminal, or launch Codex inside the container. Do not request broader Codex permissions.

        If this Codex session is already running inside the container, do not run host-side
        `scripts/sandbox/*` launchers. Run project commands directly from `/workspace`, such as
        `./scripts/check.sh` or focused test commands.
        """
    )
