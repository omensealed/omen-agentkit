"""Provider-neutral project capability intent.

This catalog names what a project needs.  Package names, repository policy,
and executable aliases remain provider-owned data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable


CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9._+-]{0,63}$")


class CapabilityCategory(str, Enum):
    BASE = "base"
    OPTIONAL = "optional"
    LANGUAGE = "language"
    DATABASE = "database"
    SANDBOX = "sandbox"


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    capability_id: str
    display_label: str
    purpose: str
    category: CapabilityCategory

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, str) or not CAPABILITY_ID_RE.fullmatch(self.capability_id):
            raise ValueError("capability_id must be a safe lowercase identifier.")
        for field, value in (("display_label", self.display_label), ("purpose", self.purpose)):
            if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > 1000:
                raise ValueError(f"{field} must be bounded non-empty text.")
        if not isinstance(self.category, CapabilityCategory):
            raise TypeError("category must be a CapabilityCategory.")


CAPABILITY_CATALOG: dict[str, CapabilityDefinition] = {
    "base.tooling": CapabilityDefinition(
        "base.tooling", "Base development tools",
        "Shell/build foundation plus Git, curl, JSON, search, archive, and compilation tools used by generated workflows.",
        CapabilityCategory.BASE,
    ),
    "optional.github-cli": CapabilityDefinition(
        "optional.github-cli", "GitHub CLI", "Optional GitHub command-line client.", CapabilityCategory.OPTIONAL
    ),
    "optional.shellcheck": CapabilityDefinition(
        "optional.shellcheck", "ShellCheck", "Optional static checks for shell scripts.", CapabilityCategory.OPTIONAL
    ),
    "language.python": CapabilityDefinition(
        "language.python", "Python toolchain", "Python runtime, isolated environments, and package installer.", CapabilityCategory.LANGUAGE
    ),
    "language.javascript": CapabilityDefinition(
        "language.javascript", "Node.js toolchain", "Node.js runtime and npm package workflow.", CapabilityCategory.LANGUAGE
    ),
    "language.rust": CapabilityDefinition(
        "language.rust", "Rust toolchain strategy", "Provider-appropriate Rust compiler, Cargo, and toolchain strategy.", CapabilityCategory.LANGUAGE
    ),
    "language.go": CapabilityDefinition(
        "language.go", "Go toolchain", "Go compiler and module workflow.", CapabilityCategory.LANGUAGE
    ),
    "language.php": CapabilityDefinition(
        "language.php", "PHP toolchain", "PHP CLI and Composer; extensions remain selected only when project requirements need them.", CapabilityCategory.LANGUAGE
    ),
    "language.cpp": CapabilityDefinition(
        "language.cpp", "C/C++ toolchain", "Compiler, debugger, CMake, and Ninja-style build tools.", CapabilityCategory.LANGUAGE
    ),
    "language.java": CapabilityDefinition(
        "language.java", "Java toolchain", "Supported JDK for JVM project builds and tests.", CapabilityCategory.LANGUAGE
    ),
    "language.godot": CapabilityDefinition(
        "language.godot", "Godot toolchain", "Godot editor/runtime with headless project checks.", CapabilityCategory.LANGUAGE
    ),
    "language.shell": CapabilityDefinition(
        "language.shell", "Shell toolchain", "Bash-compatible shell and ShellCheck.", CapabilityCategory.LANGUAGE
    ),
    "database.sqlite": CapabilityDefinition(
        "database.sqlite", "SQLite tools", "SQLite command-line development tools.", CapabilityCategory.DATABASE
    ),
    "database.mariadb": CapabilityDefinition(
        "database.mariadb", "MariaDB tools", "MariaDB development server/client capability.", CapabilityCategory.DATABASE
    ),
    "database.postgresql": CapabilityDefinition(
        "database.postgresql", "PostgreSQL tools", "PostgreSQL development server/client capability.", CapabilityCategory.DATABASE
    ),
    "sandbox.rootless-podman": CapabilityDefinition(
        "sandbox.rootless-podman", "Rootless Podman prerequisites",
        "Podman and provider-appropriate user-namespace, networking, and storage prerequisites.",
        CapabilityCategory.SANDBOX,
    ),
}


BASE_CAPABILITY_IDS = ("base.tooling",)
OPTIONAL_CAPABILITY_IDS = ("optional.github-cli", "optional.shellcheck")
LANGUAGE_CAPABILITY_IDS = {
    "python": "language.python",
    "javascript": "language.javascript",
    "rust": "language.rust",
    "go": "language.go",
    "php": "language.php",
    "cpp": "language.cpp",
    "java": "language.java",
    "godot": "language.godot",
    "shell": "language.shell",
}
DATABASE_CAPABILITY_IDS = {
    "sqlite": "database.sqlite",
    "mariadb": "database.mariadb",
    "postgresql": "database.postgresql",
}
ROOTLESS_PODMAN_CAPABILITY_ID = "sandbox.rootless-podman"


def select_capabilities(
    language_keys: Iterable[str],
    database: str,
    *,
    github: bool = True,
    rootless_podman: bool = False,
) -> tuple[str, ...]:
    """Select ordered provider-neutral intent for current project choices."""

    selected = list(BASE_CAPABILITY_IDS)
    if github:
        selected.append("optional.github-cli")
    for language in language_keys:
        capability_id = LANGUAGE_CAPABILITY_IDS.get(language)
        if capability_id:
            selected.append(capability_id)
    database_capability = DATABASE_CAPABILITY_IDS.get(database.lower())
    if database_capability:
        selected.append(database_capability)
    if rootless_podman:
        selected.append(ROOTLESS_PODMAN_CAPABILITY_ID)
    return tuple(dict.fromkeys(selected))


def unknown_capability_ids(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(value for value in values if value not in CAPABILITY_CATALOG)


def require_complete_provider_catalog(provider_id: str, capability_ids: Iterable[str]) -> None:
    keys = set(capability_ids)
    expected = set(CAPABILITY_CATALOG)
    missing = sorted(expected - keys)
    unexpected = sorted(keys - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise ValueError(f"Provider {provider_id!r} does not match the canonical capability catalog ({'; '.join(details)}).")
