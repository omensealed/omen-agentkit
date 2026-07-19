"""Cohesive generated-artifact template families."""

from .codex import CODEX_TEMPLATE_REGISTRY, render_codex_config, render_model_policy_summary
from .bootstrap import render_bootstrap_script
from .architecture import render_architecture_doc, render_modularity_contract
from .agent_guidance import render_advisor_doc, render_agents_md, render_first_prompt
from .licenses import AGPL_3_OR_LATER_TEXT, agpl_3_or_later_license, mit_license, spdx_license_notice
from .navigation import render_agent_index, render_docs_index
from .orientation import render_next_steps, render_project_readme, render_start_here
from .project_memory import (
    render_decisions_doc,
    render_handoff_doc,
    render_implementation_notes,
    render_open_questions_doc,
    render_progress_doc,
)
from .project_definition import render_implementation_plan, render_project_brief, render_requirements_doc
from .quality_risk import render_security_doc, render_testing_doc, render_ux_doc
from .release_operations import render_contributing, render_deployment_doc, render_operations_doc, render_release_checklist, render_security_policy
from .script_workflows import (
    render_check_script,
    render_command_script,
    render_doctor_script,
    render_github_ci,
    render_run_script,
    render_start_agent_script,
)
from .repository_support import render_editorconfig, render_env_example, render_gitignore, render_rsync_excludes
from .shared_sections import agentkit_skill_note, first_prompt_sandbox_note, sandbox_note
from .technology_environment import effective_commands, render_development_environment_doc, render_tech_stack_doc

__all__ = [
    "CODEX_TEMPLATE_REGISTRY",
    "AGPL_3_OR_LATER_TEXT",
    "agpl_3_or_later_license",
    "effective_commands",
    "mit_license",
    "agentkit_skill_note",
    "first_prompt_sandbox_note",
    "render_next_steps",
    "render_project_readme",
    "render_start_here",
    "render_architecture_doc",
    "render_advisor_doc",
    "render_agents_md",
    "render_agent_index",
    "render_bootstrap_script",
    "render_codex_config",
    "render_check_script",
    "render_command_script",
    "render_contributing",
    "render_docs_index",
    "render_doctor_script",
    "render_decisions_doc",
    "render_deployment_doc",
    "render_development_environment_doc",
    "render_editorconfig",
    "render_env_example",
    "render_first_prompt",
    "render_gitignore",
    "render_github_ci",
    "render_handoff_doc",
    "render_implementation_notes",
    "render_implementation_plan",
    "render_model_policy_summary",
    "render_modularity_contract",
    "render_open_questions_doc",
    "render_operations_doc",
    "render_progress_doc",
    "render_project_brief",
    "render_requirements_doc",
    "render_release_checklist",
    "render_security_doc",
    "render_security_policy",
    "render_rsync_excludes",
    "render_run_script",
    "render_tech_stack_doc",
    "render_start_agent_script",
    "render_testing_doc",
    "render_ux_doc",
    "sandbox_note",
    "spdx_license_notice",
]
