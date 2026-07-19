# Changelog

## Unreleased

## 0.5.1 — 2026-07-19

- Remove public links and package-manifest claims for intentionally private maintainer ledgers so clean source checkouts
  and release verification do not depend on files that are correctly excluded from Git.
- Preserve the failed, unpublished `v0.5.0` verification tag and use a new immutable corrective release version rather
  than moving or overwriting a remote tag.

## 0.5.0 — 2026-07-19

- Prepare a local unpublished 0.5.0 candidate with aligned version/changelog metadata, exact checksum/SPDX artifact
  evidence, isolated wheel/sdist smoke, explicit dirty-tree publication refusal, and user-submitted-only burn-in intake.
- Add the v0.4.8-to-GPT-5.6-SOL migration report covering typed model selection, non-destructive schema-v2 migration,
  tested Debian/Ubuntu support boundaries, compatibility facades, deprecated legacy data, and a minimum removal window.
- Add concise human, maintainer, agent, and operations documentation entry points with canonical-owner routing,
  current-command checks, link/anchor validation, and an explicit no-deployment-authority operations boundary.
- Add a checked-in seven-scenario existing-project fixture catalog covering clean/dirty repositories, owner conflicts,
  symlink refusal, older metadata, manually edited approval-gated answers, and advisory god-file hotspots without
  changing production generation behavior.
- Add isolated no-sudo installation plus complete synthetic fresh-user journeys for CachyOS/Arch, Debian, and Ubuntu,
  spanning doctor, recommendation review, generation/checks, tasks, Sol preview, optional sandbox output, local
  deployment plan/check/build, and v1 migration without executing package, Codex, Podman, or remote actions.
- Add schema-versioned representative generation time/peak-allocation checks, bounded doctor/recommendation query
  regressions, cache no-call coverage, and lazy GUI bridge/diagnostic loading for help-only use.
- Add one explicit standard-library security regression gate covering unsafe paths, credential-like answers, malformed
  types/package injection, AI command injection, prompt data preservation, GUI redaction, deployment evidence, and
  sandbox mount/network defaults without changing production behavior.
- Add a manual-and-exact-tag-bound release workflow with clean version/changelog/full-suite/exact-artifact gates,
  fixed-name checksum-verified transfer, draft-first GitHub publication, and write authority isolated to the final job.
- Add review-only dependency automation and pull-request dependency review; pin source CI actions and provider images,
  create no-replace SHA-256/SPDX wheel/sdist evidence, and attest tested GitHub-hosted builds with narrow permissions
  without enabling release publication or third-party host package sources.
- Expand supported-Python artifact smoke to separate wheel/sdist installs, both CLI entry points, complete discovered
  module presence/imports, and representative generation/validation; add fail-closed user installer ownership markers,
  compatible pre-marker adoption, managed reinstall, and unowned/symlink preservation tests.
- Add constrained maintainer-only Ruff, mypy, Bandit, and coverage extras plus an explicit no-install quality gate,
  while retaining empty runtime dependencies and the offline-useful standard-library trusted suite.
- Keep the source CI full-check matrix on native Ubuntu with Python 3.11, 3.13, and 3.14, and add one focused
  Debian/Arch container smoke that generates and validates representative projects before running only their
  review-only bootstrap plans in read-only, network-disabled containers.
- Formalize the reviewed GitHub Action update process with typed review-date/official-commit evidence and offline
  stable-code validation that rejects mutable, short, unknown, commentless, or registry-mismatched generated action
  references while retaining workflow-level `contents: read`.
- Add a static-site-only disposable in-memory staging rehearsal that requires clean digest-bound passing evidence,
  rejects production/wrong/stale targets, tests partial failure and exact rollback, emits closed redacted events, and
  remains unavailable to CLI/Codex/generated scripts and all real targets.
- Add a typed fail-closed deployment CI identity/provenance policy, pin every generated official GitHub Action to a
  reviewed full commit SHA, and document future job-scoped OIDC, minimal permissions, build/deploy separation,
  protected production approval, checksums, and attestations without generating a deploy job or apply path.
- Strengthen the generated Codex deployment boundary in `AGENTS.md` and every task packet: local code/docs/tests and
  sandboxed plan/check/build are allowed, while apply/push/publication/migration/secret access require a separate
  human-approved tool operation and free-form “deploy it” wording is never production authorization.
- Add a pure P6-007 apply-gate state model with exact plan/check/artifact/identity/human-authentication/typed-confirmation/
  rollback/redacted-audit bindings, stale-approval invalidation, and no apply-capable adapter, CLI, persistence, or side effect.
- Add a typed deployment secrets contract with centralized reference validation, metadata-only ignored/0600
  environment-file and SSH-agent-socket checks, explicit unverified external stores, and no secret-value access.
- Add `deployment build` for clean-revision-bound deterministic local ZIP assembly with double-build comparison,
  embedded provenance and SPDX-2.3 inventory, atomic no-replace output, and no command/network/push/apply authority.
- Add `deployment check` for strict digest-bound local project/source/artifact/readiness evidence with explicit
  unverified target/credential/reproducibility boundaries and no command, network, credential, target, write, or apply
  authority.

- Added generated guidance telling Codex to avoid creating or extending god files and to split code by responsibility once files mix unrelated concerns.
- Began the compatibility-preserving GPT-5.6-SOL migration with a typed Sol/medium policy, strict schema v2 parsing and v1 migration, cohesive CLI/template/safe-write seams, controlled package discovery, isolated artifact smoke coverage, and collision-safe idea prompts.
- Defined the redacted host-profile and review-only platform-provider contract as the first Phase 2 seam, without adding host detection or package-manager behavior.
- Added bounded CachyOS/Arch, Debian, and Ubuntu host detection with package-manager proof, explicit warned overrides, and no package-manager execution or package mappings.
- Added the CachyOS/Arch provider, moved preserved Arch package mappings behind capability records, restricted live queries to validated read-only pacman operations, and made AUR/manual records unverified and non-installable.
- Added one data-driven Debian/Ubuntu provider with official-package capability mappings, read-only dpkg/APT metadata queries, separate apt-get refresh/install plans, executable aliases, and non-installable third-party review records.
- Added one provider-neutral capability catalog, exact provider coverage checks, capability-only advisor output, strict loaded capability validation, and capability-backed sandbox package selection while preserving legacy Arch package APIs and output order.
- Reworked `doctor` into provider-first structured findings with stable PASS/action/optional/blocked/unverified states, redacted `--json` output, and read-only provider-appropriate installed-package checks that never treat `pacman` as a Debian/Ubuntu requirement.
- Replaced the generated Arch-only bootstrap with a runtime-detected CachyOS/Arch, Debian, and Ubuntu plan that omits installed packages, is non-mutating by default, keeps APT refresh separate from explicit installation, and never performs a full-system upgrade.
- Added explicit, host-independent `arch-toolchain` and `debian-toolchain` sandbox image profiles and removed world-writable `/home/codex` image permissions while preserving project-scoped volume ownership handling.
- Added a file-backed CachyOS/Arch/Debian/Ubuntu provider matrix, reviewed golden package-plan argv, unsupported-distribution coverage, representative Debian/Ubuntu generation smoke tests, and an opt-in no-pull/no-network container check.
- Added an exact pre-advisor disclosure of the minimal redacted host profile and passed the same canonical JSON into the read-only advisor prompt without persisting host inventory.
- Replaced the live advisor command/package response with a strict bounded capability-first contract for architecture fit, required/optional intent, rationale, confidence, risks, and questions.
- Added a non-executing recommendation pipeline that preserves the deterministic project baseline, resolves validated capability intent through the detected provider, checks local repository/installed state, renders a beginner review, and saves only confirmed capability IDs.
- Enriched recommendation review items with cumulative typed provenance, need reason, confidence, provider/package mapping, verification, installed and official/manual source states, and unresolved questions without granting approval or execution authority.
- Added strict project-owned per-capability decisions: optional accept/reject, required accept/challenge with limitation, separate persistence from advisor output, and generated decision visibility without execution authority.
- Made review provenance explicit and conservative across terminal/generated output, and proved the labeled local deterministic fallback completes review, decisions, generation, and validation without Codex or network access.
- Added a private structured-only recommendation cache keyed by project intent and non-identifying host/provider facts, with strict revalidation, relevant-change invalidation, safe atomic persistence, offline reuse, and a visible default-off refresh action.
- Added adversarial advisor coverage and centralized rejection for command-shaped, privileged/destructive, download-pipe, credential-request, and prompt-injection prose, while proving fake model packages cannot enter provider queries or plans.
- Added typed Guided and Advanced CLI/GUI entry modes over the same canonical configuration and approval boundaries; CLI preserves the full advanced default while GUI guides beginners with visible conservative defaults and reversible advanced-field disclosure.
- Added a shared strict CLI/GUI task composer with six plain-language starting choices, task-relevant questions, equivalent bounded credential-safe packets, preserved prompt-template mapping, and planning-only deployment output.
- Added a shared five-section task contract with explicit Edit answers and Approve prompt actions; unapproved composition withholds prompt text, and approval remains non-launching data only.
- Added a stable seven-field plain-language diagnostic model with conservative backend exception mappings, explicit project-change state, secret-safe bounded details, and native expandable GUI presentation.
- Added private atomic GUI draft sessions for incomplete project/task state with restart-safe resume, selected-project/updated-time display, secret rejection, explicit discard, and no-replace export.
- Hardened every GUI backend boundary with stable exception/status diagnostics, observed generation mutation state, preserved path confinement, sanitized Codex display fields, and an injected private bounded redacted desktop log.
- Made the desktop GUI keyboard-complete with focus management, a skip link, labeled live status, visible non-color current state, copy-only reviewed remediation commands, and consequence-specific prompt/draft/generation confirmations.
- Added a two-step GUI launch review showing exact model, sandbox, approval, network, search, execution-location, and target state; GUI launch requires a current in-memory preview and repeats validation/policy verification, while the shared CLI launcher now blocks validation errors before preflight or Codex access.
- Added a concise generated `START_HERE.md` for humans with project summary, honest current status, non-mutating first checks, one next action, and help pointers, while preserving existing files through proposals.
- Added a compact generated `docs/AGENT-INDEX.md` with project/module navigation, task-specific minimum references, current phase/decision pointers, testing commands, security/deployment links, and freshness metadata; generated Codex prompts now read it first, and the bundled Agent Kit skill is versioned `0.2.0` for the same routing contract.
- Centralized generated model, command-network, deployment, progress-ledger, and implementation-notes policy fragments in one domain registry; `AGENTS.md` renders them once, task prompts render owner references, shared deployment boundaries preserve plan-only behavior, and stable conflict tests reject contradictory claims.
- Added a strict advisory-only structure policy with 500-line module and 80-line function review signals, module/class responsibility breadth, introduced-cycle, repeated-large-append, and undocumented-public-module warnings plus reasoned non-executable payload exemptions.
- Added read-only human/JSON `audit-structure` output with bounded Python measurements, likely responsibilities, detectable import cycles, strict project-confined baseline deltas, and acknowledged exemptions; hotspots remain non-blocking.
- Added one generated modularity contract to `AGENTS.md` and architecture guidance requiring verified module ownership, coherent vertical slices, clear public boundaries, reason-to-change splits, no placeholder/wrapper sprawl, updated project maps, and preserved public-interface compatibility.
- Began the P5-007 template-family source split by moving architecture/modularity rendering and shared deterministic formatting into cohesive discovered submodules, with direct compatibility exports, fixed byte hashes, pre-extraction manifest equivalence, and installed-artifact imports.
- Continued P5-007 by moving MIT/SPDX/AGPL license rendering and the bundled verbatim AGPL payload into one cohesive discovered module, preserving legacy functions/constants, normalized/full byte hashes, and the unchanged 63-file manifest.
- Continued P5-007 by moving `README.md`, `START_HERE.md`, and `NEXT_STEPS.md` rendering plus their shared optional skill/sandbox sections into cohesive discovered modules, preserving direct legacy exports, fixed bytes across three configurations, and the unchanged 63-file manifest.
- Continued P5-007 by moving `.gitignore`, rsync exclusions, `.env.example`, and `.editorconfig` rendering into one cohesive discovered repository-support module, preserving direct legacy exports, fixed bytes across three stack/data profiles, and the unchanged 63-file manifest.
- Continued P5-007 by moving generated documentation and agent navigation indexes into one cohesive discovered module, preserving direct legacy exports, fixed new/renovation bytes, prompt-routing behavior, and the unchanged 63-file manifest.
- Continued P5-007 by moving progress, decisions, implementation notes, agent handoff, and open-question rendering into one cohesive discovered durable-memory module, preserving direct legacy exports, fixed default/existing-project bytes, ledger ownership, and the unchanged 63-file manifest.
- Continued P5-007 by moving project brief, requirements, and phased implementation-plan rendering into one cohesive discovered definition module, preserving direct legacy exports, fixed default/high-risk-existing bytes, database guidance ownership, and the unchanged 63-file manifest.
- Continued P5-007 by moving technology-stack and development-environment rendering plus reviewed/default command selection into one cohesive discovered module, preserving direct legacy exports, fixed new/existing-advisor bytes, provider and custom-command policy, and the unchanged 63-file manifest.
- Continued P5-007 by moving testing, security/privacy, and UX/accessibility guidance into one cohesive discovered quality/risk module, preserving direct legacy exports, fixed default/high-risk-existing bytes, command approval and safety language, and the unchanged 63-file manifest.
- Continued P5-007 by moving binding `AGENTS.md`, advisory-review, and first-work-prompt rendering into one cohesive discovered agent-guidance module, preserving direct legacy and shared-section/modularity exports, fixed manual/existing-advisor bytes, canonical policy ownership, and the unchanged 63-file manifest.
- Continued P5-007 by moving release checklist, operations, contribution, and security-policy rendering into one cohesive discovered governance module, preserving direct legacy exports, fixed source/container and SQLite/MariaDB bytes, canonical database guidance, and the unchanged 63-file manifest.
- Completed the P5-007 artifact-family portion by moving local workflow-script and GitHub-CI rendering into one cohesive discovered module, preserving six direct legacy exports, aggregate new/existing-sandbox byte locks, generated Bash syntax, and the unchanged 63-file manifest; `templates.py` remains the compatibility surface.
- Continued P5-007 CLI splitting by moving `example-answers` and `toolchains` handlers plus parser registration into one cohesive discovered information-command module, preserving direct handler exports, parser dispatch, exact output/exit streams, no-replace behavior, and installed-artifact discovery.
- Continued P5-007 CLI splitting by moving `validate`, `audit-structure`, and `doctor` handlers plus position-preserving parser registration into one cohesive discovered inspection-command module, preserving direct exports, text/JSON output, redaction, exit codes, and installed-artifact discovery.
- Continued P5-007 CLI splitting by moving repo-local `$agentkit` skill status/install/update/uninstall handlers and nested parser registration into one cohesive discovered module, preserving direct exports, confirmation/decline behavior, backup and user-content refusal safety, streams, exit codes, and installed-artifact discovery.
- Continued P5-007 by moving sandbox doctor/preflight/clean CLI registration and presentation into one cohesive module with explicit injected orchestration/runner boundaries, preserving direct exports, parser dispatch, dry-run/force/volume flags, and existing safety behavior.
- Extracted the acyclic sandbox-orchestration prerequisite: generated-project metadata loading plus logged/unlogged project command execution, with direct `cli` aliases and unchanged behavior.
- Completed the sandbox-orchestration seam by moving fingerprints, atomic preflight stamps, freshness state, Podman image inspection, and doctor/build/check sequencing into one cohesive module, preserving direct `cli` exports and exact launch/status/log/stamp behavior.
- Continued P5-007 by moving local workspace status, GitHub-readiness gating, and reviewed rsync mirror planning into one cohesive command module, preserving direct helper/handler exports, command order, exact evidence/output/exit behavior, inside-root refusal, plan-only default, and explicit execution.
- Continued P5-007 by moving deterministic continuation-prompt rendering, interactive task presentation, explicit edit/approve review, and no-replace output handling into one cohesive command module, preserving eight direct exports, parser dispatch, fixed prompt bytes, CLI/GUI packet equivalence, secret rejection, and approval-without-launch behavior.
- Continued P5-007 by moving assessment-only Ollama inventory, context/coding heuristics, conservative selection, explicit risk override, and local-model handoff presentation into one cohesive command module, preserving nine direct exports, parser dispatch, fixed handoff bytes, fail-closed thresholds, and the Codex-primary/no-alternate-launch boundary.
- Continued P5-007 by moving official Codex authorization and validation/preflight-gated launch into one cohesive command module, preserving four direct exports, parser order/dispatch, status-only non-mutation, explicit install/login gates, GUI compatibility, container-runner confinement, and launch failure behavior.
- Continued P5-007 by moving answers loading/safety screening, generation reporting, explicit interactive remote handoff, and `new`/`init`/`generate` registration into one cohesive lifecycle module, preserving direct exports, parser behavior, strict custom-command/credential gates, dry-run/conflict/backup output, and installed-artifact discovery; added a root ignore rule and regression test keeping the local `kfnotepad/` workspace out of GitHub.
- Continued P5-007 wizard splitting by moving credential-safe ask/confirm/choice/list primitives and reusable language/database questions into one discovered guided-question module, preserving direct `wizard` exports, exact transcript/default behavior, cancellation, secret rejection, normalization, Guided/Advanced flows, and installed-artifact discovery.
- Continued P5-007 generator splitting by moving the deterministic managed-artifact catalog, required/executable contracts, generated helper renderers, redacted project metadata, and manifest rendering into one discovered registry, preserving seven direct exports, a fixed 48-artifact aggregate hash, generated bytes/modes, and all safe-write/conflict/backup behavior in `generator.py`.
- Continued P5-007 generator splitting by moving `ValidationReport`, generated shell discovery, and the ordered read-only workspace validator into one discovered validation module, preserving three direct `generator` exports, exact diagnostics, v1/v2 support, bounded `bash -n`, CLI/GUI/launch/readiness behavior, and installed-artifact discovery.
- Completed the planned P5-007 generator split by moving the complete confined write transaction into `generation.service`, preserving eight direct compatibility exports, dry-run non-mutation, path/symlink refusal, atomic writes, proposals, backups, mode repair, bounded local Git initialization, mutation observation, validation, and installed-artifact behavior; `generator.py` is now a 37-line facade.
- Completed P5-007 by moving redacted advisor payloads, recommendation/capability-decision presentation, conservative fallback, and explicit Codex readiness into one cohesive guided module, preserving seven direct `wizard` exports, fixed prompt bytes, exact question/state ordering, offline behavior, and installed-artifact discovery; the remaining `run_wizard` is the ordered compatibility-sensitive state machine.
- Added P5-008 read-only `audit-context` human/JSON metrics for first-run words/lines, default prompt required files, task-prompt size, and normalized duplicate paragraph fingerprints, with bounded non-symlink reads and strictly advisory targets that never block generation, validation, or launch.
- Completed P5-009 with typed bounded continuation deltas covering objective, changes, failures, exact references, acceptance checks, and unresolved decisions; generated handoff templates use the same contract, default prompts avoid full historical-ledger rereads, and reviewed explicit prompts remain below the 500-word advisory target.
- Began Phase 6 with four exact typed deployment target contracts (`static-site`, `oci-image`, `linux-service-bundle`, and `ssh-rsync`), all currently plan-only and fail-closed for untested targets, network, remote writes, secrets, push/apply, and production use.
- Added generated `docs/16-DEPLOYMENT.md` Stage-A guidance for exact target contracts, environment ownership, artifact provenance, reference-only secrets, data backup/migration, health checks, rollback, monitoring, and maintenance without selecting a target or adding execution authority.
- Added `agent-starter deployment plan` with strict bounded project-local target profiles, fixed local Git source-state evidence, canonical JSON/human text, SHA-256 digests, and atomic create-only output; profile argv is display-only and no build/check, credential, network, remote, or apply action occurs.

## 0.4.8 — 2026-07-02

- Added an optional `pywebview` desktop wizard (`agent-starter gui` / `agent-starter-gui`) that uses local HTML/CSS/JS and the existing core generator/validation/Codex boundaries.
- Fixed regeneration idempotency for fresh configs by reusing existing generated metadata timestamps, preventing timestamp-only conflicts in manifest, project metadata, docs memory, and Agent Kit skill sidecar files.
- Improved optional GUI behavior so preview panes wrap long output and the launch-Codex action closes the wizard before handing off.
- Added `agent-starter sandbox clean` and strengthened generated `scripts/sandbox/clean`; generated sandbox images are now reused by default and rebuilt only with `scripts/sandbox/build --rebuild`.
- Added explicit game/Godot `sandbox.gui_passthrough` opt-in for generating an advanced `scripts/sandbox/playtest-gui` helper with host GPU/audio/controller passthrough warnings.
- Hardened generated rootless Podman wrappers to use `--userns=keep-id` with the current `id -u` / `id -g` instead of a fixed UID/GID, keeping `/workspace` files host-owned on CachyOS/Arch-style systems.
- Hardened generated rootless Podman sandbox preflight with fingerprinted freshness checks, generated `scripts/sandbox/preflight`, status reporting for missing/stale/failed/valid stamps, and logs under `.agent-starter/logs/`.
- Added generated `scripts/sandbox/status` so Codex can check preflight validity even when `agent-starter` is not on the session `PATH`.
- Updated generated sandbox wrappers to use project-local container home/cache directories, no-network toolchain execution by default, explicit `AGENTKIT_SANDBOX_NETWORK=default` opt-in, basic hardening flags, and consistent generated-resource labels.
- Added generated `docs/CACHYOS-PODMAN.md` and clearer prompts/docs so Codex knows host preflight may use an adjacent `../agent-starter` launcher and should not repair rootless Podman from inside a constrained session.
- Fixed generated `.gitignore` and rsync exclude handling so `.env.sandbox.example` and other example env files remain trackable.
- Changed the source project and generated-project default license to `AGPL-3.0-or-later`.
- Expanded generated Git/GitHub ignore policy so AI-facing notes, prompts, skill metadata, and starter runtime files stay local while end-user documentation remains trackable.
- Fixed Python 3.11 CI compatibility by removing f-string expressions with embedded backslashes and adding a 3.11 grammar parse regression test.
- Improved generated Godot sandbox guidance with `docs/GODOT-SANDBOX.md`, `artifacts/headless/`, and a project-owned `scripts/godot-headless-test.sh` hook for future scene/export/screenshot checks without enabling GUI passthrough by default.

## 0.4.7 — 2026-06-28

- `agent-starter sandbox preflight` now writes `.agent-starter/sandbox/preflight.json` after a successful host preflight.
- Updated generated first-run, autonomous, sandbox, and `$agentkit` prompts so an already-open constrained Codex session does not rerun host-side Podman bootstrap when the preflight stamp says setup already passed.
- Clarified that `scripts/sandbox/check` should run from Codex only when the current sandbox/approval policy permits rootless Podman access; otherwise the human should run verification from a normal host terminal or use Codex-inside-container mode.

## 0.4.6 — 2026-06-28

- Added `agent-starter sandbox preflight` to run generated sandbox `doctor`, `build`, and `check` wrappers before Codex launch.
- Updated `agent-starter launch` and generated `START_AGENT.sh` so active sandbox modes run preflight before Codex starts; Codex-inside-container kickoff uses `scripts/sandbox/codex-exec` after preflight.

## 0.4.5 — 2026-06-28

- Clarified generated sandbox prompts so Codex does not request full permissions to bootstrap rootless Podman; host-side sandbox preflight should be run from a normal host terminal or Codex should be launched inside the built container.

## 0.4.4 — 2026-06-27

- Added an `AGENTKIT_INSIDE_SANDBOX=1` marker to generated project container launches and taught generated sandbox wrappers to avoid accidental nested Podman when run inside the container.
- Changed generated inside-container behavior so `scripts/sandbox/check`, `exec`, `shell`, `web`, and `headless-test` run direct project commands, while host-only sandbox scripts refuse with a clear message.
- Updated generated and source documentation to distinguish host-side sandbox wrappers from inside-container project commands such as `./scripts/check.sh`.

## 0.4.3 — 2026-06-27

- Clarified generated rootless Podman sandbox contracts so `toolchain` mode explicitly means host Codex editing mounted project files while build/test/toolchain commands run in Podman.
- Strengthened generated first prompts, autonomous prompts, sandbox docs, and `$agentkit` idea prompts so requested sandbox failures stop as `BLOCKED_ENVIRONMENT` or require explicit human approval before host-only fallback.

## 0.4.2 — 2026-06-27

- Changed generated rootless Podman toolchain `exec` and `check` helpers to avoid allocating a TTY in noninteractive runs, removing Podman's non-TTY warning while keeping `scripts/sandbox/shell` interactive.

## 0.4.1 — 2026-06-27

- Fixed generated rootless Podman toolchain `shell`, `exec`, and `check` helpers so ephemeral commands do not reuse a fixed container name and collide after parallel or interrupted runs.

## 0.4.0 — 2026-06-27

- Added `agent-starter idea-prompt` for local prompt-file generation from short `$agentkit` requests.
- Added `agent-starter codex skill-status`, `install-agentkit-skill`, `update-agentkit-skill`, and `uninstall-agentkit-skill` for versioned repo-local Agent Kit Codex skill management.
- Generated projects can include `.agents/skills/agentkit/SKILL.md` and `agentkit-skill.json` by default, with answers-file opt-out through `codex_agentkit_skill: false`.
- Added optional rootless Podman sandbox generation with `agent-starter sandbox doctor`, generated `scripts/sandbox/*` helpers, sandbox-aware `$agentkit` prompts, project-scoped Codex-inside-container launch scripts when explicitly selected, and no-secrets container handoff guidance.

## 0.3.0 — 2026-06-24

- Added `agent-starter prompt` to generate copy/paste Codex continuation prompts for later project phases and feature requests.
- The generated continuation prompt reinforces project-memory reading order, phase-sized implementation, testing, documentation updates, and approval boundaries.
- Added `agent-starter ollama-check` to assess installed Ollama models before generating a warning-rich local-model handoff prompt.
- Ollama handoff prompts require confirmed strong model suitability or an explicit `--override`; the feature does not rewrite Codex configuration or add an alternate launcher.
- Added `Apache-2.0`, `BSD-3-Clause`, `GPL-3.0-or-later`, `AGPL-3.0-or-later`, and `MPL-2.0` as built-in generated project license options.
- Changed interactive and example defaults to defer GitHub Actions so new projects prove local setup/tests before adding CI or remote repository noise.
- Added generated `NEXT_STEPS.md` and completion-output guidance so beginners start with local checks, understand placeholder scripts, and pause GitHub until Phase 0 is useful.
- Added `agent-starter status` to summarize generated workspace readiness, Codex install/auth state, Git/GitHub state, AI-local artifact ignores, and the next recommended local action.
- Added `agent-starter github-ready` as a local-first gate before creating GitHub remotes, enabling CI, or pushing.
- Added `agent-starter prompt --interactive` to guide beginners through task type, recent changes, affected surfaces, risk, and verification before producing a Codex continuation prompt.
- Added `agent-starter prompt --template` options for feature, bug, cleanup, docs, test-baseline, and release-prep continuation work.
- Added generated `.agent-starter/rsync-excludes` and review-first `agent-starter rsync-plan` for local/SSH source mirrors that require explicit `--run` before execution.
- Updated source repository ignore rules so local `.agents/` and `.codex/` workspaces are not accidentally staged for GitHub publication.

## 0.2.0 — 2026-06-24

- Refactored the starter kit into an OpenAI Codex CLI–only workflow.
- Removed alternate-client selection, adapters, generated compatibility files, examples, launcher paths, authorization flags, and documentation.
- Simplified `auth`, `launch`, wizard setup, project metadata validation, and generated agent scripts around Codex.
- Added Codex-only regression coverage and refreshed all maintainer/user documentation.
- Kept OAuth under the official Codex CLI and retained the existing safe-write, CachyOS, testing, and implementation-note workflow.

## 0.1.0 — 2026-06-23

- Initial standard-library Python wizard and deterministic answers-file generator.
- Added CachyOS toolchain guidance, safe existing-project writes, generated project documentation, test scripts, CI, Git helpers, authorization delegation, and implementation-note requirements.
- Added source, generation, and isolated installation checks.
