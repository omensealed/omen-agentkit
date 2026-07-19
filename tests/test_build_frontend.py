from __future__ import annotations

import tempfile
import tarfile
import unittest
from pathlib import Path

from agent_starter.build_frontend import build_artifacts


class _FakeBackend:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build_sdist(self, sdist_directory: str) -> str:
        self.assert_at_root()
        name = "example-1.0.tar.gz"
        source = self.root / "pyproject.toml"
        with tarfile.open(Path(sdist_directory) / name, "w:gz") as archive:
            archive.add(source, arcname="example-1.0/pyproject.toml")
        return name

    def build_wheel(self, wheel_directory: str, *_args: object, **_kwargs: object) -> str:
        if Path.cwd().name != "example-1.0" or not (Path.cwd() / "pyproject.toml").is_file():
            raise AssertionError("wheel was not built from the extracted source distribution")
        name = "example-1.0-py3-none-any.whl"
        (Path(wheel_directory) / name).write_bytes(b"wheel")
        return name

    def assert_at_root(self) -> None:
        if Path.cwd() != self.root:
            raise AssertionError("backend was not invoked from the project root")


class BuildFrontendTests(unittest.TestCase):
    def test_builds_exact_create_only_artifacts_and_restores_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "source"
            output = base / "artifacts"
            root.mkdir()
            (root / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
            previous = Path.cwd()
            wheel, sdist = build_artifacts(root, output, backend=_FakeBackend(root))
            self.assertEqual(Path.cwd(), previous)
            self.assertEqual(wheel.name, "example-1.0-py3-none-any.whl")
            self.assertEqual(sdist.name, "example-1.0.tar.gz")
            with self.assertRaises(FileExistsError):
                build_artifacts(root, output, backend=_FakeBackend(root))

    def test_rejects_missing_project_and_symlinked_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            with self.assertRaises(ValueError):
                build_artifacts(base, base / "output", backend=_FakeBackend(base))
            root = base / "source"
            root.mkdir()
            (root / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
            real_output = base / "real-output"
            real_output.mkdir()
            linked_output = base / "linked-output"
            linked_output.symlink_to(real_output, target_is_directory=True)
            with self.assertRaises(ValueError):
                build_artifacts(root, linked_output, backend=_FakeBackend(root))


if __name__ == "__main__":
    unittest.main()
