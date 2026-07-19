# GPT-5.6-SOL migration report

## Release status and scope

This report compares the checked-in `0.4.8` / GPT-5.5-era baseline with the completed migration work through Phase 8 P8-003. Candidate preparation has since aligned the working source at `0.5.0`; this report remains a baseline comparison, not a stable-release announcement. P8-005 owns local candidate and user-submitted burn-in evidence.

The migration is incremental. Existing public commands, import surfaces, generated-project safety, standard-library runtime, and Codex-owned authentication remain compatibility requirements. See the [migration status](GPT-5.6-SOL-MIGRATION-STATUS.md) for task-by-task evidence and the [security model](SECURITY-MODEL.md) for binding trust boundaries.

## What changed from the v0.4.8 baseline

| Area | v0.4.8 / GPT-5.5-era behavior | Migrated behavior |
| --- | --- | --- |
| Model | A hard-coded GPT-5.5 complex-coding reference | Typed project policy defaults to exact `gpt-5.6-sol`, label `GPT-5.6-SOL`, and `medium` reasoning; reviewed override and inherited-global modes are distinct |
| Configuration | Mostly flat answers with permissive conversions and schema-v1 compatibility assumptions | One canonical schema-v2 parser validates CLI answers, JSON, GUI payloads, and generator input; issues carry field path, stable code, explanation, and remedy |
| Linux platforms | CachyOS/Arch package assumptions dominated host behavior | Provider-neutral capabilities resolve through tested CachyOS/Arch, Debian, or Ubuntu providers; sandbox image policy remains an independent explicit choice |
| Recommendation | Advisor data could contain package names and suggested command arrays | Live advice is closed, bounded, capability-first intent; deterministic providers own package mapping and executable argv; every item gets evidence and an explicit human decision |
| User workflow | One large advanced wizard and thinner error/draft handling | Guided and Advanced presentations share the same schema and approvals; CLI compatibility keeps Advanced as the no-flag default; GUI adds bounded diagnostics, private drafts, accessibility, and two-step launch review |
| Prompts and context | Repeated generated guidance and same-day prompt filenames could collide | Canonical policy fragments, human/agent indexes, task-routed context, strict task contracts, and collision-safe atomic prompt creation preserve earlier files |
| Modularity | CLI, generator, wizard, and templates concentrated unrelated responsibilities | Cohesive `cli_app`, `config_schema`, `generation`, `guided`, and `template_sets` modules own real seams while established public facades re-export or delegate |
| Packaging | A fixed setuptools package list could omit new subpackages | Controlled discovery plus isolated wheel and sdist installation verifies every source module, public imports, CLI help, generation, and validation |
| Deployment | No typed deployment evidence workflow | Strict local plan/check/build evidence, reference-only secret metadata, a fail-closed future gate, and disposable in-memory staging rehearsal exist; no real target or apply route exists |
| Supply chain | Ordinary checks had less explicit artifact/release separation | Reviewed immutable action/image identities, native and provider CI, checksums/SPDX/provenance, installer ownership, and a manual exact-tag release workflow separate verification from publication authority |

Unchanged safety promises are as important as the additions: unsafe roots and path escapes reject; symlink parents reject; writes remain atomic; existing-file conflicts become proposals; forced replacement creates a backup; custom commands require explicit approval; package installation, remote creation, push, release, and deployment remain explicit human actions; AgentKit never reads Codex credentials.

## Model selection

The default explicit policy is:

- provider: `openai`
- exact model ID: `gpt-5.6-sol`
- display label: `GPT-5.6-SOL`
- reasoning effort: `medium`
- selection: `explicit`
- fallback behavior: `ask`

The exact ID and display label are separate fields. A reviewed explicit override keeps its exact ID. With `selection: "inherit"`, generated project configuration omits model and reasoning keys so the user's global Codex policy remains authoritative. If an explicit model is unavailable, AgentKit never silently downgrades it: launch returns an actionable message asking the human to choose inherited-global policy or review another exact model.

Generated `.codex/config.toml` retains conservative supported policy: approval `on-request`, sandbox `workspace-write`, command network access off, and web search `cached`. GPT-5.5 is historical context only; it is not a current recommendation or generated baseline.

## Schema-v1 to schema-v2 migration

Schema v2 is current. All untrusted entry points use the same parser for strict JSON booleans, enums, bounded strings/lists, paths, package identifiers, model policy, advisor records, and custom commands. A string such as `"false"` is invalid where a JSON boolean is required; it is never converted with generic truthiness. Unknown top-level fields remain warnings for forward compatibility, while invalid known data fails with structured issues.

Migration is ordered and non-destructive:

```bash
agent-starter config migrate --input answers-v1.json
agent-starter config migrate --input answers-v1.json --output answers-v2.json
```

The first command prints a dry-run preview. The second creates a separate new file. It refuses to overwrite the source or an existing destination.

The v1 `cachyos_packages` list becomes `extra_packages_by_provider.arch`, preserving order and removing duplicates. Those names are never translated, guessed, or copied into Debian or Ubuntu package intent. Missing model policy becomes the reviewed schema-v2 default. Existing recognized project values remain loadable; custom executable arrays still require the separate `--allow-custom-commands` approval when generating.

Loaded legacy advisor package and setup/build/test/lint command fields remain documentation-only compatibility data. They never enter the live advisor schema, provider query, install plan, or automatic execution path. New advisor data uses canonical capability records and separately stored human decisions.

## Debian and Ubuntu support level

The supported host matrix covers CachyOS, Arch Linux, Debian, and Ubuntu. Debian and Ubuntu share one data-driven provider with distinct identities. Support includes:

- bounded `/etc/os-release` detection plus proof of `apt-get` and `dpkg-query`;
- structured doctor findings using read-only installed-state queries;
- provider-owned official-package mappings for the canonical capability catalog;
- generated review-only bootstrap arrays, with explicit install and separately explicit APT refresh modes;
- representative generation/validation journeys for both providers;
- rootless Podman prerequisite guidance and an explicit host-independent `debian-toolchain` image profile;
- native Ubuntu full-suite CI and focused no-network Debian/Arch preloaded-image checks.

The boundary is deliberately conservative. AgentKit uses only already configured official APT sources, never adds PPAs, signing keys, source entries, or pinning, and never performs a distribution upgrade. Third-party records remain manual, unverified, and non-installable. Default doctor/bootstrap behavior is read-only. Container verification never pulls implicitly and skips when reviewed images are not preloaded. CachyOS/Arch remains the primary beginner-oriented documentation path, but Debian/Ubuntu provider behavior is tested rather than best-effort guessing.

Sandbox image profile does not follow host detection: a Debian host may review `arch-toolchain`, and an Arch host may review `debian-toolchain`. Project target platforms also do not select a host package provider.

## Compatibility and deprecation timeline

For this policy, **T0** means the first stable release containing the GPT-5.6-SOL migration. **T+1** means the next minor stable release after T0. P8-005 must keep the compatibility shims through T0 and T+1. No removal may occur before a later major release, and then only with a changelog notice, a replacement path, migration fixtures, artifact/import tests, and a separately reviewed decision.

| Surface | Current status | Replacement | Earliest possible removal |
| --- | --- | --- | --- |
| Answers `cachyos_packages` | Deprecated for newly written schema-v2 answers; still accepted/migrated | `extra_packages_by_provider.arch` | A future schema v3 in a major release after T+1, subject to the gates above |
| Saved `advisor.toolchain_packages` | Legacy/deprecated for new advisor data; readable as documentation-only data | `advisor.recommended_capabilities` plus provider resolution | A future schema v3 in a major release after T+1, only with a converter preserving the text as non-executable history |
| Saved advisor `setup_commands`, `build_commands`, `test_commands`, `lint_commands` | Legacy/deprecated for new advisor data; readable as documentation-only data | Deterministic provider plans and reviewed project-owned commands | A future schema v3 in a major release after T+1, only with explicit historical-data preservation |

No public Python module or CLI command is formally deprecated by this migration. `agent_starter.cli:main`, `agent_starter.templates`, `agent_starter.generator`, and `agent_starter.wizard` remain supported compatibility facades. The old `packages_for()`, `Toolchain.packages`, Arch package constants, template renderer names, and directly exported CLI helpers are compatibility views with no scheduled removal. Internal ownership moving to cohesive subpackages is not itself a deprecation.

If any facade, command, flag, or compatibility view is formally deprecated later, the project must announce it at least at T0-equivalent timing and preserve it through the following minor stable release before considering a major-version removal. P8-005 may extend this window based on user-submitted issues; it may not shorten it.

## Recommendation, deployment, and release boundaries

Capability recommendations remain untrusted intent until provider verification and explicit per-item human review. They never authorize a package command. Offline fallback is complete but labeled as not AI-reviewed; structured cached advice is private, bounded, revalidated, and contains neither raw transcripts nor host identity.

Deployment support stops at local evidence. There is no `deployment apply` command, production adapter, generated deploy script, remote staging path, or free-form prompt authority. Plan/check/build results do not authorize a target operation. Secret handling accepts reference names and bounded metadata only, never secret values.

This report does not justify a stable release by itself. P8-005 must run the exact release-candidate gates, retain the compatibility window, collect only user-submitted issues without default telemetry, and fix material migration/provider/packaging/safety regressions before a stable release is considered.
