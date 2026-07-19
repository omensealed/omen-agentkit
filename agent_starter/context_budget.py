"""Bounded, read-only, advisory measurements for generated agent context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Iterable


MAX_CONTEXT_FILE_BYTES = 1024 * 1024
CONTEXT_FILES = (
    "START_HERE.md",
    "docs/AGENT-INDEX.md",
    "FIRST_PROMPT.md",
    "AGENTS.md",
)
SUGGESTED_TARGETS: dict[str, tuple[int | None, int | None]] = {
    "START_HERE.md": (1000, 120),
    "docs/AGENT-INDEX.md": (1000, 120),
    "FIRST_PROMPT.md": (500, None),
}
MIN_DUPLICATE_PARAGRAPH_WORDS = 12
_PATH_REFERENCE_RE = re.compile(r"`((?:\.?[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+(?:\.md|\.sh)?)`")


class ContextAuditError(ValueError):
    """Raised when context cannot be inspected through a safe local path."""


@dataclass(frozen=True, slots=True)
class ContextFileMetric:
    path: str
    words: int
    lines: int
    present: bool
    suggested_max_words: int | None
    suggested_max_lines: int | None
    within_suggested_target: bool


@dataclass(frozen=True, slots=True)
class DuplicateParagraph:
    fingerprint: str
    words: int
    paths: tuple[str, ...]
    excerpt: str


@dataclass(frozen=True, slots=True)
class ContextAuditIssue:
    path: str
    code: str
    explanation: str
    remedy: str


@dataclass(frozen=True, slots=True)
class ContextBudgetReport:
    root: Path
    files: tuple[ContextFileMetric, ...]
    duplicate_paragraphs: tuple[DuplicateParagraph, ...]
    default_required_files: tuple[str, ...]
    task_prompt_words: int
    issues: tuple[ContextAuditIssue, ...]
    schema_version: int = 1
    advisory_only: bool = True
    blocking: bool = False

    @property
    def default_required_file_count(self) -> int:
        return len(self.default_required_files)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "blocking": self.blocking,
            "root": str(self.root),
            "files": [asdict(item) for item in self.files],
            "duplicate_paragraphs": [asdict(item) for item in self.duplicate_paragraphs],
            "default_required_files": list(self.default_required_files),
            "default_required_file_count": self.default_required_file_count,
            "task_prompt_words": self.task_prompt_words,
            "issues": [asdict(item) for item in self.issues],
        }


def _validate_root(root: Path) -> Path:
    absolute = root.expanduser().absolute()
    if not absolute.exists():
        raise ContextAuditError("Context audit root does not exist.")
    if absolute.is_symlink() or not absolute.is_dir():
        raise ContextAuditError("Context audit root must be a regular local directory, not a symlink.")
    return absolute.resolve()


def _read_context_file(root: Path, relative: str) -> str | None:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ContextAuditError(f"Unsafe context path: {relative}")
    current = root
    for part in pure.parts:
        current = current / part
        if not current.exists() and not current.is_symlink():
            return None
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ContextAuditError(f"Context path must not use symlinks: {relative}")
    if not current.is_file():
        raise ContextAuditError(f"Context path must be a regular file: {relative}")
    if current.stat().st_size > MAX_CONTEXT_FILE_BYTES:
        raise ContextAuditError(f"Context file exceeds the 1 MiB read limit: {relative}")
    try:
        return current.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContextAuditError(f"Context file must be valid UTF-8: {relative}") from exc


def _metric(path: str, text: str | None) -> ContextFileMetric:
    max_words, max_lines = SUGGESTED_TARGETS.get(path, (None, None))
    words = len(text.split()) if text is not None else 0
    lines = len(text.splitlines()) if text is not None else 0
    within = text is not None and (max_words is None or words <= max_words) and (max_lines is None or lines <= max_lines)
    return ContextFileMetric(path, words, lines, text is not None, max_words, max_lines, within)


def _normalized_paragraphs(text: str) -> Iterable[tuple[str, int, str]]:
    for raw in re.split(r"\n\s*\n", text):
        normalized = re.sub(r"[`*_>#|\[\]()]", " ", raw)
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()
        words = len(normalized.split())
        if words < MIN_DUPLICATE_PARAGRAPH_WORDS:
            continue
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        excerpt = re.sub(r"\s+", " ", raw).strip()[:160]
        yield fingerprint, words, excerpt


def _duplicate_paragraphs(contents: dict[str, str]) -> tuple[DuplicateParagraph, ...]:
    occurrences: dict[str, tuple[int, str, set[str]]] = {}
    for path, text in contents.items():
        for fingerprint, words, excerpt in _normalized_paragraphs(text):
            if fingerprint not in occurrences:
                occurrences[fingerprint] = (words, excerpt, set())
            occurrences[fingerprint][2].add(path)
    duplicates = (
        DuplicateParagraph(fingerprint, words, tuple(sorted(paths)), excerpt)
        for fingerprint, (words, excerpt, paths) in occurrences.items()
        if len(paths) > 1
    )
    return tuple(sorted(duplicates, key=lambda item: (-len(item.paths), item.fingerprint)))


def _path_references(text: str) -> list[str]:
    return [match.group(1).removeprefix("./") for match in _PATH_REFERENCE_RE.finditer(text)]


def _default_required_files(first_prompt: str, agent_index: str) -> tuple[str, ...]:
    introduction = first_prompt.split("\n## ", 1)[0]
    references = _path_references(introduction)
    for line in agent_index.splitlines():
        if line.startswith("| Baseline/discovery |"):
            references.extend(_path_references(line))
            break
    ordered: list[str] = []
    for path in references:
        if path not in ordered:
            ordered.append(path)
    return tuple(ordered)


def audit_context(project_root: Path) -> ContextBudgetReport:
    """Measure generated first-run context without changing files or blocking work."""

    root = _validate_root(project_root)
    contents: dict[str, str] = {}
    issues: list[ContextAuditIssue] = []
    metrics: list[ContextFileMetric] = []
    for relative in CONTEXT_FILES:
        text = _read_context_file(root, relative)
        metrics.append(_metric(relative, text))
        if text is None:
            issues.append(ContextAuditIssue(
                relative,
                "context.file-missing",
                "A standard first-run context file is missing, so its budget cannot be measured.",
                "Generate or restore the file, then rerun the advisory context audit.",
            ))
        else:
            contents[relative] = text

    first_prompt = contents.get("FIRST_PROMPT.md", "")
    agent_index = contents.get("docs/AGENT-INDEX.md", "")
    required = _default_required_files(first_prompt, agent_index)
    for item in metrics:
        if item.present and not item.within_suggested_target:
            issues.append(ContextAuditIssue(
                item.path,
                "context.suggested-target-exceeded",
                "The file exceeds a suggested context budget; this is advisory and may be justified by project complexity.",
                "Review repetition and routing, or record why the additional context is necessary.",
            ))
    return ContextBudgetReport(
        root=root,
        files=tuple(metrics),
        duplicate_paragraphs=_duplicate_paragraphs(contents),
        default_required_files=required,
        task_prompt_words=len(first_prompt.split()),
        issues=tuple(issues),
    )


def render_context_audit(report: ContextBudgetReport) -> str:
    lines = ["Context budget audit — advisory only", f"Project: {report.root}", ""]
    for item in report.files:
        if item.suggested_max_words is None and item.suggested_max_lines is None:
            state = "measured; no suggested target"
        else:
            state = "within suggested target" if item.within_suggested_target else "review suggested"
        lines.append(f"- {item.path}: {item.words} words, {item.lines} lines ({state})")
    lines.extend((
        f"- Default first-prompt required files: {report.default_required_file_count}",
        f"- Default task prompt size: {report.task_prompt_words} words",
        f"- Duplicate paragraph fingerprints: {len(report.duplicate_paragraphs)}",
    ))
    for duplicate in report.duplicate_paragraphs:
        lines.append(f"  - {duplicate.fingerprint[:12]} in {', '.join(duplicate.paths)}: {duplicate.excerpt}")
    for issue in report.issues:
        lines.append(f"[advisory] {issue.path}: {issue.explanation} {issue.remedy}")
    lines.append("No finding blocks generation, validation, or launch.")
    return "\n".join(lines) + "\n"
