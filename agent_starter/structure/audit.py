"""Read-only Python source structure measurement and advisory reporting."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import io
import json
import os
from pathlib import Path, PurePosixPath
import token
import tokenize
from typing import Any, Iterable, Iterator

from .policy import (
    DEFAULT_STRUCTURE_POLICY,
    FunctionMeasurement,
    ResponsibilityMeasurement,
    StructureExemption,
    StructureFinding,
    StructureObservation,
    StructurePolicy,
    evaluate_structure,
)


MAX_SOURCE_FILES = 5000
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_BASELINE_BYTES = 1024 * 1024
IGNORED_DIRECTORIES = frozenset({
    ".git", ".hg", ".svn", ".agent-starter", ".agents", ".codex", ".venv", "venv",
    "node_modules", "build", "dist", "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
})


class AuditError(ValueError):
    """Raised when the requested read boundary or baseline is unsafe."""


@dataclass(frozen=True, slots=True)
class AuditFunction:
    name: str
    logical_lines: int
    start_line: int
    payload_only: bool


@dataclass(frozen=True, slots=True)
class AuditClass:
    name: str
    logical_lines: int
    start_line: int
    responsibility_groups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuditModule:
    path: str
    module_name: str
    logical_lines: int
    functions: tuple[AuditFunction, ...]
    classes: tuple[AuditClass, ...]
    responsibility_groups: tuple[str, ...]
    public_module: bool
    documented_purpose: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "module_name": self.module_name,
            "logical_lines": self.logical_lines,
            "functions": [asdict(item) for item in self.functions],
            "classes": [asdict(item) for item in self.classes],
            "responsibility_groups": list(self.responsibility_groups),
            "public_module": self.public_module,
            "documented_purpose": self.documented_purpose,
        }


@dataclass(frozen=True, slots=True)
class AuditIssue:
    path: str
    code: str
    explanation: str
    remedy: str
    severity: str = "warning"


@dataclass(frozen=True, slots=True)
class AuditChange:
    path: str
    baseline_logical_lines: int
    current_logical_lines: int
    logical_lines_delta: int
    function_count_delta: int
    class_count_delta: int


@dataclass(frozen=True, slots=True)
class AcknowledgedExemption:
    path: str
    category: str
    reason: str


@dataclass(frozen=True, slots=True)
class StructureHotspot:
    path: str
    score: int
    findings: tuple[StructureFinding, ...]


@dataclass(frozen=True, slots=True)
class StructureAuditReport:
    modules: tuple[AuditModule, ...]
    hotspots: tuple[StructureHotspot, ...]
    dependency_cycles: tuple[tuple[str, ...], ...]
    changes: tuple[AuditChange, ...]
    acknowledged_exemptions: tuple[AcknowledgedExemption, ...]
    issues: tuple[AuditIssue, ...]
    baseline_status: str
    schema_version: int = 1
    advisory_only: bool = True
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "blocking": self.blocking,
            "root": ".",
            "scope": "python-source",
            "baseline_status": self.baseline_status,
            "modules": [item.to_dict() for item in self.modules],
            "hotspots": [
                {"path": item.path, "score": item.score, "findings": [asdict(finding) for finding in item.findings]}
                for item in self.hotspots
            ],
            "dependency_cycles": [list(item) for item in self.dependency_cycles],
            "changes": [asdict(item) for item in self.changes],
            "acknowledged_exemptions": [asdict(item) for item in self.acknowledged_exemptions],
            "issues": [asdict(item) for item in self.issues],
        }


@dataclass(frozen=True, slots=True)
class _BaselineMetric:
    logical_lines: int
    function_count: int
    class_count: int
    append_only_changes: int


@dataclass(frozen=True, slots=True)
class _Baseline:
    status: str
    modules: dict[str, _BaselineMetric]
    cycles: frozenset[frozenset[str]]
    exemptions: dict[str, StructureExemption]


@dataclass(frozen=True, slots=True)
class _ParsedModule:
    measured: AuditModule
    tree: ast.Module
    package_module: bool


_RESPONSIBILITY_WORDS: dict[str, frozenset[str]] = {
    "cli": frozenset({"argparse", "click", "typer", "cli", "command", "parser"}),
    "configuration": frozenset({"config", "configuration", "json", "toml", "yaml"}),
    "filesystem": frozenset({"path", "pathlib", "file", "files", "shutil", "tempfile", "os"}),
    "networking": frozenset({"http", "https", "socket", "urllib", "requests", "network", "client"}),
    "persistence": frozenset({"database", "db", "sqlite", "sqlite3", "repository", "storage", "persist", "save"}),
    "process": frozenset({"subprocess", "process", "popen", "shell", "exec"}),
    "security": frozenset({"auth", "token", "secret", "security", "permission", "credential"}),
    "templates": frozenset({"template", "render", "markdown", "html", "css"}),
    "ui": frozenset({"ui", "gui", "view", "window", "webview", "dialog"}),
}


def _safe_relative_path(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
        raise AuditError(f"{field} must be a bounded relative path.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AuditError(f"{field} must stay inside the project root.")
    return path.as_posix()


def _strict_nonnegative(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuditError(f"{field} must be a non-negative integer.")
    return value


def _load_baseline(root: Path, requested: Path | None) -> _Baseline:
    default = root / ".agent-starter" / "structure-baseline.json"
    if requested is None and not default.exists() and not default.is_symlink():
        return _Baseline("not-recorded", {}, frozenset(), {})
    candidate = default if requested is None else requested.expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise AuditError("Structure baseline must be a regular non-symlink file inside the project root.")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise AuditError("Structure baseline must exist inside the project root.") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_BASELINE_BYTES:
        raise AuditError("Structure baseline must be a regular file no larger than 1 MiB.")
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError("Structure baseline must be valid bounded UTF-8 JSON.") from exc
    if not isinstance(raw, dict) or set(raw) - {"schema_version", "modules", "dependency_cycles", "exemptions"}:
        raise AuditError("Structure baseline contains unknown fields or is not an object.")
    if raw.get("schema_version") != 1:
        raise AuditError("Structure baseline schema_version must be 1.")
    modules_raw = raw.get("modules", {})
    cycles_raw = raw.get("dependency_cycles", [])
    exemptions_raw = raw.get("exemptions", {})
    if not isinstance(modules_raw, dict) or not isinstance(cycles_raw, list) or not isinstance(exemptions_raw, dict):
        raise AuditError("Structure baseline modules/exemptions must be objects and dependency_cycles must be a list.")
    modules: dict[str, _BaselineMetric] = {}
    for path_value, metric in modules_raw.items():
        path = _safe_relative_path(path_value, field="baseline module path")
        if not isinstance(metric, dict) or set(metric) != {
            "logical_lines", "function_count", "class_count", "append_only_changes"
        }:
            raise AuditError("Each baseline module requires exact logical/function/class/append measurements.")
        modules[path] = _BaselineMetric(
            _strict_nonnegative(metric["logical_lines"], field="baseline logical_lines"),
            _strict_nonnegative(metric["function_count"], field="baseline function_count"),
            _strict_nonnegative(metric["class_count"], field="baseline class_count"),
            _strict_nonnegative(metric["append_only_changes"], field="baseline append_only_changes"),
        )
    cycles: set[frozenset[str]] = set()
    for item in cycles_raw:
        if not isinstance(item, list) or len(item) < 3 or len(item) > 64 or item[0] != item[-1]:
            raise AuditError("Each baseline dependency cycle must be a closed list of 3 to 64 module names.")
        names = tuple(_safe_module_name(value, field="baseline cycle member") for value in item)
        cycles.add(frozenset(names[:-1]))
    exemptions: dict[str, StructureExemption] = {}
    for path_value, exemption_raw in exemptions_raw.items():
        path = _safe_relative_path(path_value, field="baseline exemption path")
        if not isinstance(exemption_raw, dict) or set(exemption_raw) - {
            "category", "reason", "hides_executable_complexity"
        }:
            raise AuditError("Each baseline exemption has only category, reason, and optional complexity flag.")
        try:
            exemptions[path] = StructureExemption(
                category=exemption_raw.get("category"),
                reason=exemption_raw.get("reason"),
                hides_executable_complexity=exemption_raw.get("hides_executable_complexity", False),
            )
        except ValueError as exc:
            raise AuditError(f"Invalid structure exemption for {path}: {exc}") from exc
    return _Baseline("loaded", modules, frozenset(cycles), exemptions)


def _safe_module_name(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise AuditError(f"{field} must be a bounded module name.")
    if any(not part.isidentifier() for part in value.split(".")):
        raise AuditError(f"{field} must contain dotted Python identifiers.")
    return value


def _source_files(root: Path, issues: list[AuditIssue]) -> list[Path]:
    files: list[Path] = []
    for directory, names, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        kept: list[str] = []
        for name in sorted(names):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if name in IGNORED_DIRECTORIES:
                continue
            if path.is_symlink():
                issues.append(AuditIssue(relative, "structure.symlink-skipped", "A symlinked directory was skipped.", "Audit its real project-local target separately if intended."))
                continue
            kept.append(name)
        names[:] = kept
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = base / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(AuditIssue(relative, "structure.symlink-skipped", "A symlinked source file was skipped.", "Replace it with a regular project-local file or audit its target separately."))
                continue
            files.append(path)
            if len(files) >= MAX_SOURCE_FILES:
                issues.append(AuditIssue(".", "structure.file-limit", "The 5000-file audit limit was reached.", "Narrow the project scope or review ignored/generated directories."))
                return files
    return files


def _logical_lines(source: str, start: int = 1, end: int | None = None) -> int:
    significant = {
        item.start[0]
        for item in tokenize.generate_tokens(io.StringIO(source).readline)
        if item.type not in {
            token.ENDMARKER, token.ENCODING, token.INDENT, token.DEDENT, token.NEWLINE,
            tokenize.NL, tokenize.COMMENT,
        }
        and item.start[0] >= start
        and (end is None or item.start[0] <= end)
    }
    return len(significant)


def _words(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for item in ast.walk(node):
        raw: str | None = None
        if isinstance(item, (ast.Name, ast.Attribute, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            raw = item.id if isinstance(item, ast.Name) else item.attr if isinstance(item, ast.Attribute) else item.name
        elif isinstance(item, ast.alias):
            raw = item.name
        if raw:
            values.update(part.lower() for part in raw.replace(".", "_").split("_") if part)
    return values


def _responsibilities(node: ast.AST) -> tuple[str, ...]:
    words = _words(node)
    return tuple(category for category, hints in _RESPONSIBILITY_WORDS.items() if words & hints)


def _payload_only(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return bool(body) and all(
        (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str))
        or (isinstance(item, ast.Return) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str))
        for item in body
    )


def _module_name(relative: str) -> tuple[str, bool]:
    path = PurePosixPath(relative)
    parts = list(path.with_suffix("").parts)
    package_module = bool(parts and parts[-1] == "__init__")
    if package_module:
        parts.pop()
    return ".".join(parts), package_module


def _measure(path: Path, root: Path, source: str, tree: ast.Module) -> AuditModule:
    relative = path.relative_to(root).as_posix()
    module_name, _package = _module_name(relative)
    functions = tuple(sorted((
        AuditFunction(
            item.name,
            _logical_lines(source, item.lineno, item.end_lineno),
            item.lineno,
            _payload_only(item),
        )
        for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ), key=lambda item: (item.start_line, item.name)))
    classes = tuple(sorted((
        AuditClass(
            item.name,
            _logical_lines(source, item.lineno, item.end_lineno),
            item.lineno,
            _responsibilities(item),
        )
        for item in ast.walk(tree)
        if isinstance(item, ast.ClassDef)
    ), key=lambda item: (item.start_line, item.name)))
    public = not path.stem.startswith("_") and "tests" not in path.relative_to(root).parts
    return AuditModule(
        path=relative,
        module_name=module_name,
        logical_lines=_logical_lines(source),
        functions=functions,
        classes=classes,
        responsibility_groups=_responsibilities(tree),
        public_module=public,
        documented_purpose=bool(ast.get_docstring(tree, clean=False)),
    )


def _dependency_name(name: str, known: set[str]) -> str | None:
    candidate = name
    while candidate:
        if candidate in known:
            return candidate
        candidate = candidate.rpartition(".")[0]
    return None


def _dependencies(parsed: _ParsedModule, known: set[str]) -> set[str]:
    current = parsed.measured.module_name
    package = current if parsed.package_module else current.rpartition(".")[0]
    result: set[str] = set()
    for node in ast.walk(parsed.tree):
        candidates: list[str] = []
        if isinstance(node, ast.Import):
            candidates.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".") if package else []
                remove = max(node.level - 1, 0)
                prefix = parts[: len(parts) - remove] if remove <= len(parts) else []
                base = ".".join([*prefix, *(node.module.split(".") if node.module else [])])
            else:
                base = node.module or ""
            candidates.append(base)
            candidates.extend(".".join(part for part in (base, alias.name) if part) for alias in node.names)
        for candidate in candidates:
            dependency = _dependency_name(candidate, known)
            if dependency and dependency != current:
                result.add(dependency)
    return result


def _canonical_cycle(cycle: tuple[str, ...]) -> tuple[str, ...]:
    body = list(cycle[:-1])
    smallest = min(range(len(body)), key=lambda index: body[index])
    rotated = body[smallest:] + body[:smallest]
    return tuple([*rotated, rotated[0]])


def _cycles(graph: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
    found: set[tuple[str, ...]] = set()
    visited: set[str] = set()
    active: set[str] = set()

    for start in sorted(graph):
        if start in visited:
            continue
        visited.add(start)
        active.add(start)
        path = [start]
        frames: list[tuple[str, Iterator[str]]] = [(start, iter(sorted(graph.get(start, ()))))]
        while frames:
            module, dependencies = frames[-1]
            try:
                dependency = next(dependencies)
            except StopIteration:
                frames.pop()
                path.pop()
                active.remove(module)
                continue
            if dependency not in visited:
                visited.add(dependency)
                active.add(dependency)
                path.append(dependency)
                frames.append((dependency, iter(sorted(graph.get(dependency, ())))))
            elif dependency in active:
                index = path.index(dependency)
                found.add(_canonical_cycle(tuple([*path[index:], dependency])))
    return tuple(sorted(found))


_SCORES = {
    "structure.dependency-cycle": 100,
    "structure.mixed-responsibilities": 80,
    "structure.function-size": 60,
    "structure.module-size": 50,
    "structure.repeated-large-append": 40,
    "structure.public-purpose-missing": 20,
}


def _hotspots(findings: Iterable[StructureFinding]) -> tuple[StructureHotspot, ...]:
    grouped: dict[str, list[StructureFinding]] = {}
    for finding in findings:
        grouped.setdefault(finding.path, []).append(finding)
    values = [
        StructureHotspot(path, sum(_SCORES.get(item.code, 10) for item in items), tuple(items))
        for path, items in grouped.items()
    ]
    return tuple(sorted(values, key=lambda item: (-item.score, item.path)))


def audit_project(
    project_root: Path | str,
    *,
    baseline_path: Path | None = None,
    policy: StructurePolicy = DEFAULT_STRUCTURE_POLICY,
) -> StructureAuditReport:
    """Measure Python source without importing, executing, or writing the target project."""

    requested = Path(project_root).expanduser()
    if requested.is_symlink():
        raise AuditError("Project root must be a real directory, not a symlink.")
    try:
        root = requested.resolve(strict=True)
    except (OSError, FileNotFoundError) as exc:
        raise AuditError("Project root must exist and be readable.") from exc
    if not root.is_dir() or root == Path(root.anchor):
        raise AuditError("Refusing to audit a non-directory or filesystem root.")
    baseline = _load_baseline(root, baseline_path)
    issues: list[AuditIssue] = []
    parsed: list[_ParsedModule] = []
    total_bytes = 0
    for path in _source_files(root, issues):
        try:
            size = path.stat().st_size
        except OSError:
            issues.append(AuditIssue(path.relative_to(root).as_posix(), "structure.read-error", "Source metadata could not be read.", "Check local permissions and retry."))
            continue
        if size > MAX_SOURCE_BYTES or total_bytes + size > MAX_TOTAL_BYTES:
            issues.append(AuditIssue(path.relative_to(root).as_posix(), "structure.size-limit", "A source file or total audit input exceeded the bounded read limit.", "Exclude generated content or audit a narrower project root."))
            continue
        total_bytes += size
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path.name)
            measured = _measure(path, root, source, tree)
        except (OSError, UnicodeError, SyntaxError, tokenize.TokenError) as exc:
            code = "structure.parse-error" if isinstance(exc, (SyntaxError, tokenize.TokenError)) else "structure.read-error"
            issues.append(AuditIssue(path.relative_to(root).as_posix(), code, "Python source could not be safely measured.", "Fix the syntax/encoding or exclude generated non-source content."))
            continue
        parsed.append(_ParsedModule(measured, tree, path.name == "__init__.py"))
    parsed.sort(key=lambda item: item.measured.path)
    known = {item.measured.module_name for item in parsed if item.measured.module_name}
    graph = {item.measured.module_name: _dependencies(item, known) for item in parsed if item.measured.module_name}
    cycles = _cycles(graph)
    introduced = (
        [cycle for cycle in cycles if frozenset(cycle[:-1]) not in baseline.cycles]
        if baseline.status == "loaded"
        else []
    )
    findings: list[StructureFinding] = []
    changes: list[AuditChange] = []
    for item in parsed:
        module = item.measured
        metric = baseline.modules.get(module.path)
        cycle = next((value for value in introduced if module.module_name in value[:-1]), ())
        observation = StructureObservation(
            path=module.path,
            module_logical_lines=module.logical_lines,
            functions=tuple(FunctionMeasurement(value.name, value.logical_lines, value.payload_only) for value in module.functions),
            responsibility_categories=module.responsibility_groups,
            class_responsibilities=tuple(
                ResponsibilityMeasurement(value.name, value.responsibility_groups) for value in module.classes
            ),
            introduced_dependency_cycle=cycle,
            append_only_changes=metric.append_only_changes if metric else 0,
            public_module=module.public_module,
            documented_purpose=module.documented_purpose,
            exemption=baseline.exemptions.get(module.path),
        )
        findings.extend(evaluate_structure(observation, policy).findings)
        if baseline.status == "loaded":
            old = metric or _BaselineMetric(0, 0, 0, 0)
            changes.append(AuditChange(
                module.path,
                old.logical_lines,
                module.logical_lines,
                module.logical_lines - old.logical_lines,
                len(module.functions) - old.function_count,
                len(module.classes) - old.class_count,
            ))
    if baseline.status == "loaded":
        current_paths = {item.measured.path for item in parsed}
        for path, metric in baseline.modules.items():
            if path not in current_paths:
                changes.append(AuditChange(path, metric.logical_lines, 0, -metric.logical_lines, -metric.function_count, -metric.class_count))
    acknowledged = tuple(
        AcknowledgedExemption(path, exemption.category, exemption.reason)
        for path, exemption in sorted(baseline.exemptions.items())
    )
    return StructureAuditReport(
        modules=tuple(item.measured for item in parsed),
        hotspots=_hotspots(findings),
        dependency_cycles=cycles,
        changes=tuple(sorted(changes, key=lambda item: item.path)),
        acknowledged_exemptions=acknowledged,
        issues=tuple(sorted(issues, key=lambda item: (item.path, item.code))),
        baseline_status=baseline.status,
    )


def render_audit_text(report: StructureAuditReport) -> str:
    lines = [
        "Structure audit — advisory only",
        "Findings are review signals and never change the command exit status.",
        f"Baseline: {'loaded' if report.baseline_status == 'loaded' else 'not recorded'}",
        f"Python modules measured: {len(report.modules)}",
        f"Hotspots: {len(report.hotspots)}",
    ]
    if report.dependency_cycles:
        lines.append("Dependency cycles:")
        lines.extend(f"  - {' -> '.join(cycle)}" for cycle in report.dependency_cycles)
    if report.hotspots:
        lines.append("Hotspots (highest review score first):")
        for hotspot in report.hotspots:
            lines.append(f"  [warning] {hotspot.path} (score {hotspot.score})")
            for finding in hotspot.findings:
                measurement = ""
                if finding.measured is not None:
                    measurement = f" [{finding.measured} > {finding.threshold}]" if finding.threshold is not None else f" [{finding.measured}]"
                lines.append(f"    - {finding.code}: {finding.explanation}{measurement}")
                lines.append(f"      Remedy: {finding.remedy}")
    if report.changes:
        lines.append("Changes since baseline:")
        lines.extend(
            f"  - {item.path}: logical lines {item.logical_lines_delta:+d}, functions {item.function_count_delta:+d}, classes {item.class_count_delta:+d}"
            for item in report.changes
        )
    if report.acknowledged_exemptions:
        lines.append("Acknowledged exemptions:")
        lines.extend(
            f"  - {item.path} [{item.category}]: {item.reason}" for item in report.acknowledged_exemptions
        )
    if report.issues:
        lines.append("Audit warnings:")
        lines.extend(f"  - {item.path}: {item.code}: {item.explanation} Remedy: {item.remedy}" for item in report.issues)
    return "\n".join(lines) + "\n"
