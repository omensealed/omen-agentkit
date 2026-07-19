from __future__ import annotations

import unittest

from agent_starter.structure.policy import (
    DEFAULT_STRUCTURE_POLICY,
    FunctionMeasurement,
    ResponsibilityMeasurement,
    StructureExemption,
    StructureObservation,
    evaluate_structure,
)


class StructurePolicyTests(unittest.TestCase):
    def test_default_thresholds_are_review_signals_not_failures(self) -> None:
        self.assertEqual(DEFAULT_STRUCTURE_POLICY.module_logical_lines, 500)
        self.assertEqual(DEFAULT_STRUCTURE_POLICY.function_logical_lines, 80)
        self.assertEqual(DEFAULT_STRUCTURE_POLICY.repeated_append_count, 3)

        result = evaluate_structure(StructureObservation(path="agent_starter/large.py", module_logical_lines=501))
        self.assertEqual([item.code for item in result.findings], ["structure.module-size"])
        self.assertEqual(result.findings[0].severity, "warning")
        self.assertFalse(result.findings[0].blocking)
        self.assertIn("review", result.findings[0].remedy.lower())

    def test_all_six_policy_signals_are_reported_deterministically(self) -> None:
        observation = StructureObservation(
            path="agent_starter/broad.py",
            module_logical_lines=700,
            functions=(FunctionMeasurement("run_everything", 120),),
            responsibility_categories=("cli", "persistence", "networking"),
            introduced_dependency_cycle=("agent_starter.broad", "agent_starter.storage", "agent_starter.broad"),
            append_only_changes=4,
            public_module=True,
            documented_purpose=False,
        )
        result = evaluate_structure(observation)
        self.assertEqual(
            [item.code for item in result.findings],
            [
                "structure.module-size",
                "structure.function-size",
                "structure.mixed-responsibilities",
                "structure.dependency-cycle",
                "structure.repeated-large-append",
                "structure.public-purpose-missing",
            ],
        )
        self.assertTrue(all(item.severity == "warning" and not item.blocking for item in result.findings))

    def test_threshold_edges_and_cohesive_module_do_not_warn(self) -> None:
        result = evaluate_structure(
            StructureObservation(
                path="agent_starter/cohesive.py",
                module_logical_lines=500,
                functions=(FunctionMeasurement("render", 80),),
                responsibility_categories=("templates",),
                append_only_changes=2,
                public_module=True,
                documented_purpose=True,
            )
        )
        self.assertEqual(result.findings, ())

    def test_class_with_unrelated_responsibilities_is_a_soft_signal(self) -> None:
        result = evaluate_structure(
            StructureObservation(
                path="agent_starter/service.py",
                module_logical_lines=200,
                class_responsibilities=(
                    ResponsibilityMeasurement("ProjectService", ("validation", "persistence")),
                ),
            )
        )
        self.assertEqual([item.code for item in result.findings], ["structure.mixed-responsibilities"])
        self.assertEqual(result.findings[0].subject, "ProjectService")
        self.assertFalse(result.findings[0].blocking)

    def test_reviewed_exemption_requires_reason_and_cannot_hide_complexity(self) -> None:
        for category in ("generated-data", "static-data", "license", "protocol-table", "cohesive-template"):
            with self.subTest(category=category):
                exemption = StructureExemption(
                    category=category,
                    reason="This file is cohesive non-executable payload data.",
                )
                result = evaluate_structure(
                    StructureObservation(
                        path=f"payload/{category}.py",
                        module_logical_lines=900,
                        functions=(FunctionMeasurement("payload", 200, payload_only=True),),
                        exemption=exemption,
                    )
                )
                self.assertEqual(result.findings, ())
                self.assertEqual(result.acknowledged_exemption, exemption)

        with self.assertRaises(ValueError):
            StructureExemption(category="static-data", reason=" ")
        with self.assertRaises(ValueError):
            StructureExemption(
                category="cohesive-template",
                reason="Claims to exempt complex executable behavior.",
                hides_executable_complexity=True,
            )

        executable = evaluate_structure(
            StructureObservation(
                path="templates/executable.py",
                module_logical_lines=900,
                functions=(FunctionMeasurement("branching_renderer", 200),),
                exemption=StructureExemption(
                    category="cohesive-template",
                    reason="The module contains a large cohesive template payload.",
                ),
            )
        )
        self.assertEqual([item.code for item in executable.findings], ["structure.function-size"])

        result = evaluate_structure(
            StructureObservation(
                path="agent_starter/mixed.py",
                module_logical_lines=900,
                responsibility_categories=("ui", "storage"),
                introduced_dependency_cycle=("agent_starter.mixed", "agent_starter.ui", "agent_starter.mixed"),
                append_only_changes=5,
                exemption=StructureExemption(
                    category="cohesive-template",
                    reason="Large cohesive template payload; executable risks still reviewed.",
                ),
            )
        )
        self.assertEqual(
            [item.code for item in result.findings],
            [
                "structure.mixed-responsibilities",
                "structure.dependency-cycle",
                "structure.repeated-large-append",
            ],
        )

    def test_observations_are_strict_and_bounded(self) -> None:
        with self.assertRaises(ValueError):
            StructureObservation(path="", module_logical_lines=1)
        with self.assertRaises(ValueError):
            StructureObservation(path="module.py", module_logical_lines=-1)
        with self.assertRaises(ValueError):
            FunctionMeasurement("bad", -1)
        with self.assertRaises(ValueError):
            StructureObservation(
                path="module.py",
                module_logical_lines=1,
                responsibility_categories=("ui", "ui"),
            )


if __name__ == "__main__":
    unittest.main()
