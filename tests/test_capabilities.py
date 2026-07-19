from __future__ import annotations

import unittest

from agent_starter.capabilities import (
    CAPABILITY_CATALOG,
    CapabilityCategory,
    require_complete_provider_catalog,
    select_capabilities,
    unknown_capability_ids,
)
from agent_starter.platforms import ARCH_CAPABILITIES, DEBIAN_CAPABILITIES


class CapabilityCatalogTests(unittest.TestCase):
    def test_catalog_is_provider_neutral_and_provider_maps_are_complete(self) -> None:
        self.assertEqual(set(CAPABILITY_CATALOG), set(ARCH_CAPABILITIES))
        self.assertEqual(set(CAPABILITY_CATALOG), set(DEBIAN_CAPABILITIES))
        self.assertTrue(all(not hasattr(item, "packages") for item in CAPABILITY_CATALOG.values()))
        self.assertEqual(CAPABILITY_CATALOG["language.rust"].category, CapabilityCategory.LANGUAGE)
        self.assertIn("strategy", CAPABILITY_CATALOG["language.rust"].purpose)

    def test_selection_preserves_order_and_can_include_rootless_podman(self) -> None:
        self.assertEqual(
            select_capabilities(("python", "shell"), "sqlite", github=True, rootless_podman=True),
            (
                "base.tooling", "optional.github-cli", "language.python", "language.shell",
                "database.sqlite", "sandbox.rootless-podman",
            ),
        )
        self.assertEqual(
            select_capabilities(("unknown",), "none", github=False),
            ("base.tooling",),
        )

    def test_catalog_validation_and_unknown_ids_are_explicit(self) -> None:
        require_complete_provider_catalog("complete", CAPABILITY_CATALOG)
        with self.assertRaisesRegex(ValueError, "missing"):
            require_complete_provider_catalog("partial", ("base.tooling",))
        self.assertEqual(unknown_capability_ids(("language.python", "unknown.value")), ("unknown.value",))


if __name__ == "__main__":
    unittest.main()
