# User guide

## 1. Run without installing

Extract the archive, open a terminal in its directory, and inspect the host:

```bash
./agent-starter doctor
```

`doctor` classifies CachyOS/Arch, Debian, and Ubuntu from `/etc/os-release` before checking capabilities. If metadata is incomplete on an intentionally unusual host, `--platform-provider arch|debian|ubuntu` requests an explicit override. The override is rejected when its package-manager executable is missing and remains visibly warned when it contradicts OS metadata.

`doctor` changes nothing. It reports `PASS`, `ACTION NEEDED`, `OPTIONAL`, `BLOCKED`, and `UNVERIFIED` findings for Python, core executables, provider-resolved base tooling, Codex, and optional Podman. Installed-package checks use only `pacman -Qq` for CachyOS/Arch or `dpkg-query` for Debian/Ubuntu. Ubuntu/Debian reports never treat missing `pacman` as a problem. No repository query, index refresh, update, installation, or source change occurs.

For machine-readable automation, use `./agent-starter doctor --json`. The versioned JSON report includes stable finding codes, capability IDs, explanations, remedies, and bounded evidence. It excludes executable paths, usernames, hostnames, home paths, environment data, and credential state beyond the official Codex CLI's boolean authorization result.

Maintainers can review Python structure without changing a project:

```bash
./agent-starter audit-structure /path/to/project
./agent-starter audit-structure /path/to/project --json
```

The report shows measurements, likely responsibility groups, detectable import cycles, and advisory hotspots. An
optional strict baseline at `.agent-starter/structure-baseline.json` adds deltas and reviewed exemptions; the command
never creates or replaces it. Findings return success because they are review prompts, while an unsafe root or invalid
baseline returns an actionable error. See `docs/STRUCTURE-POLICY.md` for the closed baseline schema.

To measure generated first-run context without changing or validating it:

```bash
./agent-starter audit-context /path/to/generated-project
./agent-starter audit-context /path/to/generated-project --json
```

This advisory report counts words and lines in `START_HERE.md`, `docs/AGENT-INDEX.md`, `FIRST_PROMPT.md`, and
`AGENTS.md`; fingerprints repeated paragraphs; counts the unique files selected by the default Baseline/discovery
prompt; and reports task-prompt words. Suggested targets produce review notes only and never block generation,
validation, or launch. Symlinked, non-UTF-8, or over-1-MiB context files are refused.

Start the guided setup:

```bash
./agent-starter new --mode guided
```

Guided mode presents one decision at a time, explains security and workflow consequences, and uses conservative defaults for implementation details such as toolchain-container settings, test layers, dependency restraint, local-first CI timing, and the default branch. Switch to `--mode advanced` for every setting. For compatibility, plain `agent-starter new` retains the established advanced question sequence.

The desktop GUI offers the same choice on its Welcome page and defaults to Guided. Advanced fields can be revealed at any time without losing current form values. The mode is never written into generated project configuration; both presentations feed the same strict parser and generation/approval boundaries. When a filesystem, subprocess, validation, Codex-adapter, task, draft, or unexpected backend failure occurs, the GUI returns a stable diagnostic: code/severity, plain explanation, explicit project-files-changed state, safe next action, and expandable redacted details. Missing or unauthorized Codex is reported without starting login.

The running desktop GUI keeps the same sanitized diagnostics in `${XDG_STATE_HOME:-~/.local/state}/omen-agentkit/diagnostics/gui-diagnostics.jsonl`. The directory/file modes are 0700/0600, the log rotates at a bounded size, and symlinked roots/files are refused. Records contain no traceback, raw command argv, project or filesystem path, or recognized credential-like value. A logging failure never replaces the user-facing operation result.

Use **Save current draft** to retain an incomplete project form and partial task answers. Drafts live in private user-local application data at `${XDG_DATA_HOME:-~/.local/share}/omen-agentkit/drafts`; they are presentation state, not validated project configuration or approved prompts. The list shows each selected project and UTC last-updated time. **Resume selected draft** restores the fields, **Discard selected draft** removes only that local draft after confirmation, and **Export selected draft** writes a private copy to a new path without replacing an existing file. Credential-like content rejects before any draft directory or file is written.

Keyboard users can tab through every control, use the step buttons to move directly, and use the skip link to reach the current form. Focus moves to a new step heading or newly revealed Guided decision. The current step is named in visible text as well as styling, and status regions announce updates without relying on color. When Codex reports a reviewed installation command, it appears as selectable text with **Copy remediation command**; copying never runs it. Confirmations state whether an action releases prompt text, permanently deletes one local draft, or writes under the selected project folder.

On the Result page, **Review launch settings** does not start Codex. It first validates the workspace and shows the exact target, project model policy (including exact ID versus display label and inherited-global state), reasoning effort, project/Codex sandbox modes, approval policy, project network requirement, command network access, and web-search state. The default generated implementation policy is explicit `gpt-5.6-sol` with `medium` reasoning; reviewed explicit overrides remain exact, while inherited policy is labeled unknown/inherited instead of pretending to be Sol. Select **Confirm and launch Codex** only after reviewing the summary. AgentKit revalidates and recomputes it before closing; errors, policy drift, or a stale/missing preview stop launch.

`agent-starter launch PROJECT` uses the same generated policy and now runs full project validation before sandbox preflight, authorization checks, or Codex access. It prints every validation error and exits without launching when the workspace is invalid.

Running `./agent-starter` with no subcommand does the same thing.

## 2. Optional user-level install

```bash
./install.sh
agent-starter --version
```

This installs beneath your user data/bin directories and does not require root. `./uninstall.sh` removes only those installed starter-kit files.

## 3. Describe the project

The wizard asks whether this is a new project or an existing codebase, then collects:

- project type, stage, plain-language description, goals, and first-release exclusions;
- intended users, target platforms, and packaging targets;
- whether Codex should recommend the stack or the user wants to select it;
- implementation languages and whether to minimize dependencies;
- database/persistence needs, including SQLite, MariaDB, PostgreSQL, an existing database, no database, or an undecided choice;
- network, account, personal-data, payment, and security constraints;
- test layers, browser testing, local Git, and optional later GitHub Actions/repository setup;
- whether to generate optional rootless Podman sandbox files for containerized project checks;
- initial license choice, defaulting to AGPL-3.0-or-later and also offering MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-or-later, MPL-2.0, or undecided; the wizard shows a short permissive/copyleft guide before this choice;
- extra trusted CachyOS packages and unresolved questions.

Never enter a database password, OAuth token, API key, cookie, private key, or production secret. The kit does not need them.

## 4. Use Codex stack advice safely

When selected, the kit asks Codex for a structured recommendation from a temporary directory using a read-only sandbox. You see the proposed languages, database, architecture, rationale, risks, and questions before deciding what to accept.

The live advisor cannot return package names or command arrays. When Codex is unavailable or its response is invalid, the wizard uses conservative built-in advice instead. Legacy saved command text remains documentation-only and never enters the provider review or an executable plan.

After a successful live review, the wizard may save only that strict structured recommendation in the private user cache under `$XDG_CACHE_HOME/omen-agentkit/recommendations/` when set, otherwise `~/.cache/omen-agentkit/recommendations/`. Cache filenames are opaque hashes of project intent and a non-identifying OS-version/architecture/provider fingerprint; changing the selected stack or those host facts produces a miss. The file contains no raw transcript, commands, host label, project path, or separate copy of the project brief/configuration. A hit is announced. Choose the visible, default-off refresh action to contact Codex again; otherwise the cached result is usable offline.

## 5. Review generated files

For an existing repository, conflicts do not overwrite current files. Review alternatives under:

```text
.agent-starter/proposals/
```

Only use `--force` after reviewing the result. Forced replacement stores original content under:

```text
.agent-starter/backups/
```

Read `AGENTS.md`, `FIRST_PROMPT.md`, `docs/00-PROJECT-BRIEF.md`, `docs/08-IMPLEMENTATION-PLAN.md`, and `docs/11-IMPLEMENTATION-NOTES.md` before the first Codex session.

Generated projects keep local AI/runtime artifacts out of GitHub by default. `AGENTS.md`, `FIRST_PROMPT.md`, implementation notes, progress/handoff notes, Codex skill metadata, saved prompt drafts, Codex logs, session JSONL files, local-model handoff drafts, starter runtime state, proposals, and backups are ignored by `.gitignore`; end-user docs, scripts, and source files remain trackable.

The wizard recommends a local-first path. Local Git can be initialized immediately, but GitHub Actions default to off so you can run `./scripts/check.sh`, complete Phase 0, and decide later whether a remote repository or CI workflow is worth adding.

When enabled, generated check CI uses immutable full-SHA pins for official actions and workflow-level `contents: read`
only. It contains no deploy job or OIDC permission. Generated deployment guidance records the requirements for a later
reviewed deployment workflow without enabling one.

AgentKit’s static-site staging rehearsal is maintainer test infrastructure, not a user command or hosting adapter. It
uses disposable in-memory digest state to prove success and partial-failure rollback behavior. Production and every
real target remain disabled, and generated Codex launch scripts contain no rehearsal or apply entry point.

## 6. Prepare the supported Linux host

Inside the generated project:

```bash
./scripts/doctor.sh
./scripts/bootstrap-dev.sh
```

The first bootstrap invocation prints the proposed packages and commands. After checking them:

```bash
./scripts/bootstrap-dev.sh --install
```

The helper safely detects CachyOS/Arch, Debian, or Ubuntu, confirms the matching package manager, queries installed package state, and omits already-installed packages. Use `--provider arch|debian|ubuntu` only as a reviewed override; it does not change the project's target or sandbox image.

The complete support and rootless Podman prerequisite matrix is in `docs/SUPPORTED-HOSTS.md`.

When AI stack advice is available, the wizard displays the exact redacted host snapshot immediately before requesting advice. Review that JSON directly. It excludes identity, paths, addresses, environment/history data, credentials, browser/SSH state, and unrelated package inventory. If advice is unavailable, the offline deterministic recommendation remains usable and no host snapshot is sent.

The proposed-stack screen always includes a review-mode label. A fallback says `Local deterministic default — not AI-reviewed`; manual selection says `Local manual selection — not AI-reviewed`; old saved data without reliable provenance says AI review is not established. The local default still supplies a language/database hypothesis, deterministic capability baseline, review screen, per-item decisions, and valid generated workspace without contacting Codex or the network.

Accepted advisor output contains only a stack hypothesis, known logical capabilities, architecture notes, risks, and questions. Capability entries show purpose, required/optional intent, rationale, and confidence. The advisor cannot supply package-manager names or setup/build/test/lint command arrays through this contract; those fields cause rejection and the wizard uses its safe offline fallback.

The same parser rejects high-signal shell syntax, `sudo`/destructive commands, download-to-shell pipelines, requests to paste or reveal credentials, and prompt-injection directives. Ordinary security discussion remains allowed, but accepted prose is still untrusted display data. Unknown/fake packages cannot enter provider resolution: only canonical capability IDs are mapped to deterministic provider-owned package records.

After you choose the final languages and database, the wizard adds the deterministic project baseline and resolves known capabilities through the detected CachyOS/Arch, Debian, or Ubuntu provider. It checks only the exact provider-owned package candidates against local repository metadata and installed state, then labels them already installed, available but not installed, unavailable, or unverified. Unsupported hosts remain unresolved instead of receiving Arch guidance. No package or command runs.

Each capability section identifies its reason, provenance (`deterministic`, `ai-suggested`, and/or `user-requested`), confidence, exact provider mapping, verification and installed states, official/manual-review package source, provider note, and unresolved advisor questions. A manual-review source is not an automatic install candidate and is not sent through official-repository or installed-package queries by this review.

Review every item when prompted. Optional items can be accepted or rejected. A required item can be challenged, but the wizard records and displays what project need may not work without it. Accepted capability IDs remain the compatibility intent list; every accepted, rejected, or challenged decision is separately stored in top-level `capability_decisions` and rendered in `docs/AI-STACK-RECOMMENDATION.md`. A decision is not permission to install a package or execute a command.

`--install` may invoke `sudo pacman -S --needed` or `sudo apt-get install --yes`; the starter never supplies or stores the password. On Debian/Ubuntu, refresh indexes separately and only when needed:

```bash
./scripts/bootstrap-dev.sh --refresh
./scripts/bootstrap-dev.sh --install
```

The refresh runs `apt-get update` only and does not install or upgrade packages. Bootstrap never runs a full Arch or Debian-family system upgrade. Project-specific setup remains separate from system package installation.

Run the local quality gate:

```bash
./scripts/check.sh
```

## 7. Use the optional Podman sandbox

Choose either the tested `arch-toolchain` or `debian-toolchain` image in the wizard/GUI or `sandbox.image_profile` in an answers file. This is an explicit project toolchain choice: an Ubuntu host may deliberately build the Arch image, and a CachyOS host may deliberately build the Debian image. Host detection never silently changes it.

If you enabled the rootless Podman sandbox, inspect it before relying on it:

```bash
# Normal host terminal, from the host project root:
agent-starter sandbox doctor .
agent-starter sandbox preflight .
scripts/sandbox/preflight
scripts/sandbox/doctor
scripts/sandbox/build
scripts/sandbox/check
```

`scripts/sandbox/preflight` uses `agent-starter` from `PATH` or an adjacent `../agent-starter` launcher when
available, then runs the generated `doctor`, `build`, and `check` wrappers before Codex starts. It writes
`.agent-starter/sandbox/preflight.json` after success. `agent-starter launch .` and generated `START_AGENT.sh`
run this preflight automatically for active sandbox modes. The stamp includes a fingerprint of generated sandbox
inputs; trust it only while `agent-starter status .` or generated `scripts/sandbox/status` reports it as
valid/current. If Codex is already open and preflight is valid/current, do not make Codex rerun
`scripts/sandbox/doctor` or `scripts/sandbox/build` from
inside its constrained sandbox. If the stamp is missing, stale, or failed, run preflight from a normal host
terminal. Do not widen Codex to host full-access just to make these rootless Podman wrappers work. If Codex cannot
access `/run/user/<uid>/libpod` or another rootless Podman runtime path, run verification from a normal host
terminal or launch Codex inside the built container.

Toolchain `check`, `exec`, and `shell` default to no network:

```bash
scripts/sandbox/check
AGENTKIT_SANDBOX_NETWORK=default scripts/sandbox/check   # explicit reviewed opt-in
```

Preflight logs are under `.agent-starter/logs/`. Generated projects also include `docs/CACHYOS-PODMAN.md` for
CachyOS/rootless Podman diagnostics.

Inside the generated container, run project commands directly instead of host-side sandbox launchers:

```bash
./scripts/check.sh
npm test
python3 -m unittest
```

The default `toolchain` sandbox mode keeps Codex on the host editing the local project files and runs project build/test/toolchain work in a container against the mounted `/workspace`. If the sandbox was requested and `doctor`, `build`, or `check` fails, do not treat host checks as equivalent unless you deliberately approve a temporary host-only fallback. If you explicitly selected Codex-inside-container mode, use:

Generated Podman wrappers use `--userns=keep-id` with your current `id -u` and `id -g`, not a fixed UID/GID. On normal rootless Podman setups this keeps files created in `/workspace` owned by your host account.

```bash
scripts/sandbox/codex-login
scripts/sandbox/codex
scripts/sandbox/resume
```

`codex-login` is an explicit user action and stores Codex state in a project-specific container home volume. The generated sandbox does not mount host `~/.codex`, `~/.ssh`, browser profiles, production configs, or the host home directory by default. Prefer `docs/agent-prompts/create-container-handoff.md` to create a no-secrets handoff summary instead of copying raw session transcripts.

For Godot or interactive game projects, containerized headless checks are the default. Godot projects get `docs/GODOT-SANDBOX.md` and a `scripts/sandbox/headless-test` helper that can call a future project-owned `scripts/godot-headless-test.sh` hook for scene/export/screenshot artifacts. Interactive rendering, audio, and controller testing should use `scripts/playtest-host` unless you explicitly enable `sandbox.gui_passthrough`. That advanced option generates `scripts/sandbox/playtest-gui` and intentionally exposes selected host Wayland, GPU, PipeWire audio, and input/controller interfaces to the project container.

Rootless Podman reduces host filesystem risk, but container commands can still change mounted project files and can misuse network access when networking is available. Do not use host full-access as the default answer to permission friction, and do not deploy, push, rsync production targets, or mount real secrets without explicit approval.

## 8. Authorize Codex

From the installed starter:

```bash
agent-starter auth --status
agent-starter auth
```

Use device-code login when browser opening is unsuitable:

```bash
agent-starter auth --device-auth
```

From a generated project, the equivalent helpers are:

```bash
./scripts/setup-agent.sh
./scripts/agent-status.sh
```

All account interaction belongs to the official Codex CLI. Confirm in that flow that you selected the intended ChatGPT account.

## 9. Start implementation

Launch from the generated project:

```bash
less START_HERE.md
less NEXT_STEPS.md
agent-starter status .
./START_AGENT.sh
```

Or use the installed starter:

```bash
agent-starter launch /path/to/project
```

`START_HERE.md` is the short human entry page: project summary, honest generated-baseline status, three non-mutating first checks, one next action, and help pointers. `NEXT_STEPS.md` supplies the detailed local checks, placeholder scripts, GitHub pause, and Codex setup path. Codex prompts read `docs/AGENT-INDEX.md` first, select the matching task row, and load only its minimum relevant references; `docs/README.md` retains the full reference catalog. `agent-starter status`
summarizes generated-file validation, Codex readiness, Git/GitHub state, ignored AI-local artifacts, and the next
recommended local action. Codex receives `FIRST_PROMPT.md` as its initial instruction. A noninteractive first pass is also available:

The binding `AGENTS.md` canonical policy registry owns model, command-network, deployment/external-action,
current-progress, and implementation-note rules. Generated prompts point there and to the named owner files; prompt
text cannot select a different model, enable command networking, authorize deployment, or choose alternate ledgers.
For deployment, Codex may prepare code, docs, tests, plans, and sandboxed local plan/check/build evidence. It must stop
before remote apply, repository push, release publication, database migration, or secret access unless a separate
human-approved tool operation is invoked. Every task-composer packet repeats this boundary, and typing “deploy it” into
a request is not production authorization.

```bash
agent-starter launch /path/to/project --kickoff
```

The initial prompt tells Codex to inspect the existing repository, verify the project hypothesis, establish or repair the test baseline, update project docs, work the first safe phase, and record an implementation note.
Generated agent instructions also tell Codex to avoid "god files": do not keep pushing unrelated UI, domain logic, persistence, networking, state, configuration, and tests into one oversized file. Small projects can stay simple, but files should split by responsibility once they start mixing concerns.

## 10. Continue safely

At every meaningful phase:

1. Read local AI working docs such as `AGENTS.md`, current progress, recent implementation notes, decisions, and handoff.
2. Update the plan before making broad changes.
3. Keep changes phase-sized and avoid unrelated rewrites.
4. Run the closest tests during work and `./scripts/check.sh` before ending the phase.
5. Update requirements, architecture, security, and operations docs when behavior changes.
6. Append a complete local entry to `docs/11-IMPLEMENTATION-NOTES.md`.
7. Refresh local `docs/09-PROGRESS.md` and `docs/14-AGENT-HANDOFF.md` with the exact next step.

A note skeleton can be appended with:

```bash
./scripts/new-implementation-note.sh codex "Implement phase name"
```

When you know what you want next but are unsure how to prompt Codex, generate a continuation prompt from the project metadata and documented workflow:

```bash
agent-starter prompt /path/to/project --request "Add CSV import"
```

When the prior session has a known delta, provide it explicitly:

```bash
agent-starter prompt /path/to/project --request "Finish CSV import" \
  --changes "CSV parsing is characterized." \
  --failures "Malformed rows still fail." \
  --relevant-reference agent_starter/imports.py \
  --relevant-reference tests/test_imports.py \
  --acceptance "Focused and full checks pass." \
  --unresolved-decision "Keep partial imports atomic?"
```

Each continuation includes the objective, changes, failures, exact references, acceptance checks, and unresolved
decisions. Repeat `--relevant-reference` and `--unresolved-decision` as needed. Values are bounded and screened for
credential-like content; references must be safe project-relative paths or dotted modules. If fields are omitted, the
prompt points to current handoff/progress/open-question owners and does not request a full historical-ledger reread.

For a guided prompt builder:

```bash
agent-starter prompt /path/to/project --interactive
```

For task-specific guidance:

```bash
agent-starter prompt /path/to/project --template bug --request "Fix CSV import crash"
```

The prompt is printed to the terminal for copy/paste into Codex. To save it for review:

```bash
agent-starter prompt /path/to/project --request "Add CSV import" --output NEXT_PROMPT.md
```

The generated prompt tells Codex to read the project instructions and current progress, inspect the actual code, work in a small tested phase, update the implementation notes and handoff, and avoid privileged, destructive, credential, publish, deploy, and remote-push actions without explicit approval.

Interactive mode and the GUI Task Composer share six starting choices: Add a feature, Fix a problem, Change existing behavior, Review or improve code, Improve tests/documentation, and Prepare a deployment plan. Feature, fix, and change paths use the outcome/example/compatibility/reproduction questions appropriate to that work rather than a generic questionnaire. Answers are closed, bounded text; credential-like values and unexpected fields reject.

The composer next shows a review-required contract with: what Codex will attempt, what it must not change, files or areas likely involved, tests/acceptance checks, and risks/approvals. **Edit answers** returns to the questionnaire and invalidates that review. **Approve prompt** releases the prompt text for the next step but does not launch Codex, execute a command, or implicitly save a draft. The separate draft controls above remain explicit. Deployment contracts retain an explicit planning-only/no-deploy boundary. Named noninteractive templates remain `feature`, `bug`, `cleanup`, `docs`, `test-baseline`, and `release-prep`.

## 11. Check GitHub readiness

Before creating a GitHub remote, enabling GitHub Actions, or pushing, run:

```bash
agent-starter github-ready /path/to/project
```

The command validates the generated workspace, runs `./scripts/check.sh` unless `--skip-check` is supplied, checks local Git cleanliness, verifies AI-local artifact ignores, and inspects the CI workflow when one exists. It does not contact GitHub, create a repository, push, install packages, or deploy anything.

## 12. Plan a local mirror

To review a local or SSH source mirror command without running it:

```bash
agent-starter rsync-plan /path/to/project /path/to/project-mirror
```

The plan uses `.agent-starter/rsync-excludes` to skip credentials, local databases, caches, Codex session files, prompt drafts, starter proposals/backups, and `.git` history. Add `--run` only after reviewing the command and target. Add `--delete` only when target-side deletion is intended.

## 13. Create an immutable deployment plan

Create a reviewed target-profile JSON using the closed schema documented in generated `docs/16-DEPLOYMENT.md`, then
render human text or canonical JSON plus its SHA-256 digest:

```bash
agent-starter deployment plan /path/to/project --profile deployment-target.json --format text
agent-starter deployment plan /path/to/project --profile deployment-target.json --format json \
  --output .agent-starter/deployment-plans/staging.json
```

The profile and output path must stay inside the project and cannot use symlinks or traversal. Existing output is
never replaced. Profile commands are argv arrays displayed in the plan and never executed. The command records local
Git revision/dirty state but performs no build/check, credential read, network request, remote write, push, migration,
staging/production change, or apply. A plan digest is evidence of exact plan bytes, not deployment approval.

## 14. Check immutable local deployment evidence

Use the JSON plan file created above:

```bash
agent-starter deployment check /path/to/project \
  --plan .agent-starter/deployment-plans/staging.json --format text
```

The command validates the plan digest/schema, project identity and structure, recorded source state, a confined
artifact checksum, and health/rollback declarations. It does not run project tests or commands, build an artifact,
contact a target, inspect credential values, or write files. Facts that require those actions are `unverified`; exit 1
means the evidence is not yet complete, while invalid/tampered input returns 2. No result authorizes deployment.

## 15. Assemble a deterministic local deployment artifact

For a static-site or Linux-service-bundle plan recorded from a clean Git revision, first prepare one dedicated local
build-output directory through a separately reviewed workflow. Then package it without executing any profile command:

```bash
agent-starter deployment build /path/to/project \
  --plan .agent-starter/deployment-plans/staging.json \
  --source public --format text
```

The plan must name a new `.zip` output and list it under `local_writes`. AgentKit assembles twice, compares the bytes,
and atomically creates the output only after they match. The ZIP embeds normalized provenance, per-file checksums,
source revision, display-only commands, tool versions, and an SPDX-2.3 file inventory. Project/profile commands,
credentials, network access, target contact, push, remote writes, and apply remain disabled.

## 16. Use reference-only deployment credentials

Target profiles contain a safe reference name and mechanism, never a value. For example:

```json
{"name": "docs-api", "mechanism": "environment-file"}
```

This refers to `.env.docs-api` at the project root. Create and populate it yourself outside AgentKit, ensure Git ignores
it, and set mode `0600`. Deployment checks use metadata only and never open the file. The `ssh-agent` mechanism checks
only socket metadata without listing keys. OS-keyring, CI-secret-store, and target-secret-manager references remain
`unverified` until reviewed metadata-only adapters exist. Never paste a value into answers, profiles, plans, prompts,
logs, argv, artifacts, provenance, SBOMs, manifests, Git, or implementation notes.

## 17. Understand the apply gate

AgentKit now models—but does not execute—the prerequisites for a future separate apply operation. The gate binds the
exact reviewed plan, complete passing check report, reproducible artifact digest, explicit environment and target,
human target-tool authentication, exact local typed confirmation, available rollback, and redacted audit metadata.
Changing any reviewed plan, artifact, environment, or target binding invalidates approval. Every current target is
blocked because no apply-capable production-ready adapter exists. There is no `deployment apply` command, and prompts
or model output cannot authenticate, confirm, write audit state, contact a target, or perform an apply.

## 18. Check a local Ollama handoff

Codex remains the default and supported agent path. If you want to experiment with a local Ollama model for a later focused task, check whether the installed model is a plausible handoff target first:

```bash
agent-starter ollama-check /path/to/project --request "Add CSV import"
```

The command inspects only local Ollama metadata:

- `ollama list` for installed model names;
- `ollama show <model> --json` for confirmed context length when Ollama exposes it;
- model-name signals such as code-focused and large general-model families.

Only models with strong coding signals and confirmed large context are treated as suitable. Borderline or inadvisable models do not get a handoff prompt unless you explicitly accept the warning:

```bash
agent-starter ollama-check /path/to/project --model llama3.2:3b --override
```

This command does not edit `.codex/config.toml`, switch the generated project away from Codex, install Ollama models, pull models, or run a model against the project. It produces a warning-rich handoff prompt only after the readiness gate passes or is manually overridden.

The reference baseline for this warning is AgentKit's quality-first `GPT-5.6-SOL` policy with medium reasoning. The Ollama check is a conservative local metadata assessment, not a guarantee that a local model will match Codex quality.

Answers schema v2 strictly validates types at CLI, GUI, load, and generation boundaries. Use `agent-starter config migrate --input OLD.json` for a no-write preview or add a separate `--output NEW.json`; the source is never overwritten by migration.
