"""Deterministic registry of generated project artifacts and manifest metadata."""

from __future__ import annotations

import hashlib
import json

from .. import templates
from ..codex_skill import skill_files
from ..models import ProjectConfig
from ..sandbox import SANDBOX_EXECUTABLES, file_map as sandbox_file_map


REQUIRED_FILES: tuple[str, ...] = (
    "AGENTS.md", "FIRST_PROMPT.md", "START_HERE.md", "NEXT_STEPS.md", "README.md",
    ".agent-starter/rsync-excludes", ".agent-starter/project.json", "docs/README.md",
    "docs/AGENT-INDEX.md", "docs/00-PROJECT-BRIEF.md", "docs/01-REQUIREMENTS.md",
    "docs/02-ARCHITECTURE.md", "docs/03-TECH-STACK.md", "docs/04-DEVELOPMENT-ENVIRONMENT.md",
    "docs/05-TESTING.md", "docs/06-SECURITY.md", "docs/07-UX-ACCESSIBILITY.md",
    "docs/08-IMPLEMENTATION-PLAN.md", "docs/09-PROGRESS.md", "docs/10-DECISIONS.md",
    "docs/11-IMPLEMENTATION-NOTES.md", "docs/12-RELEASE-CHECKLIST.md", "docs/13-OPERATIONS.md",
    "docs/14-AGENT-HANDOFF.md", "docs/15-OPEN-QUESTIONS.md", "docs/16-DEPLOYMENT.md",
    "docs/AI-STACK-RECOMMENDATION.md",
    "scripts/bootstrap-dev.sh", "scripts/doctor.sh", "scripts/build.sh", "scripts/test.sh",
    "scripts/lint.sh", "scripts/check.sh", "scripts/run.sh", "scripts/setup-agent.sh",
    "scripts/agent-status.sh", "scripts/new-implementation-note.sh", "START_AGENT.sh",
)

EXECUTABLE_FILES: tuple[str, ...] = (
    "START_AGENT.sh", "scripts/bootstrap-dev.sh", "scripts/doctor.sh", "scripts/build.sh",
    "scripts/test.sh", "scripts/lint.sh", "scripts/check.sh", "scripts/run.sh",
    "scripts/setup-agent.sh", "scripts/agent-status.sh", "scripts/new-implementation-note.sh",
    *SANDBOX_EXECUTABLES,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _redacted_config_dict(config: ProjectConfig) -> dict[str, object]:
    """Serialize configuration without model transcripts or credentials."""

    data = config.to_dict()
    advisor = data.get("advisor")
    if isinstance(advisor, dict):
        advisor["raw_output"] = ""
    return data


def _codex_scripts() -> tuple[str, str]:
    setup = templates.clean(
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        INSTALL_URL='https://chatgpt.com/codex/install.sh'
        if ! command -v codex >/dev/null 2>&1; then
          if [[ "${1:-}" != "--install" ]]; then
            printf '%s\n' 'Codex is not installed.'
            printf 'Review the official installer, then run: %s --install\n' "$0"
            printf 'Installer source: %s\n' "$INSTALL_URL"
            exit 2
          fi
          printf '%s\n' 'Running the vendor-published Codex installer after explicit approval.'
          curl -fsSL "$INSTALL_URL" | sh
          export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
        fi

        printf '%s\n' 'Starting the official Codex account authorization flow.'
        printf '%s\n' 'This script never reads or stores the OAuth token.'
        codex login
        codex login status
        """
    )
    status = templates.clean(
        r"""
        #!/usr/bin/env bash
        set -u
        if ! command -v codex >/dev/null 2>&1; then
          printf '%s\n' '[missing] OpenAI Codex CLI'
          exit 1
        fi
        codex --version || true
        if codex login status; then
          printf '%s\n' '[ok] Codex reports an authorized account.'
        else
          printf '%s\n' '[not authorized] Run ./scripts/setup-agent.sh'
          exit 2
        fi
        """
    )
    return setup, status


def _new_note_script() -> str:
    return templates.clean(
        r"""
        #!/usr/bin/env bash
        set -euo pipefail
        ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
        FILE="$ROOT/docs/11-IMPLEMENTATION-NOTES.md"
        AGENT_NAME=${1:-human-or-agent}
        OBJECTIVE=${2:-Describe the objective}
        NOW=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

        cat >>"$FILE" <<EOF

        ## $NOW — $AGENT_NAME

        - Objective/phase: $OBJECTIVE
        - Files/subsystems changed: Pending
        - Behavior/design decisions: Pending
        - Commands and tests run: Pending
        - Results: Pending
        - Security/data/performance/UX implications: Pending
        - Unresolved problems: Pending
        - Exact next step: Pending
        EOF

        printf 'Appended an implementation-note template to %s\n' "$FILE"
        """
    )


def build_file_map(config: ProjectConfig) -> dict[str, str]:
    """Render every managed file for a configured project."""

    setup_agent, agent_status = _codex_scripts()
    data: dict[str, str] = {
        "AGENTS.md": templates.agents_md(config),
        "FIRST_PROMPT.md": templates.first_prompt(config),
        "START_HERE.md": templates.start_here(config),
        "NEXT_STEPS.md": templates.next_steps(config),
        "README.md": templates.project_readme(config),
        ".gitignore": templates.gitignore(config),
        ".agent-starter/rsync-excludes": templates.rsync_excludes(config),
        ".env.example": templates.env_example(config),
        ".editorconfig": templates.editorconfig(),
        ".codex/config.toml": templates.codex_config(config.model_policy),
        "CONTRIBUTING.md": templates.contributing(config),
        "SECURITY.md": templates.security_policy(config),
        "docs/README.md": templates.docs_index(config),
        "docs/AGENT-INDEX.md": templates.agent_index(config),
        "docs/00-PROJECT-BRIEF.md": templates.project_brief(config),
        "docs/01-REQUIREMENTS.md": templates.requirements_doc(config),
        "docs/02-ARCHITECTURE.md": templates.architecture_doc(config),
        "docs/03-TECH-STACK.md": templates.tech_stack_doc(config),
        "docs/04-DEVELOPMENT-ENVIRONMENT.md": templates.development_environment_doc(config),
        "docs/05-TESTING.md": templates.testing_doc(config),
        "docs/06-SECURITY.md": templates.security_doc(config),
        "docs/07-UX-ACCESSIBILITY.md": templates.ux_doc(config),
        "docs/08-IMPLEMENTATION-PLAN.md": templates.implementation_plan(config),
        "docs/09-PROGRESS.md": templates.progress_doc(config),
        "docs/10-DECISIONS.md": templates.decisions_doc(config),
        "docs/11-IMPLEMENTATION-NOTES.md": templates.implementation_notes(config),
        "docs/12-RELEASE-CHECKLIST.md": templates.release_checklist(config),
        "docs/13-OPERATIONS.md": templates.operations_doc(config),
        "docs/14-AGENT-HANDOFF.md": templates.handoff_doc(config),
        "docs/15-OPEN-QUESTIONS.md": templates.open_questions_doc(config),
        "docs/16-DEPLOYMENT.md": templates.deployment_doc(config),
        "docs/AI-STACK-RECOMMENDATION.md": templates.advisor_doc(config),
        "scripts/bootstrap-dev.sh": templates.bootstrap_script(config),
        "scripts/doctor.sh": templates.doctor_script(config),
        "scripts/build.sh": templates.command_script(config, "build"),
        "scripts/test.sh": templates.command_script(config, "test"),
        "scripts/lint.sh": templates.command_script(config, "lint"),
        "scripts/check.sh": templates.check_script(config),
        "scripts/run.sh": templates.run_script(config),
        "scripts/setup-agent.sh": setup_agent,
        "scripts/agent-status.sh": agent_status,
        "scripts/new-implementation-note.sh": _new_note_script(),
        "START_AGENT.sh": templates.start_agent_script(config),
    }
    if config.github_actions:
        data[".github/workflows/ci.yml"] = templates.github_ci(config)
    if config.codex_agentkit_skill:
        data.update(skill_files(installed_at=config.created_at, updated_at=config.updated_at))
    data.update(sandbox_file_map(config))
    license_name = config.license_name.strip().lower()
    if license_name == "mit":
        data["LICENSE"] = templates.mit_license()
    elif license_name in {"apache-2.0", "apache2"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="Apache License 2.0", spdx="Apache-2.0",
            url="https://www.apache.org/licenses/LICENSE-2.0.html",
            summary="This project is licensed under the Apache License, Version 2.0.",
        )
    elif license_name in {"bsd-3-clause", "bsd3"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="BSD 3-Clause License", spdx="BSD-3-Clause",
            url="https://opensource.org/license/bsd-3-clause",
            summary="This project is licensed under the BSD 3-Clause License.",
        )
    elif license_name in {"gpl-3.0-or-later", "gplv3-or-later", "gpl-3.0+"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="GNU General Public License v3.0 or later", spdx="GPL-3.0-or-later",
            url="https://www.gnu.org/licenses/gpl-3.0.html",
            summary=("This project is licensed under the GNU General Public License, version 3 "
                     "or any later version published by the Free Software Foundation."),
        )
    elif license_name in {"agpl-3.0-or-later", "agplv3-or-later", "agpl-3.0+"}:
        data["LICENSE"] = templates.agpl_3_or_later_license()
    elif license_name in {"mpl-2.0", "mpl2"}:
        data["LICENSE"] = templates.spdx_license_notice(
            title="Mozilla Public License 2.0", spdx="MPL-2.0",
            url="https://www.mozilla.org/MPL/2.0/",
            summary="This project is licensed under the Mozilla Public License, version 2.0.",
        )

    data[".agent-starter/project.json"] = json.dumps(
        _redacted_config_dict(config), indent=2, sort_keys=True
    ) + "\n"
    data[".agent-starter/README.md"] = templates.clean(
        """
        # Agent Starter metadata

        `project.json` records non-secret wizard choices so future humans and agents can understand how this
        workspace was initialized. Do not put credentials, API keys, access tokens, database passwords, private
        customer data, or model authentication artifacts in this directory.

        `manifest.json` lists the intended generated files and their hashes. Existing-file conflicts are preserved
        under timestamped `proposals/`; forced replacements are copied to timestamped `backups/` first.
        """
    )
    return data


def _manifest(config: ProjectConfig, files: dict[str, str]) -> str:
    payload = {
        "schema_version": 1,
        "kit_version": config.kit_version,
        "generated_at": config.created_at,
        "project_name": config.project_name,
        "files": {
            path: {"sha256": _sha256(content.encode("utf-8")), "executable": path in EXECUTABLE_FILES}
            for path, content in sorted(files.items())
            if path != ".agent-starter/manifest.json"
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
