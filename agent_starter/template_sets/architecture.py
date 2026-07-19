"""Architecture and modularity-contract templates."""

from __future__ import annotations

from ..models import ProjectConfig
from .common import clean, inline_list, yes_no


def render_modularity_contract() -> str:
    return clean(
        """
        ## Modularity contract

        - Identify the existing module responsible before editing; inspect its callers, tests, and public boundary.
        - Do not append a second unrelated workflow to an already broad module.
        - Prefer a vertical slice with clear public boundaries over horizontal utility or wrapper sprawl.
        - Split when a file has more than one primary reason to change, not merely to satisfy a line count.
        - Do not create empty directories, placeholder abstractions, or one-line wrapper sprawl.
        - Update the project/module map when responsibilities move; keep `docs/AGENT-INDEX.md` and
          `docs/02-ARCHITECTURE.md` aligned with the verified code.
        - Preserve compatibility at public interfaces through tested delegation, re-exports, adapters, or an
          explicit migration when responsibilities move.
        """
    )


def render_architecture_doc(config: ProjectConfig) -> str:
    advisor_arch = (
        config.advisor.architecture
        or config.stack_notes
        or "To be validated during Phase 0 after inventory and a vertical-slice design."
    )
    return clean(
        f"""
        # Architecture

        ## Proposed direction

        {advisor_arch}

        This is a starting hypothesis, not permission for a speculative rewrite. The agent must verify it against
        the project brief, existing code (when present), testability, operational cost, and user experience.

        ## Required boundaries

        - **Entry/UI layer:** translates user or protocol input into validated application requests.
        - **Application/domain layer:** owns rules and behavior without depending directly on UI or infrastructure.
        - **Infrastructure layer:** filesystem, database, network, clock, randomness, process, and platform adapters.
        - **Persistence boundary:** migrations/schema and repositories are explicit; domain code does not assemble raw queries.
        - **Test boundary:** adapters can be replaced with deterministic fakes or temporary resources.

        Small projects may keep these in a few files; the boundaries matter more than directory ceremony.
        Do not let convenience turn one file into the whole application; apply the contract below before adding
        behavior to a broad module.

        {render_modularity_contract()}

        ## Data flow to document during Phase 0

        1. Identify each entry point and trust boundary.
        2. Trace one representative request/input through validation, domain behavior, persistence, and output.
        3. Mark sensitive data, irreversible actions, external services, concurrency, and failure points.
        4. Add a text or Mermaid diagram only after the flow is verified.

        ## Architecture constraints

        - Selected languages: {inline_list(config.languages)}
        - Database: {config.database}
        - Minimal dependencies: {yes_no(config.minimal_dependencies)}
        - Networked behavior: {yes_no(config.network_access)}
        - Prefer one deployable unit until requirements prove a split is beneficial.
        - Avoid global mutable state and hidden singleton dependencies.
        - Use explicit timeouts and cancellation around external processes or network calls.

        ## Migration rule

        Any architecture change affecting data formats, public interfaces, saved games/files, URLs, CLI flags, or
        configuration must include compatibility impact, migration steps, rollback, and tests before implementation.
        """
    )
