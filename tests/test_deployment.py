from __future__ import annotations

import unittest

from agent_starter.deployment import (
    DEPLOYMENT_TARGET_CONTRACTS,
    DeploymentContractError,
    DeploymentOperation,
    DeploymentTarget,
    deployment_contract,
    list_deployment_contracts,
    parse_deployment_target,
)


class DeploymentContractTests(unittest.TestCase):
    def test_registry_is_narrow_complete_and_stably_ordered(self) -> None:
        expected = ("static-site", "oci-image", "linux-service-bundle", "ssh-rsync")
        self.assertEqual(tuple(target.value for target in DeploymentTarget), expected)
        self.assertEqual(tuple(contract.target.value for contract in list_deployment_contracts()), expected)
        self.assertEqual(set(DEPLOYMENT_TARGET_CONTRACTS), set(DeploymentTarget))

    def test_every_contract_has_only_reviewed_local_operations_and_is_non_remote(self) -> None:
        for contract in list_deployment_contracts():
            with self.subTest(target=contract.target.value):
                expected = (DeploymentOperation.PLAN, DeploymentOperation.CHECK)
                if contract.target in {DeploymentTarget.STATIC_SITE, DeploymentTarget.LINUX_SERVICE_BUNDLE}:
                    expected += (DeploymentOperation.BUILD,)
                self.assertEqual(contract.enabled_operations, expected)
                self.assertNotIn(DeploymentOperation.APPLY, contract.reviewed_future_operations)
                self.assertNotIn(DeploymentOperation.PUSH, contract.reviewed_future_operations)
                self.assertFalse(contract.allows_network)
                self.assertFalse(contract.allows_remote_writes)
                self.assertFalse(contract.allows_secret_values)
                self.assertFalse(contract.production_ready)

    def test_only_static_site_has_disposable_staging_rehearsal_without_apply(self) -> None:
        supported = [
            contract.target
            for contract in list_deployment_contracts()
            if contract.disposable_staging_rehearsal
        ]
        self.assertEqual(supported, [DeploymentTarget.STATIC_SITE])
        contract = deployment_contract("static-site")
        self.assertNotIn(DeploymentOperation.APPLY, contract.enabled_operations)
        self.assertFalse(contract.production_ready)

    def test_plan_contract_requires_effects_credentials_health_and_rollback(self) -> None:
        sections = deployment_contract("static-site").required_plan_sections
        self.assertIn("environment and exact target identity", sections)
        self.assertIn("artifact provenance and digest", sections)
        self.assertIn("local and remote filesystem effects", sections)
        self.assertIn("credential mechanism by reference only", sections)
        self.assertIn("health checks and success evidence", sections)
        self.assertIn("rollback and recovery", sections)
        self.assertIn("monitoring, log locations, and maintenance ownership", sections)

    def test_exact_identifier_is_distinct_from_display_label(self) -> None:
        contract = deployment_contract("oci-image")
        self.assertEqual(contract.target.value, "oci-image")
        self.assertEqual(contract.display_label, "OCI image artifact")
        self.assertEqual(parse_deployment_target("oci-image"), DeploymentTarget.OCI_IMAGE)

    def test_unknown_alias_generic_cloud_and_wrong_type_fail_closed(self) -> None:
        for value in ("OCI image artifact", "kubernetes", "generic-cloud", "ssh", True, None):
            with self.subTest(value=value), self.assertRaises(DeploymentContractError) as caught:
                parse_deployment_target(value)
            issue = caught.exception.issue
            self.assertEqual(issue.path, "deployment.target")
            self.assertIn(issue.code, {"unsupported_deployment_target", "invalid_deployment_target_type"})
            self.assertIn("static-site", issue.remedy)

    def test_serialization_exposes_no_execution_or_secret_authority(self) -> None:
        value = deployment_contract("ssh-rsync").to_dict()
        self.assertEqual(value["enabled_operations"], ["plan", "check"])
        self.assertFalse(value["allows_network"])
        self.assertFalse(value["allows_remote_writes"])
        self.assertFalse(value["allows_secret_values"])
        self.assertNotIn("argv", value)
        self.assertNotIn("credentials", value)


if __name__ == "__main__":
    unittest.main()
