# Performance and resource checks

Run the focused standard-library gate from the repository root:

```bash
./scripts/performance-resource-check.sh
```

The runner emits schema-versioned JSON measurements, then runs the resource regression tests. It creates two temporary representative workspaces: a fresh Python/SQLite CLI and an existing PHP/JavaScript/MariaDB web renovation with sandbox and CI output. Each profile must generate successfully within 10 seconds and 128 MiB peak Python allocation. These are conservative regression budgets for supported CI hosts, not product speed claims; the emitted elapsed and peak values are the observation for that run.

The accompanying tests also require:

- `agent-starter-gui --help` imports neither the GUI bridge nor `pywebview`; the bridge, diagnostics, and optional desktop dependency load only for an actual GUI launch;
- a valid structured recommendation cache can be read without invoking Codex or a package provider;
- one recommendation review resolves capabilities once and performs one deduplicated availability batch and one installed-state batch;
- doctor looks up only its fixed executable allowlist and queries only the provider mapping for `base.tooling`, never a full installed-package enumeration.

The gate installs nothing, contacts no network, invokes no Codex process or package manager, and reads no host package inventory. Provider calls use synthetic injected runners. Measurements are temporary-directory confined and preserve normal conflict/proposal behavior for the renovation profile.

When changing budgets, profiles, caching, GUI imports, doctor, or recommendation queries, record the before/after measurements and justify the change in `docs/IMPLEMENTATION-NOTES.md`. Do not weaken a budget solely to hide an unexplained regression.
