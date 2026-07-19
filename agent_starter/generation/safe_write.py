"""Atomic local file primitives with explicit replace/create semantics."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _write_temp(path: Path, data: bytes, mode: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        return temp
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def atomic_replace(path: Path, data: bytes, mode: int = 0o644) -> None:
    temp = _write_temp(path, data, mode)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_create(path: Path, data: bytes, mode: int = 0o644) -> None:
    """Atomically publish a new file and fail if the destination exists."""

    temp = _write_temp(path, data, mode)
    try:
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)
