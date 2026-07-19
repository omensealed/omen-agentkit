# CLI AI Agent Starter Kit — Codex Edition

A standard-library-only Python wizard that turns a project idea—or an existing codebase—into a documented, test-oriented workspace for **OpenAI Codex CLI**. It is designed for beginners using CachyOS while keeping the generated workflow useful on other Linux systems.

The kit asks the project questions that are easy to skip during vibe coding: what is being built, which languages fit, whether persistence is needed, which database is appropriate, what Codex must be able to test, what security boundaries apply, and whether Git/GitHub automation should be included. It then writes the project memory Codex needs before implementation begins.

Choose the shortest documentation path for your role:

- [Human start](docs/HUMAN-START.md) — install, create a first project/task, and repair common local problems.
- [Maintainer guide](docs/MAINTAINER-GUIDE.md) — architecture, providers, schemas, security, testing, and release routing.
- [Agent guide](docs/AGENT-GUIDE.md) — concise contracts and task-to-canonical-document routing for source work.
- [Operations guide](docs/OPERATIONS-GUIDE.md) — local deployment evidence, rollback, reference-only secrets, and audit boundaries.

Upgrading from the checked-in v0.4.8/GPT-5.5-era baseline? Read the [GPT-5.6-SOL migration report](docs/GPT-5.6-SOL-MIGRATION-REPORT.md) for model/schema changes, provider support, compatibility shims, and the minimum deprecation window.
The corrective 0.5.1 candidate and opt-in reporting boundaries are recorded in [release-candidate evidence](docs/RELEASE-CANDIDATE-0.5.1.md) and the [burn-in guide](docs/BURN-IN.md); neither document by itself represents publication.

## What it creates

A generated workspace can include:

- a canonical `AGENTS.md` contract for Codex;
- `FIRST_PROMPT.md`, ready to start the first implementation phase;
- `START_HERE.md`, a short human-oriented project, status, safe-command, next-action, and help page;
- `NEXT_STEPS.md`, a beginner-safe local sequence for the first run after generation;
- `docs/AGENT-INDEX.md`, a compact task-to-minimum-context map that Codex prompts read first;
- numbered `docs/*.md` files covering requirements, architecture, stack, CachyOS setup, testing, security, UX, phases, decisions, progress, implementation notes, release, operations, handoff, and open questions;
- `.codex/config.toml` with conservative project defaults;
- `START_AGENT.sh` plus Codex setup/status helpers;
- build, run, lint, test, and aggregate check scripts appropriate to the selected toolchains;
- optional repo-local `$agentkit` Codex skill files under `.agents/skills/agentkit/`;
- optional rootless Podman sandbox files for containerized build/test work and, when explicitly selected, Codex inside a project-scoped container;
- optional local Git initialization and deferred GitHub Actions workflow;
- immutable official-action pins and a fail-closed future OIDC/provenance deployment-CI contract;
- safe handling for existing repositories through proposals and timestamped backups instead of silent replacement.

The generated `docs/11-IMPLEMENTATION-NOTES.md` is the durable local work journal. `AGENTS.md` instructs Codex to update it after every meaningful phase so a later session can recover the exact state of the project. These AI-facing files are kept out of GitHub by default; beginner-facing product docs such as `README.md`, `SECURITY.md`, setup notes, and architecture docs remain trackable.

## Fast start on CachyOS

The starter itself requires Python 3.11 or newer and Bash. Run it directly from the extracted directory:

```bash
./agent-starter doctor
./agent-starter new
# Or use the shorter beginner flow:
./agent-starter new --mode guided
```

For a user-level installation:

```bash
./install.sh
agent-starter doctor

# Only when OS detection needs a reviewed override; executable proof is required.
agent-starter doctor --platform-provider ubuntu
agent-starter doctor --json
agent-starter new
```

`doctor` detects the host provider first, then reports structured `PASS`, `ACTION NEEDED`, `OPTIONAL`, `BLOCKED`, and `UNVERIFIED` findings. Its base-tooling package checks are read-only and provider-specific (`pacman -Qq` on Arch-family hosts or `dpkg-query` on Debian/Ubuntu); it never runs an update, install, repository refresh, or source change. JSON output is redacted and omits executable paths and host/user identity.

The installer writes only beneath the user data and binary directories, normally `~/.local/share/cli-ai-agent-starter-kit` and `~/.local/bin/agent-starter`. It does not use `sudo`.

## Optional desktop GUI

The CLI remains the primary dependency-light path. A beginner-friendly desktop wizard is available as an optional `pywebview` frontend over the same `ProjectConfig`, `generate_project()`, validation, and Codex adapter boundaries:

```bash
pip install 'cli-ai-agent-starter-kit[gui]'
agent-starter gui
# or
agent-starter-gui
```

The GUI uses local HTML, CSS, and JavaScript only. It is keyboard-complete through native controls and a keyboard-addressable step list, moves focus to newly shown steps, provides a skip link and strong visible focus, and labels status regions for assistive technology. The current step and diagnostic severity/change state are stated in text rather than color alone. Reviewed Codex remediation commands are selectable and have a copy-only button that never executes them. Prompt approval, permanent local-draft discard, and workspace generation confirmations name their exact consequence. Launch is a separate two-step review: the GUI validates the generated workspace, verifies its project-local Codex policy, and displays the target project, exact model selection/ID/label/reasoning, project and Codex sandbox modes, approval policy, command-network state, and web-search state. A current in-memory review is required and validation runs again before the window closes; changed, invalid, symlinked, or policy-drifted settings block launch. The shared CLI launcher also validates before sandbox preflight, authorization, or Codex process access. Backend failures use a stable plain-language diagnostic showing the problem, whether project files changed, and a safe next action; redacted technical details stay behind an expandable disclosure. When the real desktop GUI is running, the same redacted records are appended to a private bounded log at `${XDG_STATE_HOME:-~/.local/state}/omen-agentkit/diagnostics/gui-diagnostics.jsonl`; logs omit tracebacks, raw subprocess argv, filesystem paths, and secret-like values. Explicit Save/Resume controls keep incomplete project/task drafts under `${XDG_DATA_HOME:-~/.local/share}/omen-agentkit/drafts` with private permissions and show the selected project plus last-updated time. Drafts can be discarded or exported to a new file; saving/resuming does not validate, generate, approve, or launch. The GUI does not load CDN assets, ask for credentials, inspect Codex token files, install packages, run `sudo`, create remotes, push, deploy, or bypass generated conflict/proposal behavior. If the optional GUI dependency is unavailable or the desktop stack cannot open a window, use `agent-starter new` or `agent-starter generate`.

## The guided workflow

The interactive wizard walks through:

1. **Project identity and scope** — new or existing project, current stage, type, description, goals, non-goals, users, platforms, and packaging targets.
2. **Codex readiness** — detect Codex, optionally run the official installer, and authorize the user through Codex’s own login flow.
3. **Technology choice** — manually choose languages and persistence, or ask Codex for a read-only structured recommendation and review it before accepting anything.
4. **Data and security** — database type, network access, accounts, personal data, payments, existing schemas, and project-specific risks.
5. **Quality workflow** — tests, browser testing, build/lint commands, local Git, and deferred GitHub Actions/repository setup after local checks prove useful.
6. **Linux providers and sandboxing** — generate reviewable CachyOS/Arch, Debian, or Ubuntu host-package guidance plus an independently selected, tested `arch-toolchain` or `debian-toolchain` rootless Podman image profile; no package installation or Podman command runs during generation.

See [Supported Linux hosts](docs/SUPPORTED-HOSTS.md) for detection, package-source, rootless Podman prerequisite, and provider-matrix details.
The source GitHub workflow runs the trusted suite on native Ubuntu with Python 3.11, 3.13, and 3.14. A separate focused
job preloads official Debian and Arch images, then runs representative generation and read-only bootstrap plans with
container networking disabled; the images are pinned to reviewed Linux/amd64 manifest digests, and the job does not
duplicate the full suite or install packages. Pull requests also receive dependency review. Trusted main/dispatch builds
produce create-only SHA-256 and SPDX evidence plus GitHub-hosted provenance with narrow job permissions; this does not
publish a release. See [Supply-chain policy](docs/SUPPLY-CHAIN-POLICY.md).

Before the first AI stack-advisor request, the wizard prints the exact redacted host-profile JSON that will accompany the project brief. It includes only approved OS/provider/tool availability, rootless Podman status, and selected language/target fields; it is not persisted as a host inventory.

Advisor responses are strict capability-first JSON: logical capability ID, purpose, required/optional status, rationale, confidence, architecture notes, risks, and questions. The live schema rejects package-name and command-array fields; provider mapping and executable argv remain deterministic AgentKit responsibilities. High-signal command syntax, privileged/destructive or download-pipe text, credential requests, and prompt-injection directives also reject the complete response and trigger the safe fallback path.

After the user accepts the stack hypothesis, AgentKit combines it with the deterministic project baseline, resolves only known capability IDs through the detected provider, checks configured-repository metadata and the exact candidate packages' installed state, and displays installed/missing/unavailable results. This review never constructs or runs an install/update command.

Every review item explicitly shows why it is needed; deterministic, AI-suggested, and user-requested provenance; confidence; provider-to-package mapping; repository verification; installed state; official or manual-review source; and unresolved advisor questions. Manual/third-party candidates remain unverified and outside automatic provider queries.

The wizard then asks about every item. Optional capabilities may be accepted or rejected. Required capabilities may be kept or challenged; a challenge records the resulting project limitation instead of silently treating the requirement as optional. These human decisions are stored in top-level `capability_decisions`, separately from advisor output, and appear in the generated AI recommendation document. They select intent only and never authorize installation or command execution.
7. **Handoff** — validate the generated workspace and optionally launch Codex with `FIRST_PROMPT.md`.

Interactive CLI entry defaults to `--mode advanced` so existing scripts and question sequences keep the full established flow. `--mode guided` asks the essential decisions one at a time, explains consequences, and applies visible conservative defaults to nonessential implementation settings. The desktop GUI defaults to Guided and can switch to Advanced at any time. Entry mode is presentation only: both modes use the same canonical schema, validation, approvals, conflict handling, and generator, and it is not persisted into project answers.

When Codex is absent, unauthorized, or cannot return valid structured advice, the deterministic fallback remains complete enough for capability review, decisions, generation, and validation. The wizard and generated review label it exactly as `Local deterministic default — not AI-reviewed`; manual and provenance-unknown saved recommendations likewise never claim AI review.

Successful structured Codex recommendations may be reused from a private user cache. The cache contains only the strictly validated recommendation—not raw advisor output, commands, host identity, or a separate copy of project configuration—and its opaque key changes with project intent, selected stack, OS version, architecture, or provider. A current entry is shown explicitly; when Codex is ready, the wizard offers a default-off refresh action before making another advisor request.

Generated projects use an explicit quality-first Codex policy by default: exact model ID `gpt-5.6-sol`, display label `GPT-5.6-SOL`, and medium reasoning. A reviewed answers file may select a different explicit model or `selection: "inherit"`; inherited mode omits project model/reasoning keys. AgentKit never silently downgrades an unavailable explicit model.

## Codex authorization and account ownership

Authorization is delegated to the official Codex CLI. The starter kit never asks for, reads, copies, logs, or stores OAuth tokens, API keys, browser cookies, or keyring data.

Useful commands:

```bash
agent-starter auth --status
agent-starter auth
agent-starter auth --device-auth
agent-starter auth --relogin
```

When Codex is missing, the starter prints the official installer command. Running it requires explicit approval:

```bash
agent-starter auth --install
```

A generated project also includes:

```bash
./scripts/setup-agent.sh
./scripts/agent-status.sh
```

Browser OAuth is the default. Device-code authorization is available when the local browser flow is inconvenient.

## Useful commands

```bash
# Interactive wizard; also the default when no subcommand is supplied
agent-starter new

# Add the workflow to a specified directory
agent-starter new --path /path/to/project

# Generate without launching Codex
agent-starter new --no-launch

# Preview intended writes
agent-starter new --dry-run

# Write an editable JSON answers example
agent-starter example-answers --output answers.json

# Deterministic generation from reviewed answers
agent-starter generate --answers answers.json

# Preview a v1-to-v2 migration without changing the source file
agent-starter config migrate --input answers-v1.json

# Write migration output only to a separate new file
agent-starter config migrate --input answers-v1.json --output answers-v2.json

# Permit explicitly supplied custom commands after manual review
agent-starter generate --answers answers.json --allow-custom-commands

# Validate a generated workspace
agent-starter validate /path/to/project --verbose

# Summarize readiness and the next local action
agent-starter status /path/to/project

# Check local readiness before creating a GitHub remote, enabling CI, or pushing
agent-starter github-ready /path/to/project

# Review a local/SSH source mirror command without running it
agent-starter rsync-plan /path/to/project /path/to/project-mirror

# Inspect the host, CachyOS tools, and Codex status
agent-starter doctor

# Open the optional desktop wizard when pywebview is installed
agent-starter gui

# Launch Codex interactively with the prepared first prompt
agent-starter launch /path/to/project

# Run the first prompt as a one-shot Codex task
agent-starter launch /path/to/project --kickoff

# Generate a copy/paste prompt for the next Codex session
agent-starter prompt /path/to/project --request "Add import support"

# Render a digest-bound deployment plan from reviewed project-local JSON; no target is contacted
agent-starter deployment plan /path/to/project --profile deployment-target.json --format json

# Check immutable local plan evidence without project-command execution, target contact, or writes
agent-starter deployment check /path/to/project --plan deployment-plan.json --format text

# Deterministically assemble a reviewed local input; no profile command, network, push, or apply
agent-starter deployment build /path/to/project --plan deployment-plan.json --source public --format text

# Supply a concise reviewed delta for the next session
agent-starter prompt /path/to/project --request "Finish import support" \
  --changes "CSV parsing is characterized." \
  --failures "Malformed rows still fail." \
  --relevant-reference agent_starter/imports.py \
  --relevant-reference tests/test_imports.py \
  --acceptance "Focused and full checks pass." \
  --unresolved-decision "Keep partial imports atomic?"

# From inside a generated project, turn a short Codex skill request into a full prompt file
agent-starter idea-prompt --from-codex --arguments "implement Add SQLite save/load support"

# Install or update the repo-local $agentkit Codex skill
agent-starter codex install-agentkit-skill /path/to/project
agent-starter codex skill-status /path/to/project

# Check generated rootless Podman sandbox readiness without installing anything
agent-starter sandbox doctor /path/to/project

# Run generated sandbox doctor/build/check before launching Codex
agent-starter sandbox preflight /path/to/project

# Remove generated project sandbox containers, and optionally image/volumes
agent-starter sandbox clean /path/to/project
agent-starter sandbox clean /path/to/project --dry-run
agent-starter sandbox clean /path/to/project --image
agent-starter sandbox clean /path/to/project --volumes --force

# Add task-specific guidance
agent-starter prompt /path/to/project --template bug --request "Fix CSV import crash"

# Ask guided questions before generating that continuation prompt
agent-starter prompt /path/to/project --interactive

# Save that continuation prompt for review
agent-starter prompt /path/to/project --request "Add import support" --output NEXT_PROMPT.md

# Assess local Ollama models before attempting a local-model handoff
agent-starter ollama-check /path/to/project --request "Continue the import feature"

# Show built-in language/database package mappings
agent-starter toolchains
```

## Existing-project safety

The generator treats existing source code as user data:

- it refuses unsafe roots such as `/` and the home directory itself;
- generated paths are constrained to the selected project root;
- writes through symlinked parent directories are rejected;
- new files are written atomically;
- identical files are left unchanged;
- conflicting files are preserved and generated alternatives go under `.agent-starter/proposals/`;
- `--force` first creates timestamped copies under `.agent-starter/backups/`;
- Git initialization never creates a commit or pushes a remote;
- GitHub Actions are deferred by default for new projects so beginners can prove local setup and tests first;
- GitHub repository creation is opt-in and never pushes code automatically.
- local AI/runtime artifacts such as `AGENTS.md`, `FIRST_PROMPT.md`, implementation notes, progress/handoff notes, Codex skill metadata, prompt drafts, Codex logs, session JSONL files, local-model handoff drafts, and starter proposals/backups are ignored by the generated `.gitignore` so GitHub stays focused on source code and end-user documentation.

Answers files are also checked for common credential patterns. Custom executable commands require `--allow-custom-commands` so downloaded or copied JSON cannot silently become code execution.

## Generated project routine

After generation, the normal project loop is:

```bash
cd /path/to/project
less START_HERE.md
less NEXT_STEPS.md
./scripts/doctor.sh
./scripts/bootstrap-dev.sh             # prints/reviews the plan
./scripts/bootstrap-dev.sh --install   # explicit install of reviewed missing packages
# Debian/Ubuntu only, kept separate from installation:
./scripts/bootstrap-dev.sh --refresh   # explicit APT index refresh
./scripts/check.sh
agent-starter status .
./START_AGENT.sh
```

Codex prompts begin with `docs/AGENT-INDEX.md`, select the matching task row, and then read only the linked
task-relevant policy, project memory, source, and tests. The complete reference catalog remains in `docs/README.md`.
Durable model, command-network, deployment, progress-ledger, and implementation-notes rules are owned by one
generated canonical registry in `AGENTS.md`; task prompts link to those owners instead of copying policy blocks.
The deployment rule explicitly permits local code, documentation, tests, and sandboxed plan/check/build preparation,
then requires Codex to stop before remote apply, repository push, release publication, database migration, or secret
access unless a separate human-approved tool operation is invoked. Every serialized task-composer packet and approved
prompt carries the same boundary; a prompt saying “deploy it” is not production authorization.

The source deployment vocabulary is intentionally narrow: `static-site`, `oci-image`, `linux-service-bundle`, and
`ssh-rsync`. `agent_starter.deployment` distinguishes these exact IDs from display labels and currently grants only
local plan/read-only-check authority plus deterministic ZIP assembly for static-site and Linux-service-bundle inputs.
OCI/SSH builders, target adapters, network access, remote writes, registry push, apply, credentials, and production
support are not implemented by this contract layer. Unknown,
generic-cloud, and Kubernetes targets fail closed instead of implying untested support.

Generated workspaces include `docs/16-DEPLOYMENT.md`, a Stage-A planning worksheet covering environment and human
ownership, supported artifact contracts, provenance, reference-only configuration/secrets, data backup/migration,
health checks, rollback, monitoring/log locations, and maintenance responsibility. Generation selects no deployment
target or environment and grants no implicit build, network, remote-write, push, migration, staging, production, or apply authority.

`agent-starter deployment plan PROJECT --profile PROFILE` strictly loads the generated project metadata and a bounded,
project-confined target profile, records fixed local Git revision/dirty-state evidence, and renders canonical JSON or
human text plus its SHA-256 digest. Profile commands remain argv data for display only. Standard output is the default;
`--output` atomically creates one new project-relative file and never replaces it. Planning performs no build/check,
credential access, network request, remote write, push, migration, staging/production change, or apply operation.

`agent-starter deployment check PROJECT --plan PLAN` verifies the immutable digest/schema, local project identity and
structure, source state, a confined artifact checksum, and declared health/rollback evidence. It never runs project or
profile commands, builds, contacts a target, queries credential values, or writes. Evidence requiring those actions is
reported as `unverified`, keeps the report non-ready, and grants no apply authority.

`agent-starter deployment build PROJECT --plan PLAN --source SOURCE` accepts only an exactly matching clean Git plan
for a supported local ZIP target. It packages a dedicated reviewed source path twice with normalized metadata, compares
the bytes, embeds source/plan/command/tool/checksum provenance and an SPDX-2.3 file inventory, then atomically creates
the plan's new `.zip` output. It refuses the project root, credential-prone names, symlinks, special files, excessive
input, existing output, and unsupported targets. Display-only commands are recorded but never executed; success never
pushes or applies.

Deployment credentials are reference-only. `environment-file` name `docs-api` means `.env.docs-api`; checks inspect
only regular-file type, owner-only mode `0600`, and quiet Git-ignore status, never file contents. `ssh-agent` checks
only that `SSH_AUTH_SOCK` identifies a socket and never lists keys. OS-keyring, CI-store, and target-secret-manager
references stay `unverified` until narrow metadata adapters exist. AgentKit never creates, prompts for, reads, hashes,
prints, persists, or transmits secret values, and reports only safe reference names plus stable status codes.

`agent_starter.deployment_gate` is a pure fail-closed model for later apply authorization. It requires an enabled,
production-ready target adapter, exact reviewed plan and reproducible-artifact digests, the complete passing check set,
explicit environment/target identity, target-tool human authentication, exact typed local-human confirmation, rollback,
and closed redacted audit metadata. Any plan, artifact, environment, or target change invalidates prior approval. All
current targets remain adapter-blocked, no `deployment apply` command exists, and evaluation performs no command,
credential access, target/network contact, filesystem write, remote change, or apply.

`agent_starter.deployment_ci` centralizes reviewed full-commit GitHub Action pins and the future deployment-workflow
contract. Generated CI remains build/check-only with `contents: read`; no deploy job or OIDC token permission is
generated. A future reviewed cloud adapter must use short-lived GitHub OIDC, separate environments and jobs, protected
production approval, and artifact checksum plus attestation evidence.

Generated-workspace validation also rejects mutable, short, unknown, commentless, or registry-mismatched action
references without contacting GitHub. Maintainers update action pins through
[`docs/GITHUB-ACTIONS-UPDATE-POLICY.md`](docs/GITHUB-ACTIONS-UPDATE-POLICY.md), including official-source review,
permission/runtime inspection, complete local checks, and explicit human acceptance rather than auto-merge.

`agent_starter.deployment_staging` adds one static-site-only disposable staging rehearsal for maintainer tests. It
requires exact clean plan/check/artifact evidence, rejects production and stale/wrong targets, executes no commands,
and always proves rollback to its prior in-memory digest after success or injected partial failure. It is not exposed
through the CLI or generated scripts and does not contact a real target.

Maintainer-side source-structure policy is advisory: modules over 500 logical lines, functions over 80, mixed
class/module responsibilities, new cycles, repeated growth, and undocumented public modules produce review signals,
not build failures. Run `agent-starter audit-structure .` for human output or add `--json` for a versioned report.
The bounded read-only auditor imports or executes no target code and never writes a baseline. See
`docs/STRUCTURE-POLICY.md` for baseline and exemption rules.

Generated context budgets are also advisory. Run `agent-starter audit-context /path/to/generated-project` or add
`--json` to measure first-run words/lines, the default prompt's required-file count, task-prompt words, and repeated
paragraph fingerprints. Suggested targets never block generation, validation, or launch, and the command refuses
symlinked or oversized context inputs rather than following them.

Generated `AGENTS.md` and `docs/02-ARCHITECTURE.md` share a binding modularity contract: identify the responsible
module before editing, prefer tested vertical slices and clear public boundaries, split only at real reasons to
change, avoid placeholder/wrapper sprawl, update the project map when ownership moves, and preserve public-interface
compatibility. Existing generated files retain normal proposal/backup protection.

Maintainer template code follows the same rule incrementally. Architecture and modularity rendering live in
`agent_starter.template_sets.architecture`, shared deterministic Markdown formatting lives in
`agent_starter.template_sets.common`, license rendering and the bundled AGPL text live in
`agent_starter.template_sets.licenses`, human project-entry documents live in
`agent_starter.template_sets.orientation`, and their optional cross-document skill/sandbox sections live in
`agent_starter.template_sets.shared_sections`. Repository ignore, mirror-exclusion, environment-example, and editor
defaults live in `agent_starter.template_sets.repository_support`. The established `agent_starter.templates`
imports remain compatible. Generated human/agent documentation maps live together in
`agent_starter.template_sets.navigation`. Generated progress, decisions, implementation notes, handoff, and open
questions live together in `agent_starter.template_sets.project_memory`.
Generated scope, requirements, acceptance, and phased implementation intent live in
`agent_starter.template_sets.project_definition`.
Generated stack rationale, provider-safe environment guidance, and reviewed/default command selection live in
`agent_starter.template_sets.technology_environment`.
Generated testing, security/privacy, and UX/accessibility acceptance guidance lives in
`agent_starter.template_sets.quality_risk`.
Generated binding agent policy, structured advisory review, and first-work prompt live in
`agent_starter.template_sets.agent_guidance`.
Generated release evidence, operational recovery, contribution, and vulnerability-reporting guidance live in
`agent_starter.template_sets.release_operations`.
Generated doctor/build/test/lint/check/run/Codex-launch scripts and GitHub CI live in
`agent_starter.template_sets.script_workflows`; `agent_starter.templates` is now a compact compatibility surface.
Read-only `example-answers` and `toolchains` parser/handler ownership lives in
`agent_starter.cli_app.information_commands`; `agent_starter.cli:main` remains the public dispatcher.
Read-only workspace validation, structure auditing, and host/Codex doctor commands live in
`agent_starter.cli_app.inspection_commands`, with text/JSON and exit behavior preserved through direct exports.
Repo-local `$agentkit` skill status/install/update/uninstall registration and handlers live in
`agent_starter.cli_app.skill_commands`; confirmation and user-content backup/refusal safety remain unchanged.
Sandbox doctor/preflight/clean registration and presentation live in `agent_starter.cli_app.sandbox_commands`;
fingerprinting, preflight stamps/state, and host-side orchestration live in
`agent_starter.cli_app.sandbox_orchestration` behind direct `agent_starter.cli` compatibility exports.
Generated-project metadata loading and logged/unlogged command execution now live in `agent_starter.cli_app.project_runtime`.
Local `status`, `github-ready`, and `rsync-plan` registration, readiness evidence, and reviewed mirror planning live in
`agent_starter.cli_app.readiness_commands`; these commands never create a remote or push, and rsync remains plan-only
unless `--run` is explicit.
Continuation-prompt templates, interactive task-question presentation, explicit edit/approve review, and `prompt`
output handling live in `agent_starter.cli_app.prompt_commands`; typed questions/contracts and approval state remain
authoritative in `agent_starter.task_composer`, and prompt approval never launches Codex.
Assessment-only Ollama inventory, metadata scoring, conservative selection, explicit risk override, and local-model
handoff presentation live in `agent_starter.cli_app.local_model_commands`. This does not add an alternate agent adapter,
authentication path, or generated launch configuration; Codex remains the primary agent and quality baseline.
Official Codex install/auth presentation plus validation- and preflight-gated project launch live in
`agent_starter.cli_app.agent_commands`. `agent_starter.cli` directly re-exports the established helpers/handlers so GUI
and external callers retain the same boundary; status-only auth never installs or logs in.

Answers-file loading, credential/custom-command screening, generation reporting, and the `new`/`init`/`generate`
lifecycle live in `agent_starter.cli_app.generation_commands`. The established `agent_starter.cli` names and parser
behavior remain direct compatibility aliases; GitHub repository creation remains an explicit interactive choice and is
never part of answers-file generation.

Credential-safe ask/confirm/choose/list primitives plus reusable language and database questions live in
`agent_starter.guided.questions`. `agent_starter.wizard` directly re-exports the established types and helpers, so
existing imports, cancellation behavior, Guided/Advanced transcripts, and answers remain compatible.

The deterministic managed-artifact catalog, required/executable contracts, generated helper renderers, redacted project
metadata, and manifest rendering live in `agent_starter.generation.registry`. `agent_starter.generator` directly
re-exports the established names. `agent_starter.generation.service` owns the complete confined write transaction:
root/path/symlink checks, atomic writes, conflicts, proposals, backups, explicit local Git initialization, mutation
observation, and post-write validation.

Read-only generated-workspace inspection and its structured report live in `agent_starter.generation.validation`.
`agent_starter.generator.ValidationReport`, `_shell_files`, and `validate_project` remain direct compatibility aliases;
CLI, GUI, launch, readiness, provider-matrix, and post-generation checks all consume the same validator.

GitHub can stay off until the project has a useful local baseline. Enable a workflow or create a remote only after `./scripts/check.sh` and Phase 0 documentation make the project worth publishing or backing up remotely.
Run `agent-starter github-ready /path/to/project` before creating a remote, enabling GitHub Actions, or pushing; it checks validation, local checks, Git cleanliness, CI posture, and ignored AI-local artifacts without contacting GitHub.
For a local or SSH source mirror, `agent-starter rsync-plan /path/to/project /path/to/project-mirror` prints the exact `rsync` command and uses `.agent-starter/rsync-excludes`; it only executes when `--run` is supplied.

Inside the Codex session, the local `AGENTS.md` requires the agent to inspect the project docs, work one phase at a time, run the available tests, and append an implementation note before ending the phase. Those AI notes are for local continuity, not the public repository. The helper below creates a note skeleton:

```bash
./scripts/new-implementation-note.sh codex "Phase objective"
```

For later work, the starter can generate a focused continuation prompt that tells Codex what to read, how to preserve the project contract, which safety boundaries apply, and how to report completion:

```bash
agent-starter prompt /path/to/project --request "Implement the next planned feature"
```

For a guided beginner flow, use `agent-starter prompt /path/to/project --interactive`. The shared task composer starts with Add a feature, Fix a problem, Change existing behavior, Review or improve code, Improve tests/documentation, or Prepare a deployment plan, then asks only the questions relevant to that choice. CLI and GUI use the same strict bounded, credential-rejecting task packet. Before releasing prompt text they display what Codex will attempt, protected behavior, likely areas, acceptance checks, and risks/approvals. Choose **Edit answers** to revise it or **Approve prompt** to release copyable prompt text. Approval does not launch Codex or execute anything, and deployment requests are explicitly plan-only.
Named templates are available with `--template feature`, `--template bug`, `--template cleanup`, `--template docs`, `--template test-baseline`, and `--template release-prep`.

Generated projects can also include a repo-local Agent Kit Codex skill. Inside Codex, `$agentkit` is a skill invocation, not a custom slash command:

```text
$agentkit implement Add your feature idea here
$agentkit fix Describe the bug here
$agentkit plan Describe the project change here
```

The skill does not send keystrokes, run a daemon, modify `~/.codex/config.toml`, contact OpenAI or GitHub by itself, or bypass approvals. It tells Codex to run the local prompt builder, `agent-starter idea-prompt`, read the generated file under `docs/agent-prompts/`, and treat that generated prompt as the task brief. Use `agent-starter codex skill-status`, `update-agentkit-skill`, and `uninstall-agentkit-skill` to inspect or manage the versioned skill sidecar. Restart Codex if a newly installed or updated skill does not appear immediately.

## Optional rootless Podman sandbox

New local projects can include a rootless Podman sandbox. The default `toolchain` sandbox mode keeps Codex on the host editing the local project files and runs project build/test/toolchain commands in a project container against the mounted `/workspace`. An explicit Codex-inside-container mode generates project-scoped Codex launch scripts and a project-specific Codex home volume.

Generated sandbox files live under `.agent-starter/sandbox/` and `scripts/sandbox/`. They do not mount host `~/.codex`, `~/.ssh`, browser profiles, GitHub credentials, production configs, or the host home directory by default. Container auth uses `scripts/sandbox/codex-login` only when the user deliberately runs it. The starter recommends handoff summaries instead of copying raw Codex sessions or auth files into containers.

Generated project containers use rootless Podman `--userns=keep-id` with the current `id -u` and `id -g` instead of assuming UID/GID `1000`. This keeps files created under the mounted `/workspace` owned by the real host user on CachyOS/Arch-style systems.

Useful generated commands:

```bash
# Run this from a normal host terminal before relying on the sandbox:
scripts/sandbox/preflight

# The preflight command uses agent-starter from PATH or ../agent-starter when available,
# then runs these generated wrappers:
scripts/sandbox/doctor
scripts/sandbox/build
scripts/sandbox/check
scripts/sandbox/shell
scripts/sandbox/codex-login  # only when Codex-inside-container mode was explicitly selected
scripts/sandbox/codex
```

`agent-starter launch` and generated `START_AGENT.sh` run the preflight automatically before launching Codex for
active sandbox modes. A successful preflight writes `.agent-starter/sandbox/preflight.json` with a fingerprint of
the generated sandbox inputs. Trust that stamp only while `agent-starter status .` or generated
`scripts/sandbox/status` reports it as valid/current; if it is missing, stale, or failed, run
`scripts/sandbox/preflight` from a normal host terminal. Do not make Codex
rerun `scripts/sandbox/doctor` or `scripts/sandbox/build` from inside its own constrained sandbox. Do not use Codex `danger-full-access`, host
full-access, privileged containers, or Podman socket mounts just to make rootless Podman bootstrap work from inside
a constrained Codex session. If verification wrappers fail because Codex cannot access `/run/user/<uid>/libpod` or
other rootless Podman runtime paths, fix or run verification from a normal terminal or launch Codex inside the
built container.

Toolchain `scripts/sandbox/check`, `exec`, and `shell` default to `--network none`. If a reviewed task truly needs
dependency downloads or networked checks, opt in explicitly:

```bash
AGENTKIT_SANDBOX_NETWORK=default scripts/sandbox/check
AGENTKIT_SANDBOX_NETWORK=default scripts/sandbox/exec -- npm install
```

Preflight logs are written under `.agent-starter/logs/`, including `sandbox-preflight-doctor.log`,
`sandbox-build.log`, and `sandbox-check.log`. Generated projects also include `docs/CACHYOS-PODMAN.md` with
rootless Podman diagnostics for CachyOS/Arch-style systems.

Inside the container, do not run host-side `scripts/sandbox/*` launchers. Run project commands directly:

```bash
./scripts/check.sh
npm test
python3 -m unittest
cargo test
```

Rootless Podman reduces host filesystem risk, but it does not make untrusted code safe. It can still damage mounted project files and misuse network access when network is enabled. If the sandbox was requested and `scripts/sandbox/doctor`, `scripts/sandbox/build`, or `scripts/sandbox/check` fails, record the failure and fix the sandbox or explicitly approve a host-only fallback; do not silently treat host checks as equivalent. Do not use host `danger-full-access`, do not mount real secrets, and do not deploy, push, or rsync production targets without explicit approval.

For Godot or other interactive game projects, headless sandbox checks are the default autonomous path. Godot projects also get `docs/GODOT-SANDBOX.md`, which explains the `scripts/godot-headless-test.sh` hook for future scene/export/screenshot checks and keeps artifacts under `artifacts/headless/`. Real rendering, audio, and controller playtesting usually needs either host playtesting with `scripts/playtest-host` or the advanced opt-in `sandbox.gui_passthrough: true` setting. When enabled, the generated `scripts/sandbox/playtest-gui` helper intentionally exposes selected host Wayland, GPU, PipeWire audio, and input/controller interfaces to the project container. Leave it off unless the project needs containerized interactive playtesting and you accept that extra host interface exposure.

If a user wants to attempt continuation with a local Ollama model, check the installed models first:

```bash
agent-starter ollama-check /path/to/project --request "Implement the next planned feature"
```

The check inspects `ollama list` and `ollama show <model> --json` locally, looks for confirmed context length and coding-model signals, and refuses to generate a local-model handoff prompt when the model is inadvisable unless the user passes `--override`. It does not rewrite Codex configuration or add an alternate launcher.

## Runtime requirements

- Python 3.11+
- Bash
- Linux for the complete generated shell workflow
- Git and curl, plus `pacman` on CachyOS/Arch or APT/dpkg tools on Debian/Ubuntu
- OpenAI Codex CLI for AI advice and implementation work
- GitHub CLI only when repository creation is requested

The Python package has no third-party runtime dependencies.

## Development and tests

From the starter-kit source tree:

```bash
./scripts/check.sh
```

That command performs Python syntax checks, the unit/integration suite, shell syntax validation, CLI smoke checks, fresh-project generation and validation, generated-project checks, and an isolated install/uninstall test. It deliberately does not access a real OpenAI account, run OAuth, invoke network installers, use `sudo`, or publish a repository.

For a focused standard-library security gate, run `./scripts/security-regression-check.sh`. It consolidates the unsafe-path,
credential-pattern, strict-input, AI-injection, prompt-preservation, GUI-redaction, deployment-evidence, and sandbox-policy
contracts also covered by the full suite. See [Security regression suite](docs/SECURITY-REGRESSION-SUITE.md).

`./scripts/performance-resource-check.sh` records time and peak Python allocation for two representative temporary
generations and locks cache reuse, bounded provider queries, and lazy GUI imports. See
[Performance and resource checks](docs/PERFORMANCE-RESOURCE-CHECKS.md).

`./scripts/end-to-end-journey-check.sh` runs the isolated no-sudo installer smoke and complete synthetic fresh-user
journeys for CachyOS/Arch, Debian, and Ubuntu without real package installation, Codex, Podman, or deployment access.
See [End-to-end user journeys](docs/END-TO-END-JOURNEYS.md).

`./scripts/existing-project-fixture-check.sh` exercises clean and dirty repositories, owner-file conflicts, symlink
refusal, older metadata, manual answers, and advisory god-file hotspots. See
[Existing-project compatibility fixtures](docs/EXISTING-PROJECT-FIXTURES.md).

On each supported Python CI version, the artifact smoke builds both sdist and wheel, installs each without an index into
separate temporary environments, verifies both CLI entry points, compares installed discovery with every source module,
imports every safe module, and generates/validates a representative project. The user-local installer marks owned data,
supports recognized pre-marker upgrades, and refuses arbitrary or symlinked launcher/data paths during install or removal.

Source releases use a separate manual-only workflow. A maintainer must dispatch from an exact existing semantic tag,
repeat that tag as input, pass clean version/changelog/full-check/exact-artifact smoke gates, and explicitly enable the
default-off publication choice. Ordinary CI success cannot trigger it, and only the final protected-environment job gets
GitHub release write authority. See [Release safety](docs/RELEASE-SAFETY.md).

Maintainers may explicitly install the constrained, non-runtime quality extra and run the separate gate:

```bash
python3 -m pip install -e '.[quality]'
./scripts/quality-check.sh
```

The gate runs critical Ruff correctness checks, mypy over typed policy/schema seams, a medium/high Bandit scan, and
branch coverage with an 80% floor. It never installs a tool. The trusted `./scripts/check.sh` remains standard-library
and offline-useful when the optional extra is absent. Repository-wide formatter adoption is intentionally staged because
the pre-tooling baseline is not Ruff-formatted; do not combine that mechanical rewrite with feature work.

## Project layout

```text
agent_starter/
  agents.py       Codex CLI boundary and structured advisor call
  cli.py          commands, validation, authorization, launch, GitHub setup
  codex_skill.py  repo-local Agent Kit skill rendering/status/update helpers
  generator.py    safe rendering, writes, conflict handling, validation
  idea_prompts.py local prompt-file builder used by the $agentkit skill
  models.py       serializable project configuration
  model_policy.py typed explicit/inherited Codex model policy
  config_schema/  strict parsing and ordered schema migrations
  cli_app/        extracted cohesive CLI command families
  template_sets/  extracted cohesive generated-artifact families
  generation/     shared safe generation primitives
  guided/         reusable wizard questions and advisor support
  templates.py    generated project files and documentation
  capabilities.py provider-neutral toolchain/database/sandbox intent
  recommendation.py non-executing capability/provider review pipeline
  toolchains.py   language commands, ignores, CI, and compatibility views
  wizard.py       ordered beginner-oriented setup state machine
docs/              maintainer documentation and implementation memory
examples/          reviewed Codex-only answer files
scripts/           source checks, generation smoke test, install smoke test
tests/             standard-library unittest suite
```

## License

AGPL-3.0-or-later. See `LICENSE`.
