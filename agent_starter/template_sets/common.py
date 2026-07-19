"""Shared deterministic formatting primitives for generated artifact families."""

from __future__ import annotations

import json
from typing import Iterable


def clean(text: str) -> str:
    """Remove a template's own margin while preserving unindented inserts."""

    lines = text.strip("\n").splitlines()
    margin = 0
    for line in lines:
        if line.strip():
            margin = len(line) - len(line.lstrip(" "))
            break
    if margin:
        prefix = " " * margin
        lines = [line[margin:] if line.startswith(prefix) else line for line in lines]
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def md_list(items: Iterable[str], *, empty: str = "- None recorded.") -> str:
    values = [item.strip() for item in items if item.strip()]
    return "\n".join(f"- {item}" for item in values) if values else empty


def md_checklist(items: Iterable[str]) -> str:
    values = [item.strip() for item in items if item.strip()]
    return "\n".join(f"- [ ] {item}" for item in values)


def inline_list(items: Iterable[str], *, fallback: str = "Not decided") -> str:
    values = [item.strip() for item in items if item.strip()]
    return ", ".join(values) if values else fallback


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def json_string(value: str) -> str:
    """Return a double-quoted JSON scalar, which is also valid YAML."""

    return json.dumps(value, ensure_ascii=False)


def command_section(commands: Iterable[str], *, placeholder: str) -> str:
    values = [command.strip() for command in commands if command.strip()]
    if not values:
        return f"```bash\n# {placeholder}\n```"
    return "```bash\n" + "\n".join(values) + "\n```"
