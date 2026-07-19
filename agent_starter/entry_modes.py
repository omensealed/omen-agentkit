"""Shared presentation policy for guided and advanced entry flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EntryMode(str, Enum):
    GUIDED = "guided"
    ADVANCED = "advanced"


@dataclass(frozen=True, slots=True)
class EntryModePolicy:
    mode: EntryMode
    label: str
    explanation: str
    show_advanced_settings: bool


ENTRY_MODE_POLICIES = {
    EntryMode.GUIDED: EntryModePolicy(
        EntryMode.GUIDED,
        "Guided",
        "One decision at a time with consequences explained and conservative safe defaults; "
        "nonessential implementation settings stay hidden.",
        False,
    ),
    EntryMode.ADVANCED: EntryModePolicy(
        EntryMode.ADVANCED,
        "Advanced",
        "Expose the full settings while retaining the same canonical validation, approvals, and safety boundaries.",
        True,
    ),
}


def parse_entry_mode(value: str | EntryMode) -> EntryMode:
    if isinstance(value, EntryMode):
        return value
    if not isinstance(value, str):
        raise ValueError("Entry mode must be guided or advanced.")
    try:
        return EntryMode(value.strip().lower())
    except ValueError as exc:
        raise ValueError("Entry mode must be guided or advanced.") from exc


def entry_mode_policy(value: str | EntryMode) -> EntryModePolicy:
    return ENTRY_MODE_POLICIES[parse_entry_mode(value)]
