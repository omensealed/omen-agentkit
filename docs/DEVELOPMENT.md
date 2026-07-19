# Development

## Requirements

- Python 3.11+
- Bash
- Git for repository-oriented checks
- No third-party Python runtime packages

CachyOS is the primary user environment, but source tests should remain portable across normal Linux development hosts.

## Commands

```bash
./scripts/check.sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q agent_starter tests starter.py
bash -n install.sh uninstall.sh scripts/*.sh
./scripts/smoke-test.sh
./scripts/install-smoke-test.sh
./scripts/package-smoke-test.sh
./scripts/security-regression-check.sh
./scripts/performance-resource-check.sh
./scripts/end-to-end-journey-check.sh
./scripts/existing-project-fixture-check.sh
./scripts/audience-documentation-check.sh
./scripts/migration-report-check.sh
./scripts/release-candidate-check.sh
./scripts/quality-check.sh  # only after explicitly installing the constrained .[quality] extra
./agent-starter audit-context /path/to/generated-project
```

`.[quality]` is a maintainer-only optional extra containing constrained Ruff, mypy, Bandit, and coverage.py release
lines. `scripts/quality-check.sh` first verifies all four modules are already available and exits with an actionable
message if not; it never invokes pip or contacts an index. Ruff currently gates syntax/undefined-name correctness,
mypy covers the typed model-policy/config-schema/action-policy seams, Bandit reports medium/high runtime findings, and
branch coverage must remain at least 80%. The ordinary `scripts/check.sh` does not invoke this optional gate and remains
useful without third-party packages or network access.

Ruff formatting is available to maintainers for inspection, but the inherited source baseline would require a broad
mechanical rewrite. Keep formatter adoption as a separately reviewed compatibility slice; do not mix it into feature or
security work, and never use an automatic formatter to overwrite protected user changes.

The native Python 3.11/3.13/3.14 CI matrix runs every source, compatibility, generation, validation, and user-local
install check. The minimum supported Python 3.11 job additionally runs package smoke because the no-install artifact
builder requires the already-provided setuptools backend, which newer hosted Python images do not promise to bundle.
Package smoke builds one sdist and wheel, installs them into separate temporary venvs without an index, verifies the
`agent-starter` and dependency-free `agent-starter-gui --help` entry points, compares installed discovery against all
source Python modules, imports every module except executable `agent_starter.__main__`, and performs representative
generation/validation and deployment-local smoke. The sdist venv may expose only the runner's already-installed build
backend through `--system-site-packages`; the AgentKit distribution itself must resolve inside that venv. Local
`./scripts/check.sh` still runs the complete gate, including package smoke; `--skip-package-smoke` is the explicit CI
matrix split and does not install or download a backend.

User-local installation ownership is indicated by `.agent-starter-install-owner`. Install/reinstall may replace only a
matching marked directory, or the narrowly recognized canonical pre-marker layout for compatibility. Uninstall removes
only marked or recognized legacy data. Both operations refuse unrecognized or symlinked data/launcher paths; tests must
prove external targets and arbitrary files survive.

Supply-chain updates and build evidence follow `docs/SUPPLY-CHAIN-POLICY.md`. Dependabot proposals always require human
review, action pins must match the typed full-SHA registry, and CI provider images must match reviewed digest records.
For a new wheel/sdist directory, `python3 -m agent_starter.release_artifacts <directory>` creates `SHA256SUMS` and an SPDX
2.3 artifact SBOM without replacement. This command alone is never release authorization. The separate manual/tagged
workflow and preparation contract are documented in `docs/RELEASE-SAFETY.md`.

## Test strategy

Unit tests cover models, normalization, JSON extraction, Codex command construction, templates, security boundaries, conflict behavior, project validation, CLI answers, and wizard helpers. Generator tests use temporary directories and disable Git unless Git behavior is under examination.

`scripts/security-regression-check.sh` is the named P7-007 security compatibility gate. It invokes only
`tests.test_security_regressions`; the full discovery run invokes that module too. Keep its synthetic cases aligned with
`docs/SECURITY-REGRESSION-SUITE.md`, temporary-directory confined, process-mocked where applicable, and free of package
installation, network, Codex, credential, real-target, and production access.

`scripts/performance-resource-check.sh` is the P7-008 standard-library resource gate. It records schema-versioned
temporary generation measurements and runs the cache/query/lazy-import regressions documented in
`docs/PERFORMANCE-RESOURCE-CHECKS.md`. Keep budgets conservative enough for supported CI but treat unexplained growth as
a regression. Provider checks must use injected synthetic runners; never turn this gate into host inventory, package
metadata, Codex, network, installation, or display-server work.

`scripts/end-to-end-journey-check.sh` is the P8-001 compatibility journey gate documented in
`docs/END-TO-END-JOURNEYS.md`. Keep the provider/AI/package/sandbox/deployment boundaries synthetic and injected. The
runner may execute only the repository-owned isolated installer smoke and generated local check scripts under temporary
roots; it must never install a host package, run Codex/Podman, contact a target, apply a deployment, or use credentials.

`scripts/existing-project-fixture-check.sh` owns the P8-002 renovation scenarios documented in
`docs/EXISTING-PROJECT-FIXTURES.md`. Add scenarios through the checked-in catalog and reconstruct them only in temporary
directories. Tests must prove owner data and dirty changes survive, conflicts use proposals, symlinks cannot escape,
manual commands remain approval-gated/unexecuted, and structure findings remain advisory.

Agent Kit skill and `idea-prompt` tests use temporary generated projects. They must not require Codex to be installed, must not read `~/.codex`, and must not use shell interpolation for user-provided idea text.

Sandbox tests use temporary generated projects and mocks. They must not require Podman to be installed, must not run `sudo`, must not install packages, must not perform real Codex login, and must not mount or inspect host Codex credentials, SSH keys, browser profiles, or the host home directory.

`agent-starter sandbox preflight` and generated `scripts/sandbox/preflight` are the Agent Kit-managed host setup gates for generated sandbox projects. The generated script may use `agent-starter` from `PATH` or an adjacent `../agent-starter` launcher, then falls back to a local shell implementation so projects created beside the starter can still preflight before Codex launches. Active sandbox launches must run preflight before Codex starts, including generated `START_AGENT.sh`, and tests should mock command execution rather than requiring Podman. A successful preflight writes `.agent-starter/sandbox/preflight.json` with a fingerprint of generated sandbox inputs and logs under `.agent-starter/logs/`; generated `scripts/sandbox/status` must be able to report valid/missing/stale/failed state even when `agent-starter` is not on `PATH`. Generated prompts must not tell an already-open constrained Codex session to rerun host-side Podman bootstrap when that stamp is valid/current. Missing, stale, or failed stamps should direct the human to run host preflight from a normal terminal.

GUI tests cover `agent_starter.ui_schema` and `agent_starter.gui.bridge` without opening a display server. `pywebview` is an optional extra, so GUI module imports must skip or degrade cleanly when it is absent, and no GUI test may start Codex login, install packages, or read credential files.

No automated test invokes Codex login/advice against a real account, network installers, `sudo`, `pacman`, GitHub publication, remote pushes, or production databases. Subprocess tests use mocks or isolated commands. Installation tests replace `HOME`, `XDG_DATA_HOME`, and `XDG_BIN_HOME` with a temporary tree.

The smoke test generates a fresh project, validates it, runs its generated checks, validates all shell scripts, and confirms expected Codex/project-memory files.

Configuration behavior belongs in `config_schema/`; model selection belongs in `model_policy.py`; extracted CLI command families belong in `cli_app/`; generated artifact families belong in `template_sets/`; atomic generation primitives belong in `generation/`. Keep `agent_starter.cli:main`, public model imports, and `templates.py` exports as compatibility delegates. Add a package only when real cohesive behavior moves into it; do not create placeholders or one-function fragmentation.
`cli_app/information_commands.py` owns `example-answers` and `toolchains` registration/handling. Preserve direct handler
identity from `cli.py`, exact stdout/stderr and exit codes, schema/model-policy example content, and existing-file refusal.
`cli_app/inspection_commands.py` owns `validate`, `audit-structure`, `audit-context`, and `doctor` registration/handling. Preserve direct
handler identity, command ordering/help, text/JSON output, redaction, advisory audit behavior, and report exit codes;
keep validation, audit, provider detection, and doctor-report logic in their canonical domain modules.

`context_budget.py` measures only bounded regular UTF-8 generated Markdown. Preserve the versioned advisory-only report,
human/JSON equivalence, symlink and 1-MiB refusal, stable word/line counts, normalized paragraph fingerprints, and
Baseline/discovery required-file routing. Suggested targets are review signals, never validation or launch gates.
`cli_app/skill_commands.py` owns repo-local skill command registration, confirmation, and result presentation. Keep
path confinement, managed-content detection, atomic replacement, backups, and user-owned-content refusal in
`codex_skill.py`; characterize declined updates and non-managed uninstall refusal through `main`.
`cli_app/sandbox_commands.py` owns sandbox parser/presentation only. Keep orchestration injected rather than importing
`cli.py`; preserve dry-run/image/volume/all/force/yes argv ordering. `cli_app/sandbox_orchestration.py` owns fingerprint,
stamp/state, and host preflight sequencing; retain direct `cli.py` exports and exact stamp/log/exit behavior.
`cli_app/readiness_commands.py` owns `status`, `github-ready`, and `rsync-plan` registration/handling plus their local
evidence helpers. Preserve direct `cli.py` exports, top-level command order, exact output/exit behavior, path-inside-root
refusal, plan-only default, and explicit `--run`; never add remote creation or push behavior to this family.
`cli_app/prompt_commands.py` owns `prompt` registration, deterministic continuation rendering, interactive presentation,
review-loop adaptation, typed bounded continuation deltas, and output handling. Preserve objective/change/failure/reference/
acceptance/decision ordering, safe project-relative references, credential screening, conservative omitted-field defaults,
the under-500-word advisory characterization, and the no-historical-reread boundary. Keep questions, strict packets,
contracts, and approval state in `task_composer.py`; preserve direct `cli.py` exports, intentional fixed prompt bytes,
no-replace default, and the rule that Approve prompt releases text only and never launches or executes it.
`cli_app/local_model_commands.py` owns `ollama-check`, assessment heuristics, and handoff presentation. Preserve direct
`cli.py` exports, argv-only bounded list/show inspection, fail-closed thresholds, explicit override, fixed handoff bytes,
and no-replace output. Never turn this assessment seam into an alternate adapter, auth flow, generated launcher, or
automatic model switch; Codex remains the primary agent and quality baseline.
`cli_app/agent_commands.py` owns `auth` and `launch`, official adapter presentation, validation/preflight gating, and
container kickoff delegation. Preserve direct `cli.py` exports for GUI/external callers, status-only non-mutation,
explicit `--install`/`--relogin`, validation before adapter access, active-sandbox preflight, generated-runner confinement,
and actionable explicit-model launch failure text. Tests must mock every install, login, Codex, and sandbox process edge.
`cli_app/generation_commands.py` owns noninteractive answers loading/screening, generation-result presentation, explicit
interactive remote handoff, and `new`/`init`/`generate` registration. Keep canonical schema validation and project writes
in their existing packages, preserve direct `cli.py` exports, and test no-launch/dry-run/custom-command/credential gates.
Never make GitHub creation part of answers-file generation or run it without the established explicit interactive choice.
`guided/questions.py` owns reusable wizard presentation and normalization primitives. Preserve direct `wizard.py`
aliases, exact prompts/options/defaults, credential rejection, EOF/Ctrl-C cancellation, custom-language normalization,
and database aliases. `guided/advisor.py` owns only the redacted advisor payload, recommendation/decision presentation,
offline fallback, and explicit Codex readiness support. Preserve its direct `wizard.py` aliases and characterized prompt
bytes. Keep host/provider/cache selection, question order, state transitions, and final generation approval in
`wizard.py`; its long `run_wizard` is one compatibility-sensitive interactive state machine, not a reason for wrapper
sprawl. Do not duplicate the canonical configuration parser in either guided module.
`generation/registry.py` owns deterministic artifact membership/content assembly and manifest metadata only. Preserve
direct `generator.py` aliases and aggregate byte-equivalence across representative configuration, including generated
helper scripts, licenses, skills, sandbox files, redacted advisor data, required files, and executable modes. Its artifact
table may exceed the advisory function threshold as cohesive static mapping; do not split it into wrapper-only fragments.
Keep filesystem mutation, confinement, conflict/proposal/backup handling, Git subprocesses, and validation out of it.
`generation/validation.py` owns one read-only ordered diagnostic pass and `ValidationReport`. Preserve direct
`generator.py` aliases, diagnostic wording/order, v1/v2 metadata support, secret-material detection, workflow references,
executable/shell checks, CI/manifest checks, and proposal warnings. Its validator is slightly over the advisory function
threshold because the ordered pass is one reason to change; split only with explicit diagnostic-order equivalence, not
into thin wrappers. All subprocess calls must remain bounded argv-only `bash -n` checks.
`generation/service.py` owns the confined generation transaction. Preserve direct `generator.py` aliases, canonical
config reparse, dangerous-root/path/symlink refusal, timestamp stability, exact report ordering, dry-run non-mutation,
atomic create/replace use, executable-mode repair, proposals, force backups, bounded argv-only local Git initialization,
mutation observation, and post-write validation. Per-artifact resolution and local Git setup are private cohesive helpers;
do not move any of these gates into presentation code or weaken them to simplify callers.

Guided/Advanced behavior belongs in `entry_modes.py` plus thin presentation conditionals. Keep entry mode out of `ProjectConfig` and answers schemas. CLI no-flag behavior remains Advanced for compatibility; GUI may default Guided. Guided may suppress only nonessential implementation questions and must state every applied default plus how to reach Advanced. Never suppress security/data classification, final write review, or approval decisions. Both modes must reach `parse_config()` and the same safe generator.

Task kinds, questions, and the derived five-section review contract belong in `task_composer.py`; do not duplicate authoritative questionnaire or contract logic in CLI or GUI code. Keep answer objects closed, text-only, bounded, control-safe, and credential-rejecting. CLI and GUI equivalence tests must compare serialized `TaskPacket` values. A composed contract starts `review-required`; only the explicit Approve prompt adapter action may return its prompt, and that value must never launch or execute automatically. Edit answers must rebuild through validation. Persistence remains deferred to the draft phase. Deployment composition is always plan-only.

Presentation error results and private diagnostic logging belong in `diagnostics.py`. Keep the seven serialized fields stable and ordered. Mapping and logs must not emit tracebacks, raw subprocess argv, raw filesystem paths, or secret-like exception text. The operation boundary must explicitly supply `project_changed`; generator code must invoke its private observer only after a successful mutation and remain idempotent when unchanged. GUI code renders plain fields first and puts details in a native expandable disclosure using `textContent`, not injected HTML. Inject logging only from the real desktop launcher so headless/library tests never touch real user state; tests use temporary XDG/state roots, assert 0700/0600, bounded rotation, redaction, and symlink refusal.

Incomplete GUI persistence belongs in `draft_sessions.py`, never `ProjectConfig` or task approval state. Keep the draft schema closed to the actual form fields, strictly bool/text typed, bounded, control-safe, and credential-rejecting. Tests must isolate XDG data, reconstruct the store to prove restart survival, assert 0700/0600 modes, exercise malformed/oversized/symlink cases, and prove save/resume never calls generation, approval, or launch. Use atomic create/replace; discard only a validated draft ID; export only to a new non-symlink path. Loaded drafts must pass normal config/task validation later before gaining any authority.

Keep the GUI keyboard-complete with native controls, a visible global `:focus-visible` treatment, focus management after page/Guided-decision changes, a skip link, accessible labels, textual current/severity/change status, and live regions for operation results. Any remediation command must remain sanitized selectable text and clipboard-only—never `eval`, `exec`, shell interpolation, or automatic execution. Confirmation text must name the exact mutation or data transition. Static/headless tests should cover this presentation contract and a representative form-to-generation plus bug-fix-prompt flow without JSON editing.

GUI launch must remain preview-first and fail closed. Build the preview from strict generated metadata plus the bounded, confined, non-symlink project Codex TOML; compare it with `DEFAULT_CODEX_WORKSPACE_POLICY` rather than duplicating safety values. Display exact-versus-inherited model state, reasoning, both sandbox layers, approval, project/command network state, web search, execution location, and target. Require the bridge-local preview fingerprint, revalidate/recompute immediately before launch, consume it before window close, and prove every invalid/stale path leaves `launch_agent` and `close_window` untouched.

Keep full project validation inside shared `launch_agent()` before sandbox preflight and adapter/auth access so non-GUI callers cannot bypass the launch safety gate. CLI regression tests must prove an invalid project reaches none of those boundaries.

Provider-neutral intent belongs in `capabilities.py`. Capability definitions must contain no package names, and every default provider catalog must pass exact key-coverage validation. Toolchains and advisor schemas select canonical IDs; package names and executable aliases belong only in provider records or explicitly provider-scoped compatibility fields.

Platform-neutral host facts and provider interfaces belong in `platforms/`. Keep host detection, provider-specific package mappings, and execution coordination out of the base contract. Tests for this boundary must use synthetic profiles and fake providers; they must not enumerate host packages or invoke a real package manager. Any future advisor handoff must use `HostProfile.to_advisor_dict()` rather than serializing arbitrary host state.

The advisor disclosure must use the same canonical JSON rendering for user output and prompt input. Tests must prove the disclosure occurs before the advisor call, that project paths and forbidden identity/credential/history/browser/SSH fields are absent, and that the snapshot is not persisted. Do not expand the allowlist merely because additional host data is available.

The live advisor response schema in `agents.py` must remain closed, capability-first, and manually validated even when Codex reports schema-conforming output. Every string/list/object field needs explicit type, count, length, enum, required-key, additional-key, and duplicate checks as applicable. Do not restore package names or command arrays to the live schema. Saved legacy fields are compatibility data, not execution authority.

Keep adversarial advisor prose checks centralized in that same parser and applied to every free-text field before model construction or caching. Reject command substitution/pipeline syntax, privileged/destructive or download-pipe commands, credential-exfiltration requests, and prompt-injection directives without echoing payload content. Maintain a negative-control test proving ordinary security discussion remains accepted. Tests must mock process boundaries and prove model prose/fake package names never reach provider argv or install plans.

The recommendation pipeline belongs in `recommendation.py`. Tests must inject synthetic profiles/providers and prove the call order is capability resolution, repository verification, then installed-state query; provider update/install-plan methods must not be called. Keep deterministic baseline intent even when advisor output omits it, leave unknown IDs unresolved, and never substitute Arch mappings for an unsupported host. Render beginner-readable states and persist only confirmed capability IDs, not provider package names, argv, or raw advisor JSON.

Keep recommendation provenance typed and cumulative: deterministic, AI-suggested, and user-requested evidence may coexist. Every rendered item must retain need reason, confidence, provider mapping, verification, installed state, source authority, and unresolved questions. Manual-review mappings must stay unverified/non-installable and out of official package queries.

Capability decisions belong in top-level `ProjectConfig.capability_decisions`, never inside raw or structured advisor output. Parse the nested list strictly and enforce canonical IDs, uniqueness, closed fields, bounded limitations, deterministic-baseline requirements, and valid optional/required state transitions. Wizard prompts must cover each item. Required challenges must explain limitations. Generated documentation must state that a decision selects intent but does not approve commands or packages.

Keep advisor review-mode labeling centralized on `AdvisorRecommendation`; wizard and template output must consume the same property. Local fallback/manual sources must say not AI-reviewed, and uncertain saved provenance must not infer review. Offline tests must mock the adapter and provider boundary, prohibit advisor/install calls, and complete review, decisions, generation, and validation with temporary paths and no network.

Recommendation caching belongs in `recommendation_cache.py`. Cache only data that passes the closed advisor parser again; never store raw output, commands, host snapshots, paths, or unhashed project intent. Key invalidation tests must cover OS version, provider, language, and database changes. Keep private modes, bounded reads, symlink rejection, atomic replacement, conservative cache provenance, and a visible default-off refresh action. Tests must replace the cache boundary and never touch a developer's real cache.

Deterministic OS classification belongs in `platforms/detection.py`. Test it with synthetic os-release strings and injected executable lookups. Metadata must select the candidate before executable proof; do not add heuristic provider selection based only on commands found on `PATH`.

Provider-matrix changes must update the file-backed fixtures under `tests/fixtures/os-release/` and the reviewed golden argv in `tests/fixtures/provider-package-plans.json`. Normal checks must keep container coverage skipped. The source CI preloads the official Debian and Arch images in a separate networked step, then the focused opt-in smoke must use no-pull/no-network execution, read-only generated-project mounts, and plan-only bootstrap without package mutation; see `docs/SUPPORTED-HOSTS.md`. Keep the full trusted suite only in the native Ubuntu Python-version matrix rather than repeating it in provider containers.

Arch package authority belongs in `platforms/arch.py` capability records. Keep `packages_for()` and `Toolchain.packages` compatibility views derived from those records. Provider tests must inject a runner; never query the developer's real package database. Read-only queries are limited to installed-state and official-repository metadata. Mutation stays argv-only, and AUR/manual records must remain non-installable.

Debian/Ubuntu mappings belong in `platforms/debian.py` and share one flavor-data-driven provider unless behavior truly differs. Tests inject `dpkg-query`/`apt-cache` results and must prove refresh/install separation. Do not add PPAs, third-party repositories, signing keys, or source-list edits. Manual third-party records require source/key/pinning/removal review details and remain outside install plans.

Structured source diagnostics belong in `doctor.py`. Tests must inject OS metadata, executable lookups, provider query runners, and Codex state; assert the stable JSON shape and all five finding statuses; and prove Ubuntu/Debian output contains no `pacman` requirement. Doctor may use only provider installed-state queries. Keep repository availability, refresh, update, install, and source-changing behavior outside this command.

Generated host bootstrap belongs in `template_sets/bootstrap.py`, with `templates.bootstrap_script` retained as the compatibility delegate. Derive all three provider arrays from canonical capabilities and provider records. Tests must execute generated scripts only with synthetic package-manager and sudo commands, prove default mode cannot mutate, prove installed packages are omitted, keep APT refresh separate from installation, and reject every full-system upgrade path. Generated-content review must cover fresh and existing projects with different stacks.

## Adding a toolchain

1. Add the provider-neutral capability definition, a focused `Toolchain` entry, and matching records in every supported provider.
2. Prefer official compiler/runtime packages; manual/AUR records must remain explicit, unverified, and outside install plans.
3. Keep setup, build, test, lint, CI, and ignore behavior mutually consistent.
4. Add normalization and generation tests.
5. Generate and inspect a representative project.
6. Update the answer-file reference and implementation notes.

Do not add a framework merely because a toolchain supports one. The wizard should preserve the user’s vanilla/minimal-dependency preference.

## Changing generated files

`agent_starter/generator.py::REQUIRED_FILES`, `build_file_map`, templates, validation, tests, README examples, and `docs/TEMPLATE-CATALOG.md` form one file contract. Update them together.

Generated `START_HERE.md`, `docs/AGENT-INDEX.md`, `AGENTS.md`, `FIRST_PROMPT.md`, numbered docs, scripts, and `.codex/config.toml` must tell one consistent story. Keep `START_HERE.md` short and human-oriented: summary, honest status, non-mutating first commands, one next action, and help pointers only. Keep `AGENT-INDEX.md` compact, task-routed, root-relative, freshness-stamped, and free of copied canonical policy; prompt families must read it first and then only their linked relevant context. Verify both a new project and an existing-project renovation after changing this contract.

Keep durable model, command-network, deployment, progress-ledger, and implementation-notes statements in
`agent_starter/policy_fragments.py`. Render them once in the binding generated `AGENTS.md`; prompt families should use
the shared owner-reference renderer. Extend the stable conflict rules and tests when adding a durable policy—do not
add a second ledger path, copied model recommendation, network enablement claim, or prompt-granted external authority.
Preserve `CODEX_DEPLOYMENT_BOUNDARY` as the single exact P6-008 contract consumed by the deployment canonical policy
and every task-composer packet/prompt. It allows local preparation plus sandboxed plan/check/build, requires a stop
before apply/push/publication/migration/secret access absent a separate human-approved tool operation, and rejects the
claim that “deploy it” is sufficient production authorization. Do not turn this boundary into an apply command.

Preserve `agent_starter/deployment_ci.py` as the single P6-009 owner for official GitHub Action pins and the future
deployment CI contract. Every generated `uses:` reference must use a reviewed 40-character commit SHA with a readable
release comment. Ordinary check CI keeps only `contents: read`; do not add `id-token: write` until a reviewed target
adapter has a separate deploy job. A future supported-cloud deploy job must use short-lived GitHub OIDC, separate
build/deploy jobs and environments, protected production approval, and checksum plus attestation evidence.

Follow `docs/GITHUB-ACTIONS-UPDATE-POLICY.md` for every pin change. Treat the full SHA, semantic version comment,
official commit evidence, and review date as one atomic review unit. Inspect official release/commit pages, release
notes, `action.yml`, runner/runtime changes, permissions, inputs, downloads, and network/cache behavior. Update typed
metadata, templates, validation cases, docs, and implementation notes together; never auto-merge or replace a broken
pin with a mutable tag. Local tests and workspace validation must remain offline.

Keep deployment target vocabulary and authority in `agent_starter/deployment.py`. New target IDs require a substantive,
tested adapter contract; do not use aliases or generic cloud/Kubernetes claims. Current targets allow local planning
and read-only checking; static-site and Linux-service-bundle additionally allow deterministic local ZIP assembly.
Network, remote writes, secrets, push/apply, and production readiness remain disabled. Adding an OCI/SSH builder,
target contact, or command-execution authority is a separate task and must not be inferred from the registry.

Keep `agent_starter/deployment_staging.py` disposable, in-memory, static-site-only, and library/test-only. It is a
Stage-C readiness state-machine rehearsal, not a hosting adapter. Require exact clean staging identity plus complete
passing digest-bound checks and reproducible artifact evidence; reject production, wrong targets, stale evidence,
failed tests, and missing health/rollback declarations before mutation. Every success or injected partial failure must
restore the exact prior state and emit only closed value-free audit metadata. Do not add a rehearsal/apply CLI or call
profile commands from this seam.

Source-structure thresholds and exemptions are defined in `docs/STRUCTURE-POLICY.md` and
`agent_starter/structure/policy.py`. Treat every finding as a review signal: do not fail builds solely for 500/80
logical-line thresholds, and do not split cohesive code merely to reduce counts. Exemptions require a bounded reason
and cannot suppress executable responsibility/cycle/growth warnings. Keep filesystem measurement and CLI output in
the cohesive `agent_starter/structure/audit.py` layer, not the policy model. `agent-starter audit-structure .` must
stay read-only and advisory: no target imports, command execution, network, Git-history interpretation, baseline
writes, or nonzero exit solely because a hotspot exists. Treat baseline JSON as strict untrusted project data.

The generated modularity contract is source-owned once by `_modularity_contract()` and rendered in both binding
`AGENTS.md` and `docs/02-ARCHITECTURE.md`. Its implementation lives in `template_sets/architecture.py`, while
`templates._modularity_contract` remains a compatibility alias. Keep its seven promises together: inspect existing ownership, reject a
second unrelated workflow in a broad module, prefer vertical slices with public boundaries, split on primary reasons
to change, avoid placeholders/wrapper sprawl, update the project map when ownership moves, and preserve public
interfaces. Test both renderers and a generated workspace. Do not make older generated workspaces invalid merely
because they predate this additive guidance; renovations receive normal proposals rather than silent replacement.

Template extraction is family-based. Shared whitespace/list/scalar formatting belongs in `template_sets/common.py`;
architecture rendering belongs in `template_sets/architecture.py`; compatibility names stay importable from
`agent_starter.templates`. License rendering and the bundled unmodified AGPL text belong in
`template_sets/licenses.py`; normalized MIT, parameterized SPDX, and full AGPL hashes protect exact output. Human
entry and next-action rendering belongs in `template_sets/orientation.py`; optional skill/sandbox sections shared
with other generated documents belong together in `template_sets/shared_sections.py`. Direct identity and hashes
for new, existing-renovation, and sandbox/skill-enabled output protect this boundary. Repository-local support
artifacts belong together in `template_sets/repository_support.py`; hashes across distinct language/database/network
profiles protect ignore, mirror, example-environment, and editor-default output. Documentation routing belongs in
`template_sets/navigation.py`; both the complete human map and compact task-routed agent map must move together,
retain canonical owner links, and pass fixed new/renovation hashes. Durable continuity documents belong together in
`template_sets/project_memory.py`; preserve append-only ledger boundaries, exact next-agent routing, open-question
behavior, direct exports, and fixed default/existing-project hashes. Project scope, risk-specific requirements,
acceptance guidance, and phased intent belong together in `template_sets/project_definition.py`; keep canonical
database guidance in `toolchains.py` and protect default/high-risk-existing output with fixed hashes. Stack rationale,
provider-safe development guidance, and the shared reviewed/default command selector belong in
`template_sets/technology_environment.py`; canonical language/database maps stay in `toolchains.py`, advisor commands
remain documentation-only, and established `templates.py` imports stay direct aliases. Quality/risk acceptance
guidance belongs together in `template_sets/quality_risk.py`: testing establishes evidence, security/privacy
prioritizes abuse and loss boundaries, and UX/accessibility defines safe recovery and observable journeys. Keep
test-command selection delegated to `technology_environment.py` and protect default/high-risk-existing output with
fixed hashes.
Binding agent policy, structured advisory review, and the Phase 0 first-work prompt belong together in
`template_sets/agent_guidance.py`. Keep canonical policy fragments, modularity text, shared optional sections, and
command selection in their existing owner modules; preserve legacy renderer and helper attributes through direct
imports/aliases.
Release evidence, deployment planning/read-only checking, operations/recovery, contribution rules, and vulnerability reporting belong together in
`template_sets/release_operations.py`. Keep database-specific operational guidance in `toolchains.py`, preserve the
human-only publish/deploy gate, and lock source/container plus SQLite/MariaDB output. The generated deployment document
must derive its exact targets from `deployment.py`, select no target/environment, refer to secret mechanisms without
values, and retain proposal/backup safety. Any plan-schema change needs deterministic digest and compatibility review;
target adapters, network access, and apply remain later tasks.

Deployment plan parsing, source-state evidence, canonical JSON/text rendering, and digesting belong in
`deployment_plan.py`; nested CLI presentation belongs in `cli_app/deployment_commands.py`. Profiles must remain closed,
bounded, project-confined, non-symlink JSON and represent commands only as argv data. Plan output is stdout or atomic
create-only inside the project. Git inspection must remain fixed, local, bounded, and disable fsmonitor/optional locks.
Never execute profile argv, inspect credential values, contact a destination, or treat a plan digest as apply approval.

Immutable-plan parsing and read-only check findings belong in `deployment_check.py`. The check may run only fixed local
source inspection and AgentKit structural validation; it must not run project/profile commands, build, query credential
values, contact a target, or write. Use stable `passed`, `failed`, and `unverified` findings. Reproducibility, target
identity, external-store credential existence, backups, and target-side least privilege stay unverified until a reviewed
mechanism can prove them without broadening check authority. Local reference checks may consume only the value-free
metadata contract from `deployment_secrets.py`.

Deterministic artifact assembly and verification belong in `deployment_build.py`. This initial local builder supports
only static-site and Linux-service-bundle `.zip` outputs declared in `local_writes`, requires an exactly matching clean
Git plan, reads one dedicated non-root project-local source, and builds twice before atomic create-only output. Preserve
normalized ZIP metadata, per-file/content-root checksums, embedded source/plan/display-command/tool provenance, SPDX
inventory, credential-prone-path refusal, size/file bounds, and no external command/network/push/apply behavior.

Deployment secret mechanisms, name validation, and metadata findings belong in `deployment_secrets.py`; target-profile
parsing must import that registry rather than duplicate it. Environment-file references map only to `.env.<name>` and
may inspect `lstat`, mode `0600`, and quiet Git-ignore status without opening the file. SSH-agent checks may inspect only
the `SSH_AUTH_SOCK` socket type and must never list keys. OS-keyring, CI, and target stores remain unverified until a
reviewed metadata adapter exists. Never accept, prompt for, read, hash, compare, print, log, persist, or transmit values.

Apply prerequisite state belongs in `deployment_gate.py`. Preserve its closed ordered gate IDs, exact plan/check/build/
environment/target bindings, local-TTY confirmation source, target-tool authentication source, rollback requirement,
redacted value-free audit shape, and invalidation on any reviewed binding change. A check report must contain the full
canonical required-check set and a build report must prove two deterministic assemblies. Current target contracts must
remain adapter-blocked; do not register `deployment apply`, add persistence, contact a target, or execute free-form data.
Generated local workflow scripts and GitHub CI belong in `template_sets/script_workflows.py`; keep reviewed/default
command selection and toolchain/CI mappings in their canonical owners. Hash both placeholder-new and reviewed-command
existing/sandbox output and parse freshly generated Bash. The artifact-family split is complete; future P5-007 work
must move to another planned seam. Every later extraction needs fixed byte-equivalence coverage, representative generation,
and isolated-artifact import coverage. Do not create single-wrapper modules or change generated bytes during a move.

AI-facing generated files such as `AGENTS.md`, `FIRST_PROMPT.md`, `FIRST_RUN_AUTONOMOUS.md`, `docs/09-PROGRESS.md`, `docs/11-IMPLEMENTATION-NOTES.md`, `docs/14-AGENT-HANDOFF.md`, `docs/agent-prompts/`, `.agents/`, `.codex/`, and `.agent-starter/` are local working memory and should stay ignored for GitHub publication. Human-oriented `START_HERE.md` and other end-user docs, scripts, source files, license files, and example env files should remain trackable.

Generated `.agents/skills/agentkit/SKILL.md` and `agentkit-skill.json` are part of the optional Codex skill contract. Keep `SKILL.md` concise and store Agent Kit-specific version data in the JSON sidecar.

Generated `.agent-starter/sandbox/`, `scripts/sandbox/`, optional `docs/12-SANDBOX.md`, optional `docs/CACHYOS-PODMAN.md`, and optional `FIRST_RUN_AUTONOMOUS.md` are part of the rootless Podman sandbox contract. Keep scripts POSIX-shell friendly where practical, reviewable, project-scoped, and free of host secret mounts. Project containers are marked with `AGENTKIT_INSIDE_SANDBOX=1` and should use Podman `--userns=keep-id` with runtime `id -u` / `id -g` rather than a fixed UID/GID so `/workspace` files remain host-owned. Container home/cache paths should be project-local under `.agent-starter/`, not the real host home. Toolchain check/exec/shell wrappers default to no network and require explicit `AGENTKIT_SANDBOX_NETWORK=default` opt-in for networked runs. Generated wrappers must either run direct project commands inside the container or refuse host-only behavior, never nested Podman. Normal tests should validate generated text and syntax without requiring Podman.

Generated sandbox images are project-scoped and reused by default once built. `scripts/sandbox/build --rebuild` is the explicit refresh path, and `scripts/sandbox/clean` / `agent-starter sandbox clean` are the cleanup paths. Volume deletion must stay explicit because project Codex home, cache, and dev database data may live there.

Sandbox image policy is explicit and independent from host detection: only `arch-toolchain` and `debian-toolchain` are supported until another profile has equivalent rendering and regression coverage. Keep `/home/codex` non-world-writable; Codex mode's project-specific named volume uses Podman's `:U` ownership adjustment with the runtime `keep-id` user.

The optional GUI lives under `agent_starter/gui/` and must remain a thin frontend over the core model, generator, validator, and Codex adapter. Keep static assets local, avoid CDN dependencies, and import the bridge, diagnostics logger, and `pywebview` only inside the actual GUI launcher so normal CLI and GUI-help use stays lightweight and standard-library-only.

## Release

1. Update `VERSION`, `agent_starter.__version__`, `ProjectConfig.kit_version`, and `pyproject.toml` together.
2. Move all intended `CHANGELOG.md` entries from Unreleased to one exact dated version heading; leave Unreleased empty.
   Update `docs/PROGRESS.md`.
3. Append a complete entry to `docs/IMPLEMENTATION-NOTES.md`.
4. Run `./scripts/check.sh` and review a clean committed source tree.
5. Create/push the exact `vMAJOR.MINOR.PATCH` tag only as an explicit human action.
6. Manually dispatch `.github/workflows/release.yml` from that exact tag and repeat it as input; use the default
   `publish: false` mode when verification-only evidence is desired.
7. Publication requires another explicit `publish: true` choice, a successful read-only verification job, and the
   `release` environment. It builds and smoke-installs the exact artifacts, publishes their checksum/SPDX evidence, and
   grants `contents: write` only to the final no-checkout job. Follow `docs/RELEASE-SAFETY.md`.
