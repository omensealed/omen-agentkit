"""Deterministic local deployment artifact assembly without command execution."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
import re
import stat
import zipfile
from typing import Any

from . import __version__
from .deployment import DeploymentOperation, deployment_contract
from .deployment_plan import (
    DeploymentPlan,
    DeploymentPlanError,
    DeploymentPlanIssue,
    _confined_path,
    confined_output_path,
    inspect_source_state,
    load_plan_project_config,
)
from .generation import atomic_create
from .generator import validate_project


BUILD_FILE_LIMIT = 10_000
BUILD_BYTE_LIMIT = 32 * 1024 * 1024
ARTIFACT_LIMIT = 40 * 1024 * 1024
_FORBIDDEN_PARTS = {".git", ".agent-starter", ".codex", ".ssh", "credentials", "secrets"}
_FORBIDDEN_NAMES = {".env", ".env.local", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials.json"}
_FORBIDDEN_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".kdbx"}


@dataclass(frozen=True, slots=True)
class SourceEntry:
    name: str
    data: bytes
    mode: int
    digest: str


@dataclass(frozen=True, slots=True)
class ArtifactVerification:
    ok: bool
    issues: tuple[str, ...]
    artifact_digest: str
    content_root_digest: str | None


@dataclass(frozen=True, slots=True)
class ArtifactBuildReport:
    plan_digest: str
    artifact_path: str
    artifact_digest: str
    content_root_digest: str
    artifact_bytes: int
    payload_files: int
    source_revision: str
    reproducible: bool
    reproduction_runs: int
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation": "deployment-build",
            "plan_digest": self.plan_digest,
            "artifact_path": self.artifact_path,
            "artifact_digest_algorithm": "sha256",
            "artifact_digest": self.artifact_digest,
            "content_root_digest": self.content_root_digest,
            "artifact_bytes": self.artifact_bytes,
            "payload_files": self.payload_files,
            "source_revision": self.source_revision,
            "reproducible": self.reproducible,
            "reproduction_runs": self.reproduction_runs,
            "sbom": {"format": "SPDX-2.3 JSON", "location": ".agentkit/sbom.spdx.json"},
            "provenance": self.provenance,
            "authority": {
                "operation": "build",
                "apply_authorized": False,
                "artifact_built": True,
                "credentials_accessed": False,
                "network_accessed": False,
                "profile_commands_executed": False,
                "project_commands_executed": False,
                "push_performed": False,
                "remote_changes_performed": False,
                "target_contacted": False,
            },
        }


def _error(path: str, code: str, explanation: str, remedy: str) -> DeploymentPlanError:
    return DeploymentPlanError([DeploymentPlanIssue(path, code, explanation, remedy)])


def _safe_source_name(relative: Path) -> bool:
    lowered_parts = {part.lower() for part in relative.parts}
    name = relative.name.lower()
    return not (
        lowered_parts & _FORBIDDEN_PARTS
        or name in _FORBIDDEN_NAMES
        or any(name.endswith(suffix) for suffix in _FORBIDDEN_SUFFIXES)
    )


def _collect_source(root: Path, relative: Path) -> tuple[SourceEntry, ...]:
    if relative in {Path("."), Path("")}:
        raise _error("source", "project_root_source_forbidden", "The whole project root cannot be packaged as deployment input.", "Choose a dedicated reviewed build-output file or directory.")
    source = _confined_path(root, relative, must_exist=True)
    if not source.exists() or source.is_symlink() or not (source.is_file() or source.is_dir()):
        raise _error("source", "unsafe_build_source", "Build source must be a regular project-local file or directory.", "Use a non-symlinked reviewed build-output path.")
    candidates = [source] if source.is_file() else sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix())
    entries: list[SourceEntry] = []
    total = 0
    for candidate in candidates:
        relative_name = Path(candidate.name) if source.is_file() else candidate.relative_to(source)
        if candidate.is_symlink() or not (candidate.is_file() or candidate.is_dir()):
            raise _error("source", "unsafe_build_source_entry", "Build source contains a symlink or special file.", "Replace it with regular reviewed files or exclude it before building.")
        if not _safe_source_name(relative_name):
            raise _error("source", "sensitive_path_forbidden", "Build source contains a credential-prone path that will not be read.", "Move secrets outside the build source and use reference-only configuration.")
        if candidate.is_dir():
            continue
        if len(entries) >= BUILD_FILE_LIMIT:
            raise _error("source", "build_file_limit", "Build source exceeds 10000 files.", "Split or reduce the reviewed artifact input.")
        try:
            size = candidate.stat().st_size
            if total + size > BUILD_BYTE_LIMIT:
                raise _error("source", "build_byte_limit", "Build source exceeds 32 MiB.", "Use an external reviewed builder for larger artifacts.")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(candidate, flags)
            with os.fdopen(descriptor, "rb") as stream:
                data = stream.read(BUILD_BYTE_LIMIT - total + 1)
        except OSError as exc:
            raise _error("source", "build_source_read_failed", "A build-source file could not be safely opened.", "Use readable regular project-local files without symlinks.") from exc
        total += len(data)
        if total > BUILD_BYTE_LIMIT:
            raise _error("source", "build_byte_limit", "Build source exceeded 32 MiB while being read.", "Use an external reviewed builder for larger artifacts.")
        mode = 0o755 if candidate.stat().st_mode & 0o111 else 0o644
        entries.append(SourceEntry(relative_name.as_posix(), data, mode, hashlib.sha256(data).hexdigest()))
    if not entries:
        raise _error("source", "empty_build_source", "Build source contains no regular files.", "Choose a non-empty reviewed build-output path.")
    return tuple(entries)


def _content_root(entries: tuple[SourceEntry, ...]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry.name.encode("utf-8") + b"\0")
        digest.update(str(entry.mode).encode("ascii") + b"\0")
        digest.update(str(len(entry.data)).encode("ascii") + b"\0")
        digest.update(entry.digest.encode("ascii") + b"\0")
    return digest.hexdigest()


def _spdx(plan: DeploymentPlan, entries: tuple[SourceEntry, ...], content_root: str) -> dict[str, Any]:
    files = [
        {
            "SPDXID": f"SPDXRef-File-{index}",
            "fileName": f"./payload/{entry.name}",
            "checksums": [{"algorithm": "SHA256", "checksumValue": entry.digest}],
        }
        for index, entry in enumerate(entries, start=1)
    ]
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"agentkit-artifact-{plan.digest[:12]}",
        "documentNamespace": f"https://agentkit.invalid/spdx/{plan.digest}/{content_root}",
        "creationInfo": {
            "created": "1980-01-01T00:00:00Z",
            "creators": [f"Tool: omen-agentkit-{__version__}"],
            "comment": "Timestamp normalized for deterministic local assembly; this document performs file inventory only.",
        },
        "files": files,
        "documentDescribes": [item["SPDXID"] for item in files],
    }


def _provenance(plan: DeploymentPlan, plan_reference: str, source_path: str, entries: tuple[SourceEntry, ...], content_root: str) -> dict[str, Any]:
    payload = plan.payload
    return {
        "schema_version": 1,
        "builder": "omen-agentkit-deterministic-zip-v1",
        "artifact_format": "zip-stored-v1",
        "plan_digest": plan.digest,
        "target": payload["target"],
        "source": payload["source"],
        "build_input": source_path,
        "content_root_digest": content_root,
        "payload_files": [
            {"path": entry.name, "sha256": entry.digest, "bytes": len(entry.data), "mode": f"{entry.mode:04o}"}
            for entry in entries
        ],
        "commands": {
            "builder_operation": ["agent-starter", "deployment", "build", ".", "--plan", plan_reference, "--source", source_path],
            "profile_display_only": payload["effects"]["commands"],
            "executed": [],
        },
        "tool_versions": {
            "agent_starter": __version__,
            "python": platform.python_version(),
            "zip_format": "ZIP_STORED",
        },
        "reproducibility": {"deterministic_metadata": True, "runs_compared": 2, "equal": True},
        "authority": {"network_accessed": False, "profile_commands_executed": False, "push_performed": False, "apply_authorized": False},
    }


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = (mode & 0xFFFF) << 16
    return info


def _assemble(plan: DeploymentPlan, plan_reference: str, source_path: str, entries: tuple[SourceEntry, ...]) -> tuple[bytes, dict[str, Any], str]:
    content_root = _content_root(entries)
    provenance = _provenance(plan, plan_reference, source_path, entries, content_root)
    sbom = _spdx(plan, entries, content_root)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.writestr(_zip_info(".agentkit/provenance.json"), json.dumps(provenance, indent=2, sort_keys=True).encode("utf-8") + b"\n")
        archive.writestr(_zip_info(".agentkit/sbom.spdx.json"), json.dumps(sbom, indent=2, sort_keys=True).encode("utf-8") + b"\n")
        for entry in entries:
            archive.writestr(_zip_info(f"payload/{entry.name}", entry.mode), entry.data)
    value = stream.getvalue()
    if len(value) > ARTIFACT_LIMIT:
        raise _error("artifact", "artifact_size_limit", "Assembled artifact exceeds 40 MiB.", "Use an external reviewed builder for larger artifacts.")
    return value, provenance, content_root


def build_artifact(root: Path, plan: DeploymentPlan, source_relative: Path, *, plan_reference: str) -> ArtifactBuildReport:
    root = root.expanduser().resolve()
    payload = plan.payload
    contract = deployment_contract(payload["target"]["id"])
    if DeploymentOperation.BUILD not in contract.enabled_operations:
        raise _error("target", "build_not_supported", "This target has no reviewed local artifact builder.", "Use static-site or linux-service-bundle, or wait for a target-specific isolated builder.")
    config = load_plan_project_config(root)
    if config.project_name != payload["project"]["name"] or config.project_slug != payload["project"]["slug"]:
        raise _error("project", "project_identity_mismatch", "Project metadata does not match the immutable plan.", "Build from the plan's original project.")
    validation = validate_project(root)
    if not validation.ok:
        raise _error("project", "project_validation_failed", "AgentKit structural validation failed.", "Resolve `agent-starter validate` errors before building.")
    planned_source = payload["source"]
    current_source = inspect_source_state(root)
    if planned_source["repository"] != "git" or planned_source["revision"] is None or planned_source["dirty"] is not False:
        raise _error("source", "clean_git_plan_required", "Artifact builds require a plan recorded from clean Git source.", "Commit or explicitly preserve changes, return to a clean checkout, and generate a new plan.")
    if current_source.repository != "git" or current_source.revision != planned_source["revision"] or current_source.dirty is not False or not current_source.project_is_repository_root:
        raise _error("source", "source_state_mismatch", "Current clean Git source does not exactly match the plan.", "Return to the planned clean revision or generate a new plan.")
    artifact_relative = Path(payload["target"]["artifact_output"])
    if artifact_relative.suffix.lower() != ".zip":
        raise _error("artifact_output", "zip_output_required", "The local deterministic builder requires a .zip artifact output.", "Generate a new plan whose artifact_output ends in .zip.")
    if payload["target"]["artifact_output"] not in payload["effects"]["local_writes"]:
        raise _error("effects.local_writes", "artifact_write_not_declared", "The plan does not declare its artifact output as a local write.", "Generate a new plan listing artifact_output in local_writes.")
    output = confined_output_path(root, artifact_relative)
    source = _confined_path(root, source_relative, must_exist=True)
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise _error("artifact_output", "artifact_inside_source", "Artifact output cannot be inside its own build source.", "Choose a separate project-local output path.")
    first_entries = _collect_source(root, source_relative)
    first_bytes, provenance, content_root = _assemble(plan, plan_reference, source_relative.as_posix(), first_entries)
    second_entries = _collect_source(root, source_relative)
    second_bytes, _, second_root = _assemble(plan, plan_reference, source_relative.as_posix(), second_entries)
    if content_root != second_root or hashlib.sha256(first_bytes).digest() != hashlib.sha256(second_bytes).digest():
        raise _error("source", "reproducibility_failed", "Two local deterministic assembly runs did not match.", "Stop concurrent source changes and regenerate the plan before retrying.")
    try:
        atomic_create(output, first_bytes, mode=0o644)
    except FileExistsError as exc:
        raise _error("artifact_output", "artifact_exists", "Artifact output already exists and was not replaced.", "Choose a new plan/output or preserve and compare the existing artifact.") from exc
    except OSError as exc:
        raise _error("artifact_output", "artifact_write_failed", "The artifact could not be atomically created.", "Use a writable project-local output with non-symlinked parents.") from exc
    return ArtifactBuildReport(
        plan.digest,
        artifact_relative.as_posix(),
        hashlib.sha256(first_bytes).hexdigest(),
        content_root,
        len(first_bytes),
        len(first_entries),
        current_source.revision or "",
        True,
        2,
        provenance,
    )


def _read_artifact_bytes(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > ARTIFACT_LIMIT:
            raise ValueError("artifact is non-regular or oversized")
        data = stream.read(ARTIFACT_LIMIT + 1)
    if len(data) > ARTIFACT_LIMIT:
        raise ValueError("artifact grew beyond the inspection limit")
    return data


def verify_built_artifact(path: Path, *, plan_digest: str) -> ArtifactVerification:
    issues: list[str] = []
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("artifact is missing, symlinked, non-regular, or oversized")
        artifact_bytes = _read_artifact_bytes(path)
        artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()
        with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)) or len(names) > BUILD_FILE_LIMIT + 2:
                raise ValueError("artifact has duplicate or excessive entries")
            if names[:2] != [".agentkit/provenance.json", ".agentkit/sbom.spdx.json"]:
                raise ValueError("artifact metadata entries are missing or out of order")
            if any(Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name for name in names):
                raise ValueError("artifact contains an unsafe member path")
            if any(item.compress_type != zipfile.ZIP_STORED or item.file_size != item.compress_size for item in infos):
                raise ValueError("artifact uses an unsupported compressed or inconsistent entry")
            if sum(item.file_size for item in infos) > ARTIFACT_LIMIT:
                raise ValueError("artifact expanded content exceeds the inspection limit")
            provenance = json.loads(archive.read(".agentkit/provenance.json"))
            sbom = json.loads(archive.read(".agentkit/sbom.spdx.json"))
            if provenance.get("plan_digest") != plan_digest or provenance.get("builder") != "omen-agentkit-deterministic-zip-v1":
                raise ValueError("artifact provenance does not match the plan/builder")
            reproducibility = provenance.get("reproducibility")
            authority = provenance.get("authority")
            commands = provenance.get("commands")
            if reproducibility != {"deterministic_metadata": True, "equal": True, "runs_compared": 2}:
                raise ValueError("artifact reproducibility record is invalid")
            if not isinstance(authority, dict) or any(authority.get(name) is not False for name in ("network_accessed", "profile_commands_executed", "push_performed", "apply_authorized")):
                raise ValueError("artifact provenance authority is invalid")
            if not isinstance(commands, dict) or commands.get("executed") != []:
                raise ValueError("artifact provenance claims command execution")
            records = provenance.get("payload_files")
            if not isinstance(records, list) or len(records) != len(names) - 2:
                raise ValueError("artifact provenance file inventory is invalid")
            rebuilt: list[SourceEntry] = []
            sbom_files = sbom.get("files")
            if sbom.get("spdxVersion") != "SPDX-2.3" or not isinstance(sbom_files, list) or len(sbom_files) != len(records):
                raise ValueError("embedded SPDX inventory is invalid")
            for record, sbom_file, info in zip(records, sbom_files, infos[2:], strict=True):
                name = info.filename
                if not isinstance(record, dict) or name != f"payload/{record.get('path')}":
                    raise ValueError("artifact payload order/path does not match provenance")
                data = archive.read(name)
                digest = hashlib.sha256(data).hexdigest()
                if digest != record.get("sha256") or len(data) != record.get("bytes") or not re.fullmatch(r"0[67][0-7]{2}", str(record.get("mode"))):
                    raise ValueError("artifact payload checksum, size, or mode does not match provenance")
                if (info.external_attr >> 16) & 0o777 != int(str(record["mode"]), 8):
                    raise ValueError("artifact payload permissions do not match provenance")
                expected_checksum = [{"algorithm": "SHA256", "checksumValue": digest}]
                if not isinstance(sbom_file, dict) or sbom_file.get("fileName") != f"./{name}" or sbom_file.get("checksums") != expected_checksum:
                    raise ValueError("embedded SPDX file evidence does not match payload")
                rebuilt.append(SourceEntry(str(record["path"]), data, int(str(record["mode"]), 8), digest))
            content_root = _content_root(tuple(rebuilt))
            if content_root != provenance.get("content_root_digest"):
                raise ValueError("artifact content-root digest does not match provenance")
        return ArtifactVerification(True, (), artifact_digest, content_root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile, RuntimeError):
        issues.append("artifact_invalid_or_unverifiable")
        try:
            digest = hashlib.sha256(_read_artifact_bytes(path)).hexdigest()
        except (OSError, ValueError):
            digest = ""
        return ArtifactVerification(False, tuple(issues), digest, None)


def render_build_json(report: ArtifactBuildReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_build_text(report: ArtifactBuildReport) -> str:
    return "\n".join((
        "# Local deterministic deployment artifact", "",
        f"Plan digest (SHA-256): {report.plan_digest}",
        f"Artifact: {report.artifact_path}",
        f"Artifact digest (SHA-256): {report.artifact_digest}",
        f"Content-root digest (SHA-256): {report.content_root_digest}",
        f"Source revision: {report.source_revision}",
        f"Payload files: {report.payload_files}",
        f"Artifact bytes: {report.artifact_bytes}",
        "Reproducibility: passed (two equal in-memory assemblies)",
        "SBOM: embedded SPDX-2.3 JSON at .agentkit/sbom.spdx.json",
        "Provenance: embedded at .agentkit/provenance.json",
        "Authority: local artifact write only; no profile/project command, credential, network, target, push, remote write, or apply occurred.", "",
    ))
