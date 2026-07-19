"""Reference-only deployment secret contracts and value-free existence checks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import re
import stat
import subprocess
from types import MappingProxyType
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class SecretReferenceContract:
    mechanism: str
    display_label: str
    reference_convention: str
    existence_check: str
    reads_values: bool = False
    logs_values: bool = False
    persists_values: bool = False


@dataclass(frozen=True, slots=True)
class SecretReferenceFinding:
    name: str
    mechanism: str
    status: str
    code: str
    explanation: str
    remedy: str
    evidence: str = "metadata_only"


_CONTRACTS = (
    SecretReferenceContract("none", "No credential required", "no reference", "not-required"),
    SecretReferenceContract("environment-file", "Ignored project environment file", ".env.<reference-name>", "local-file-metadata"),
    SecretReferenceContract("os-keyring", "Operating-system keyring item", "platform-owned reference name", "reviewed-adapter-required"),
    SecretReferenceContract("ci-secret-store", "CI secret-store entry", "CI-owned reference name", "reviewed-adapter-required"),
    SecretReferenceContract("target-secret-manager", "Target-native secret-manager entry", "target-owned reference name", "reviewed-adapter-required"),
    SecretReferenceContract("ssh-agent", "SSH agent socket", "SSH_AUTH_SOCK metadata", "local-socket-metadata"),
)
SECRET_REFERENCE_CONTRACTS: Mapping[str, SecretReferenceContract] = MappingProxyType({item.mechanism: item for item in _CONTRACTS})
CREDENTIAL_MECHANISMS = frozenset(SECRET_REFERENCE_CONTRACTS)
_REFERENCE_RE = re.compile(r"^[a-z][a-z0-9._-]{0,79}$")


def valid_secret_reference_name(value: object) -> bool:
    return isinstance(value, str) and _REFERENCE_RE.fullmatch(value) is not None


def secret_contract(mechanism: object) -> SecretReferenceContract:
    if not isinstance(mechanism, str) or mechanism not in SECRET_REFERENCE_CONTRACTS:
        choices = ", ".join(SECRET_REFERENCE_CONTRACTS)
        raise ValueError(f"Secret mechanism must be one of: {choices}.")
    return SECRET_REFERENCE_CONTRACTS[mechanism]


def list_secret_contracts() -> tuple[SecretReferenceContract, ...]:
    return _CONTRACTS


def _finding(name: str, mechanism: str, status: str, code: str, explanation: str, remedy: str) -> SecretReferenceFinding:
    return SecretReferenceFinding(name, mechanism, status, code, explanation, remedy)


def _git_ignored(root: Path, relative: Path) -> bool | None:
    environment = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })
    try:
        result = subprocess.run(
            [
                "git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
                "-C", str(root), "check-ignore", "--quiet", relative.as_posix(),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
            env=environment,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def _environment_file(
    root: Path,
    name: str,
    ignored_probe: Callable[[Path, Path], bool | None],
) -> SecretReferenceFinding:
    relative = Path(f".env.{name}")
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return _finding(name, "environment-file", "failed", "secret_reference_missing", "The named environment-file reference is absent.", "Create it outside AgentKit with mode 0600; never paste its value into configuration, prompts, or logs.")
    except OSError:
        return _finding(name, "environment-file", "unverified", "secret_reference_metadata_unavailable", "Environment-file metadata could not be checked safely.", "Restore local metadata access without printing or reading the file value.")
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        return _finding(name, "environment-file", "failed", "secret_reference_unsafe_type", "The reference is not a regular non-symlink file.", "Replace it with a regular project-local file created outside AgentKit.")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        return _finding(name, "environment-file", "failed", "secret_reference_permissions", "The reference permissions expose it beyond its owner.", "Set mode 0600 without printing or reading the value.")
    ignored = ignored_probe(root, relative)
    if ignored is False:
        return _finding(name, "environment-file", "failed", "secret_reference_not_ignored", "The reference is not ignored by Git.", "Add a narrow ignore rule and verify it before storing any value.")
    if ignored is None:
        return _finding(name, "environment-file", "unverified", "secret_reference_ignore_unverified", "Git ignore status could not be verified.", "Restore local Git ignore inspection before deployment; do not inspect the file contents.")
    return _finding(name, "environment-file", "passed", "secret_reference_present", "The reference exists as an ignored owner-only regular file; its value was not read.", "No action required.")


def _ssh_agent(name: str, environment: Mapping[str, str], stat_probe: Callable[[str], os.stat_result]) -> SecretReferenceFinding:
    socket_path = environment.get("SSH_AUTH_SOCK")
    if not isinstance(socket_path, str) or not socket_path:
        return _finding(name, "ssh-agent", "failed", "ssh_agent_missing", "No SSH agent socket reference is available.", "Start or select the intended SSH agent outside AgentKit; do not list or expose its keys.")
    try:
        metadata = stat_probe(socket_path)
    except OSError:
        return _finding(name, "ssh-agent", "failed", "ssh_agent_missing", "The SSH agent socket reference is unavailable.", "Restore the intended agent outside AgentKit without listing or exposing its keys.")
    if not stat.S_ISSOCK(metadata.st_mode):
        return _finding(name, "ssh-agent", "failed", "ssh_agent_unsafe_type", "The SSH agent reference is not a socket.", "Use a valid agent socket; do not substitute a file containing key material.")
    return _finding(name, "ssh-agent", "passed", "ssh_agent_present", "SSH agent socket metadata is present; no key was listed or inspected.", "No action required.")


def _socket_stat(path: str) -> os.stat_result:
    return os.stat(path, follow_symlinks=False)


def check_secret_references(
    root: Path,
    references: Sequence[object],
    *,
    environment: Mapping[str, str] | None = None,
    ignored_probe: Callable[[Path, Path], bool | None] = _git_ignored,
    socket_stat_probe: Callable[[str], os.stat_result] = _socket_stat,
) -> tuple[SecretReferenceFinding, ...]:
    root = root.expanduser().resolve()
    environment = os.environ if environment is None else environment
    findings: list[SecretReferenceFinding] = []
    for reference in references:
        name = getattr(reference, "name", None)
        mechanism = getattr(reference, "mechanism", None)
        if not valid_secret_reference_name(name) or not isinstance(mechanism, str) or mechanism not in CREDENTIAL_MECHANISMS:
            findings.append(_finding("invalid-reference", "invalid", "failed", "invalid_secret_reference", "The secret reference name or mechanism is invalid.", "Use the reviewed reference-only schema without a secret value."))
        elif mechanism == "none":
            findings.append(_finding(name, mechanism, "passed", "secret_not_required", "No credential is required for this reference.", "No action required."))
        elif mechanism == "environment-file":
            findings.append(_environment_file(root, name, ignored_probe))
        elif mechanism == "ssh-agent":
            findings.append(_ssh_agent(name, environment, socket_stat_probe))
        else:
            findings.append(_finding(name, mechanism, "unverified", "secret_adapter_unavailable", "The reference name is valid, but this platform store was not queried.", "Verify existence through a reviewed store-specific metadata adapter without reading or logging the value."))
    return tuple(findings)
