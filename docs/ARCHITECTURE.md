# Architecture

## Design

The kit is a single Python 3.11+ package with no runtime dependencies outside the standard library. It has one external AI boundary: the official OpenAI Codex CLI.

- `cli.py` parses subcommands and coordinates generation, validation, Codex account setup, optional GitHub setup, and launch.
- `wizard.py` owns the ordered Guided/Advanced project-setup state machine, host/provider/cache orchestration, and final generation approval while preserving established imports.
- `entry_modes.py` owns the shared typed Guided/Advanced presentation policy; it is not project domain state.
- `task_composer.py` owns task kinds, relevant questions, strict non-secret answer validation, the CLI/GUI-neutral task packet, and its typed review/approval contract.
- `recommendation_cache.py` owns private, structured-only advisor cache keys, validation, and atomic persistence.
- `agents.py` is the Codex process boundary. It invokes documented CLI commands and never reads token files, browser state, or keyrings.
- `models.py` keeps public serializable configuration exports; `config_schema/` owns strict parsing and ordered migration, while `model_policy.py` owns exact/display model selection.
- `capabilities.py` is the package-name-free catalog of project toolchain, database, optional, and sandbox intent; provider maps must cover it exactly.
- `doctor.py` owns typed provider-first readiness findings, redacted JSON serialization, and text rendering; `cli.py` remains the public command delegate.
- `diagnostics.py` owns the stable presentation-neutral error result, conservative exception/status mapping, display redaction, and private bounded GUI diagnostic log; adapters retain established compatibility fields.
- `policy_fragments.py` owns the five durable generated-policy statements, owner references, exact four-statement Codex deployment boundary, and deterministic conflict findings. `AGENTS.md` renders the full boundary once; every task packet and approved task prompt carries the same typed tuple, while other prompts render owner references only.
- `deployment.py` owns the immutable supported-target vocabulary and current operation contracts with strict exact-ID parsing. Static-site and Linux-service-bundle enable deterministic local build; OCI/SSH do not. The contract contains no CLI, project-command runner, network, credential, remote-write, push, or apply boundary.
- `deployment_plan.py` owns strict bounded target profiles, confined metadata/profile reads and immutable output paths, fixed local Git source-state inspection, canonical plan serialization, and SHA-256 digests. It never executes profile argv, reads credential values, or performs build/check/network/remote/apply actions; `cli_app/deployment_commands.py` is its thin nested-command adapter.
- `deployment_check.py` owns strict immutable-plan loading, digest/schema verification, bounded symlink-refusing local artifact checksums, explicit passed/failed/unverified findings, and non-authorizing JSON/text reports. It runs AgentKit structural validation and fixed local source inspection but no project command, build, target adapter, credential query, network request, write, or apply.
- `deployment_build.py` owns bounded deterministic ZIP assembly, clean plan/source binding, normalized entries, double-build comparison, embedded provenance/SPDX inventory, self-verification, and atomic create-only output. It reads only a reviewed non-root source path and executes no profile/project command or external builder.
- `deployment_secrets.py` owns the exact reference-only mechanism registry, shared reference-name validation, metadata-only environment-file/SSH-agent checks, and explicit external-store unverified findings. It never opens a secret file, lists keys, contacts a store, or serializes a value.
- `deployment_gate.py` owns the pure P6-007 prerequisite state model: exact plan/check/artifact/identity bindings, target-tool human-authentication evidence, separate local typed-confirmation evidence, rollback, redacted audit metadata, and approval invalidation. Current contracts expose no apply adapter, the module has no CLI or persistence boundary, and it performs no command, credential, network, target, write, remote change, or apply.
- `deployment_ci.py` owns immutable official-action pins, review date/source evidence, offline stable-code reference validation, and the fail-closed future deployment CI identity, permission, job/environment-separation, production-approval, checksum, and attestation contract. It adds no deploy job, credential, target adapter, network path, or apply authority.
- `deployment_staging.py` owns the static-site-only disposable in-memory staging rehearsal. It requires clean digest-bound passing plan/check/artifact evidence, rejects production/wrong/stale targets, always restores prior state, and emits closed redacted events. It has no CLI, generated-script, filesystem, command, credential, network, remote-target, or production boundary.
- `structure/policy.py` owns strict advisory thresholds, supplied measurements, reviewed size exemptions, non-blocking findings, and evaluation.
- `structure/audit.py` owns bounded read-only Python traversal, AST/token measurements, likely responsibility grouping, import-cycle/delta analysis, strict project-confined baselines, and human/JSON rendering. It never imports target modules or writes a baseline; `cli.py` remains the public command delegate.
- `context_budget.py` owns bounded read-only generated-context measurements, duplicate paragraph fingerprints, default first-prompt file routing, suggested targets, and human/JSON rendering. Findings are always advisory and cannot block generation, validation, or launch.
- `draft_sessions.py` owns private, bounded, partial GUI project/task presentation state, atomic persistence, restart-safe loading, discard, and no-replace export.
- `performance_checks.py` owns standard-library representative generation timing/peak-allocation measurements and their conservative maintainer budgets; it has no runtime launch, network, provider, or installation authority.
- `platforms/` defines the redacted `HostProfile`, argv-only package plans, provider protocol, deterministic detection, and CachyOS/Arch plus Debian/Ubuntu providers.
- `toolchains.py` maps selected languages/databases to capability IDs, known commands, ignore entries, and CI setup; existing Arch package views delegate to provider capability records and official CI action references delegate to the immutable pin registry.
- `templates.py` is the compact compatibility export for generated artifact families plus the established Codex-config and bootstrap delegates.
- `cli_app/information_commands.py` owns parser registration and handlers for read-only `example-answers` and `toolchains`; `cli.py` directly re-exports both handlers and remains the public parser/dispatcher.
- `cli_app/inspection_commands.py` owns position-preserving parser registration and handlers for read-only workspace validation, advisory structure audit, and redacted host/Codex doctor output; domain reports remain in their canonical modules.
- `cli_app/skill_commands.py` owns nested `codex` skill-management registration and status/install/update/uninstall presentation; `codex_skill.py` retains confined atomic writes, backups, managed-file recognition, and user-content refusal.
- `cli_app/sandbox_commands.py` owns nested sandbox registration and doctor/preflight/clean presentation; callbacks keep parser presentation separate from orchestration and command execution.
- `cli_app/project_runtime.py` owns generated metadata loading and logged/unlogged project-command execution shared by sandbox, launch, readiness, and cleanup paths.
- `cli_app/sandbox_orchestration.py` owns generated-input fingerprints, atomic preflight stamps, freshness state, Podman image-ID inspection, and host-side doctor/build/check sequencing; `cli.py` directly re-exports these APIs for launch/status and compatibility callers.
- `cli_app/readiness_commands.py` owns local workspace/Git/Codex/sandbox/ignore/CI evidence presentation, GitHub-readiness gating, and explicit local/SSH rsync mirror planning/execution. It never creates GitHub resources or pushes, and mirror execution requires `--run` after the exact argv is shown.
- `cli_app/prompt_commands.py` owns typed bounded continuation deltas, continuation templates/rendering, interactive question presentation, explicit edit/approve review, parser registration, and no-replace output handling. Deltas name objective, changes, failures, exact references, acceptance, and unresolved decisions while excluding unrelated historical rereads. `task_composer.py` remains the canonical typed question/packet/contract/approval domain and `policy_fragments.py` remains the durable policy-reference owner.
- `cli_app/local_model_commands.py` owns assessment-only Ollama list/show parsing, context/coding heuristics, conservative best-model selection, explicit override presentation, and local handoff rendering. It reuses the canonical continuation renderer and Sol model policy but creates no alternate adapter, authentication, or launcher.
- `cli_app/agent_commands.py` owns official Codex installation/authorization presentation and validated project launch. Launch strictly loads Codex-only metadata, validates the workspace, runs active sandbox preflight, then reaches adapter authorization/process methods; container kickoff delegates only to the generated confined runner.
- `cli_app/generation_commands.py` owns answers-file normalization and safety screening, generation-result presentation, explicit interactive GitHub-remote handoff, and `new`/`init`/`generate` registration. Canonical schema parsing, safe project writes, wizard collection, and Codex launch remain in their established owners and are imported across explicit boundaries.
- `guided/questions.py` owns reusable credential-safe input, confirmation, single/multiple-choice, list, slug, language, and database presentation primitives.
- `guided/advisor.py` owns the redacted advisor snapshot/prompt, recommendation presentation and explicit capability decisions, conservative offline recommendation, and explicit Codex readiness flow. `wizard.py` directly re-exports the established helper names and retains host detection, provider/cache selection, and the overall state-transition order.
- `generation/registry.py` owns the deterministic managed-artifact catalog, required/executable file contracts, generated Codex/note helpers, redacted project metadata rendering, and manifest hashes. `generator.py` remains the compatibility surface and owns path confinement, atomic safe-write orchestration, conflicts/proposals/backups, optional local Git initialization, mutation observation, and validation invocation.
- `generation/validation.py` owns the read-only generated-workspace report and ordered validation pass over required files, metadata redaction indicators, agent workflow references, ignore policy, bounded shell syntax, CI permissions/entry point/immutable action pins, manifest shape, and pending proposals. `generator.py` directly re-exports its established report/helper/function names.
- `.github/workflows/ci.yml` keeps the full source check on the native Ubuntu Python 3.11/3.13/3.14 matrix and delegates only provider/generation plan smoke to a separate Debian/Arch container job. Container execution is focused, network-off, capability-dropped, and read-only rather than a duplicate full suite.
- `pyproject.toml` owns constrained maintainer-only quality extras/configuration; `scripts/quality-check.sh` is their explicit no-install gate. Runtime dependencies remain empty, and `scripts/check.sh` stays the dependency-free trusted baseline.
- `scripts/package-smoke-test.sh` owns isolated source-artifact discovery/import/entry-point/generation validation, while `install.sh`, `uninstall.sh`, and `scripts/install-smoke-test.sh` own user-local installation markers, legacy adoption, atomic managed replacement, and unowned/symlink refusal.
- `generation/service.py` owns the complete confined generation transaction: canonical reparse, safe-root and relative-path checks, symlink-parent refusal, timestamp reuse, per-artifact create/unchanged/proposal/backup handling through atomic replacement, explicit bounded local Git initialization, mutation observation, and post-write validation. `generator.py` is the compatibility facade over registry, service, and validation.
- `template_sets/architecture.py` owns architecture guidance plus the modularity contract shared by `AGENTS.md` and `docs/02-ARCHITECTURE.md`; `template_sets/common.py` owns deterministic Markdown formatting primitives; `template_sets/licenses.py` owns license rendering and the verbatim AGPL payload; `template_sets/orientation.py` owns the three human entry/next-action documents; `template_sets/navigation.py` owns the human documentation map and task-routed agent index; `template_sets/project_memory.py` owns progress, decisions, implementation notes, handoff, and open questions; `template_sets/project_definition.py` owns the brief, requirements, and phased implementation plan; `template_sets/technology_environment.py` owns stack/environment guidance and reviewed/default command selection; `template_sets/quality_risk.py` owns testing, security/privacy, and UX/accessibility acceptance guidance; `template_sets/agent_guidance.py` owns binding agent policy, advisory review, and first-work prompting; `template_sets/release_operations.py` owns release/operations/contribution/security governance; `template_sets/script_workflows.py` owns local generated workflow scripts and GitHub CI; `template_sets/shared_sections.py` owns optional skill/sandbox sections reused across document families; `template_sets/repository_support.py` owns ignore, mirror-exclusion, environment-example, and editor-default artifacts; `template_sets/bootstrap.py` owns provider-specific host bootstrap rendering. `templates.py` directly re-exports moved public names and compatibility helper attributes.
- `sandbox.py` renders optional rootless Podman sandbox files and read-only sandbox diagnostics.
- Generated `docs/16-DEPLOYMENT.md` is rendered by the release/operations template family from the typed deployment registry. It selects no target and grants no network/credential/remote-write/push/apply authority; it documents digest-bound planning, checking, and the narrow deterministic local builder.
- `generator.py` preserves established generation/validation imports while delegating to the cohesive generation package.

`ollama-check` is an assessment-only local-model handoff gate. It inspects installed Ollama model metadata and can generate a warning-rich handoff prompt, but it does not add an alternate agent adapter, generated launcher, authentication path, or Codex configuration rewrite.

Optional rootless Podman sandbox support is generated project infrastructure, not an orchestration layer. It can create project-scoped toolchain/test scripts and explicit Codex-inside-container launch helpers, but it does not run Podman during generation, install host packages, mount host credentials, copy Codex sessions, or change the Codex-only agent invariant.

## Data flow

```text
interactive answers or reviewed JSON
                |
                v
       ProjectConfig (non-secret)
                |
                +--> optional Codex read-only advisor
                |          |
                |          v
                |   validated JSON recommendation
                |   (commands remain advisory)
                v
          template file map
                |
                v
 safe writer / proposals / backups / manifest
                |
                v
     generated workspace validation
                |
                v
 optional official Codex OAuth and project launch
```

The `primary_agent` metadata field is a fixed `codex` invariant, not a client-selection mechanism. It lets validation reject workspaces from incompatible editions instead of attempting an unsafe launch.

## Trust boundaries

Untrusted inputs include terminal answers, answers JSON, existing files, model output, project paths, and tool output. Privileged or external boundaries include `sudo pacman`, Codex OAuth/browser handling, GitHub network operations, and Codex tool execution inside a generated project.

Authority is minimized by generating and validating before launch, requiring explicit approval for system installation, using Codex sandbox/approval settings, keeping advice calls read-only, and delegating all account credentials to the official client.

Guided and Advanced are presentation policies over the same configuration domain. CLI compatibility keeps Advanced as the no-flag behavior; the beginner GUI defaults to Guided. Guided suppresses only nonessential implementation questions and assigns documented conservative values. It never hides security/data classification, project identity, stack acceptance, license, Git, final generation review, or later per-capability approvals. Advanced exposes the full established controls but cannot bypass canonical parsing, validation, conflict/proposal behavior, or command/package approvals. Entry mode is deliberately not serialized.

The task composer is a separate non-executing domain seam. Each typed task kind owns an ordered question set; CLI and GUI submit answer maps to the same closed, bounded, credential-rejecting validator and receive the same immutable packet. One deterministic builder turns that packet into the five-section review-required contract. Editing recollects and revalidates answers; explicit approval returns an immutable approved prompt value. Neither state is execution authority: the composer does not inspect the repository, implicitly persist drafts, launch Codex, or execute commands. Deployment tasks remain planning-only. The separate draft store retains incomplete presentation data only; launch preview and execution remain later boundaries.

Plain-language backend diagnostics have one immutable seven-field shape: code, severity, title, explanation, project-change state, safe next action, and bounded redacted technical details. Every GUI backend operation catches exceptions at its adapter boundary; failed generation/validation/launch statuses also receive stable codes. A private generator mutation observer fires only after successful project-root, managed-file, proposal, backup, permission, or Git changes, so exception diagnostics use observed AgentKit mutations rather than guessing from exception text. A nonzero Codex process is conservatively marked changed because external editing may have occurred and the safe remedy requires inspection.

Exception mapping never serializes tracebacks, subprocess argv, filesystem paths, or secret-like values. GUI `ok`/`error` compatibility keys remain while canonical diagnostics are attached. The desktop launcher injects a private best-effort JSONL log under XDG state; direct bridge/library use does not create a log unless one is explicitly injected. Logging re-redacts all fields, rotates at a bound, refuses symlinks, and cannot change an operation result.

Draft sessions deliberately have a separate schema from `ProjectConfig` and `TaskPacket` because incomplete form state is not valid or approved domain state. The schema is closed to existing GUI fields and relevant partial task answers, strictly typed, bounded, and credential-rejecting. User-local storage uses 0700 directories, 0600 files, bounded reads, symlink refusal, and existing atomic create/replace primitives. Resume only repopulates controls; generation and task approval still traverse their canonical validators. Export is explicit, no-replace, private, and does not discard the source draft.

GUI accessibility stays in the local presentation layer and does not alter domain authority. Native buttons/inputs/selects/textareas provide keyboard operation; the generated step list is button-based with visible and `aria-current` state; page and Guided-decision transitions manage focus; status regions and diagnostics expose textual state to assistive technology; and a skip link bypasses navigation. Reviewed remediation commands render with `textContent` as selectable code plus a clipboard-only action. Consequence-specific confirmations wrap prompt release, permanent draft deletion, and generation, while launch preview/validation policy remains a separate boundary.

GUI launch is a two-step bridge boundary. Preview validates the selected generated root, strictly loads its canonical project metadata, and verifies the actual project-local Codex TOML against the centralized workspace policy and selected model policy. Its immutable summary distinguishes exact model ID from display label and inherited-global selection, and includes project/Codex sandbox, approval, project-network, command-network, web-search, execution-location, and target fields. A bridge-local fingerprint records the displayed review. Launch requires that current fingerprint, repeats validation/policy parsing, compares the recomputed summary, consumes the review before closing the window, and blocks on missing/stale review or any validation/policy error.

The shared `launch_agent()` boundary independently calls full project validation after strict metadata loading and before sandbox preflight, adapter lookup, authorization, or process launch. This preserves CLI/GUI defense in depth even when the GUI review layer is not involved.

When enabled, the rootless Podman sandbox adds a second containment layer for project toolchain work. It still treats the project bind mount as writable user data, keeps host secrets unmounted by default, and documents that containers reduce host filesystem risk without making untrusted code safe.

## Architecture decision — local model handoff gate

The Codex-only edition may help a user evaluate whether an installed Ollama model is likely to continue a project safely, but Codex remains the only built-in launch and authorization path. The local-model gate must:

- inspect only local Ollama metadata unless the user separately runs Ollama;
- require confirmed context length and coding-capability signals before treating a model as suitable, using the explicit `gpt-5.6-sol`/medium quality policy as the baseline rather than assuming local parity;
- refuse handoff-prompt generation for borderline or inadvisable models unless `--override` is supplied;
- preserve warnings inside generated local-model handoff prompts;
- avoid editing `.codex/config.toml`, generated `START_AGENT.sh`, generated helper scripts, project metadata `primary_agent`, or Codex OAuth behavior.

This keeps local-model experimentation explicit and reversible without making generated projects unusable for the supported Codex workflow.

## Architecture decision — platform provider boundary

Platform work begins with data and authority boundaries before detection. `HostProfile` contains only OS identity metadata, architecture, a selected provider identifier, explicitly queried executable facts, rootless-Podman prerequisite status, and project-selected language/target facts. Its advisor export is an allowlist; it cannot represent usernames, hostnames, home paths, network addresses, environment dumps, shell history, credential/browser state, SSH configuration, or an unrelated installed-package inventory.

`PlatformProvider` separates detection confidence, installed-package state, repository availability, capability resolution, rootless-Podman checks, executable naming, and safe documentation labels. Update and install operations are returned as `ArgvPlan` values with explicit network/privilege flags. The interface never executes those plans and never converts them to shell text.

Detection parses bounded `/etc/os-release` assignments, uses `ID`/`ID_LIKE` before executable evidence, obtains architecture through Python's platform interface, and checks only the expected package-manager executable. It distinguishes supported, partial, unsupported, and unknown hosts. Executable presence alone never selects a family. A reviewed override must pass its executable proof and stays marked contradicted when OS metadata points elsewhere.

The Arch provider owns the preserved CachyOS package mappings as capability records. Its only executable operations are validated read-only `pacman -Qq` and `pacman -Si` queries. System update and verified official-package installation remain non-executing argv plans. Manual/AUR records are always unverified and non-installable; no AUR helper is selected or invoked.

One data-driven Debian-family provider handles Debian and Ubuntu flavor identities. It uses validated `dpkg-query` installed-state and local `apt-cache policy` candidate queries. `apt-get update` index refresh is a separate argv plan from `apt-get install`; neither performs a distribution upgrade or changes configured sources. Flavor differences and executable aliases such as `fd` to `fdfind` are data. Third-party records require explicit source, key, pinning, and removal review text and remain unverified/non-installable.

## Architecture decision — canonical capability intent

`agent_starter.capabilities` names only provider-neutral intent and contains no package names. It covers current base tooling, optional GitHub/ShellCheck tools, supported language strategies, selected databases, and rootless-Podman prerequisites. Toolchain selection and advisor output use these IDs. Arch and Debian-family catalogs are import-time checked for exact key coverage, while package names and executable aliases stay provider-owned.

The old `packages_for()`, `Toolchain.packages`, and Arch package constants remain compatibility delegates. Saved `advisor.toolchain_packages` values still load as documentation-only Arch intent, but new advisor schemas require canonical `toolchain_capabilities`; strict configuration parsing rejects unknown IDs and non-list types. Sandbox image and Podman prerequisite package lists now resolve capability IDs without changing generated Arch output.

## Architecture decision — structured doctor

`agent_starter.doctor` consumes metadata-first detection before selecting a provider. Findings have stable codes and one of `pass`, `action-needed`, `optional`, `blocked`, or `unverified`, plus a capability ID where applicable, plain-language purpose, safe remedy, and bounded evidence. Text and JSON render from the same report. The JSON host section is a redacted allowlist and never includes executable paths or user/host identity.

Doctor asks the selected provider only for installed state of the required `base.tooling` packages: validated `pacman -Qq` queries on Arch-family hosts or validated `dpkg-query` queries on Debian/Ubuntu. If the provider executable is absent, package queries are skipped. Doctor never calls repository-availability checks, builds or runs update/install plans, refreshes indexes, changes sources, or treats `pacman` as a Debian/Ubuntu requirement. Its compatibility exit code remains nonzero only for a blocked platform selection; actionable or optional tool findings remain report data.

## Architecture decision — generated provider bootstrap

Generated `scripts/bootstrap-dev.sh` detects CachyOS/Arch, Debian, or Ubuntu at runtime from bounded `ID`/`ID_LIKE` fields, or accepts an explicit reviewed provider override and then proves the matching manager exists. Host provider selection is independent of project target platforms and the sandbox image profile. Package arrays are derived from the canonical capability selection plus provider-owned mappings and provider-scoped extras; v1 extras enter only the Arch array.

The supported-host contract and rootless prerequisites are summarized in `docs/SUPPORTED-HOSTS.md`. File-backed OS fixtures and `tests/fixtures/provider-package-plans.json` are the reviewed compatibility matrix. Optional container verification is no-pull/no-network and requires preloaded official images; normal checks remain deterministic and container-independent.

## Architecture decision — advisor host disclosure

The first host-aware advisor seam reuses the immutable `HostProfile` allowlist. The wizard enriches it only with project-selected languages and targets, renders one stable JSON representation, shows that exact representation to the user, and embeds the same text in the read-only advisor prompt. It does not persist the snapshot, serialize arbitrary host state, or enumerate unrelated packages.

## Architecture decision — capability-first advisor contract

Live advisor JSON is closed and bounded. It contains summary, language/database hypotheses, nested logical capability recommendations, architecture notes, risks, and questions. Nested items accept only canonical capability IDs plus purpose, required/optional intent, rationale, and high/medium/low confidence. Package names and command arrays are not schema fields. Strict parsing occurs before constructing `AdvisorRecommendation`; flat capability IDs are derived only as a compatibility view. Old saved package/command fields remain readable but never become part of the live contract.

The shared text parser also rejects high-signal command substitution/pipeline syntax, privileged or destructive commands, download-to-shell content, credential-exfiltration requests, and prompt-injection directives. It returns only a bounded error category and does not repeat the hostile text. Normal security analysis is still representable. Rejection happens before caching, provider resolution, recommendation construction, or any subprocess boundary.

## Architecture decision — non-executing recommendation pipeline

`agent_starter.recommendation` owns one ordered join: final project stack to deterministic canonical capabilities, optional validated advisor additions, provider-owned package resolution, configured-repository verification, exact-candidate installed-state comparison, and plain-language review. Advisor omission cannot delete the deterministic baseline. Unknown advisor IDs remain visible and unresolved; unsupported hosts never fall back to Arch. The seam calls no provider update/install-plan method and stores no package name, argv, or raw advisor payload.

Review provenance is a typed, ordered set because one need may be deterministic, AI-suggested, and user-requested simultaneously. Each immutable capability item carries its reason, confidence, selected provider, unresolved questions, and provider-owned package evidence. Package evidence retains verification, installed state, official/manual authority, installability, and provider explanation. Rendering exposes those fields directly rather than collapsing them into a generic status; manual-review candidates remain unverified and outside official package queries.

`CapabilityDecision` is project-owned state at the top of `ProjectConfig`, not part of `AdvisorRecommendation`. Optional items accept `accepted` or `rejected`; required items accept `accepted` or `challenged`, and challenges require a bounded limitation explanation. Canonical loading rejects unknown IDs, duplicate records, unknown fields, invalid state/requirement combinations, and attempts to relabel deterministic baseline needs as optional. The compatibility capability list contains accepted IDs only. Generated advisory documentation renders all decisions but explicitly grants no package or command authority.

`AdvisorRecommendation.review_mode` derives a conservative provenance label from the persisted source. `local-fallback`, manual selection, and provenance-unknown saved data are never labeled AI-reviewed. A successful live advisor source is labeled `AI-reviewed structured recommendation`. The same property drives terminal and generated-document output. Offline fallback then follows the identical deterministic provider review and decision pipeline, so absence of Codex changes provenance—not generation completeness or safety authority.

## Architecture decision — structured recommendation cache

`agent_starter.recommendation_cache` stores only a recommendation re-parsed through the closed live advisor contract. It discards raw output and has no package or command fields. Its SHA-256 key covers canonical project intent, including stack choices, plus only OS ID/lineage/version, architecture, and selected provider; it includes no host label, path, or identity. Cache entries use private permissions, bounded reads, symlink refusal, and atomic replacement. The wizard announces hits and exposes a default-off refresh choice; a malformed entry fails closed and never prevents a fresh live request or deterministic fallback.

Performance/resource checks treat generation measurements as per-run evidence rather than product benchmarks. Fresh and
renovation profiles are temporary and retain normal generator safety. GUI help imports only the thin launcher; bridge,
diagnostics, and pywebview imports occur on actual launch. Recommendation package candidates are deduplicated into one
availability and one installed-state batch, while doctor is restricted to its fixed executable allowlist and the selected
provider's bounded `base.tooling` mapping rather than whole-system inventory.

Sandbox generation likewise treats the image as explicit project policy: `arch-toolchain` and `debian-toolchain` are the only tested profiles. Neither host detection nor target-platform metadata silently changes that choice. Both profiles use the same rootless `keep-id` runtime ownership contract; the image does not make `/home/codex` world-writable, and Codex mode relies on its project-scoped named volume's Podman ownership adjustment.

Default bootstrap performs validated read-only installed-state queries and prints argv arrays without mutation. It omits installed packages. `--install` is the only installation action. Debian/Ubuntu `--refresh` is a separate `apt-get update` action so networked metadata refresh cannot be hidden inside installation. Arch refresh is refused, and no `pacman -Syu`, APT upgrade, repository source/key/pinning mutation, AUR helper, or AI-produced command enters the host plan.

## Architecture decision — schema v2 and first extraction seams

All untrusted configuration boundaries use `agent_starter.config_schema.parse_config`, which returns structured field/code/message/remedy issues and performs ordered v1-to-v2 migration. v1 `cachyos_packages` is retained only as Arch-family intent. `agent_starter.cli:main` and `agent_starter.templates` remain compatibility surfaces while config migration commands and Codex templates delegate to cohesive subpackages. New subpackages are included through controlled setuptools discovery.
