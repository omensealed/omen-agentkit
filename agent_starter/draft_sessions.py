"""Private, atomic, non-authoritative project/task draft sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
from typing import Mapping

from .generation import atomic_create, atomic_replace
from .task_composer import TASK_DEFINITIONS, parse_task_kind


DRAFT_SCHEMA_VERSION = 1
DRAFT_FILE_LIMIT = 256_000
DRAFT_TEXT_LIMIT = 4000
DRAFT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SECRET_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|token)\s*[:=]\s*\S+)|"
    r"(?i:\bauthorization\s*:\s*(?:bearer|basic)\s+\S+)|"
    r"(?i:\b(?:cookie|session[_-]?id)\s*[:=]\s*\S+)|"
    r"\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}\b|"
    r"\bAKIA[0-9A-Z]{16}\b"
)

PROJECT_DRAFT_BOOLEAN_FIELDS = {
    "browser_tests",
    "codex_agentkit_skill",
    "first_run_autonomous_prompt",
    "git_enabled",
    "github_actions",
    "gui_passthrough",
    "handles_payments",
    "handles_personal_data",
    "minimal_dependencies",
    "network_access",
    "sandbox_enabled",
    "setup_agent_now",
    "user_accounts",
}
PROJECT_DRAFT_TEXT_FIELDS = {
    "database",
    "description",
    "entry_mode",
    "github_remote",
    "goals",
    "languages",
    "non_goals",
    "packaging_targets",
    "project_mode",
    "project_name",
    "project_path",
    "project_stage",
    "project_type",
    "quality_checks",
    "sandbox_image_profile",
    "sandbox_mode",
    "security_notes",
    "stack_notes",
    "target_platforms",
    "target_users",
    "tests",
}
PROJECT_DRAFT_FIELDS = PROJECT_DRAFT_BOOLEAN_FIELDS | PROJECT_DRAFT_TEXT_FIELDS


class DraftSessionError(ValueError):
    """Raised when draft content or its private filesystem boundary is unsafe."""


@dataclass(frozen=True, slots=True)
class DraftSummary:
    draft_id: str
    updated_at: str
    selected_project: str

    def to_dict(self) -> dict[str, str]:
        return {
            "draft_id": self.draft_id,
            "updated_at": self.updated_at,
            "selected_project": self.selected_project,
        }


@dataclass(frozen=True, slots=True)
class DraftSession:
    draft_id: str
    updated_at: str
    selected_project: str
    project: dict[str, object]
    task: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "draft_id": self.draft_id,
            "updated_at": self.updated_at,
            "selected_project": self.selected_project,
            "project": dict(self.project),
            "task": None if self.task is None else {
                "kind": self.task["kind"],
                "answers": dict(self.task["answers"]),
            },
        }


def default_draft_root() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        data_home = Path(base).expanduser()
        if not data_home.is_absolute():
            raise DraftSessionError("XDG_DATA_HOME must be an absolute user-local path.")
    else:
        data_home = Path.home() / ".local" / "share"
    return data_home / "omen-agentkit" / "drafts"


def get_draft_store() -> "DraftStore":
    return DraftStore()


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise DraftSessionError(f"Draft field {field} must be text.")
    if "\x00" in value or any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise DraftSessionError(f"Draft field {field} contains unsupported control content.")
    if len(value) > DRAFT_TEXT_LIMIT:
        raise DraftSessionError(f"Draft field {field} exceeds {DRAFT_TEXT_LIMIT} characters.")
    if _SECRET_RE.search(value):
        raise DraftSessionError(
            f"Draft field {field} appears to contain a credential or private key; remove it and rotate it if real."
        )
    return value


def _project_payload(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise DraftSessionError("Draft project data must be an object.")
    unexpected = sorted(set(value) - PROJECT_DRAFT_FIELDS)
    if unexpected:
        raise DraftSessionError(f"Draft project data contains unexpected fields: {', '.join(unexpected)}.")
    result: dict[str, object] = {}
    for key, item in value.items():
        if key in PROJECT_DRAFT_BOOLEAN_FIELDS:
            if not isinstance(item, bool):
                raise DraftSessionError(f"Draft field {key} must be true or false.")
            result[key] = item
        else:
            text = _text(item, field=key)
            result[key] = text
            if key == "project_path" and ("\n" in text or "\t" in text):
                raise DraftSessionError("Draft project_path must stay on one line.")
    entry_mode = result.get("entry_mode")
    if entry_mode is not None and entry_mode not in {"guided", "advanced"}:
        raise DraftSessionError("Draft entry_mode must be guided or advanced.")
    return result


def _task_payload(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"kind", "answers"}:
        raise DraftSessionError("Draft task data must contain only kind and answers.")
    try:
        kind = parse_task_kind(value["kind"])
    except ValueError as exc:
        raise DraftSessionError("Draft task kind must be one of the listed composer choices.") from exc
    answers = value["answers"]
    if not isinstance(answers, Mapping):
        raise DraftSessionError("Draft task answers must be an object.")
    definition = TASK_DEFINITIONS[kind]
    allowed = {question.key for question in definition.questions}
    unexpected = sorted(set(answers) - allowed)
    if unexpected:
        raise DraftSessionError(f"Draft task answers contain unexpected fields: {', '.join(unexpected)}.")
    normalized: dict[str, str] = {}
    for question in definition.questions:
        if question.key not in answers:
            continue
        answer = _text(answers[question.key], field=f"task.answers.{question.key}")
        valid_choices = {choice for choice, _label in question.choices}
        if answer and valid_choices and answer not in valid_choices:
            raise DraftSessionError(
                f"Draft task answer {question.key} must be one of: {', '.join(sorted(valid_choices))}."
            )
        normalized[question.key] = answer
    return {"kind": kind.value, "answers": normalized}


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 80:
        raise DraftSessionError("Draft updated time is malformed.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DraftSessionError("Draft updated time is malformed.") from exc
    if parsed.tzinfo is None:
        raise DraftSessionError("Draft updated time must include a timezone.")
    return value


def _selected_project(project: Mapping[str, object]) -> str:
    value = project.get("project_path", "")
    return str(value).strip() or "Not selected"


def _encoded(session: DraftSession) -> bytes:
    encoded = (json.dumps(session.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > DRAFT_FILE_LIMIT:
        raise DraftSessionError("Draft session exceeds the safe size limit.")
    return encoded


class DraftStore:
    """Persist incomplete presentation data without granting configuration authority."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_draft_root()

    def _path(self, draft_id: str) -> Path:
        if not isinstance(draft_id, str) or not DRAFT_ID_RE.fullmatch(draft_id):
            raise DraftSessionError("Draft identifier is malformed.")
        return self.root / f"{draft_id}.json"

    def _check_root(self, *, create: bool) -> bool:
        if not self.root.exists() and not self.root.is_symlink():
            if not create:
                return False
            try:
                self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError as exc:
                raise DraftSessionError("Draft data directory could not be created.") from exc
        if self.root.is_symlink() or not self.root.is_dir():
            raise DraftSessionError("Draft data directory must be a regular non-symlink directory.")
        try:
            os.chmod(self.root, 0o700)
        except OSError as exc:
            raise DraftSessionError("Draft data directory permissions could not be secured.") from exc
        return True

    def save(
        self,
        *,
        project: Mapping[str, object],
        task: Mapping[str, object] | None,
        draft_id: str | None = None,
    ) -> DraftSession:
        normalized_project = _project_payload(project)
        normalized_task = _task_payload(task)
        is_new = draft_id is None
        if is_new:
            draft_id = secrets.token_hex(16)
        path = self._path(draft_id)
        updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        session = DraftSession(
            draft_id=draft_id,
            updated_at=updated_at,
            selected_project=_selected_project(normalized_project),
            project=normalized_project,
            task=normalized_task,
        )
        encoded = _encoded(session)
        self._check_root(create=True)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise DraftSessionError("Draft entry must be a regular non-symlink file.")
        try:
            if is_new:
                atomic_create(path, encoded, mode=0o600)
            else:
                atomic_replace(path, encoded, mode=0o600)
            os.chmod(path, 0o600)
        except FileExistsError as exc:
            raise DraftSessionError("A draft identifier collision occurred; save again.") from exc
        except OSError as exc:
            raise DraftSessionError("Draft session could not be written atomically.") from exc
        return session

    def load(self, draft_id: str) -> DraftSession | None:
        path = self._path(draft_id)
        if not self._check_root(create=False):
            return None
        if not path.exists() and not path.is_symlink():
            return None
        if path.is_symlink() or not path.is_file():
            raise DraftSessionError("Draft entry must be a regular non-symlink file.")
        try:
            if path.stat().st_size > DRAFT_FILE_LIMIT:
                raise DraftSessionError("Draft session exceeds the safe size limit.")
            data = json.loads(path.read_text(encoding="utf-8"))
        except DraftSessionError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DraftSessionError("Draft session could not be read as valid JSON.") from exc
        expected = {"schema_version", "draft_id", "updated_at", "selected_project", "project", "task"}
        if not isinstance(data, dict) or set(data) != expected:
            raise DraftSessionError("Draft session has an unknown structure.")
        if data["schema_version"] != DRAFT_SCHEMA_VERSION or data["draft_id"] != draft_id:
            raise DraftSessionError("Draft session version or identifier does not match.")
        project = _project_payload(data["project"])
        task = _task_payload(data["task"])
        selected_project = _selected_project(project)
        if data["selected_project"] != selected_project:
            raise DraftSessionError("Draft selected project does not match its project data.")
        return DraftSession(
            draft_id=draft_id,
            updated_at=_timestamp(data["updated_at"]),
            selected_project=selected_project,
            project=project,
            task=task,
        )

    def list_summaries(self) -> list[DraftSummary]:
        if not self._check_root(create=False):
            return []
        summaries: list[DraftSummary] = []
        try:
            paths = sorted(self.root.glob("*.json"))
        except OSError as exc:
            raise DraftSessionError("Draft data directory could not be listed.") from exc
        for path in paths:
            if not DRAFT_ID_RE.fullmatch(path.stem):
                raise DraftSessionError("Draft data directory contains an unknown entry.")
            session = self.load(path.stem)
            if session is not None:
                summaries.append(DraftSummary(session.draft_id, session.updated_at, session.selected_project))
        return sorted(summaries, key=lambda item: (item.updated_at, item.draft_id), reverse=True)

    def discard(self, draft_id: str) -> bool:
        path = self._path(draft_id)
        if not self._check_root(create=False):
            return False
        if not path.exists() and not path.is_symlink():
            return False
        if path.is_symlink() or not path.is_file():
            raise DraftSessionError("Draft entry must be a regular non-symlink file.")
        try:
            path.unlink()
        except OSError as exc:
            raise DraftSessionError("Draft session could not be discarded.") from exc
        return True

    def export(self, draft_id: str, destination: Path) -> Path:
        session = self.load(draft_id)
        if session is None:
            raise DraftSessionError("Draft session was not found.")
        path = Path(destination).expanduser()
        if path.exists() or path.is_symlink():
            raise DraftSessionError("Draft export destination already exists; choose a new file.")
        for parent in path.parents:
            if parent.is_symlink():
                raise DraftSessionError("Refusing to export through a symlinked directory.")
            if parent == parent.parent:
                break
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_create(path, _encoded(session), mode=0o600)
            os.chmod(path, 0o600)
        except FileExistsError as exc:
            raise DraftSessionError("Draft export destination already exists; choose a new file.") from exc
        except OSError as exc:
            raise DraftSessionError("Draft session could not be exported atomically.") from exc
        return path
