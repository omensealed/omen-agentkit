"""Stable, plain-language diagnostics for presentation adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
import subprocess

from .agents import AgentError
from .config_schema import ConfigValidationError
from .draft_sessions import DraftSessionError
from .task_composer import TaskValidationError


DETAIL_LIMIT = 1000
DIAGNOSTIC_LOG_LIMIT = 256_000
DIAGNOSTIC_RECORD_LIMIT = 8_000
_OPERATION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SECRET_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)|"
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|token)\s*[:=]\s*\S+)|"
    r"(?i:\bauthorization\s*:\s*(?:bearer|basic)\s+\S+)|"
    r"(?i:\b(?:cookie|session[_-]?id)\s*[:=]\s*\S+)|"
    r"\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}\b|"
    r"\bAKIA[0-9A-Z]{16}\b",
    re.DOTALL,
)
_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])/(?:[^\s;]+)")
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s;]+")


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PathConfinementError(ValueError):
    """Raised when a GUI file request leaves its selected project root."""


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    code: str
    severity: DiagnosticSeverity
    title: str
    explanation: str
    project_changed: bool
    safe_next_action: str
    technical_details: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "explanation": self.explanation,
            "project_changed": self.project_changed,
            "safe_next_action": self.safe_next_action,
            "technical_details": self.technical_details,
        }


def default_diagnostic_log_root() -> Path | None:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        state_home = Path(base).expanduser()
        if not state_home.is_absolute():
            return None
    else:
        state_home = Path.home() / ".local" / "state"
    return state_home / "omen-agentkit" / "diagnostics"


def _safe_text(value: object, *, fallback: str) -> str:
    text = str(value).replace("\x00", " ")
    text = "".join(character if ord(character) >= 32 or character in "\n\t" else " " for character in text)
    text = _SECRET_RE.sub("[redacted sensitive value]", text).strip()
    return (text or fallback)[:DETAIL_LIMIT]


def safe_display_text(value: object, *, limit: int = 500) -> str:
    """Return bounded control-safe, secret-redacted text for a local UI field."""

    bounded_limit = min(max(int(limit), 1), DETAIL_LIMIT)
    return _safe_text(value, fallback="")[:bounded_limit]


def _log_text(value: object) -> str:
    text = _safe_text(value, fallback="")
    text = _ABSOLUTE_PATH_RE.sub("[redacted path]", text)
    return _WINDOWS_PATH_RE.sub("[redacted path]", text)


class DiagnosticLog:
    """Best-effort private JSONL diagnostics; logging never changes operation results."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "gui-diagnostics.jsonl"

    def write(self, diagnostic: DiagnosticResult) -> bool:
        safe_code = diagnostic.code if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", diagnostic.code) else "invalid_code"
        document = {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "diagnostic": {
                "code": safe_code,
                "severity": diagnostic.severity.value,
                "title": _log_text(diagnostic.title),
                "explanation": _log_text(diagnostic.explanation),
                "project_changed": bool(diagnostic.project_changed),
                "safe_next_action": _log_text(diagnostic.safe_next_action),
                "technical_details": _log_text(diagnostic.technical_details),
            },
        }
        encoded = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > DIAGNOSTIC_RECORD_LIMIT:
            return False
        try:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.root.is_symlink() or not self.root.is_dir():
                return False
            os.chmod(self.root, 0o700)
            if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
                return False
            if self.path.exists() and self.path.stat().st_size + len(encoded) > DIAGNOSTIC_LOG_LIMIT:
                from .generation import atomic_replace

                atomic_replace(self.path, encoded, mode=0o600)
            else:
                flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(self.path, flags, 0o600)
                with os.fdopen(descriptor, "ab") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
            os.chmod(self.path, 0o600)
        except (OSError, ValueError):
            return False
        return True


def get_diagnostic_log() -> DiagnosticLog | None:
    root = default_diagnostic_log_root()
    return None if root is None else DiagnosticLog(root)


def _operation(value: str) -> str:
    return value if isinstance(value, str) and _OPERATION_RE.fullmatch(value) else "backend_operation"


def _result(
    *,
    code: str,
    title: str,
    explanation: str,
    project_changed: bool,
    safe_next_action: str,
    operation: str,
    detail: str,
) -> DiagnosticResult:
    return DiagnosticResult(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        title=title,
        explanation=_safe_text(explanation, fallback="The operation could not be completed."),
        project_changed=bool(project_changed),
        safe_next_action=_safe_text(safe_next_action, fallback="Review the operation and try again."),
        technical_details=_safe_text(
            f"operation={_operation(operation)}; {detail}",
            fallback=f"operation={_operation(operation)}",
        ),
    )


def diagnostic_from_status(
    *,
    code: str,
    title: str,
    explanation: str,
    project_changed: bool,
    safe_next_action: str,
    operation: str,
    technical_details: str = "status=failed",
) -> DiagnosticResult:
    """Build a sanitized diagnostic for a failed result that is not an exception."""

    safe_code = code if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code) else "backend_status_failed"
    return _result(
        code=safe_code,
        title=title,
        explanation=explanation,
        project_changed=project_changed,
        safe_next_action=safe_next_action,
        operation=operation,
        detail=technical_details,
    )


def diagnostic_from_exception(
    error: BaseException,
    *,
    operation: str,
    project_changed: bool = False,
) -> DiagnosticResult:
    """Map a backend exception without tracebacks, secret values, or invented write state."""

    if isinstance(error, ConfigValidationError) and error.issues:
        issue = error.issues[0]
        return _result(
            code="configuration_invalid",
            title="Review the project settings",
            explanation=f"{issue.path}: {issue.message}",
            project_changed=project_changed,
            safe_next_action=issue.remedy,
            operation=operation,
            detail=f"field={issue.path}; issue={issue.code}",
        )
    if isinstance(error, PathConfinementError):
        return _result(
            code="path_outside_project",
            title="The requested file is outside the project",
            explanation="The requested relative path does not stay inside the selected project root.",
            project_changed=project_changed,
            safe_next_action="Choose a file inside the selected project and try again.",
            operation=operation,
            detail="exception=PathConfinementError",
        )
    if isinstance(error, TaskValidationError):
        return _result(
            code="task_invalid",
            title="Review the task answers",
            explanation=str(error),
            project_changed=project_changed,
            safe_next_action="Edit the identified answer and compose the task again.",
            operation=operation,
            detail="exception=TaskValidationError",
        )
    if isinstance(error, DraftSessionError):
        return _result(
            code="draft_invalid",
            title="The draft could not be used",
            explanation=str(error),
            project_changed=project_changed,
            safe_next_action="Review the draft selection or content and try the explicit draft action again.",
            operation=operation,
            detail="exception=DraftSessionError",
        )
    if isinstance(error, ValueError):
        is_config = operation in {"preview_config", "generate_config"}
        return _result(
            code="configuration_invalid" if is_config else "input_invalid",
            title="Review the project settings" if is_config else "Review the provided information",
            explanation=str(error),
            project_changed=project_changed,
            safe_next_action="Correct the identified value and try again.",
            operation=operation,
            detail=f"exception={type(error).__name__}",
        )
    if isinstance(error, FileNotFoundError):
        return _result(
            code="file_not_found",
            title="The requested file was not found",
            explanation="The selected file or project location does not exist.",
            project_changed=project_changed,
            safe_next_action="Choose an existing location and try again.",
            operation=operation,
            detail="exception=FileNotFoundError",
        )
    if isinstance(error, PermissionError):
        return _result(
            code="permission_denied",
            title="The location is not accessible",
            explanation="The current user does not have the required filesystem permission.",
            project_changed=project_changed,
            safe_next_action="Choose a user-writable location or review its permissions; do not use sudo.",
            operation=operation,
            detail="exception=PermissionError",
        )
    if isinstance(error, subprocess.TimeoutExpired):
        return _result(
            code="operation_timed_out",
            title="The operation took too long",
            explanation="A bounded backend operation did not finish before its timeout.",
            project_changed=project_changed,
            safe_next_action="Review the local tool status, then retry the operation.",
            operation=operation,
            detail="exception=TimeoutExpired",
        )
    if isinstance(error, subprocess.CalledProcessError):
        return _result(
            code="external_command_failed",
            title="A local tool reported a failure",
            explanation="A bounded local subprocess returned an unsuccessful status.",
            project_changed=project_changed,
            safe_next_action="Review the local tool status and retry only after understanding the failure.",
            operation=operation,
            detail="exception=CalledProcessError",
        )
    if isinstance(error, AgentError):
        return _result(
            code="codex_operation_failed",
            title="Codex could not complete the operation",
            explanation="The supported Codex CLI boundary reported a failure.",
            project_changed=project_changed,
            safe_next_action="Review Codex status and the approved model policy, then retry explicitly.",
            operation=operation,
            detail="exception=AgentError",
        )
    if isinstance(error, ImportError):
        return _result(
            code="optional_component_missing",
            title="An optional component is unavailable",
            explanation="The requested optional desktop component is not installed or could not be loaded.",
            project_changed=project_changed,
            safe_next_action="Use the CLI or install the documented optional GUI extra in a reviewed environment.",
            operation=operation,
            detail="exception=ImportError",
        )
    if isinstance(error, OSError):
        return _result(
            code="system_io_error",
            title="The local operation failed",
            explanation="The operating system could not complete the requested local operation.",
            project_changed=project_changed,
            safe_next_action="Review the selected location and local tool availability, then retry.",
            operation=operation,
            detail=f"exception={type(error).__name__}",
        )
    return _result(
        code="unexpected_backend_error",
        title="The operation could not be completed",
        explanation="An unexpected local backend error occurred.",
        project_changed=project_changed,
        safe_next_action="Stop and review the technical details before trying again.",
        operation=operation,
        detail=f"exception={type(error).__name__}",
    )
