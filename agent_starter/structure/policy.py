"""Typed, advisory-only source-structure policy.

This module evaluates measurements supplied by a later auditor. It performs no
filesystem traversal and has no exit-status or build-gate authority.
"""

from __future__ import annotations

from dataclasses import dataclass


ALLOWED_EXEMPTION_CATEGORIES = frozenset(
    {"generated-data", "static-data", "license", "protocol-table", "cohesive-template"}
)


def _bounded_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty.")
    if len(normalized) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters.")
    if any(ord(character) < 32 and character not in "\t" for character in normalized):
        raise ValueError(f"{field} must not contain control characters.")
    return normalized


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer.")
    return value


def _responsibility_categories(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("responsibility categories must be a tuple.")
    categories = tuple(_bounded_text(item, field="responsibility category", maximum=80) for item in value)
    if len(categories) > 16:
        raise ValueError("responsibility categories must contain at most 16 values.")
    if len(set(categories)) != len(categories):
        raise ValueError("responsibility categories must not contain duplicates.")
    return categories


@dataclass(frozen=True, slots=True)
class StructurePolicy:
    module_logical_lines: int = 500
    function_logical_lines: int = 80
    repeated_append_count: int = 3

    def __post_init__(self) -> None:
        for name in ("module_logical_lines", "function_logical_lines", "repeated_append_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")


DEFAULT_STRUCTURE_POLICY = StructurePolicy()


@dataclass(frozen=True, slots=True)
class FunctionMeasurement:
    qualified_name: str
    logical_lines: int
    payload_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "qualified_name", _bounded_text(self.qualified_name, field="qualified_name", maximum=256))
        _nonnegative_int(self.logical_lines, field="logical_lines")
        if not isinstance(self.payload_only, bool):
            raise ValueError("payload_only must be a boolean.")


@dataclass(frozen=True, slots=True)
class ResponsibilityMeasurement:
    subject: str
    categories: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _bounded_text(self.subject, field="responsibility subject", maximum=256))
        object.__setattr__(self, "categories", _responsibility_categories(self.categories))


@dataclass(frozen=True, slots=True)
class StructureExemption:
    category: str
    reason: str
    hides_executable_complexity: bool = False

    def __post_init__(self) -> None:
        category = _bounded_text(self.category, field="exemption.category", maximum=64)
        if category not in ALLOWED_EXEMPTION_CATEGORIES:
            choices = ", ".join(sorted(ALLOWED_EXEMPTION_CATEGORIES))
            raise ValueError(f"exemption.category must be one of: {choices}.")
        reason = _bounded_text(self.reason, field="exemption.reason", maximum=300)
        if len(reason) < 8:
            raise ValueError("exemption.reason must briefly explain why the threshold is safe to exceed.")
        if not isinstance(self.hides_executable_complexity, bool):
            raise ValueError("exemption.hides_executable_complexity must be a boolean.")
        if self.hides_executable_complexity:
            raise ValueError("A structure exemption cannot hide executable complexity.")
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True, slots=True)
class StructureObservation:
    path: str
    module_logical_lines: int
    functions: tuple[FunctionMeasurement, ...] = ()
    responsibility_categories: tuple[str, ...] = ()
    class_responsibilities: tuple[ResponsibilityMeasurement, ...] = ()
    introduced_dependency_cycle: tuple[str, ...] = ()
    append_only_changes: int = 0
    public_module: bool = False
    documented_purpose: bool = True
    exemption: StructureExemption | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _bounded_text(self.path, field="path", maximum=4096))
        _nonnegative_int(self.module_logical_lines, field="module_logical_lines")
        _nonnegative_int(self.append_only_changes, field="append_only_changes")
        if not isinstance(self.functions, tuple) or not all(isinstance(item, FunctionMeasurement) for item in self.functions):
            raise ValueError("functions must be a tuple of FunctionMeasurement values.")
        if len(self.functions) > 10000:
            raise ValueError("functions must contain at most 10000 measurements.")
        object.__setattr__(self, "responsibility_categories", _responsibility_categories(self.responsibility_categories))
        if not isinstance(self.class_responsibilities, tuple) or not all(
            isinstance(item, ResponsibilityMeasurement) for item in self.class_responsibilities
        ):
            raise ValueError("class_responsibilities must be a tuple of ResponsibilityMeasurement values.")
        if len(self.class_responsibilities) > 10000:
            raise ValueError("class_responsibilities must contain at most 10000 measurements.")
        if not isinstance(self.introduced_dependency_cycle, tuple):
            raise ValueError("introduced_dependency_cycle must be a tuple.")
        cycle = tuple(
            _bounded_text(item, field="dependency cycle member", maximum=256)
            for item in self.introduced_dependency_cycle
        )
        if cycle and (len(cycle) < 3 or len(cycle) > 64 or cycle[0] != cycle[-1]):
            raise ValueError("introduced_dependency_cycle must be a closed cycle of 3 to 64 module names.")
        object.__setattr__(self, "introduced_dependency_cycle", cycle)
        for name in ("public_module", "documented_purpose"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean.")
        if self.exemption is not None and not isinstance(self.exemption, StructureExemption):
            raise ValueError("exemption must be a StructureExemption value.")


@dataclass(frozen=True, slots=True)
class StructureFinding:
    path: str
    code: str
    explanation: str
    remedy: str
    severity: str = "warning"
    blocking: bool = False
    subject: str = "module"
    measured: int | None = None
    threshold: int | None = None


@dataclass(frozen=True, slots=True)
class StructureAssessment:
    path: str
    findings: tuple[StructureFinding, ...]
    acknowledged_exemption: StructureExemption | None = None

    @property
    def blocking(self) -> bool:
        return False


def _finding(
    observation: StructureObservation,
    code: str,
    explanation: str,
    remedy: str,
    *,
    subject: str = "module",
    measured: int | None = None,
    threshold: int | None = None,
) -> StructureFinding:
    return StructureFinding(
        path=observation.path,
        code=code,
        explanation=explanation,
        remedy=remedy,
        subject=subject,
        measured=measured,
        threshold=threshold,
    )


def evaluate_structure(
    observation: StructureObservation,
    policy: StructurePolicy = DEFAULT_STRUCTURE_POLICY,
) -> StructureAssessment:
    """Evaluate supplied measurements as advisory review signals only."""

    if not isinstance(observation, StructureObservation):
        raise ValueError("observation must be a StructureObservation value.")
    if not isinstance(policy, StructurePolicy):
        raise ValueError("policy must be a StructurePolicy value.")
    findings: list[StructureFinding] = []
    size_exempt = observation.exemption is not None
    if observation.module_logical_lines > policy.module_logical_lines and not size_exempt:
        findings.append(_finding(
            observation,
            "structure.module-size",
            "The source module exceeds the advisory logical-line threshold.",
            "Review whether it still has one primary reason to change; record a cohesive exemption or split at a tested seam.",
            measured=observation.module_logical_lines,
            threshold=policy.module_logical_lines,
        ))
    for function in observation.functions:
        function_exempt = size_exempt and function.payload_only
        if function.logical_lines > policy.function_logical_lines and not function_exempt:
            findings.append(_finding(
                observation,
                "structure.function-size",
                f"Function {function.qualified_name!r} exceeds the advisory logical-line threshold.",
                "Review the function's branches and responsibilities; extract only a cohesive, testable seam.",
                subject=function.qualified_name,
                measured=function.logical_lines,
                threshold=policy.function_logical_lines,
            ))
    if len(observation.responsibility_categories) > 1:
        findings.append(_finding(
            observation,
            "structure.mixed-responsibilities",
            "The module is reported to own multiple unrelated responsibility categories.",
            "Confirm the categories from code and tests, then separate by primary reason to change without wrapper sprawl.",
            measured=len(observation.responsibility_categories),
            threshold=1,
        ))
    for responsibility in observation.class_responsibilities:
        if len(responsibility.categories) > 1:
            findings.append(_finding(
                observation,
                "structure.mixed-responsibilities",
                "The class is reported to own multiple unrelated responsibility categories.",
                "Confirm the categories from code and tests, then separate by primary reason to change without wrapper sprawl.",
                subject=responsibility.subject,
                measured=len(responsibility.categories),
                threshold=1,
            ))
    if observation.introduced_dependency_cycle:
        findings.append(_finding(
            observation,
            "structure.dependency-cycle",
            "A new dependency direction is reported to create a module cycle.",
            "Reverse or extract the dependency boundary; an exemption cannot suppress a new executable dependency cycle.",
        ))
    if (
        observation.module_logical_lines > policy.module_logical_lines
        and observation.append_only_changes >= policy.repeated_append_count
    ):
        findings.append(_finding(
            observation,
            "structure.repeated-large-append",
            "Repeated append-only changes are reported against an already-large source module.",
            "Review the recent additions together and choose a cohesive extraction seam before appending another workflow.",
            measured=observation.append_only_changes,
            threshold=policy.repeated_append_count,
        ))
    if observation.public_module and not observation.documented_purpose:
        findings.append(_finding(
            observation,
            "structure.public-purpose-missing",
            "A public module has no documented purpose.",
            "Add a concise module/API purpose or make the module private if it is not a supported boundary.",
        ))
    return StructureAssessment(
        path=observation.path,
        findings=tuple(findings),
        acknowledged_exemption=observation.exemption,
    )
