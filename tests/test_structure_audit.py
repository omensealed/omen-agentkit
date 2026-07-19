from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_starter.cli import main
from agent_starter.structure.audit import AuditError, audit_project


class StructureAuditTests(unittest.TestCase):
    def _write_project(self, root: Path) -> None:
        package = root / "pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text('"""Synthetic package."""\n', encoding="utf-8")
        large_lines = ['"""Large synthetic module."""', "import pkg.a"]
        large_lines.extend(f"value_{index} = {index}" for index in range(510))
        large_lines.extend(("", "def huge_function():"))
        large_lines.extend(f"    branch_{index} = {index}" for index in range(90))
        large_lines.extend(("    return branch_89", "", "class ProjectService:", "    def render_ui(self):", "        return 'ui'", "", "    def save_database(self):", "        return 'db'"))
        (package / "broad.py").write_text("\n".join(large_lines) + "\n", encoding="utf-8")
        (package / "a.py").write_text("import pkg.b\n", encoding="utf-8")
        (package / "b.py").write_text("import pkg.a\n", encoding="utf-8")
        (package / "not_executed.py").write_text(
            "from pathlib import Path\nPath('AUDIT_EXECUTED').write_text('bad')\n",
            encoding="utf-8",
        )

    def _write_baseline(self, root: Path, *, exemption: bool = False) -> None:
        metadata = root / ".agent-starter"
        metadata.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "schema_version": 1,
            "modules": {
                "pkg/broad.py": {
                    "logical_lines": 500,
                    "function_count": 1,
                    "class_count": 1,
                    "append_only_changes": 3,
                }
            },
            "dependency_cycles": [],
            "exemptions": {},
        }
        if exemption:
            payload["exemptions"] = {
                "pkg/broad.py": {
                    "category": "static-data",
                    "reason": "Synthetic table payload is intentionally kept together.",
                }
            }
        (metadata / "structure-baseline.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_audit_measures_hotspots_classes_responsibilities_cycles_and_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            self._write_baseline(root)
            report = audit_project(root)

            self.assertTrue(report.advisory_only)
            self.assertFalse(report.blocking)
            self.assertEqual(report.baseline_status, "loaded")
            broad = next(item for item in report.modules if item.path == "pkg/broad.py")
            self.assertGreater(broad.logical_lines, 500)
            self.assertGreater(next(item for item in broad.functions if item.name == "huge_function").logical_lines, 80)
            service = next(item for item in broad.classes if item.name == "ProjectService")
            self.assertIn("ui", service.responsibility_groups)
            self.assertIn("persistence", service.responsibility_groups)
            self.assertTrue(report.dependency_cycles)
            codes = {finding.code for hotspot in report.hotspots for finding in hotspot.findings}
            self.assertIn("structure.module-size", codes)
            self.assertIn("structure.function-size", codes)
            self.assertIn("structure.mixed-responsibilities", codes)
            self.assertIn("structure.dependency-cycle", codes)
            self.assertIn("structure.repeated-large-append", codes)
            self.assertIn("structure.public-purpose-missing", codes)
            change = next(item for item in report.changes if item.path == "pkg/broad.py")
            self.assertGreater(change.logical_lines_delta, 0)
            self.assertEqual(report.hotspots, tuple(sorted(report.hotspots, key=lambda item: (-item.score, item.path))))
            self.assertFalse((root / "AUDIT_EXECUTED").exists())

    def test_baseline_exemption_is_visible_but_does_not_hide_executable_function(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            self._write_baseline(root, exemption=True)
            report = audit_project(root)
            self.assertEqual(len(report.acknowledged_exemptions), 1)
            self.assertEqual(report.acknowledged_exemptions[0].path, "pkg/broad.py")
            broad_codes = {
                finding.code
                for hotspot in report.hotspots
                if hotspot.path == "pkg/broad.py"
                for finding in hotspot.findings
            }
            self.assertNotIn("structure.module-size", broad_codes)
            self.assertIn("structure.function-size", broad_codes)
            self.assertIn("structure.repeated-large-append", broad_codes)

    def test_json_and_human_output_are_stable_relative_and_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["audit-structure", str(root), "--json"])
            self.assertEqual(code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["schema_version"], 1)
            self.assertTrue(data["advisory_only"])
            self.assertFalse(data["blocking"])
            self.assertEqual(data["root"], ".")
            self.assertTrue(data["modules"])
            self.assertTrue(data["dependency_cycles"])
            self.assertNotIn(
                "structure.dependency-cycle",
                {finding["code"] for hotspot in data["hotspots"] for finding in hotspot["findings"]},
            )
            self.assertNotIn(str(root), stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["audit-structure", str(root)])
            self.assertEqual(code, 0)
            text = stdout.getvalue()
            self.assertIn("advisory", text.lower())
            self.assertIn("Baseline: not recorded", text)
            self.assertIn("pkg/broad.py", text)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(after, before)

    def test_malformed_source_and_symlinks_are_safe_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pkg").mkdir()
            (root / "pkg/bad.py").write_text("def broken(:\n", encoding="utf-8")
            outside = root.parent / f"{root.name}-outside.py"
            outside.write_text("OUTSIDE = True\n", encoding="utf-8")
            try:
                (root / "pkg/linked.py").symlink_to(outside)
                report = audit_project(root)
                self.assertEqual(report.modules, ())
                self.assertTrue(any(issue.code == "structure.parse-error" for issue in report.issues))
                self.assertTrue(any(issue.code == "structure.symlink-skipped" for issue in report.issues))
                self.assertNotIn("linked.py", {item.path for item in report.modules})
            finally:
                outside.unlink(missing_ok=True)

    def test_baseline_must_be_bounded_confined_regular_and_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            outside = root.parent / f"{root.name}-baseline.json"
            outside.write_text('{"schema_version": 1}', encoding="utf-8")
            try:
                with self.assertRaises(AuditError):
                    audit_project(root, baseline_path=outside)
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(main(["audit-structure", str(root), "--baseline", str(outside)]), 2)
                self.assertIn("must exist inside the project root", stdout.getvalue())
                linked = root / "baseline.json"
                linked.symlink_to(outside)
                with self.assertRaises(AuditError):
                    audit_project(root, baseline_path=linked)
                bad = root / "bad.json"
                bad.write_text('{"schema_version": 2, "commands": ["sudo true"]}', encoding="utf-8")
                with self.assertRaises(AuditError):
                    audit_project(root, baseline_path=bad)
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
