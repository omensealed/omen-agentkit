"""Create deterministic checksum and SPDX evidence for built distributions.

This module never builds, installs, uploads, publishes, or contacts a network.
It accepts one wheel and one source distribution from a caller-owned directory
and creates evidence files without replacing existing content.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from agent_starter.generation.safe_write import atomic_create


MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
CHECKSUMS_NAME = "SHA256SUMS"
SBOM_NAME = "release.spdx.json"
_SAFE_ARTIFACT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,255}$")


@dataclass(frozen=True, slots=True)
class ReleaseArtifactIssue:
    path: str
    code: str
    explanation: str
    remedy: str


class ReleaseArtifactError(ValueError):
    def __init__(self, issue: ReleaseArtifactIssue) -> None:
        super().__init__(f"{issue.code}: {issue.explanation} Remedy: {issue.remedy}")
        self.issue = issue


@dataclass(frozen=True, slots=True)
class ArtifactDigest:
    name: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceReport:
    artifacts: tuple[ArtifactDigest, ...]
    checksums_path: str
    sbom_path: str


def _error(path: str, code: str, explanation: str, remedy: str) -> ReleaseArtifactError:
    return ReleaseArtifactError(ReleaseArtifactIssue(path, code, explanation, remedy))


def _artifact_kind(name: str) -> str | None:
    if name.endswith(".whl"):
        return "wheel"
    if name.endswith(".tar.gz"):
        return "sdist"
    return None


def _hash_regular_file(path: Path) -> ArtifactDigest:
    if path.is_symlink():
        raise _error(path.name, "artifact_symlink", "A distribution artifact is a symbolic link.", "Build into a new local directory containing regular files only.")
    try:
        initial_metadata = path.lstat()
    except OSError as exc:
        raise _error(path.name, "artifact_open_failed", "A distribution artifact could not be inspected safely.", "Use a readable regular file in a non-symlinked build directory.") from exc
    if not stat.S_ISREG(initial_metadata.st_mode):
        raise _error(path.name, "artifact_not_regular", "A distribution artifact is not a regular file.", "Build one regular wheel and one regular source archive.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise _error(path.name, "artifact_open_failed", "A distribution artifact could not be opened safely.", "Use a readable regular file in a non-symlinked build directory.") from exc
    digest = hashlib.sha256()
    size = 0
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise _error(path.name, "artifact_not_regular", "A distribution artifact is not a regular file.", "Build one regular wheel and one regular source archive.")
        if (initial_metadata.st_dev, initial_metadata.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise _error(path.name, "artifact_changed", "A distribution artifact was substituted before hashing.", "Stop concurrent writes and rebuild in a new directory.")
        if metadata.st_size > MAX_ARTIFACT_BYTES:
            raise _error(path.name, "artifact_too_large", "A distribution artifact exceeds the 128 MiB evidence limit.", "Review the artifact contents and use a separately approved large-artifact process.")
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_ARTIFACT_BYTES:
                raise _error(path.name, "artifact_too_large", "A distribution artifact grew beyond the 128 MiB evidence limit.", "Stop concurrent writes and rebuild in a new directory.")
            digest.update(chunk)
        end_metadata = os.fstat(stream.fileno())
    if (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    ) != (
        end_metadata.st_dev,
        end_metadata.st_ino,
        end_metadata.st_size,
        end_metadata.st_mtime_ns,
        end_metadata.st_ctime_ns,
    ):
        raise _error(path.name, "artifact_changed", "A distribution artifact changed during hashing.", "Stop concurrent writes and rebuild in a new directory.")
    return ArtifactDigest(path.name, digest.hexdigest(), size)


def _select_artifacts(directory: Path) -> tuple[Path, Path]:
    by_kind: dict[str, list[Path]] = {"wheel": [], "sdist": []}
    try:
        entries = tuple(directory.iterdir())
    except OSError as exc:
        raise _error("artifact_directory", "artifact_directory_unreadable", "The artifact directory could not be read.", "Provide a readable directory containing one wheel and one source distribution.") from exc
    for path in entries:
        kind = _artifact_kind(path.name)
        if kind is not None:
            if _SAFE_ARTIFACT_NAME.fullmatch(path.name) is None:
                raise _error(path.name, "artifact_name_unsafe", "A distribution artifact name is unsafe for checksum evidence.", "Use standard build-generated ASCII artifact filenames without whitespace or control characters.")
            by_kind[kind].append(path)
    for kind, paths in by_kind.items():
        if len(paths) != 1:
            raise _error(
                "artifact_directory",
                f"{kind}_cardinality",
                f"Expected exactly one {kind} artifact, found {len(paths)}.",
                "Use a new build directory containing exactly one wheel and one source distribution.",
            )
    return by_kind["wheel"][0], by_kind["sdist"][0]


def _checksum_bytes(artifacts: tuple[ArtifactDigest, ...]) -> bytes:
    return "".join(f"{item.sha256}  {item.name}\n" for item in artifacts).encode("utf-8")


def _sbom_bytes(artifacts: tuple[ArtifactDigest, ...]) -> bytes:
    identity = hashlib.sha256(_checksum_bytes(artifacts)).hexdigest()
    packages = []
    relationships = []
    for number, item in enumerate(artifacts, start=1):
        spdx_id = f"SPDXRef-Artifact-{number}"
        packages.append({
            "SPDXID": spdx_id,
            "checksums": [{"algorithm": "SHA256", "checksumValue": item.sha256}],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "name": item.name,
            "packageFileName": item.name,
            "primaryPackagePurpose": "INSTALL",
            "versionInfo": "NOASSERTION",
        })
        relationships.append({
            "relatedSpdxElement": spdx_id,
            "relationshipType": "DESCRIBES",
            "spdxElementId": "SPDXRef-DOCUMENT",
        })
    document = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "creationInfo": {
            "created": "1980-01-01T00:00:00Z",
            "creators": ["Tool: omen-agentkit-release-evidence"],
        },
        "dataLicense": "CC0-1.0",
        "documentNamespace": f"urn:uuid:{uuid.UUID(identity[:32])}",
        "name": "Omen AgentKit Python distribution artifacts",
        "packages": packages,
        "relationships": relationships,
        "spdxVersion": "SPDX-2.3",
    }
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def create_release_evidence(artifact_directory: Path) -> ReleaseEvidenceReport:
    """Create checksum and SPDX files for one wheel and one sdist."""

    supplied = artifact_directory.expanduser()
    absolute = supplied.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise _error("artifact_directory", "artifact_directory_symlink", "The artifact directory or one of its parents is a symbolic link.", "Use a directly addressed local build directory with non-symlinked parents.")
    try:
        metadata = supplied.stat()
    except OSError as exc:
        raise _error("artifact_directory", "artifact_directory_missing", "The artifact directory does not exist or is inaccessible.", "Build one wheel and one source distribution into a new directory.") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise _error("artifact_directory", "artifact_directory_not_directory", "The artifact path is not a directory.", "Provide a directory containing one wheel and one source distribution.")
    directory = supplied.resolve()
    checksums_path = directory / CHECKSUMS_NAME
    sbom_path = directory / SBOM_NAME
    if checksums_path.exists() or checksums_path.is_symlink() or sbom_path.exists() or sbom_path.is_symlink():
        raise _error("artifact_directory", "evidence_exists", "Release evidence already exists and was not replaced.", "Preserve it for review or build into a new directory.")
    wheel, sdist = _select_artifacts(directory)
    artifacts = tuple(sorted((_hash_regular_file(wheel), _hash_regular_file(sdist)), key=lambda item: item.name))
    try:
        atomic_create(sbom_path, _sbom_bytes(artifacts), mode=0o644)
        atomic_create(checksums_path, _checksum_bytes(artifacts), mode=0o644)
    except FileExistsError as exc:
        raise _error("artifact_directory", "evidence_exists", "Release evidence appeared during creation and was not replaced.", "Preserve it for review or build into a new directory.") from exc
    except OSError as exc:
        raise _error("artifact_directory", "evidence_write_failed", "Release evidence could not be created atomically.", "Use a writable local directory with non-symlinked parents.") from exc
    return ReleaseEvidenceReport(artifacts, checksums_path.name, sbom_path.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create checksums and an SPDX SBOM for one wheel and one sdist.")
    parser.add_argument("artifact_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        report = create_release_evidence(args.artifact_directory)
    except ReleaseArtifactError as exc:
        print(f"Error [{exc.issue.code}]: {exc.issue.explanation}", file=sys.stderr)
        print(f"Safe remedy: {exc.issue.remedy}", file=sys.stderr)
        return 2
    for artifact in report.artifacts:
        print(f"sha256 {artifact.sha256}  {artifact.name}")
    print(f"Created {report.checksums_path} and {report.sbom_path}; no artifact was uploaded or published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
