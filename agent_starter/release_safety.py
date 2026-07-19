"""Fail-closed local checks for explicitly tagged release intent."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import stat
import subprocess
import sys


_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_PYPROJECT_VERSION_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
_INIT_VERSION_RE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)
_MODEL_VERSION_RE = re.compile(r'^\s*kit_version:\s*str\s*=\s*"([^"]+)"', re.MULTILINE)
_CHANGELOG_RELEASE_RE = re.compile(r"^## ([0-9]+\.[0-9]+\.[0-9]+) — [0-9]{4}-[0-9]{2}-[0-9]{2}$", re.MULTILINE)
_MAX_TEXT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReleaseSafetyIssue:
    path: str
    code: str
    explanation: str
    remedy: str


@dataclass(frozen=True, slots=True)
class ReleaseSafetyReport:
    version: str | None
    tag: str
    issues: tuple[ReleaseSafetyIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def _issue(path: str, code: str, explanation: str, remedy: str) -> ReleaseSafetyIssue:
    return ReleaseSafetyIssue(path, code, explanation, remedy)


def _read_bounded_regular(root: Path, relative: str) -> tuple[str | None, ReleaseSafetyIssue | None]:
    path = root / relative
    try:
        metadata = path.lstat()
    except OSError:
        return None, _issue(relative, "release_file_missing", "A required release metadata file is missing or inaccessible.", "Restore the tracked file and rerun release verification.")
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_TEXT_BYTES:
        return None, _issue(relative, "release_file_unsafe", "A required release metadata file is symlinked, non-regular, or oversized.", "Use a tracked regular file no larger than 2 MiB.")
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError):
        return None, _issue(relative, "release_file_unreadable", "A required release metadata file is not readable UTF-8 text.", "Restore valid UTF-8 release metadata and rerun verification.")


def verify_release_safety(
    root: Path,
    *,
    expected_tag: str,
    actual_ref: str,
    git_status_text: str,
) -> ReleaseSafetyReport:
    """Verify exact tag, clean source, version fields, and changelog state."""

    issues: list[ReleaseSafetyIssue] = []
    if not isinstance(expected_tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", expected_tag):
        issues.append(_issue("release_tag", "invalid_release_tag", "Release tag must use exact vMAJOR.MINOR.PATCH form.", "Dispatch from a reviewed semantic-version tag and repeat that exact tag as input."))
        version = None
    else:
        version = expected_tag[1:]
    if actual_ref != f"refs/tags/{expected_tag}":
        issues.append(_issue("github.ref", "tag_ref_mismatch", "The workflow was not dispatched from the exact requested tag ref.", "Select the existing reviewed tag in the workflow ref chooser and repeat it exactly."))
    if git_status_text.strip():
        issues.append(_issue("git.status", "dirty_release_source", "Release source contains tracked or untracked changes.", "Release only from a clean committed tag; do not discard protected work to satisfy this check."))

    root = root.expanduser()
    if root.is_symlink():
        issues.append(_issue("root", "release_root_symlink", "Release root is a symbolic link.", "Use the directly checked-out repository directory."))
        return ReleaseSafetyReport(version, expected_tag, tuple(issues))
    files: dict[str, str] = {}
    for relative in ("VERSION", "pyproject.toml", "agent_starter/__init__.py", "agent_starter/models.py", "CHANGELOG.md"):
        text, read_issue = _read_bounded_regular(root, relative)
        if read_issue is not None:
            issues.append(read_issue)
        elif text is not None:
            files[relative] = text
    if version is None:
        return ReleaseSafetyReport(None, expected_tag, tuple(issues))

    discovered: dict[str, str | None] = {
        "VERSION": files.get("VERSION", "").strip() or None,
        "pyproject.toml": (_PYPROJECT_VERSION_RE.search(files.get("pyproject.toml", "")) or [None, None])[1],
        "agent_starter/__init__.py": (_INIT_VERSION_RE.search(files.get("agent_starter/__init__.py", "")) or [None, None])[1],
        "agent_starter/models.py": (_MODEL_VERSION_RE.search(files.get("agent_starter/models.py", "")) or [None, None])[1],
    }
    for path, found in discovered.items():
        if found != version:
            issues.append(_issue(path, "release_version_mismatch", f"Release version metadata does not equal {version}.", "Update VERSION, package metadata, public version, and ProjectConfig.kit_version together."))

    changelog = files.get("CHANGELOG.md", "")
    releases = _CHANGELOG_RELEASE_RE.findall(changelog)
    if releases.count(version) != 1:
        issues.append(_issue("CHANGELOG.md", "release_changelog_missing", "Changelog must contain exactly one dated heading for the release version.", f"Add exactly `## {version} — YYYY-MM-DD` with the reviewed release notes."))
    unreleased_match = re.search(r"^## Unreleased\s*\n(?P<body>.*?)(?=^## )", changelog, re.MULTILINE | re.DOTALL)
    if unreleased_match is None:
        issues.append(_issue("CHANGELOG.md", "unreleased_section_missing", "Changelog lacks the required Unreleased section.", "Restore `## Unreleased` before the dated release history."))
    elif unreleased_match.group("body").strip():
        issues.append(_issue("CHANGELOG.md", "unreleased_changes_present", "Unreleased changes remain at tagged release time.", "Move all intended entries under the new dated version heading before creating the tag."))
    return ReleaseSafetyReport(version, expected_tag, tuple(issues))


def _git_status(root: Path) -> tuple[str | None, ReleaseSafetyIssue | None]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None, _issue("git.status", "git_status_failed", "Git cleanliness could not be verified.", "Run from a normal clean Git checkout with Git available.")
    if result.returncode != 0:
        return None, _issue("git.status", "git_status_failed", "Git cleanliness could not be verified.", "Run from a normal clean Git checkout with Git available.")
    return result.stdout, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify clean, exact tagged release intent without publishing.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-tag", required=True)
    parser.add_argument("--actual-ref", required=True)
    args = parser.parse_args(argv)
    status, status_issue = _git_status(args.root)
    if status_issue is not None:
        report = ReleaseSafetyReport(None, args.expected_tag, (status_issue,))
    else:
        report = verify_release_safety(
            args.root,
            expected_tag=args.expected_tag,
            actual_ref=args.actual_ref,
            git_status_text=status or "",
        )
    if report.ok:
        print(f"Release safety verified for {report.tag}; no release was published.")
        return 0
    for issue in report.issues:
        print(f"Error [{issue.code}] {issue.path}: {issue.explanation}", file=sys.stderr)
        print(f"Safe remedy: {issue.remedy}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
