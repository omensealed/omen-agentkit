from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from agent_starter.release_artifacts import (
    ReleaseArtifactError,
    create_release_evidence,
    main,
)


class ReleaseArtifactEvidenceTests(unittest.TestCase):
    def _artifacts(self, root: Path) -> tuple[Path, Path]:
        wheel = root / "cli_ai_agent_starter_kit-0.4.8-py3-none-any.whl"
        sdist = root / "cli_ai_agent_starter_kit-0.4.8.tar.gz"
        wheel.write_bytes(b"synthetic wheel\n")
        sdist.write_bytes(b"synthetic source distribution\n")
        return wheel, sdist

    def test_creates_deterministic_checksums_and_spdx_without_replacing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheel, sdist = self._artifacts(root)
            report = create_release_evidence(root)
            expected = sorted((wheel, sdist), key=lambda path: path.name)
            checksum_lines = (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                checksum_lines,
                [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in expected],
            )
            self.assertEqual([item.name for item in report.artifacts], [path.name for path in expected])
            sbom = json.loads((root / "release.spdx.json").read_text(encoding="utf-8"))
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            self.assertEqual(sbom["creationInfo"]["created"], "1980-01-01T00:00:00Z")
            self.assertEqual([item["packageFileName"] for item in sbom["packages"]], [path.name for path in expected])
            self.assertEqual(
                [item["checksums"][0]["checksumValue"] for item in sbom["packages"]],
                [hashlib.sha256(path.read_bytes()).hexdigest() for path in expected],
            )
            original = (root / "SHA256SUMS").read_bytes()
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(root)
            self.assertEqual(caught.exception.issue.code, "evidence_exists")
            self.assertEqual((root / "SHA256SUMS").read_bytes(), original)

    def test_requires_exactly_one_wheel_and_one_sdist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.whl").write_bytes(b"one")
            (root / "two.whl").write_bytes(b"two")
            (root / "one.tar.gz").write_bytes(b"source")
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(root)
            self.assertEqual(caught.exception.issue.code, "wheel_cardinality")
            self.assertFalse((root / "SHA256SUMS").exists())

    def test_rejects_symlinked_artifact_and_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            (target / "package.whl").write_bytes(b"wheel")
            (target / "package.tar.gz").write_bytes(b"sdist")
            link = root / "linked-directory"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(link)
            self.assertEqual(caught.exception.issue.code, "artifact_directory_symlink")

            (target / "package.whl").unlink()
            outside = root / "outside.whl"
            outside.write_bytes(b"outside")
            (target / "package.whl").symlink_to(outside)
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(target)
            self.assertEqual(caught.exception.issue.code, "artifact_symlink")

    def test_rejects_symlinked_parent_and_unsafe_checksum_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            self._artifacts(target)
            parent = root / "linked-parent"
            parent.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(parent / ".")
            self.assertEqual(caught.exception.issue.code, "artifact_directory_symlink")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "unsafe\nname.whl").write_bytes(b"wheel")
            (root / "package.tar.gz").write_bytes(b"sdist")
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(root)
            self.assertEqual(caught.exception.issue.code, "artifact_name_unsafe")

    def test_rejects_fifo_without_blocking(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO creation is unavailable")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.mkfifo(root / "package.whl")
            (root / "package.tar.gz").write_bytes(b"sdist")
            with self.assertRaises(ReleaseArtifactError) as caught:
                create_release_evidence(root)
            self.assertEqual(caught.exception.issue.code, "artifact_not_regular")

    def test_cli_reports_stable_safe_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(main([temp]), 2)


if __name__ == "__main__":
    unittest.main()
