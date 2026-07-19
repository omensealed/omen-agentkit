"""Interactive beginner-oriented project configuration wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import AgentError, get_adapter
from .doctor import provider_for_detection
from .entry_modes import EntryMode, entry_mode_policy
from .guided.questions import (
    CancelledByUser,
    InputFn,
    OutputFn,
    Prompter,
    _choose_database,
    _looks_sensitive,
    _manual_languages,
    _normalize_database,
    _split_list,
    slugify,
)
from .guided.advisor import (
    _collect_capability_decisions,
    _local_recommendation,
    _prepare_agent,
    _print_recommendation,
    build_advisor_host_snapshot,
    build_advisor_prompt,
    render_advisor_host_snapshot,
)
from .models import (
    AdvisorRecommendation,
    CapabilityDecisionState,
    ProjectConfig,
    SandboxConfig,
)
from .platforms import detect_host
from .recommendation import build_recommendation_review, render_recommendation_review
from .recommendation_cache import (
    RecommendationCacheError,
    get_recommendation_cache,
    recommendation_cache_key,
)
from .toolchains import normalize_language, unique


@dataclass(slots=True)
class WizardResult:
    config: ProjectConfig
    launch_after_generation: bool
    kickoff_mode: bool
def run_wizard(
    *,
    initial_path: str | None = None,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
    skip_agent_setup: bool = False,
    entry_mode: str | EntryMode = EntryMode.ADVANCED,
) -> WizardResult:
    p = Prompter(input_fn, output_fn)
    mode_policy = entry_mode_policy(entry_mode)
    guided = mode_policy.mode is EntryMode.GUIDED
    p.output("CLI AI Agent Starter Kit")
    p.output("This wizard creates project guidance and executable helpers. It never asks for or stores account tokens, API keys, or database passwords.")
    p.output(f"{mode_policy.label} mode: {mode_policy.explanation}")
    if guided:
        p.output("Run `agent-starter new --mode advanced` whenever you want every implementation setting.")

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
    stage_default = "renovation" if config.project_mode == "existing" else "idea"
    config.project_stage = stage_default if guided else p.choose(
        "Current stage:",
        [("idea", "Idea"), ("prototype", "Prototype"), ("active", "Active development"), ("renovation", "Major renovation")],
        default=stage_default,
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
    packaging_defaults = ["source checkout", "documented local development build"]
    config.packaging_targets = packaging_defaults if guided else p.ask_list(
        "Desired deliverables/packages (comma-separated)", default=packaging_defaults
    )

    p.section("Security and data boundaries")
    if guided:
        p.output("These answers change the generated threat model and testing plan; choose yes whenever the feature may apply.")
    config.network_access = p.confirm("Will the program access a network or expose a network service?", default=config.project_type in {"web", "api"})
    config.user_accounts = p.confirm("Will it have user accounts, identities, or authorization?", default=False)
    config.handles_personal_data = p.confirm("Will it store personal, private, or user-generated data?", default=False)
    config.handles_payments = p.confirm("Will it handle payments or financial transactions?", default=False)
    config.security_notes = p.ask("Other security/data constraints (do not enter credentials)")

    p.section("OpenAI Codex CLI")
    config.primary_agent = "codex"
    p.output("This edition creates Codex-only workspaces and uses the official Codex CLI account flow.")
    config.setup_agent_now = not skip_agent_setup and p.confirm("Install or authorize Codex during this wizard when needed?", default=True)
    if guided:
        config.codex_agentkit_skill = True
        p.output("Safe default: include the project-local `$agentkit` prompt helper; it grants no execution or account access.")
    else:
        config.codex_agentkit_skill = p.confirm(
            "Install the repo-local `$agentkit` Codex skill so future short requests can be expanded into full Agent Kit prompts from inside Codex?",
            default=True,
        )

    p.section("Rootless Podman sandbox")
    p.output("The optional project sandbox generates reviewable Podman files only. It does not install packages or run Podman during generation.")
    existing_default = config.project_mode == "new"
    if config.project_mode == "existing":
        p.output("Existing/renovation projects may contain production assumptions. Defaulting sandbox generation to no until reviewed.")
    sandbox_enabled = p.confirm("Create a rootless Podman development sandbox for this project?", default=existing_default)
    if sandbox_enabled:
        if guided:
            image_profile = "arch-toolchain"
            sandbox_mode = "toolchain"
            autonomous = False
            p.output("Safe default: host Codex with an isolated Arch toolchain, no autonomous bootstrap, and no extra host interfaces.")
        else:
            p.output("The sandbox image is an explicit project choice and does not have to match the host distribution.")
            image_profile = p.choose(
                "Which tested toolchain image should the sandbox use?",
                [
                    ("arch-toolchain", "Arch Linux toolchain image"),
                    ("debian-toolchain", "Debian stable toolchain image"),
                ],
                default="arch-toolchain",
            )
            sandbox_mode = p.choose(
                "How should Codex use it?",
                [
                    ("toolchain", "Host Codex, containerized test/toolchain runner"),
                    ("codex", "Run Codex itself inside the project container"),
                    ("files-only", "Generate sandbox files only"),
                ],
                default="toolchain",
            )
            autonomous = p.confirm("Create a first-run autonomous bootstrap prompt for the sandbox?", default=False)
        config.sandbox = SandboxConfig(
            enabled=True,
            mode=sandbox_mode,
            image_profile=image_profile,
            codex_inside_container=sandbox_mode == "codex",
            first_run_autonomous_prompt=autonomous,
            install_agentkit_skill=config.codex_agentkit_skill,
        )
    else:
        config.sandbox = SandboxConfig()

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
    advisor_detection = None
    recommendation_cache = None
    recommendation_key = ""
    refresh_recommendation = False
    if config.use_ai_advisor:
        advisor_detection = detect_host()
        recommendation_cache = get_recommendation_cache()
        recommendation_key = recommendation_cache_key(config, advisor_detection.profile)
        try:
            cached = recommendation_cache.load(recommendation_key)
        except RecommendationCacheError as exc:
            cached = None
            p.output(f"The cached recommendation was ignored safely: {exc}")
            p.output("A new recommendation can be requested; the unsafe cache entry will not be used.")
        if cached is not None:
            p.output(f"Found a current cached structured recommendation from {cached.created_at}.")
            if agent_ready:
                p.output("A refresh action is available: Refresh this cached recommendation with Codex.")
                refresh_recommendation = p.confirm(
                    "Refresh this cached recommendation with Codex?",
                    default=False,
                )
            else:
                p.output("Using the cache offline. Refresh requires an available, authorized Codex CLI.")
            if not refresh_recommendation:
                recommendation = cached.recommendation
                p.output("Using the cached structured recommendation without contacting Codex.")
    if config.use_ai_advisor and agent_ready and recommendation is None:
        host_snapshot = build_advisor_host_snapshot(config, profile=advisor_detection.profile)
        p.output("The advisor will receive this exact redacted host snapshot:")
        p.output(render_advisor_host_snapshot(host_snapshot))
        p.output(
            "It excludes usernames, hostnames, home paths, IP addresses, environment dumps, histories, "
            "credentials, browser state, SSH configuration, and unrelated installed packages."
        )
        p.output("Requesting a structured recommendation in a temporary, read-only advisory workspace...")
        try:
            recommendation = adapter.advise(config, build_advisor_prompt(config, host_snapshot=host_snapshot))
            try:
                recommendation_cache.store(recommendation_key, recommendation)
            except RecommendationCacheError as exc:
                p.output(f"The recommendation was accepted but could not be cached safely: {exc}")
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

    if guided:
        config.stack_notes = config.advisor.architecture
        config.database_notes = ""
        config.minimal_dependencies = True
        p.output("Safe default: keep the proposed small architecture and require justification for production dependencies.")
    else:
        config.stack_notes = p.ask("Stack/architecture constraints or preferences", default=config.advisor.architecture)
        config.database_notes = p.ask("Database constraints, existing schema, or expected data size (never enter a password)")
        config.minimal_dependencies = p.confirm("Require justification before adding production dependencies?", default=True)
    if config.sandbox.enabled and (config.project_type == "game" or "godot" in config.languages):
        p.output(
            "Game/Godot note: headless sandbox checks can work without GUI passthrough, but interactive "
            "container playtesting usually needs explicit GPU/audio/controller passthrough. This mounts extra "
            "host interfaces and should stay off unless you deliberately want container playtesting."
        )
        config.sandbox.gui_passthrough = p.confirm(
            "Generate the advanced GPU/audio/controller passthrough playtest script?",
            default=False,
        )

    p.section("Testing, Git, and automation")
    default_tests = ["unit", "integration"]
    if config.project_type in {"web", "desktop", "game"}:
        default_tests.append("end-to-end smoke")
    config.tests = default_tests if guided else p.multi_choose(
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
    config.browser_tests = (
        "browser" in config.target_platforms and config.project_type == "web"
        if guided
        else "browser" in config.target_platforms and p.confirm(
            "Plan browser automation for critical flows?", default=config.project_type == "web"
        )
    )
    config.quality_checks = ["format", "lint", "build", "tests", "documentation"]
    config.git_enabled = p.confirm("Initialize a local Git repository if one is not present?", default=True)
    p.output("Local-first recommendation: prove setup and tests locally before adding GitHub Actions or a remote.")
    config.github_actions = False if guided else p.confirm("Generate a GitHub Actions CI workflow now?", default=False)
    if guided:
        p.output("Safe default: defer GitHub Actions and remote creation until local checks pass.")
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
    config.default_branch = "main" if guided else p.ask("Default Git branch", default="main", required=True)
    p.output("License quick guide:")
    p.output("  AGPL-3.0-or-later is the default for new Agent Kit projects.")
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
        default="AGPL-3.0-or-later",
    )
    arch_extras = [] if guided else p.ask_list("Extra trusted CachyOS package names to recommend (optional)")
    config.extra_packages_by_provider = {"arch": arch_extras} if arch_extras else {}

    if config.use_ai_advisor:
        advisor_detection = advisor_detection or detect_host()
        provider = provider_for_detection(advisor_detection)
        review = build_recommendation_review(
            config,
            profile=advisor_detection.profile,
            provider=provider,
            advisor=config.advisor,
        )
        p.output("")
        for line in render_recommendation_review(review):
            p.output(line)
        # Persist project-owned decisions and accepted provider-neutral intent
        # only. Neither decision state nor advisor content authorizes commands.
        config.capability_decisions = _collect_capability_decisions(p, review)
        config.advisor.toolchain_capabilities = [
            item.capability_id
            for item in config.capability_decisions
            if item.decision is CapabilityDecisionState.ACCEPTED
        ]
        config.advisor.raw_output = ""

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
