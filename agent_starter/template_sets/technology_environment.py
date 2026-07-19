"""Generated technology selection and development-environment templates."""

from __future__ import annotations

from ..models import ProjectConfig
from ..toolchains import DATABASE_COMMANDS, commands_for, selected_toolchains, unique
from .common import clean, command_section, inline_list, md_list


def effective_commands(config: ProjectConfig, kind: str) -> list[str]:
    """Return reviewed commands or conservative built-in defaults.

    AI-advisor command strings remain documentation-only proposals. They are
    never copied into executable scripts automatically.
    """

    custom = {
        "setup": config.custom_setup_commands,
        "build": config.custom_build_commands,
        "test": config.custom_test_commands,
        "lint": config.custom_lint_commands,
    }[kind]
    if custom:
        return unique(custom)
    if config.project_mode == "new":
        # A language choice is an architectural hypothesis, not proof that a
        # package manifest or source tree exists. Phase 0 replaces these
        # placeholders after scaffolding the smallest working vertical slice.
        return []
    return unique(commands_for(config.languages, kind))


def render_tech_stack_doc(config: ProjectConfig) -> str:
    tools = selected_toolchains(config.languages)
    tool_lines = [f"{tool.display}: CachyOS packages `{', '.join(tool.packages)}`" for tool in tools]
    rationale = config.advisor.rationale or ["Selected from the user's stated preferences and conservative local defaults; validate during Phase 0."]
    return clean(
        f"""
        # Technology stack

        ## Selected stack

        - Languages/runtimes: {inline_list(config.languages)}
        - Database: {config.database}
        - Dependency posture: {'standard library and small focused packages preferred' if config.minimal_dependencies else 'dependencies allowed when justified and reviewed'}
        - Coding agent: OpenAI Codex CLI

        ## Toolchain

        {md_list(tool_lines, empty="- The stack remains undecided; complete a decision record before creating application code.")}

        ## Rationale

        {md_list(rationale)}

        ## Dependency acceptance checklist

        Before adding a production dependency, record:

        - exact capability it supplies and alternatives considered;
        - maintenance activity, release provenance, security history, and license;
        - transitive dependency and binary/install impact;
        - how it is pinned, updated, tested, and removed;
        - whether a standard-library or small local implementation is safer and simpler.

        ## Database direction

        {DATABASE_COMMANDS.get(config.database, DATABASE_COMMANDS['undecided'])}

        Schema and migration files belong in version control. Credentials, local database files, dumps, and production
        data do not. Use a separate development database/account for network database engines.

        ## Re-evaluation triggers

        Revisit the stack only when a measured requirement cannot be met, a dependency becomes unmaintained or
        vulnerable, packaging support fails on a target platform, or complexity is materially reduced by a change.
        Capture the decision in `10-DECISIONS.md` before migration.
        """
    )


def render_development_environment_doc(config: ProjectConfig) -> str:
    advisor_capabilities = md_list(config.advisor.toolchain_capabilities, empty="- None.")
    legacy_advisor_packages = md_list(config.advisor.toolchain_packages, empty="- None.")
    return clean(
        f"""
        # Development environment — supported Linux providers

        ## Safety first

        Review package commands before running them. Coding agents must not run `sudo`; the human installs system
        packages. `bootstrap-dev.sh` detects CachyOS/Arch, Debian, or Ubuntu from bounded OS metadata and confirms
        `pacman` or `apt-get`. A reviewed `--provider` override selects the host package provider only; it does not
        change project target platforms or the optional sandbox image profile.

        ## Review-first host bootstrap

        ```bash
        ./scripts/bootstrap-dev.sh                              # detect/query/print argv only
        ./scripts/bootstrap-dev.sh --provider ubuntu            # reviewed override with apt-get proof
        ./scripts/bootstrap-dev.sh --provider ubuntu --refresh  # separate APT index refresh
        ./scripts/bootstrap-dev.sh --provider ubuntu --install  # install reviewed missing packages
        ```

        The default invocation changes nothing. It constructs provider commands as Bash argv arrays and omits
        packages already reported installed. On Debian/Ubuntu, `--refresh` runs only `apt-get update`; it is separate
        because it uses the network and changes local repository metadata. `--install` does not refresh indexes.
        Project bootstrap never performs `pacman -Syu`, `apt-get upgrade`, or another full-system upgrade.

        CachyOS/Arch uses configured official `pacman` repositories. Any AUR-only suggestion is unverified and
        manual: inspect its PKGBUILD and sources and make a separate human decision. AgentKit never enables or
        invokes an AUR helper. Debian/Ubuntu uses already configured official APT sources and never adds a PPA,
        signing key, pin, or third-party repository.

        AI-advisor capability intent is provider-neutral and must be resolved and verified for the selected host:

        {advisor_capabilities}

        Legacy saved advisor package suggestions remain documentation-only Arch intent and never execute automatically:

        {legacy_advisor_packages}

        ## Agent clients

        - Codex CLI install: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`
        - Authorization is performed by `codex login`; the starter kit never receives or reads tokens.
        - Use `agent-starter auth` from the kit or run `./scripts/setup-agent.sh` in this project.

        ## Project setup

        {command_section(effective_commands(config, 'setup'), placeholder='Establish setup commands during Phase 0 and update this file.')}

        ## Stable workflow

        ```bash
        ./scripts/doctor.sh
        ./scripts/check.sh
        ./scripts/run.sh
        ```

        `doctor.sh` checks executables and versions. `check.sh` is the stable local/CI verification entry point.
        `run.sh` must become the simplest supported development launch command.

        ## Environment and secrets

        Copy `.env.example` to `.env` only when the application requires local configuration. `.env` is ignored.
        Never paste secrets into agent prompts or commit them. Prefer a local OS keyring for long-lived credentials.

        ## Sandbox posture

        - Codex project config requests `workspace-write` plus on-request approvals.
        - Do not use danger/full-access or permission-skipping modes on the host for routine development.
        - Keep the project in its own directory and review every request to access paths outside it.
        """
    )
