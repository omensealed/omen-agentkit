from __future__ import annotations

import argparse
import importlib
import os
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Protocol


class BuildBackend(Protocol):
    def build_sdist(self, sdist_directory: str) -> str: ...

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: dict[str, object] | None = None,
        metadata_directory: str | None = None,
    ) -> str: ...


def _safe_artifact(output_dir: Path, name: str, suffix: str) -> Path:
    if not name or Path(name).name != name or not name.endswith(suffix):
        raise RuntimeError(f"Build backend returned an unsafe {suffix} artifact name.")
    artifact = output_dir / name
    if artifact.is_symlink() or not artifact.is_file():
        raise RuntimeError(f"Build backend did not create the expected {suffix} artifact.")
    return artifact


def _extract_sdist(sdist: Path, destination: Path) -> Path:
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise RuntimeError("Build backend created an empty source distribution.")
        roots: set[str] = set()
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise RuntimeError("Source distribution contains an unsafe path.")
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise RuntimeError("Source distribution contains an unsupported special entry.")
            roots.add(relative.parts[0])
        if len(roots) != 1:
            raise RuntimeError("Source distribution must contain exactly one top-level directory.")
        archive.extractall(destination, filter="data")
    extracted = destination / next(iter(roots))
    if not extracted.is_dir() or not (extracted / "pyproject.toml").is_file():
        raise RuntimeError("Source distribution does not contain a buildable project root.")
    return extracted


def build_artifacts(
    root: Path,
    output_dir: Path,
    *,
    backend: BuildBackend | None = None,
) -> tuple[Path, Path]:
    root = root.resolve(strict=True)
    if not root.is_dir() or not (root / "pyproject.toml").is_file():
        raise ValueError("Build root must be a project directory containing pyproject.toml.")
    if output_dir.is_symlink():
        raise ValueError("Build output directory must not be a symlink.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve(strict=True)
    if any(output_dir.glob("*.whl")) or any(output_dir.glob("*.tar.gz")):
        raise FileExistsError("Build output already contains a wheel or source distribution.")

    selected = backend
    if selected is None:
        try:
            selected = importlib.import_module("setuptools.build_meta")  # type: ignore[assignment]
        except ImportError as exc:
            raise RuntimeError(
                "The declared setuptools build backend is unavailable; use a Python environment that provides it."
            ) from exc

    previous = Path.cwd()
    try:
        os.chdir(root)
        sdist_name = selected.build_sdist(str(output_dir))
        sdist = _safe_artifact(output_dir, sdist_name, ".tar.gz")
        with tempfile.TemporaryDirectory(prefix="agentkit-wheel-source-") as temp:
            wheel_root = _extract_sdist(sdist, Path(temp))
            os.chdir(wheel_root)
            wheel_name = selected.build_wheel(str(output_dir))
    finally:
        os.chdir(previous)

    wheel = _safe_artifact(output_dir, wheel_name, ".whl")
    return wheel, sdist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build one wheel and one sdist without installing a build frontend.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root; defaults to the current directory.")
    parser.add_argument("--outdir", type=Path, required=True, help="Create-only artifact output directory.")
    args = parser.parse_args(argv)
    try:
        wheel, sdist = build_artifacts(args.root, args.outdir)
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(wheel)
    print(sdist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
