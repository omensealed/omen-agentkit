"""Reusable, credential-safe wizard questions and normalized choices."""

from __future__ import annotations

import re
from typing import Callable, Iterable

from ..toolchains import TOOLCHAINS, normalize_language, unique

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


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
                self.output(
                    "That entry resembles a credential. Do not put passwords, tokens, API keys, or private keys in project answers."
                )
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
    normalized = _normalize_database(default)
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
        default=normalized if normalized in {"none", "sqlite", "mariadb", "postgresql", "existing", "undecided"} else "undecided",
    )
