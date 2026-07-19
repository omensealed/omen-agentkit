# Security model

## Protected assets

- Existing source code and project documentation.
- User account authorization, OAuth artifacts, API keys, keyrings, browser state, and cookies.
- Local files outside the selected project root.
- System package-manager authority and `sudo` access.
- Git history, remotes, repositories, deployments, and production data.
- Integrity of generated commands, tests, project metadata, and implementation notes.

## Main threats and controls

### Existing-file destruction

Generated destinations are validated as safe relative paths. Filesystem root and the home directory itself are rejected as project roots. Parent-directory symlinks are rejected, writes are atomic, unchanged content is retained, conflicts become proposals, and forced replacements create timestamped backups first.

### Model-output command injection

Codex stack advice runs in an empty temporary directory with a read-only sandbox and a strict JSON output schema. Responses are parsed as data, normalized, displayed for review, and not automatically executed. Raw advisor output is removed from persisted project metadata.

Answers-file command arrays require `--allow-custom-commands`. Interactive setup and generated bootstrap scripts show commands before privileged execution.

### Credential capture

The kit never asks for tokens or passwords and rejects common credential-like answer strings. OAuth is executed by the official `codex` command; status checks use `codex login status` and never inspect its storage. Generated instructions prohibit secrets in prompts, source files, logs, tests, and repositories.

The optional desktop GUI follows the same boundary. It is a local frontend over the existing model/generator/validator APIs, uses local static assets, and does not ask for API keys, OAuth tokens, passwords, SSH keys, browser cookies, or Codex credential files.

### Package-manager authority

Provider-scoped package names are validated. Generated bootstrap safely parses only bounded `ID`/`ID_LIKE` values, confirms `pacman` or both `apt-get` and `dpkg-query`, and uses read-only installed-state queries. Default mode prints argv arrays only. `sudo pacman` or `sudo apt-get` is reached only through an explicit reviewed action; APT refresh is a separate `--refresh`, installation is `--install`, and neither performs a full-system upgrade. Tests replace manager and sudo commands with synthetic local scripts.

The platform-provider boundary represents future update/install actions only as argument vectors with explicit network and privilege requirements. Provider methods do not grant execution authority. Host facts are exported through a redacted `HostProfile` allowlist that excludes user/host identity, paths, network addresses, environment values, histories, credentials, browser state, SSH configuration, and unrelated installed packages.

Platform detection reads only bounded `/etc/os-release` text, Python-reported architecture, and availability of an expected package-manager executable. It does not execute package managers or enumerate packages. A provider cannot be inferred from executable presence when OS metadata is unsupported or contradictory; explicit overrides require executable proof and produce a warning when metadata disagrees.

The Arch provider permits only validated package identifiers in read-only `pacman -Qq` installed-state and `pacman -Si` repository-metadata queries. Update/install methods return argv for human review and do not execute it. Install plans require verified official-repository records. AUR/manual records are unverified, non-installable, and cannot enable or invoke `yay`, `paru`, or another helper.

The Debian-family provider permits validated `dpkg-query` installed-state and `apt-cache policy` candidate queries. Refresh and install are separate, review-only `apt-get` argv plans; no upgrade, PPA, source-list, signing-key, or pinning mutation is generated. Any third-party capability must document source, key, pinning, and removal review and remains non-installable until a separately approved future policy exists.

Source CI keeps `contents: read` by default. Pull requests receive read-only dependency review. Only a tested main/dispatch
artifact job receives narrow `id-token: write` and `attestations: write` permissions to bind GitHub-hosted provenance to
the create-only wheel/sdist checksum subjects; it has no contents/package/release/deployment write permission. Evidence
generation rejects symlinked, special, ambiguous, oversized, substituted, or previously evidenced artifacts. Automated
dependency updates are untrusted human-review proposals and never auto-merge. See `docs/SUPPLY-CHAIN-POLICY.md`.

Source `doctor` detects the provider before capability checks and performs installed-state queries only: `pacman -Qq` for Arch-family or `dpkg-query` for Debian/Ubuntu. It skips the query when the selected manager is missing and never invokes repository checks, refresh/update/install plans, `sudo`, or source changes. Its JSON report is an explicit redacted allowlist with bounded evidence and excludes executable paths, user/host identity, environment values, and secrets. Codex authorization is reported only through the existing official CLI boolean status boundary.

### Codex overreach

Generated `.codex/config.toml` uses workspace-write sandboxing, on-request approval, command network access disabled, and cached web search. Generated instructions prohibit unrelated paths, credential stores, permission-bypass options, destructive migrations, remote pushes, repository publication, deployment, and irreversible operations without human approval.

Generated `START_HERE.md` is bounded human-facing orientation, not execution authority. Its first-command block contains only local diagnosis, review-only bootstrap planning, and the aggregate check. It contains no install, sudo, login, network-enablement, publish, deploy, or remote action. Existing files retain normal proposal/backup protection, and the page remains trackable end-user documentation rather than ignored AI-local state.

Generated `docs/AGENT-INDEX.md` is navigation, not authority. It points to the binding `AGENTS.md` and owning security, operations, release, status, decision, and testing documents instead of copying their full policies. Its deployment row is planning-only and grants no credentials, remote access, installation, publication, or production change. Existing indexes retain normal proposal/backup protection and remain trackable documentation.

Generated `docs/16-DEPLOYMENT.md` is also documentation, not an executable plan or approval record. It derives the
four exact plan-only targets from the typed source registry, leaves staging/production disabled, and requires artifact
provenance, reference-only secret mechanisms, backup/migration analysis, health evidence, rollback, monitoring, and
human ownership. It contains no executable adapter, credential value, remote destination, or default target. Existing
runbooks remain untouched and receive a proposal through the normal conflict-safe writer.

Generated check CI pins each official action to a reviewed full commit SHA and retains only workflow-level
`contents: read`. The typed deployment CI policy keeps deployment jobs disabled. A later supported-cloud adapter must
scope `id-token: write` to its separate deploy job, use GitHub OIDC instead of long-lived credentials, separate build
and deploy environments, require protected production approval, and bind checksum plus attestation evidence to the
reviewed artifact. These requirements do not themselves authorize deployment.

Action-pin validation is offline and registry-bound. Every generated `uses:` line must contain a full lowercase
40-character SHA and matching semantic release comment from the reviewed typed registry. Mutable tags/branches, short
SHAs, missing comments, unknown actions, and mismatched pins fail generated-workspace validation. Pin updates follow
`docs/GITHUB-ACTIONS-UPDATE-POLICY.md`; automated proposals are never auto-merged and do not gain permissions.

The sole staging adapter is a disposable in-memory static-site test double. It stores an artifact digest only and
always rolls back to the exact prior state. It refuses production, wrong targets, dirty source, stale plan/artifact
evidence, failed or incomplete checks, and missing health/rollback declarations before changing disposable state.
It never reads plan commands or credential references and has no CLI, generated-script, filesystem, subprocess,
network, remote-target, authentication, or production path. Its audit events have a closed value-free schema.

`deployment plan` treats target-profile JSON as untrusted data: closed fields and types, bounded lists/text/files,
exact target/environment/credential-mechanism enums, project-relative paths, symlink/traversal refusal, secret-like
value rejection, and required health/rollback evidence. Profile commands are argv arrays serialized for review and
are never executed. Source evidence uses only fixed local Git `rev-parse` and `status` queries with fsmonitor, optional
locks, global config, system config, inherited `GIT_*` overrides, and terminal prompting disabled; dirty path names and Git errors are not persisted. Canonical plan
JSON excludes the absolute project path and is SHA-256 bound. Optional output uses atomic create-only confinement and
cannot replace a prior plan. The command performs no build/check, credential read, network access, remote write, push,
migration, staging/production change, or apply, and the digest grants no such authority.

`deployment check` treats the saved plan as untrusted, bounded, project-confined JSON. It requires exact wrapper and
payload fields, revalidates the target/profile contract, and recomputes the canonical SHA-256 before inspecting local
evidence. Artifact hashing refuses traversal, symlinks, special files, more than 10,000 files, or more than 512 MiB.
The check runs AgentKit structural validation and fixed local Git inspection only; it does not run project/profile
commands, build, read credentials, use network access, contact a target, write, or apply. Facts that cannot be proved
inside those boundaries are `unverified`, make the report non-ready, and receive an actionable remedy.

`deployment build` is a bounded standard-library artifact assembler, not a command runner. It supports only static-site
and Linux-service-bundle plans with a new `.zip` output explicitly declared in `local_writes`, exact project identity,
an exactly matching clean Git revision, and a dedicated non-root project-local source. It refuses traversal, source or
parent symlinks, special files, credential-prone names before opening them, more than 10,000 files, more than 32 MiB of
input, more than 40 MiB of output, output-inside-source, and replacement. Accepted files are opened without following
their final symlink where supported. Two normalized ZIP assemblies must match before the existing atomic create-only
primitive writes once. Embedded provenance binds the plan, source revision, display-only argv, checksums, and tool
versions; an SPDX-2.3 inventory binds every payload checksum. No project/profile command, external builder, credential,
network, target, push, remote write, or apply action runs merely because assembly succeeds.

Deployment secret handling is reference-only. The canonical mechanism registry accepts `none`, `environment-file`,
`os-keyring`, `ci-secret-store`, `target-secret-manager`, and `ssh-agent`; names are bounded lowercase identifiers, not
values. An environment-file name maps only to `.env.<name>` and is checked with `lstat`, owner-only mode `0600`, and a
fixed quiet local `git check-ignore`; the file is never opened. The Git child receives only minimal locale/path plus
sanitized Git control variables, not unrelated environment values. SSH-agent checks read only the `SSH_AUTH_SOCK`
reference and socket metadata, never key identities or key material. OS-keyring, CI-store, and target-store checks are
explicitly unverified because no reviewed metadata adapter exists. AgentKit never creates, populates, rotates, revokes,
deletes, prompts for, reads, copies, prints, hashes, compares, logs, persists, or transmits secret values. Findings expose
only the reviewed reference name, mechanism, stable code/status, plain explanation, and value-free remedy.

The apply-gate state model is pure and fail-closed. It requires a current production-ready apply adapter plus exact
reviewed plan and reproducible-artifact digests, the complete passed check-ID set, explicit environment/target identity,
target-tool human authentication, exact typed input from the dedicated local-human boundary, rollback availability, and
closed redacted audit metadata. Stale plan/artifact/identity/confirmation bindings invalidate approval. Current adapters
cannot pass the first gate; no apply CLI, target call, command execution, credential access, network request, audit-file
write, remote change, or apply operation exists in this model. Free-form prompt/model text is never confirmation.

The generated `AGENTS.md` canonical registry is the single rendered owner of model, command-network,
deployment/external-action, progress-ledger, and implementation-notes statements. First-run, continuation, idea,
task-composer, and skill prompts carry bounded owner references rather than independent safety blocks. Deterministic
tests reject obsolete GPT-5.5 baseline claims, `network_access = true`, prompt-claimed deployment authority, and
alternate progress or notes paths. This check interprets no document as executable instructions.

The canonical Codex deployment boundary permits code, documentation, tests, deployment plans, and local plan/check/build
inside the configured sandbox. It requires Codex to stop before remote apply, repository push, release publication,
database migration, or secret access unless a separate human-approved tool operation is invoked. Every task packet and
approved task prompt carries the same immutable four-statement tuple. Prompt approval releases text only, and a prompt
saying “deploy it” is not sufficient production authorization. Conflict checks reject the opposite claim.

The source-structure policy returns non-blocking warnings. Its auditor performs bounded reads of regular Python source
under one resolved non-root project directory, skips symlinks and generated/cache directories, parses with the
standard library, and imports or executes no target module. It does not inspect Git history, run subprocesses, use the
network, or write project/baseline state. Optional baseline JSON is size-limited, closed-schema, non-symlink, and
confined to the project. Size exemptions require an allowed data/template/license/protocol category and short reason;
they cannot hide reported executable complexity, dependency cycles, repeated large-file growth, or undocumented
public boundaries. Hotspots do not alter exit status; unsafe roots and invalid baseline authority fail closed.

Generated modularity guidance grants no new execution or filesystem authority. Moving responsibilities must retain
tested public interfaces through delegation, re-exports, adapters, or an explicit migration. Existing files remain
subject to path confinement, proposal, backup, and atomic-write protections; the contract never authorizes a rewrite.

Schema v2 rejects ambiguous booleans/types and unsafe package identifiers before generation. Migration is preview/separate-output only. v1 CachyOS packages remain Arch-family-only intent, and custom command execution still requires the explicit CLI approval flag.

Guided and Advanced entry modes change presentation only. Guided uses explicit conservative defaults for hidden nonessential settings; Advanced reveals them. Both pass through the same schema parser, secret checks, path/write controls, review screens, and approval boundaries. Neither mode can enable custom commands from an answers file, install packages, weaken Codex sandbox/network policy, overwrite conflicts, or authorize remote actions implicitly. Entry mode is not trusted or persisted as project authority.

Task-composer packets contain one enum task kind and a closed set of bounded text answers. Unexpected fields, wrong types, controls, excessive lengths, invalid choices, and credential/private-key patterns reject before rendering. GUI and CLI share the exact validator. A derived contract is review-required until the human chooses Edit answers or Approve prompt; approval releases text only and contains no launch, argv, filesystem, subprocess, network, or remote-action authority. Editing causes a new packet and contract. The deployment-plan kind embeds a no-deploy/no-publish/no-production-change boundary in both contract and prompt.

Source deployment target contracts are fail-closed and permit only reviewed local operations. Static-site and
Linux-service-bundle additionally permit deterministic ZIP assembly; OCI and SSH/rsync remain plan/check-only. The exact reviewed identifiers are `static-site`,
`oci-image`, `linux-service-bundle`, and `ssh-rsync`; display labels are not accepted as IDs, and generic cloud or
Kubernetes claims have no adapter contract. Every current contract denies network access, remote writes, secret
values, push/apply, and production readiness. Plans must identify source state, environment/target identity, artifact inputs/outputs and provenance,
remote effects, exact commands for separate review, network destinations, credential mechanisms by reference only,
health evidence, rollback, monitoring/log locations, and maintenance ownership. This model does not itself write a plan or execute any operation.

Presentation diagnostics never include tracebacks. Their technical-details field is bounded and redacts credential assignments, private-key blocks, authorization headers, cookies/session IDs, and common token forms; filesystem and subprocess mappings do not serialize paths or argv. `project_changed` is supplied by the operation boundary rather than inferred from an exception string. Generation uses a private callback invoked only after successful AgentKit mutations; validation, status, read, preview, task, and draft-error paths report false. A nonzero external Codex run reports true conservatively and instructs the user to inspect for partial changes.

The desktop-only diagnostic log repeats the redaction and also strips absolute paths. It lives under XDG state with 0700/0600 permissions, a 256 KB rotation bound, symlink refusal, one JSON object per line, and no stack trace or raw exception. Logging is best-effort and cannot trigger retry, login, generation, launch, network access, or another write outside its own user-local state file.

Draft sessions store only closed, bounded GUI presentation fields and partial relevant task answers. They reject credential/private-key/token-like patterns before creating the storage directory. They are not `ProjectConfig`, approved prompt data, or execution authority. The XDG user-data directory and entries use modes 0700/0600; reads are bounded; malformed, unknown, oversized, or symlinked entries fail closed; writes use atomic create/replace. Export refuses existing destinations and symlinked parents. Resume never generates, approves, launches, installs, contacts a network, or changes project files.

Accessibility helpers grant no additional authority. Step navigation and focus movement only change presentation. Remediation commands are inserted with `textContent`, remain selectable, and the copy button writes only the already-sanitized displayed string to the clipboard; it never evaluates or executes command text. Confirmations explicitly distinguish prompt release, deletion of one local draft, and project-scoped generation. They do not weaken canonical validation, conflict/proposal handling, path confinement, or later launch controls.

The GUI cannot launch from an unreviewed or stale state. Launch preview validates required project files, strictly loads project metadata, confines and bounds `.codex/config.toml`, refuses symlinks, and verifies explicit model/reasoning or inherited-global absence plus on-request approval, workspace-write sandboxing, command networking off, and cached web search. The displayed summary is fingerprinted only in bridge memory. Launch revalidates and recomputes before consuming that fingerprint and closing the window. Validation errors, conservative-policy drift, target changes, missing previews, and stale previews report `project_changed: false` and never call the Codex launcher.

The CLI launch boundary also runs full validation before rootless-sandbox preflight, Codex adapter lookup, authorization, or launch. Invalid generated workspaces therefore cannot bypass the GUI gate by using the shared launcher directly.

New advisor output selects only enum-constrained canonical capability IDs, not raw host package names. Loaded capability intent is strictly list-parsed and rejected when unknown. Provider resolution owns package names and repository policy. Legacy saved advisor package suggestions remain documentation-only Arch intent and never enter execution automatically.

The optional repo-local `$agentkit` skill is a local prompt-building workflow only. It does not send keystrokes into an open terminal, run a daemon, add MCP/app-server/plugin automation, call OpenAI or GitHub, inspect Codex credentials, modify `~/.codex/config.toml`, start `codex login`, or bypass Codex approvals. Skill updates are managed through a versioned JSON sidecar and backed up before replacement.

### Rootless Podman project sandbox

Optional sandbox generation separates three layers:

- Codex's own sandbox: `read-only`, `workspace-write`, and other official Codex approval modes.
- Rootless Podman project container: container filesystem plus the project bind mount at `/workspace`.
- Host system: not mounted except for the selected project workspace and explicit local artifacts.

The generated sandbox does not mount host `~/.codex`, `~/.ssh`, browser profiles, GPG/SSH agents, GitHub credentials, production configs, or the host home directory by default. Codex-inside-container mode uses a project-specific Codex home volume and requires the user to run `scripts/sandbox/codex-login` deliberately. The scripts must not capture device codes or tokens and must not inspect Codex credential files.

Rootless Podman reduces host filesystem risk, but untrusted code can still modify mounted project files and can misuse network access if networking is available. Generated toolchain `check`, `exec`, and `shell` wrappers default to `--network none`; network-enabled runs require an explicit reviewed `AGENTKIT_SANDBOX_NETWORK=default ...` opt-in. Generated docs prohibit `--dangerously-bypass-approvals-and-sandbox`, host full-access as the default permission answer, production secret mounts, deployment, rsync to production, GitHub pushes, and remote resource creation without explicit approval.

Provider matrix tests use synthetic OS metadata and injected/read-only behavior. The optional preloaded-image check uses `--pull=never`, `--network=none`, no-new-privileges, and dropped capabilities; it runs only a fixed package-manager version argv and performs no package refresh, install, or update. See `docs/SUPPORTED-HOSTS.md`.

AI advisor host context is an explicit allowlist rendered before first use. It may contain OS identity fields, architecture, selected provider, bounded executable availability/version facts, rootless Podman prerequisite status, and project-selected languages/targets. It has no representation for usernames, hostnames, home/project paths, IP addresses, environment dumps, histories, tokens, browser state, SSH configuration, or unrelated installed packages. The disclosure is passed only in the temporary read-only advisor request and is not saved as project metadata.

Advisor output is untrusted JSON validated against a closed, bounded capability-first contract. Unknown/additional fields, package-name or command-array fields, unknown/duplicate capabilities, invalid requirement/confidence values, malformed types, control content, and excessive counts/lengths are rejected. High-signal shell metacharacter patterns, privileged/destructive commands, download-to-shell pipelines, credential requests, and prompt-injection directives also reject the entire response before recommendation construction or caching. Errors identify only the violated policy and do not echo hostile text. Accepted text remains data only; it cannot directly alter provider package resolution or process argv. Legacy saved command suggestions remain documentation-only and retain their separate explicit custom-command approval boundary.

The recommendation review adds the deterministic project baseline before provider resolution, so advisor omission cannot remove required intent. Only canonical capability IDs reach a provider; only provider-owned official/installable candidate names receive read-only repository and installed-state queries. Unknown capabilities and unsupported providers remain visibly unresolved. The pipeline never requests an update/install plan, never executes a command, and clears raw advisor output.

Provenance and confidence are display evidence, never authority. A capability may retain multiple typed sources without becoming approved. Provider mappings expose exact verification, installed, official/manual-review, installability, and explanatory states. Manual/third-party records remain unverified, non-installable, and excluded from official repository and installed-state queries. Unresolved advisor questions remain visible as untrusted text and cannot alter provider input or process argv.

Per-item decisions are strict project-owned records separate from untrusted advisor fields and raw output. Required baseline needs cannot be relabeled optional or rejected; they may be challenged only with a visible limitation. Optional needs may be accepted or rejected. Accepted IDs select intent, while rejected/challenged records preserve the human choice for audit. No decision state is installation approval, subprocess authority, or permission to weaken sandbox/network policy.

Review provenance fails closed: local fallback and manual selection explicitly say they are not AI-reviewed, while old saved data with uncertain provenance says AI review is not established. Offline fallback calls no advisor and needs no network. It still uses the same canonical capabilities, provider boundaries, human decisions, redacted persistence, and generation validation as a live reviewed response.

The optional recommendation cache persists only a revalidated copy of the closed structured response, never raw advisor output, package/command arrays, the redacted host snapshot, project paths, or a separate plain project-configuration record. Its opaque key hashes intent with a non-identifying OS-version/architecture/provider fingerprint so relevant changes invalidate reuse. The cache directory/file modes are private, writes are atomic, reads are bounded, and symlinked or malformed entries are refused. Cached content remains untrusted data and grants no package, subprocess, network, or approval authority.

Generated sandbox launcher scripts are host-side wrappers unless they explicitly detect `AGENTKIT_INSIDE_SANDBOX=1` and run direct project commands. Containers receive this environment marker, use rootless Podman `--userns=keep-id` plus the current `id -u` / `id -g` instead of a hard-coded UID/GID, and generated docs tell inside-container agents to run commands such as `./scripts/check.sh` rather than starting nested Podman. Project container home/cache paths are project-local under `.agent-starter/`, not the real host home. The sandbox does not mount the Podman socket and does not use privileged Podman-in-Podman behavior.

The tested `arch-toolchain` and `debian-toolchain` image profiles are explicit project choices independent of host-provider detection. Container images keep `/home/codex` non-world-writable. Codex-inside-container mode uses Podman's ownership adjustment only on its project-specific named home volume, while the shared `/tmp/agentkit-home` uses sticky-directory permissions appropriate to a temporary home mount point.

Generated preflight writes `.agent-starter/sandbox/preflight.json` with a fingerprint of generated sandbox inputs and log files under `.agent-starter/logs/`. Codex guidance treats the stamp as trustworthy only when current, and tells constrained sessions to ask the human to run host preflight from a normal terminal when the stamp is missing, stale, or failed.

Game/Godot GUI passthrough is an advanced opt-in profile. When enabled, the generated playtest helper intentionally exposes selected host Wayland, GPU, PipeWire audio, and input/controller interfaces to the project container for local interactive playtesting. It remains off by default, does not mount host home, Codex credentials, SSH keys, or the Podman socket, and headless checks remain the preferred autonomous Codex path.

Host Codex session/history import is not automatic. Generated projects prefer a no-secrets handoff summary in `docs/CODEX-HANDOFF.md` over copying raw session transcripts or auth files into the container.

### Local-model overreach

Ollama support is limited to a local readiness check and warning-rich handoff prompt. The starter inspects installed model metadata and refuses inadvisable handoff prompts unless the user passes `--override`. It never pulls models, installs packages, sends repository content to Ollama, executes local-model output, rewrites Codex configuration, or changes project metadata away from Codex.

### Repository and network side effects

Git initialization is local and creates no commit. GitHub Actions are deferred by default so local setup and tests can prove the project before CI noise is introduced. GitHub repository creation is optional, uses the official `gh` client, and does not push code. Network access, account handling, payments, and personal-data requirements are captured in the project security docs and phase plan.

The source CI keeps the complete check suite on native Ubuntu across the supported Python matrix. Its focused provider
job uses network only in the explicit official-image preload step. Debian/Arch smoke execution then disables container
networking and pulling, drops capabilities, enables no-new-privileges, mounts generated projects read-only, and invokes
only bootstrap plan mode. It never selects refresh/install and does not repeat the full suite in either container.

Maintainer lint/type/security/coverage tools are constrained under the optional `quality` extra and are not runtime
dependencies. Their separate script checks local availability before use, never installs or downloads a tool, keeps its
coverage data in a temporary file, and cannot make the standard-library trusted suite depend on network access. Bandit
is a static signal rather than proof of security; findings still require source review and regression tests.

Artifact smoke installs locally built wheel and sdist with `--no-index --no-deps`; the sdist build sees only the
already-installed runner build backend and verifies AgentKit resolves from its temporary venv. GUI help never imports
pywebview or opens a display. User-local install/uninstall treats a fixed marker or narrowly recognized legacy layout as
ownership evidence, preflights launcher and data paths before replacement, refuses symlinks/unrecognized paths, and
never follows an external target for removal. Generated projects and Codex authorization remain outside uninstall scope.

Release publication is isolated from ordinary CI. The source workflow is manual-only, requires selection and repetition
of an exact existing semantic tag, defaults publication off, and refuses dirty/version/changelog/ref mismatches. Test and
build code gets no write-capable token and checkout credentials are not persisted. Only the post-verification
`release`-environment job has `contents: write`; it has no checkout, downloads one fixed-name candidate through a pinned
official action whose digest mismatch default is error, rechecks artifact checksums and tag-to-commit binding, then creates
a draft release before its final publish operation. There is no pull-request, workflow-run, push, schedule, package-index,
container-push, deployment, migration, credential-inspection, automatic overwrite, delete, or rollback path.

The focused `scripts/security-regression-check.sh` gate and its full-suite-discovered test module lock the major safety
boundaries together: unsafe roots/symlink parents/traversal, credential-like answers, strict types and package names,
AI command injection, collision-safe prompts, redacted GUI errors, stale or wrong deployment evidence, and conservative
sandbox mounts/networking. The suite is standard-library-only, synthetic, non-networked, and non-executing; its durable
scope and change rule are documented in `docs/SECURITY-REGRESSION-SUITE.md`.

## Residual risks

- Users can manually approve unsafe commands or weaken generated Codex settings.
- Third-party compilers, package repositories, GitHub Actions, and Codex itself remain external trust dependencies.
- A model can produce incorrect code even inside a sandbox; tests and human review remain necessary.
- Existing projects may contain their own malicious build scripts or instruction files; Codex and the user must inspect them before execution.
- Authorization status proves that Codex reports a session, not which human account is intended; the user must verify the account in the official login experience.
- Backups stored inside a project can still be deleted by later manual action; source control and external backups are recommended for valuable projects.
