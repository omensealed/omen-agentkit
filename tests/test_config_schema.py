from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_starter.cli import main
from agent_starter.config_schema import ConfigValidationError, migrate_config, parse_config


class ConfigSchemaTests(unittest.TestCase):
    def base(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "project_name": "Strict Config",
            "project_path": "/tmp/strict-config",
            "project_mode": "new",
            "database": "none",
            "primary_agent": "codex",
        }

    def test_v1_migration_preserves_arch_only_package_intent(self) -> None:
        raw = {**self.base(), "schema_version": 1, "cachyos_packages": ["ripgrep", "python"]}
        migration = migrate_config(raw)
        self.assertEqual(migration.data["schema_version"], 2)
        self.assertNotIn("cachyos_packages", migration.data)
        self.assertEqual(migration.data["extra_packages_by_provider"], {"arch": ["ripgrep", "python"]})
        self.assertNotIn("debian", migration.data["extra_packages_by_provider"])
        parsed = parse_config(raw)
        self.assertEqual(parsed.config.arch_extra_packages, ["ripgrep", "python"])

    def test_ambiguous_boolean_and_type_values_have_structured_issues(self) -> None:
        for value in ("false", "0", 0, [], {}):
            with self.subTest(value=value), self.assertRaises(ConfigValidationError) as raised:
                parse_config({**self.base(), "network_access": value})
            issue = raised.exception.issues[0]
            self.assertEqual(issue.path, "network_access")
            self.assertEqual(issue.code, "invalid_boolean")
            self.assertIn("true or false", issue.remedy)

    def test_strict_lists_packages_commands_and_enums(self) -> None:
        cases = (
            ({"languages": "python"}, "languages", "invalid_list"),
            ({"database": "oracle"}, "database", "invalid_enum"),
            ({"extra_packages_by_provider": {"arch": ["--overwrite=*"]}}, "extra_packages_by_provider.arch[0]", "invalid_package_identifier"),
            ({"extra_packages_by_provider": {"debian": ["bad package"]}}, "extra_packages_by_provider.debian[0]", "invalid_package_identifier"),
            ({"extra_packages_by_provider": {"BAD PROVIDER": ["safe"]}}, "extra_packages_by_provider", "invalid_provider"),
            ({"custom_test_commands": ["\x00bad"]}, "custom_test_commands[0]", "invalid_string"),
        )
        for update, path, code in cases:
            with self.subTest(path=path), self.assertRaises(ConfigValidationError) as raised:
                parse_config({**self.base(), **update})
            self.assertTrue(any(issue.path == path and issue.code == code for issue in raised.exception.issues))

    def test_sandbox_image_profile_is_a_strict_enum(self) -> None:
        parsed = parse_config({
            **self.base(),
            "sandbox": {"enabled": True, "mode": "toolchain", "image_profile": "debian-toolchain"},
        })
        self.assertEqual(parsed.config.sandbox.image_profile, "debian-toolchain")
        with self.assertRaises(ConfigValidationError) as raised:
            parse_config({
                **self.base(),
                "sandbox": {"enabled": True, "mode": "toolchain", "image_profile": "host-auto"},
            })
        issue = next(item for item in raised.exception.issues if item.path == "sandbox.image_profile")
        self.assertEqual(issue.code, "invalid_enum")
        self.assertIn("arch-toolchain", issue.remedy)

    def test_unknown_field_is_a_stable_warning(self) -> None:
        result = parse_config({**self.base(), "future_extension": "kept elsewhere"})
        issue = next(issue for issue in result.issues if issue.path == "future_extension")
        self.assertEqual(issue.code, "unknown_field")
        self.assertEqual(issue.severity, "warning")

    def test_advisor_capabilities_use_the_canonical_catalog(self) -> None:
        parsed = parse_config({
            **self.base(),
            "advisor": {"toolchain_capabilities": ["language.python"]},
        })
        self.assertEqual(parsed.config.advisor.toolchain_capabilities, ["language.python"])
        with self.assertRaises(ConfigValidationError) as raised:
            parse_config({
                **self.base(),
                "advisor": {"toolchain_capabilities": ["package.python"]},
            })
        issue = next(item for item in raised.exception.issues if item.code == "invalid_capability")
        self.assertEqual(issue.path, "advisor.toolchain_capabilities[0]")
        with self.assertRaises(ConfigValidationError) as raised_type:
            parse_config({
                **self.base(),
                "advisor": {"toolchain_capabilities": "language.python"},
            })
        self.assertTrue(any(
            item.path == "advisor.toolchain_capabilities" and item.code == "invalid_list"
            for item in raised_type.exception.issues
        ))

    def test_loaded_capability_first_advisor_data_uses_the_strict_contract(self) -> None:
        advisor = {
            "summary": "Use Python.",
            "languages": ["python"],
            "database": "none",
            "recommended_capabilities": [{
                "capability_id": "language.python",
                "purpose": "Run Python.",
                "requirement": "required",
                "rationale": "Matches the project.",
                "confidence": "high",
            }],
            "architecture_notes": ["Keep the CLI thin."],
            "questions": [],
            "risks": [],
        }
        parsed = parse_config({**self.base(), "advisor": advisor})
        self.assertEqual(parsed.config.advisor.recommended_capabilities[0].capability_id, "language.python")
        malformed = {**advisor, "recommended_capabilities": [{
            **advisor["recommended_capabilities"][0],
            "capability_id": "unknown.capability",
        }]}
        with self.assertRaises(ConfigValidationError) as raised:
            parse_config({**self.base(), "advisor": malformed})
        self.assertTrue(any(
            item.path == "advisor" and item.code == "invalid_advisor_response"
            for item in raised.exception.issues
        ))

    def test_capability_decisions_are_strict_project_owned_records(self) -> None:
        decisions = [
            {
                "capability_id": "language.python",
                "decision": "accepted",
                "requirement": "required",
                "limitation": "",
            },
            {
                "capability_id": "optional.shellcheck",
                "decision": "rejected",
                "requirement": "optional",
                "limitation": "",
            },
            {
                "capability_id": "database.sqlite",
                "decision": "challenged",
                "requirement": "required",
                "limitation": "The selected database workflow will not be available.",
            },
        ]
        parsed = parse_config({**self.base(), "capability_decisions": decisions})
        self.assertEqual(
            [item.decision.value for item in parsed.config.capability_decisions],
            ["accepted", "rejected", "challenged"],
        )
        serialized = parsed.config.to_dict()
        self.assertIn("capability_decisions", serialized)
        self.assertNotIn("capability_decisions", serialized["advisor"])

        invalid_cases = (
            ("not-a-list", "capability_decisions", "invalid_list"),
            ([{**decisions[0], "decision": "rejected"}], "capability_decisions[0].decision", "invalid_decision"),
            ([{**decisions[1], "decision": "challenged"}], "capability_decisions[0].decision", "invalid_decision"),
            ([{**decisions[2], "limitation": ""}], "capability_decisions[0].limitation", "missing_limitation"),
            ([{**decisions[0], "capability_id": "unknown.tool"}], "capability_decisions[0].capability_id", "invalid_capability"),
            ([{**decisions[0], "extra": True}], "capability_decisions[0].extra", "unknown_field"),
            ([{
                "capability_id": "base.tooling", "decision": "rejected",
                "requirement": "optional", "limitation": "",
            }], "capability_decisions[0].requirement", "invalid_requirement"),
        )
        for value, path, code in invalid_cases:
            with self.subTest(path=path, code=code), self.assertRaises(ConfigValidationError) as raised:
                parse_config({**self.base(), "capability_decisions": value})
            self.assertTrue(any(
                issue.path == path and issue.code == code
                for issue in raised.exception.issues
            ))

    def test_migrate_command_is_preview_or_separate_output_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "v1.json"
            output = Path(temp) / "v2.json"
            original = {**self.base(), "schema_version": 1, "cachyos_packages": ["ripgrep"]}
            source.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(main(["config", "migrate", "--input", str(source), "--output", str(output)]), 0)
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), original)
            migrated = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated["extra_packages_by_provider"]["arch"], ["ripgrep"])
            self.assertEqual(main(["config", "migrate", "--input", str(source), "--output", str(source)]), 2)


if __name__ == "__main__":
    unittest.main()
