"""CachyOS toolchain knowledge and generated command defaults."""

from __future__ import annotations

from dataclasses import dataclass
import textwrap
from typing import Iterable

from .capabilities import (
    BASE_CAPABILITY_IDS,
    DATABASE_CAPABILITY_IDS,
    LANGUAGE_CAPABILITY_IDS,
    OPTIONAL_CAPABILITY_IDS,
    select_capabilities,
)
from .deployment_ci import github_action_reference
from .platforms.arch import arch_packages_for_capabilities


@dataclass(frozen=True, slots=True)
class Toolchain:
    key: str
    display: str
    aliases: tuple[str, ...]
    commands: tuple[str, ...]
    setup_commands: tuple[str, ...] = ()
    build_commands: tuple[str, ...] = ()
    test_commands: tuple[str, ...] = ()
    lint_commands: tuple[str, ...] = ()
    gitignore: tuple[str, ...] = ()
    ci_setup: tuple[str, ...] = ()

    @property
    def capabilities(self) -> tuple[str, ...]:
        """Compatibility view over provider-neutral catalog selection."""

        capability_id = LANGUAGE_CAPABILITY_IDS.get(self.key)
        return (capability_id,) if capability_id else ()

    @property
    def packages(self) -> tuple[str, ...]:
        """Compatibility view; Arch package authority lives in capability records."""

        return arch_packages_for_capabilities(self.capabilities)


TOOLCHAINS: tuple[Toolchain, ...] = (
    Toolchain(
        key="python",
        display="Python",
        aliases=("python", "python3", "py"),
        commands=("python3",),
        setup_commands=("python3 -m venv .venv", "source .venv/bin/activate"),
        build_commands=("python3 -m compileall -q .",),
        test_commands=("python3 -m unittest discover -s tests -v",),
        lint_commands=("python3 -m compileall -q .",),
        gitignore=(".venv/", "__pycache__/", "*.py[cod]", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/"),
        ci_setup=(
            f"      - name: Set up Python\n        uses: {github_action_reference('actions/setup-python')}\n        with:\n          python-version: '3.13'",
        ),
    ),
    Toolchain(
        key="javascript",
        display="JavaScript / Node.js",
        aliases=("javascript", "js", "node", "nodejs", "typescript", "ts"),
        commands=("node", "npm"),
        setup_commands=("[ -f package.json ] && npm install || printf '%s\\n' 'No package.json; skipping npm install.'",),
        build_commands=("[ -f package.json ] && npm run build --if-present || printf '%s\\n' 'No package.json; skipping npm build.'",),
        test_commands=("[ -f package.json ] && npm test --if-present || printf '%s\\n' 'No package.json; skipping npm tests.'",),
        lint_commands=("[ -f package.json ] && npm run lint --if-present || printf '%s\\n' 'No package.json; skipping npm lint.'",),
        gitignore=("node_modules/", "npm-debug.log*", "coverage/", "dist/", ".parcel-cache/"),
        ci_setup=(
            f"      - name: Set up Node.js\n        uses: {github_action_reference('actions/setup-node')}\n        with:\n          node-version: '24'",
        ),
    ),
    Toolchain(
        key="rust",
        display="Rust",
        aliases=("rust", "cargo"),
        commands=("cargo", "rustc"),
        setup_commands=("rustup default stable", "rustup component add rustfmt clippy"),
        build_commands=("cargo build --locked",),
        test_commands=("cargo test --all-targets --all-features",),
        lint_commands=("cargo fmt --all -- --check", "cargo clippy --all-targets --all-features -- -D warnings"),
        gitignore=("target/", "**/*.rs.bk"),
        ci_setup=("      - name: Set up Rust\n        run: rustup toolchain install stable --profile minimal --component rustfmt,clippy",),
    ),
    Toolchain(
        key="go",
        display="Go",
        aliases=("go", "golang"),
        commands=("go",),
        setup_commands=("go mod download",),
        build_commands=("go build ./...",),
        test_commands=("go test ./...",),
        lint_commands=("gofmt -l . | tee /tmp/gofmt-files && test ! -s /tmp/gofmt-files", "go vet ./..."),
        gitignore=("bin/", "*.test", "coverage.out"),
        ci_setup=(f"      - name: Set up Go\n        uses: {github_action_reference('actions/setup-go')}\n        with:\n          go-version: 'stable'",),
    ),
    Toolchain(
        key="php",
        display="PHP",
        aliases=("php", "php8"),
        commands=("php",),
        setup_commands=("[ -f composer.json ] && composer install --no-interaction || printf '%s\\n' 'No composer.json; skipping composer install.'",),
        build_commands=("[ -f composer.json ] && composer validate --no-check-publish || printf '%s\\n' 'No composer.json; skipping composer validate.'",),
        test_commands=("[ -f composer.json ] && composer run-script test || printf '%s\\n' 'No composer.json; skipping composer tests.'",),
        lint_commands=("find . -type f -name '*.php' -not -path './vendor/*' -print0 | xargs -0 -r -n1 php -l",),
        gitignore=("vendor/", ".phpunit.result.cache", "composer.phar"),
        ci_setup=("      - name: Set up PHP\n        run: sudo apt-get update && sudo apt-get install -y php-cli composer",),
    ),
    Toolchain(
        key="cpp",
        display="C / C++",
        aliases=("c", "c++", "cpp", "clang", "gcc"),
        commands=("cmake", "ninja"),
        setup_commands=("cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug",),
        build_commands=("cmake --build build",),
        test_commands=("ctest --test-dir build --output-on-failure",),
        lint_commands=("cmake --build build",),
        gitignore=("build/", "cmake-build-*/", "*.o", "*.obj", "*.so", "*.a", "compile_commands.json"),
    ),
    Toolchain(
        key="java",
        display="Java",
        aliases=("java", "kotlin", "jvm"),
        commands=("java",),
        setup_commands=("./gradlew --version",),
        build_commands=("./gradlew build",),
        test_commands=("./gradlew test",),
        lint_commands=("./gradlew check",),
        gitignore=(".gradle/", "build/", "*.class", "out/"),
        ci_setup=(f"      - name: Set up Java\n        uses: {github_action_reference('actions/setup-java')}\n        with:\n          distribution: temurin\n          java-version: '21'",),
    ),
    Toolchain(
        key="godot",
        display="Godot / GDScript",
        aliases=("godot", "gdscript"),
        commands=("godot",),
        build_commands=("godot --headless --path . --editor --quit",),
        test_commands=("godot --headless --path . --quit",),
        lint_commands=("godot --headless --path . --editor --quit",),
        gitignore=(".godot/", "export.cfg", "export_presets.cfg", "*.tmp"),
    ),
    Toolchain(
        key="shell",
        display="POSIX shell / Bash",
        aliases=("shell", "bash", "sh"),
        commands=("bash", "shellcheck"),
        test_commands=("bash tests/run.sh",),
        lint_commands=("find . -type f -name '*.sh' -not -path './.git/*' -print0 | xargs -0 -r shellcheck",),
    ),
)

BASE_CAPABILITIES = BASE_CAPABILITY_IDS
OPTIONAL_CAPABILITIES = OPTIONAL_CAPABILITY_IDS

DATABASE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    name: (capability_id,)
    for name, capability_id in DATABASE_CAPABILITY_IDS.items()
}

# Compatibility constants remain derived from the authoritative Arch catalog.
BASE_PACKAGES = arch_packages_for_capabilities(BASE_CAPABILITIES)
OPTIONAL_PACKAGES = arch_packages_for_capabilities(OPTIONAL_CAPABILITIES)
DATABASE_PACKAGES: dict[str, tuple[str, ...]] = {
    name: arch_packages_for_capabilities(capabilities)
    for name, capabilities in DATABASE_CAPABILITIES.items()
}

DATABASE_COMMANDS: dict[str, str] = {
    "none": "No database is planned.",
    "sqlite": "Use a local SQLite file outside version control; commit schema and migrations, never generated database files.",
    "mariadb": "Use a dedicated MariaDB development database and least-privilege application user; keep credentials only in ignored local environment files.",
    "postgresql": "Use a dedicated PostgreSQL development database and least-privilege application role; keep credentials only in ignored local environment files.",
    "existing": "Reuse the existing database only through documented migrations, backups, and a non-production development account.",
    "undecided": "The database choice remains a recorded architecture decision before persistence code begins.",
}


def normalize_language(value: str) -> str:
    candidate = value.strip().lower()
    for toolchain in TOOLCHAINS:
        if candidate == toolchain.key or candidate in toolchain.aliases:
            return toolchain.key
    return candidate.replace(" ", "-")


def selected_toolchains(languages: Iterable[str]) -> list[Toolchain]:
    keys = {normalize_language(item) for item in languages if item.strip()}
    result: list[Toolchain] = []
    for toolchain in TOOLCHAINS:
        if toolchain.key in keys:
            result.append(toolchain)
    return result


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def capabilities_for(
    languages: Iterable[str],
    database: str,
    *,
    github: bool = True,
    rootless_podman: bool = False,
) -> list[str]:
    language_keys = [toolchain.key for toolchain in selected_toolchains(languages)]
    return list(select_capabilities(
        language_keys,
        database,
        github=github,
        rootless_podman=rootless_podman,
    ))


def packages_for(languages: Iterable[str], database: str, *, github: bool = True) -> list[str]:
    """Return the preserved CachyOS/Arch package view for existing callers."""

    return list(arch_packages_for_capabilities(capabilities_for(languages, database, github=github)))


def commands_for(languages: Iterable[str], kind: str) -> list[str]:
    attribute = {
        "setup": "setup_commands",
        "build": "build_commands",
        "test": "test_commands",
        "lint": "lint_commands",
    }[kind]
    commands: list[str] = []
    for toolchain in selected_toolchains(languages):
        commands.extend(getattr(toolchain, attribute))
    return unique(commands)


def gitignore_for(languages: Iterable[str], database: str) -> list[str]:
    lines = [
        ".env",
        ".env.*",
        "!.env.example",
        "!.env.sandbox.example",
        "!.env.*.example",
        "*.local",
        "*.log",
        ".DS_Store",
        "Thumbs.db",
        ".idea/",
        ".vscode/settings.json",
        "AGENTS.md",
        "FIRST_PROMPT.md",
        "FIRST_RUN_AUTONOMOUS.md",
        ".agents/",
        ".codex/",
        ".agent-starter/",
        ".codex-log/",
        ".codex/*.log",
        ".codex/*.jsonl",
        ".codex/sessions/",
        ".codex/tmp/",
        ".agent-starter/runtime.json",
        ".agent-starter/backups/",
        ".agent-starter/proposals/",
        "NEXT_PROMPT.md",
        "LOCAL_MODEL_HANDOFF.md",
        "OLLAMA_HANDOFF.md",
        "*-codex-prompt.md",
        "*-local-model-handoff.md",
        "docs/09-PROGRESS.md",
        "docs/11-IMPLEMENTATION-NOTES.md",
        "docs/14-AGENT-HANDOFF.md",
        "docs/AI-STACK-RECOMMENDATION.md",
        "docs/agent-prompts/",
        "tmp/",
        "temp/",
    ]
    for toolchain in selected_toolchains(languages):
        lines.extend(toolchain.gitignore)
    if database.lower() == "sqlite":
        lines.extend(("*.sqlite", "*.sqlite3", "*.db", "*.db-wal", "*.db-shm"))
    return unique(lines)


def fallback_recommendation(project_type: str, platforms: Iterable[str], network_access: bool) -> tuple[list[str], str, str]:
    """Return a conservative recommendation when an online agent is unavailable."""

    kind = project_type.lower()
    platform_text = " ".join(platforms).lower()
    if kind in {"cli", "automation", "data"}:
        languages = ["python"]
        architecture = "A small Python package with a thin CLI entry point, pure domain modules, and standard-library unittest coverage."
    elif kind in {"web", "website", "web-app"}:
        languages = ["javascript"]
        architecture = "A minimal Node.js service with vanilla browser HTML/CSS/JavaScript, a small HTTP boundary, and separated domain logic."
    elif kind in {"game", "video-game"} and "browser" in platform_text:
        languages = ["javascript"]
        architecture = "A browser game using Canvas and vanilla JavaScript, with deterministic game-state modules separated from rendering and input."
    elif kind in {"game", "video-game"}:
        languages = ["godot"]
        architecture = "A Godot project with scenes kept thin, gameplay logic split into testable scripts, and headless smoke checks."
    elif kind in {"system", "native", "desktop"}:
        languages = ["rust"]
        architecture = "A Rust workspace with a small core library, a thin application shell, explicit error types, and cargo-based tests."
    elif kind in {"api", "service", "server"}:
        languages = ["go"]
        architecture = "A small Go service organized around handlers, domain services, and repository interfaces, with httptest-based integration coverage."
    else:
        languages = ["python"]
        architecture = "A modular Python project that starts with one end-to-end vertical slice and standard-library tests."

    database = "sqlite" if network_access or kind in {"web", "api", "service", "desktop", "game"} else "none"
    return languages, database, architecture


def ci_setup_for(languages: Iterable[str]) -> list[str]:
    lines: list[str] = []
    for toolchain in selected_toolchains(languages):
        for snippet in toolchain.ci_setup:
            normalized = textwrap.dedent(snippet).strip()
            if normalized and normalized not in lines:
                lines.append(normalized)
    return lines
