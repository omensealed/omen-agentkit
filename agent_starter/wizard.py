"""Interactive beginner-oriented project configuration wizard."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .agents import AgentAdapter, AgentError, get_adapter
from .models import AdvisorRecommendation, ProjectConfig
from .toolchains import TOOLCHAINS, fallback_recommendation, normalize_language, packages_for, unique

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


@dataclass(slots=True)
class WizardResult:
    config: ProjectConfig
    launch_after_generation: bool
    kickoff_mode: bool


class CancelledByUser(RuntimeError):
    """Raised when the user deliberately cancels the wizard."""


def slugify(value: str) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return candidate or "new-project"


def _split_list(value: str) -> list[str]:
    return unique(part.strip() for part in re.split(r"[,;\n]+", value) if part.strip())


def _looks_sensitive(value: str) -> bool:
    patterns = (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\s*[:=]\s*\S+",
        r"\bsk-[A-Za-z0-9_-]{16,}\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)


class Prompter:
    def __init__(self, input_fn: InputFn = input, output_fn: OutputFn = print) -> None:
        self.input = input_fn
        self.output = output_fn

    def section(self, title: str) -> None:
        self.output(f"\n=== {title} ===")

    def ask(self, question: str, *, default: str = "", required: bool = False, secret_safe: bool = True) -> str:
        while True:
            suffix = f" [{default}]" if default else ""
            try:
                answer = self.input(f"{question}{suffix}: ").strip()
            except (EOFError, KeyboardInterrupt) as exc:
                self.output("")
                raise CancelledByUser("Wizard cancelled.") from exc
            value = answer or default
            if required and not value:
                self.output("Please enter a value.")
                continue
            if secret_safe and value and _looks_sensitive(value):
                self.output("That entry resembles a credential. Do not put passwords, tokens, API keys, or private keys in project answers.")
                continue
            return value

    def confirm(self, question: str, *, default: bool = True) -> bool:
        marker = "Y/n" if default else "y/N"
        while True:
            answer = self.ask(f"{question} ({marker})", secret_safe=False).lower()
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            self.output("Enter yes or no.")

    def choose(self, question: str, options: list[tuple[str, str]], *, default: str) -> str:
        self.output(question)
        lookup: dict[str, str] = {}
        for index, (key, label) in enumerate(options, start=1):
            self.output(f"  {index}. {label}")
            lookup[str(index)] = key
            lookup[key.lower()] = key
        while True:
            answer = self.ask("Choice", default=default, secret_safe=False).lower()
            if answer in lookup:
                return lookup[answer]
            self.output("Choose a listed number or name.")

    def multi_choose(
        self,
        question: str,
        options: list[tuple[str, str]],
        *,
        defaults: Iterable[str] = (),
        allow_other: bool = True,
    ) -> list[str]:
        self.output(question)
        lookup: dict[str, str] = {}
        for index, (key, label) in enumerate(options, start=1):
            self.output(f"  {index}. {label}")
            lookup[str(index)] = key
            lookup[key.lower()] = key
        default_text = ",".join(defaults)
        while True:
            answer = self.ask("Choices (comma-separated)", default=default_text, secret_safe=False)
            if not answer:
                return []
            result: list[str] = []
            invalid: list[str] = []
            for raw in _split_list(answer):
                key = lookup.get(raw.lower())
                if key:
                    result.append(key)
                elif allow_other:
                    result.append(raw.strip().lower())
                else:
                    invalid.append(raw)
            if not invalid:
                return unique(result)
            self.output(f"Unknown choice(s): {', '.join(invalid)}")

    def ask_list(self, question: str, *, default: Iterable[str] = ()) -> list[str]:
        return _split_list(self.ask(question, default=", ".join(default)))


def _normalize_database(value: str) -> str:
    text = value.strip().lower().replace(" ", "-")
    aliases = {
        "no": "none",
        "no-database": "none",
        "sqlite3": "sqlite",
        "maria": "mariadb",
        "mysql": "mariadb",
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "existing-db": "existing",
    }
    return aliases.get(text, text)


def build_advisor_prompt(config: ProjectConfig) -> str:
    project = {
        "name": config.project_name,
        "mode": config.project_mode,
        "stage": config.project_stage,
        "type": config.project_type,
        "description": config.description,
        "goals": config.goals,
        "non_goals": config.non_goals,
        "target_users": config.target_users,
        "target_platforms": config.target_platforms,
        "packaging_targets": config.packaging_targets,
        "network_access": config.network_access,
        "user_accounts": config.user_accounts,
        "handles_personal_data": config.handles_personal_data,
        "handles_payments": config.handles_payments,
        "constraints": [
            "Development host is CachyOS/Arch Linux.",
            "Prefer vanilla language/runtime features and a small dependency surface.",
            "The coding agent must be able to build, lint, and test from the CLI.",
            "Do not include credentials or commands requiring secrets.",
            "Favor a simple architecture a beginner can maintain.",
        ],
    }
    return (
        "Act only as a read-only software architecture advisor. Recommend a practical initial stack for the project below. "
        "Do not create files, execute commands, browse the workspace, or assume production scale. Prefer the standard library "
        "and mature small tools. Database must be one of none, sqlite, mariadb, postgresql, existing, or undecided. "
        "Commands are proposals for human review, not authorization to execute them. Return exactly one JSON object with these "
        "keys: summary (string), languages (string array using names such as python, javascript, rust, go, php, cpp, java, godot, shell), "
        "database (string), architecture (string), toolchain_packages (string array of CachyOS package names), setup_commands, "
        "build_commands, test_commands, lint_commands (string arrays), rationale, risks, questions (string arrays).\n\n"
        + json.dumps(project, indent=2)
    )


def _print_recommendation(prompt: Prompter, recommendation: AdvisorRecommendation) -> None:
    prompt.output("\nProposed stack:")
    prompt.output(f"  Languages: {', '.join(recommendation.languages) or 'undecided'}")
    prompt.output(f"  Database:  {recommendation.database}")
    prompt.output(f"  Summary:   {recommendation.summary}")
    prompt.output(f"  Shape:     {recommendation.architecture}")
    if recommendation.rationale:
        prompt.output("  Why:")
        for item in recommendation.rationale:
            prompt.output(f"    - {item}")
    if recommendation.risks:
        prompt.output("  Risks to verify:")
        for item in recommendation.risks:
            prompt.output(f"    - {item}")


def _local_recommendation(config: ProjectConfig, *, source: str = "local-fallback") -> AdvisorRecommendation:
    languages, database, architecture = fallback_recommendation(
        config.project_type, config.target_platforms, config.network_access
    )
    return AdvisorRecommendation(
        summary="Conservative offline recommendation based on project type and target platform.",
        languages=languages,
        database=database,
        architecture=architecture,
        toolchain_packages=packages_for(languages, database, github=config.github_actions),
        rationale=[
            "Uses a familiar, CLI-testable toolchain available on CachyOS.",
            "Starts with a small dependency surface and one maintainable implementation path.",
            "Can be revised after Phase 0 discovery and a working vertical slice.",
        ],
        risks=["The recommendation is based on a short brief and must be verified against real constraints."],
        questions=["Which acceptance criteria and packaging target are essential for the first usable release?"],
        source=source,
    )


def _prepare_agent(prompt: Prompter, adapter: AgentAdapter, *, need_advisor: bool, setup_now: bool) -> bool:
    prompt.output(f"\nCodex client: {adapter.display_name}")
    prompt.output(f"Account flow: {adapter.account_description}")
    if not adapter.exists():
        prompt.output("The CLI is not currently available on PATH.")
        prompt.output(f"Official installer command: {adapter.install_command}")
        if not setup_now or not prompt.confirm("Run that vendor-published installer now?", default=False):
            return False
        if not adapter.install():
            prompt.output("Installation did not make the CLI available in this shell. You can finish setup later with the generated helper.")
            return False
        prompt.output(f"Installed: {adapter.version()}")
    else:
        prompt.output(f"Detected: {adapter.version()}")

    status = adapter.auth_status()
    if status is True:
        prompt.output("The CLI reports that an account is authorized.")
        return True
    if status is False:
        message = "An authorized account is required for AI stack advice." if need_advisor else "The CLI is not authorized yet."
        prompt.output(message)
    else:
        prompt.output("Codex authorization status could not be confirmed automatically.")

    if not setup_now:
        return False
    if not prompt.confirm("Start Codex's official account authorization flow now?", default=need_advisor):
        return False
    device_auth = prompt.confirm("Use Codex device-code authorization instead of opening a local browser?", default=False)
    if adapter.login(device_auth=device_auth):
        prompt.output("The official CLI authorization flow completed.")
        return True
    prompt.output("Authorization was not confirmed. No token was read or stored by this starter kit.")
    return False


def _manual_languages(prompt: Prompter, defaults: Iterable[str] = ()) -> list[str]:
    options = [(toolchain.key, toolchain.display) for toolchain in TOOLCHAINS]
    selected = prompt.multi_choose(
        "Select one or more implementation languages/toolchains. Custom names are allowed but receive no automatic commands:",
        options,
        defaults=defaults or ("python",),
        allow_other=True,
    )
    return unique(normalize_language(item) for item in selected)


def _choose_database(prompt: Prompter, *, default: str) -> str:
    return prompt.choose(
        "Persistence/database plan:",
        [
            ("none", "No database"),
            ("sqlite", "SQLite file database (simple local/default choice)"),
            ("mariadb", "MariaDB service"),
            ("postgresql", "PostgreSQL service"),
            ("existing", "An existing database must be discovered safely"),
            ("undecided", "Leave as an explicit Phase 0 decision"),
        ],
        default=_normalize_database(default) if _normalize_database(default) in {"none", "sqlite", "mariadb", "postgresql", "existing", "undecided"} else "undecided",
    )


def run_wizard(
    *,
    initial_path: str | None = None,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
    skip_agent_setup: bool = False,
) -> WizardResult:
    p = Prompter(input_fn, output_fn)
    p.output("CLI AI Agent Starter Kit")
    p.output("This wizard creates project guidance and executable helpers. It never asks for or stores account tokens, API keys, or database passwords.")

    config = ProjectConfig()

    p.section("Project location and purpose")
    config.project_mode = p.choose(
        "Are you starting fresh or adding the workflow to existing code?",
        [("new", "New project"), ("existing", "Existing project / renovation")],
        default="new",
    )
    default_path = initial_path or ("." if config.project_mode == "existing" else "")
    if config.project_mode == "existing":
        path_text = p.ask("Existing project directory", default=default_path or ".", required=True)
        root = Path(path_text).expanduser().resolve()
        default_name = root.name
    else:
        name_first = p.ask("Project name", required=True)
        slug_first = slugify(name_first)
        path_text = p.ask("New project directory", default=initial_path or f"./{slug_first}", required=True)
        root = Path(path_text).expanduser().resolve()
        default_name = name_first
    config.project_name = p.ask("Project display name", default=default_name, required=True)
    config.project_slug = slugify(config.project_name)
    config.project_path = str(root)
    config.description = p.ask("Describe what the finished project should do", required=True)
    config.project_type = p.choose(
        "Project type:",
        [
            ("cli", "Command-line application"),
            ("web", "Website / web application"),
            ("api", "API / network service"),
            ("desktop", "Desktop application"),
            ("game", "Game"),
            ("library", "Reusable library"),
            ("automation", "Automation / data tool"),
            ("embedded", "Embedded / hardware project"),
            ("other", "Other"),
        ],
        default="cli",
    )
    config.project_stage = p.choose(
        "Current stage:",
        [("idea", "Idea"), ("prototype", "Prototype"), ("active", "Active development"), ("renovation", "Major renovation")],
        default="renovation" if config.project_mode == "existing" else "idea",
    )
    config.target_users = p.ask("Who will use it?", default="The project owner and intended end users")
    config.goals = p.ask_list("Top goals (comma-separated)", default=("Deliver one reliable end-to-end workflow", "Keep setup and maintenance understandable"))
    config.non_goals = p.ask_list("Anything explicitly out of scope for the first release (optional)")

    config.target_platforms = p.multi_choose(
        "Target platforms:",
        [
            ("cachyos-linux", "CachyOS / Linux"),
            ("linux", "Other Linux distributions"),
            ("windows", "Windows"),
            ("macos", "macOS"),
            ("browser", "Web browser"),
            ("server", "Hosted server"),
            ("android", "Android"),
            ("ios", "iOS"),
            ("embedded", "Embedded hardware"),
        ],
        defaults=("cachyos-linux",),
    )
    config.packaging_targets = p.ask_list(
        "Desired deliverables/packages (comma-separated)",
        default=("source checkout", "documented local development build"),
    )

    p.section("Security and data boundaries")
    config.network_access = p.confirm("Will the program access a network or expose a network service?", default=config.project_type in {"web", "api"})
    config.user_accounts = p.confirm("Will it have user accounts, identities, or authorization?", default=False)
    config.handles_personal_data = p.confirm("Will it store personal, private, or user-generated data?", default=False)
    config.handles_payments = p.confirm("Will it handle payments or financial transactions?", default=False)
    config.security_notes = p.ask("Other security/data constraints (do not enter credentials)")

    p.section("OpenAI Codex CLI")
    config.primary_agent = "codex"
    p.output("This edition creates Codex-only workspaces and uses the official Codex CLI account flow.")
    config.setup_agent_now = not skip_agent_setup and p.confirm("Install or authorize Codex during this wizard when needed?", default=True)
    config.codex_agentkit_skill = p.confirm(
        "Install the repo-local `$agentkit` Codex skill so future short requests can be expanded into full Agent Kit prompts from inside Codex?",
        default=True,
    )

    p.section("Technology stack")
    config.stack_strategy = p.choose(
        "How should the first stack be selected?",
        [("ai", "Ask Codex for a read-only recommendation, then review it"), ("manual", "Choose languages and database manually")],
        default="ai",
    )
    config.use_ai_advisor = config.stack_strategy == "ai"
    adapter = get_adapter()
    agent_ready = False
    if config.setup_agent_now or config.use_ai_advisor:
        agent_ready = _prepare_agent(
            p,
            adapter,
            need_advisor=config.use_ai_advisor,
            setup_now=config.setup_agent_now,
        )

    recommendation: AdvisorRecommendation | None = None
    if config.use_ai_advisor and agent_ready:
        p.output("Requesting a structured recommendation in a temporary, read-only advisory workspace...")
        try:
            recommendation = adapter.advise(config, build_advisor_prompt(config))
        except AgentError as exc:
            p.output(f"The AI recommendation could not be used: {exc}")
    if config.use_ai_advisor and recommendation is None:
        recommendation = _local_recommendation(config)
        p.output("Using a conservative offline recommendation instead.")

    if recommendation is not None:
        recommendation.languages = unique(normalize_language(item) for item in recommendation.languages)
        recommendation.database = _normalize_database(recommendation.database)
        config.advisor = recommendation
        _print_recommendation(p, recommendation)
        if p.confirm("Accept these languages as the Phase 0 hypothesis?", default=True):
            config.languages = recommendation.languages
        else:
            config.languages = _manual_languages(p, recommendation.languages)
        config.database = _choose_database(p, default=recommendation.database)
        if config.database != recommendation.database:
            config.open_questions.append("Reconcile the chosen database with the advisor recommendation during Phase 0.")
    else:
        config.advisor = _local_recommendation(config, source="manual-seed")
        config.languages = _manual_languages(p)
        config.database = _choose_database(p, default="none")

    config.stack_notes = p.ask("Stack/architecture constraints or preferences", default=config.advisor.architecture)
    config.database_notes = p.ask("Database constraints, existing schema, or expected data size (never enter a password)")
    config.minimal_dependencies = p.confirm("Require justification before adding production dependencies?", default=True)

    p.section("Testing, Git, and automation")
    default_tests = ["unit", "integration"]
    if config.project_type in {"web", "desktop", "game"}:
        default_tests.append("end-to-end smoke")
    config.tests = p.multi_choose(
        "Expected test layers:",
        [
            ("unit", "Unit tests"),
            ("integration", "Integration tests"),
            ("end-to-end", "End-to-end tests"),
            ("regression", "Regression/characterization tests"),
            ("performance", "Performance checks"),
            ("security", "Security-focused tests"),
        ],
        defaults=default_tests,
    )
    config.browser_tests = "browser" in config.target_platforms and p.confirm("Plan browser automation for critical flows?", default=config.project_type == "web")
    config.quality_checks = ["format", "lint", "build", "tests", "documentation"]
    config.git_enabled = p.confirm("Initialize a local Git repository if one is not present?", default=True)
    p.output("Local-first recommendation: prove setup and tests locally before adding GitHub Actions or a remote.")
    config.github_actions = p.confirm("Generate a GitHub Actions CI workflow now?", default=False)
    if config.github_actions:
        config.github_remote = p.choose(
            "GitHub repository setup:",
            [
                ("later", "Configure/create the remote later"),
                ("none", "Do not use a GitHub remote"),
                ("create-private", "Create a private GitHub repository after generation"),
                ("create-public", "Create a public GitHub repository after generation"),
            ],
            default="later",
        )
    else:
        config.github_remote = "none"
    config.default_branch = p.ask("Default Git branch", default="main", required=True)
    p.output("License quick guide:")
    p.output("  MIT, Apache-2.0, and BSD-3-Clause are permissive choices for broad reuse.")
    p.output("  GPL-3.0-or-later and AGPL-3.0-or-later are copyleft choices; AGPL has network-service source-sharing obligations.")
    p.output("  MPL-2.0 is file-level copyleft. Choose Undecided if you are not ready to decide.")
    config.license_name = p.choose(
        "Initial license:",
        [
            ("MIT", "MIT License"),
            ("Apache-2.0", "Apache License 2.0"),
            ("BSD-3-Clause", "BSD 3-Clause License"),
            ("GPL-3.0-or-later", "GNU General Public License v3.0 or later"),
            ("AGPL-3.0-or-later", "GNU Affero General Public License v3.0 or later"),
            ("MPL-2.0", "Mozilla Public License 2.0"),
            ("Undecided", "Leave licensing undecided (no LICENSE generated)"),
        ],
        default="MIT",
    )
    config.cachyos_packages = p.ask_list("Extra trusted CachyOS package names to recommend (optional)")

    p.section("Review")
    p.output(f"Project:   {config.project_name}")
    p.output(f"Directory: {config.project_path}")
    p.output("Agent:     OpenAI Codex CLI")
    p.output(f"Stack:     {', '.join(config.languages) or 'undecided'}")
    p.output(f"Database:  {config.database}")
    p.output(f"Git/CI:    {'yes' if config.git_enabled else 'no'} / {'yes' if config.github_actions else 'no'}")
    p.output("Generation preserves existing files. Conflicts become proposals unless a separate --force run is used.")
    if not p.confirm("Generate the project starter workspace now?", default=True):
        raise CancelledByUser("Generation cancelled before writing files.")

    launch = p.confirm("After generation, launch Codex with the prepared first prompt?", default=True)
    return WizardResult(config=config, launch_after_generation=launch, kickoff_mode=False)
