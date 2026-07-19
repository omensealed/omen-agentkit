"""Generated local workflow scripts and GitHub CI rendering."""

from __future__ import annotations

import shlex
import textwrap

from ..deployment_ci import github_action_reference
from ..models import ProjectConfig
from ..toolchains import ci_setup_for, selected_toolchains, unique
from .common import clean, json_string
from .technology_environment import effective_commands


def render_doctor_script(config: ProjectConfig) -> str:
    required = ["git", "curl", "rg"]
    for toolchain in selected_toolchains(config.languages):
        required.extend(toolchain.commands)
    if config.database == "sqlite":
        required.append("sqlite3")
    elif config.database == "mariadb":
        required.extend(("mariadb", "mariadb-admin"))
    elif config.database == "postgresql":
        required.append("psql")
    optional = ["gh"] if config.github_actions else []
    optional.append("codex")
    required = unique(required)
    optional = [item for item in unique(optional) if item not in required]
    required_checks = "\n".join(f"check_required {shlex.quote(command)}" for command in required)
    optional_checks = "\n".join(f"check_optional {shlex.quote(command)}" for command in optional)
    optional_checks_block = optional_checks or "printf '%s\\n' 'None.'"
    return clean(
        fr"""
        #!/usr/bin/env bash
        set -u
        cd "$(dirname "${{BASH_SOURCE[0]}}")/.."
        failures=0

        version_for() {{
          "$1" --version 2>&1 | head -n 1 || true
        }}

        check_required() {{
          local name="$1"
          if command -v "$name" >/dev/null 2>&1; then
            printf '[ok]   %-16s %s\n' "$name" "$(version_for "$name")"
          else
            printf '[miss] %-16s required\n' "$name"
            failures=$((failures + 1))
          fi
        }}

        check_optional() {{
          local name="$1"
          if command -v "$name" >/dev/null 2>&1; then
            printf '[ok]   %-16s %s\n' "$name" "$(version_for "$name")"
          else
            printf '[note] %-16s optional/deferred\n' "$name"
          fi
        }}

        printf 'Project: %s\n' {shlex.quote(config.project_name)}
        printf 'Kernel:  %s\n' "$(uname -srmo)"
        if [[ -r /etc/os-release ]]; then
          . /etc/os-release
          printf 'OS:      %s\n' "${{PRETTY_NAME:-unknown}}"
        fi
        printf '\nRequired toolchain:\n'
        {required_checks}
        printf '\nOptional integrations:\n'
        {optional_checks_block}

        printf '\nRepository:\n'
        if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
          printf '[ok]   git repository (%s)\n' "$(git branch --show-current 2>/dev/null || true)"
          if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
            printf '[note] working tree has uncommitted changes\n'
          fi
        else
          printf '[miss] git repository not initialized\n'
          failures=$((failures + 1))
        fi

        if (( failures > 0 )); then
          printf '\n%d required item(s) are missing. See docs/04-DEVELOPMENT-ENVIRONMENT.md.\n' "$failures"
          exit 1
        fi
        printf '\nEnvironment check passed; optional integrations may still be deferred.\n'
        """
    )


def render_command_script(config: ProjectConfig, kind: str) -> str:
    commands = effective_commands(config, kind)
    guard_map = {
        "build": "Build",
        "test": "Tests",
        "lint": "Lint/static checks",
    }
    title = guard_map[kind]
    if not commands:
        body = (
            f"printf '%s\\n' '{title} command is not established yet; this is a placeholder, "
            "not proof that a real app harness exists.'\n"
            "printf '%s\\n' 'Phase 0 must replace this script with the smallest real project command.'"
        )
    else:
        body = "\n".join(f"printf '+ %s\\n' {shlex.quote(command)}\n{command}" for command in commands)
    return clean(
        fr"""
        #!/usr/bin/env bash
        set -euo pipefail
        cd "$(dirname "${{BASH_SOURCE[0]}}")/.."
        {body}
        """
    )


def render_check_script(config: ProjectConfig) -> str:
    del config
    return clean(
        r"""
        #!/usr/bin/env bash
        set -euo pipefail
        cd "$(dirname "${BASH_SOURCE[0]}")/.."

        printf '%s\n' '== Lint/static checks =='
        ./scripts/lint.sh
        printf '%s\n' '== Build =='
        ./scripts/build.sh
        printf '%s\n' '== Tests =='
        ./scripts/test.sh
        printf '%s\n' '== Documentation invariants =='
        test -s AGENTS.md
        test -s docs/README.md
        test -s docs/09-PROGRESS.md
        test -s docs/11-IMPLEMENTATION-NOTES.md
        test -s docs/14-AGENT-HANDOFF.md
        printf '%s\n' 'All configured checks passed.'
        """
    )


def render_run_script(config: ProjectConfig) -> str:
    message = f"No development run command has been established for {config.project_name}."
    return clean(
        fr"""
        #!/usr/bin/env bash
        set -euo pipefail
        cd "$(dirname "${{BASH_SOURCE[0]}}")/.."
        printf '%s\n' {shlex.quote(message)}
        printf '%s\n' 'Phase 0 must replace this file with the simplest supported launch command.'
        exit 2
        """
    )


def render_start_agent_script(config: ProjectConfig) -> str:
    sandbox_preflight = ""
    codex_inside = ""
    host_codex = clean(
        r"""
        if ! command -v codex >/dev/null 2>&1; then
          printf '%s\n' 'codex is not installed. Run ./scripts/setup-agent.sh --install after reviewing it.' >&2
          exit 1
        fi
        if ! codex login status >/dev/null 2>&1; then
          printf '%s\n' 'Starting the official Codex account authorization flow.'
          codex login
        fi

        PROMPT=$(cat FIRST_PROMPT.md)
        if [[ "${1:-}" == "--kickoff" ]]; then
          exec codex exec --cd "$ROOT" --sandbox workspace-write "$PROMPT"
        fi
        exec codex --cd "$ROOT" "$PROMPT"
        """
    )
    if config.sandbox.enabled and config.sandbox.mode in {"toolchain", "codex"}:
        sandbox_preflight = clean(
            r"""
            scripts/sandbox/preflight
            """
        )
    if config.sandbox.codex_inside_container:
        codex_inside = clean(
            r"""
            if [[ "${1:-}" == "--kickoff" ]]; then
              PROMPT_FILE=FIRST_PROMPT.md
              if [[ -f FIRST_RUN_AUTONOMOUS.md ]]; then
                PROMPT_FILE=FIRST_RUN_AUTONOMOUS.md
              fi
              exec scripts/sandbox/codex-exec "$PROMPT_FILE"
            fi
            printf '%s\n' 'Launching Codex inside the project sandbox. Run scripts/sandbox/codex-login first if this container has not been authorized.'
            exec scripts/sandbox/codex
            """
        )
        host_codex = ""
    return clean(
        fr"""
        #!/usr/bin/env bash
        set -euo pipefail
        ROOT=$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)
        cd "$ROOT"

        {sandbox_preflight}

        {codex_inside}

        {host_codex}
        """
    )

def render_github_ci(config: ProjectConfig) -> str:
    setup_blocks: list[str] = []
    for snippet in ci_setup_for(config.languages):
        normalized = textwrap.dedent(snippet).strip()
        if normalized:
            setup_blocks.append(textwrap.indent(normalized, "      "))

    lines = [
        "name: CI",
        "",
        "on:",
        "  push:",
        f"    branches: [{json_string(config.default_branch)}]",
        "  pull_request:",
        "  workflow_dispatch:",
        "",
        "permissions:",
        "  contents: read",
        "",
        "concurrency:",
        "  group: ${{ github.workflow }}-${{ github.ref }}",
        "  cancel-in-progress: true",
        "",
        "jobs:",
        "  check:",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 20",
        "    steps:",
        "      - name: Check out repository",
        f"        uses: {github_action_reference('actions/checkout')}",
    ]
    for block in setup_blocks:
        lines.extend(block.splitlines())
    lines.extend(
        [
            "      - name: Run project checks",
            "        run: ./scripts/check.sh",
            "",
        ]
    )
    return "\n".join(lines)
