"""Pure rendering functions for generated project files."""

from __future__ import annotations

import json
import shlex
import textwrap
from typing import Iterable

from .models import ProjectConfig
from .model_policy import CodexModelPolicy
from .policy_fragments import render_canonical_policy_registry, render_prompt_policy_references
from .template_sets.agent_guidance import (
    render_advisor_doc as advisor_doc,
    render_agents_md as agents_md,
    render_first_prompt as first_prompt,
)
from .template_sets.architecture import render_architecture_doc, render_modularity_contract
from .template_sets.codex import render_codex_config
from .template_sets.bootstrap import render_bootstrap_script
from .template_sets.common import clean, command_section, inline_list, json_string, md_checklist, md_list, yes_no
from .template_sets.licenses import AGPL_3_OR_LATER_TEXT, agpl_3_or_later_license, mit_license, spdx_license_notice
from .template_sets.navigation import render_agent_index as agent_index, render_docs_index as docs_index
from .template_sets.orientation import (
    render_next_steps as next_steps,
    render_project_readme as project_readme,
    render_start_here as start_here,
)
from .template_sets.project_memory import (
    render_decisions_doc as decisions_doc,
    render_handoff_doc as handoff_doc,
    render_implementation_notes as implementation_notes,
    render_open_questions_doc as open_questions_doc,
    render_progress_doc as progress_doc,
)
from .template_sets.project_definition import (
    render_implementation_plan as implementation_plan,
    render_project_brief as project_brief,
    render_requirements_doc as requirements_doc,
)
from .template_sets.quality_risk import (
    render_security_doc as security_doc,
    render_testing_doc as testing_doc,
    render_ux_doc as ux_doc,
)
from .template_sets.release_operations import (
    render_contributing as contributing,
    render_deployment_doc as deployment_doc,
    render_operations_doc as operations_doc,
    render_release_checklist as release_checklist,
    render_security_policy as security_policy,
)
from .template_sets.script_workflows import (
    render_check_script as check_script,
    render_command_script as command_script,
    render_doctor_script as doctor_script,
    render_github_ci as github_ci,
    render_run_script as run_script,
    render_start_agent_script as start_agent_script,
)
from .template_sets.repository_support import (
    render_editorconfig as editorconfig,
    render_env_example as env_example,
    render_gitignore as gitignore,
    render_rsync_excludes as rsync_excludes,
)
from .template_sets.shared_sections import agentkit_skill_note, first_prompt_sandbox_note, sandbox_note
from .template_sets.technology_environment import (
    effective_commands,
    render_development_environment_doc as development_environment_doc,
    render_tech_stack_doc as tech_stack_doc,
)
from .toolchains import (
    DATABASE_COMMANDS,
    ci_setup_for,
    selected_toolchains,
    unique,
)


_modularity_contract = render_modularity_contract


architecture_doc = render_architecture_doc


def codex_config(policy: CodexModelPolicy | None = None) -> str:
    """Compatibility export for the extracted Codex template family."""

    return render_codex_config(policy or CodexModelPolicy())


def bootstrap_script(config: ProjectConfig) -> str:
    return render_bootstrap_script(config, effective_commands(config, "setup"))
