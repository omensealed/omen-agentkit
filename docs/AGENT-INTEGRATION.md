# OpenAI Codex integration

## Supported client

This edition integrates only with the official `codex` command. The adapter detects the executable, reports `codex --version`, checks authorization with `codex login status`, starts browser OAuth with `codex login`, and can request device-code authorization with `codex login --device-auth`.

The official installer command exposed by the starter is:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

It is displayed first and executed only after explicit approval. Tests never run the installer or make account/network calls.

## Authorization boundary

The starter never proxies OAuth and never reads Codex credential storage. It launches the official CLI as a child process and uses only its exit status. This keeps account selection, browser authorization, token refresh, revocation, and secure storage inside Codex.

The relevant starter commands are:

```bash
agent-starter auth --status
agent-starter auth
agent-starter auth --device-auth
agent-starter auth --relogin
```

Generated workspaces expose the same boundary through `scripts/setup-agent.sh` and `scripts/agent-status.sh`.

## Read-only stack advisor

When the user asks Codex to recommend a stack, the adapter creates an empty temporary directory, supplies a strict capability-only JSON schema, and runs `codex exec` with a read-only sandbox. The response is parsed as JSON, normalized, provider-resolved, and shown to the user. The wizard records a separate human decision for every capability; required challenges include limitations. Advisor output cannot provide commands or package names, and no decision authorizes execution.

Responses containing command-shaped shell syntax, privileged/destructive or download-pipe instructions, credential requests, or prompt-injection directives are discarded before caching or provider review. Parser errors state the policy category without reproducing hostile text. The wizard then uses a reviewed retry, a valid prior cache entry, or the complete deterministic fallback; it never executes or repairs the hostile suggestion.

If Codex is unavailable, unauthorized, times out, fails, or returns malformed output, the wizard falls back to deterministic local recommendations based on project type, constraints, and built-in toolchain mappings. Terminal and generated output explicitly label this `Local deterministic default — not AI-reviewed`. The fallback still completes provider review, human decisions, generation, and validation without contacting Codex or the network.

A successful strictly parsed result can be reused from a private structured-only cache. The wizard labels this `Cached AI-reviewed structured recommendation`, announces the hit, and offers an explicit default-off refresh when Codex is available. Cache reuse never bypasses the normal provider review or per-item decisions and never grants command, package, network, or installation authority.

Raw model output is removed before project metadata is persisted.

## Project launch

Interactive launch passes the complete `FIRST_PROMPT.md` content to Codex while setting the generated project as the working directory. One-shot kickoff uses `codex exec` with workspace-write sandboxing. The generated `.codex/config.toml` defaults to exact `gpt-5.6-sol` with medium reasoning, on-request approval, workspace-limited writes, command networking disabled, and cached web search. Inherited-global policy omits only model/reasoning keys. A failed explicit-policy launch is reported without choosing a fallback.

The starter does not use permission-bypass flags, auto-publish changes, push Git remotes, deploy software, or grant access outside the selected project.

## Continuation prompts

After the first session, `agent-starter prompt /path/to/project --request "..."` generates a copy/paste Codex prompt for the next focused phase or feature request. It loads only the generated project metadata, not raw credential stores or large project-document excerpts, and tells Codex to read the current project memory inside the sandbox before editing.

Generated `START_HERE.md` is for the human handoff before agent context: a short project summary, honest baseline status, safe local checks, one next action, and pointers to `NEXT_STEPS.md`, `docs/README.md`, and `AGENTS.md`. It does not replace the Codex contract or prompt and contains no privileged or network-enabling action.

Generated first-run, continuation, idea, and task-composer prompts read `docs/AGENT-INDEX.md` first. Its task table selects the minimum relevant project memory before `AGENTS.md` applies the binding policy; full reference browsing remains available through `docs/README.md`. The index contains pointers and freshness metadata, not executable commands or duplicated authority.

Continuation prompts and generated `docs/14-AGENT-HANDOFF.md` share a delta contract: current objective, changes since
the prior handoff, current failures, exact relevant docs/modules, acceptance checks, and unresolved decisions. Optional
CLI delta values are bounded, credential-screened, and restricted to safe project-relative references. Missing values
point to current owners; prompts explicitly avoid reading every historical implementation-note entry by default.

`agent_starter.policy_fragments` defines the durable generated model, command-network, deployment, progress, and
notes policies once. `AGENTS.md` renders that registry; every prompt surface and the repo-local skill render shared
owner references. The task composer retains its planning-only deployment boundary through the same domain constant.
Its exact P6-008 tuple permits code/docs/tests and sandboxed local plan/check/build, then requires Codex to stop before
remote apply, repository push, release publication, database migration, or secret access unless a separate
human-approved tool operation is invoked. Every serialized task packet and approved task prompt includes this tuple;
free-form “deploy it” wording cannot authorize production.

Generated `AGENTS.md` and `docs/02-ARCHITECTURE.md` also render the same modularity contract. Codex must identify the
existing responsible module and its callers/tests before editing, prefer a coherent vertical slice, avoid unrelated
append-only growth and placeholder abstractions, update the project/module map when responsibility moves, and retain
tested public-interface compatibility. The contract does not require splitting cohesive files solely by line count.
The source renderer is `agent_starter.template_sets.architecture`; the legacy `agent_starter.templates` surface
delegates directly so installed and source-checkout callers retain identical output.

Generated license artifacts likewise come from `agent_starter.template_sets.licenses`. The compatibility surface
retains the established MIT, SPDX-notice, AGPL function, and AGPL-text names without changing generated bytes.

The human entry path (`README.md`, `START_HERE.md`, and `NEXT_STEPS.md`) comes from
`agent_starter.template_sets.orientation`; optional AgentKit-skill and sandbox sections shared with other documents
come from `agent_starter.template_sets.shared_sections`. Legacy renderer and section names remain direct exports,
and extraction does not change the generated orientation, launch, approval, network, or credential guidance.

Repository-local support artifacts come from `agent_starter.template_sets.repository_support`. The established
`.gitignore`, rsync-exclusion, `.env.example`, and `.editorconfig` renderer names remain direct compatibility
exports; the move does not change secret exclusions, local AI/runtime exclusions, example values, or mirror scope.

Generated `docs/README.md` and `docs/AGENT-INDEX.md` routing comes from
`agent_starter.template_sets.navigation`. The former remains the complete human documentation map and the latter
remains the compact task-to-minimum-context map read first by prompts. Both established renderer names remain direct
compatibility exports, and canonical policy ownership or task routing is unchanged.

Generated progress, decisions, implementation notes, handoff, and open questions come from
`agent_starter.template_sets.project_memory`. These five files remain one durable continuity contract: concise
current state, append-only decisions/work chronology, exact next-agent state, and unresolved decision inputs.
Established renderer names remain direct compatibility exports and ledger ownership is unchanged.

Generated project brief, requirements, and implementation plan come from
`agent_starter.template_sets.project_definition`. They jointly preserve scope, risk-specific requirements,
acceptance evidence, existing-project compatibility work, and the ordered Phase 0–4 gates. Established renderer
names remain direct exports and database-specific guidance continues to come from the canonical toolchain table.

Generated stack and development-environment guidance comes from
`agent_starter.template_sets.technology_environment`. It also owns the reviewed custom-command versus conservative
built-in command selector shared by generated docs and scripts. Existing `agent_starter.templates` names remain
direct exports; advisor command suggestions remain documentation-only and provider safety text is unchanged.

Generated testing, security/privacy, and UX/accessibility guidance comes from
`agent_starter.template_sets.quality_risk`. These documents jointly define quality evidence, prioritized loss/abuse
controls, safe user recovery, and accessible observable behavior. Existing renderer names remain direct exports;
test-command policy continues to come from the technology/environment family.

Generated binding `AGENTS.md`, structured advisor review, and `FIRST_PROMPT.md` come from
`agent_starter.template_sets.agent_guidance`. The family assembles canonical policy-owner references, modularity,
reviewed command selection, and optional skill/sandbox sections without taking ownership of those shared policies.
Established renderers and compatibility helper attributes remain directly available from `agent_starter.templates`.

Generated release checklist, deployment plan/check worksheet, operations/recovery guidance, contribution rules, and security reporting policy come
from `agent_starter.template_sets.release_operations`. The family preserves human-only publication/deployment,
backup/rollback, minimum-disclosure, and durable-ledger requirements while consuming canonical database guidance and
the typed deployment registry. `docs/16-DEPLOYMENT.md` selects no target/environment and grants no build, network,
remote-write, secret, staging, production, or apply authority.

`agent_starter.deployment_plan` converts a strict project-local target profile plus fixed local Git source evidence
into immutable canonical plan data and a SHA-256 digest. `agent_starter.deployment_check` verifies strict plan bytes and
bounded local evidence while identifying facts that remain unverified. `agent_starter.deployment_build` deterministically
assembles supported local ZIP inputs twice and embeds provenance/SPDX. `cli_app.deployment_commands` exposes all three
as nested commands. Profile argv is display-only and never executed. No path grants credential, network, remote,
target-contact, push, or apply authority; plan/artifact outputs cannot replace existing files and checks write nothing.

`agent_starter.deployment_secrets` provides the shared exact mechanism registry and value-free metadata findings used
by profile parsing and deployment checks. Environment-file checks use regular-file/0600/Git-ignore metadata without
opening contents; SSH-agent checks use socket metadata without listing keys. OS keyring, CI, and target stores remain
unverified. Reports contain safe reference names and stable codes only, never values or store output.

`agent_starter.deployment_gate` models every prerequisite for a later separate apply boundary and always fails closed
against the current adapter registry. Its typed evidence binds the exact reviewed plan, complete passing check report,
reproducible artifact digest, environment/target identity, target-tool human authentication, separate local typed
confirmation, rollback, and redacted audit metadata. Binding changes invalidate approval. It provides no CLI command,
credential access, audit persistence, network/target contact, remote write, or apply behavior.

`agent_starter.deployment_ci` is non-executing typed policy. It owns generated official-action full-SHA pins and the
future GitHub OIDC, least-permission, separate build/deploy job and environment, protected production approval,
checksum, and attestation requirements. Current generated CI remains check-only with no deploy job or `id-token` grant.
Its offline validator rejects mutable, unknown, or review-mismatched action references. Maintainers must follow
`docs/GITHUB-ACTIONS-UPDATE-POLICY.md`; model or issue text is not trusted pin evidence.

`agent_starter.deployment_staging` is a library/test-only disposable state machine. It accepts no free-form command,
executes nothing, stores one in-memory staging artifact digest, and always restores the prior digest after health
evaluation or injected partial failure. Its closed events exclude profile commands and secret references. There is no
Codex, CLI, generated-script, network, real-target, or production route to it.

Generated doctor, build/test/lint/check/run, Codex-start, and GitHub CI artifacts come from
`agent_starter.template_sets.script_workflows`. It consumes reviewed command selection and canonical toolchain/CI
mappings without owning them. Existing `agent_starter.templates` script names remain direct compatible exports.

The read-only `example-answers` and `toolchains` CLI family is registered and handled by
`agent_starter.cli_app.information_commands`. `agent_starter.cli:main` remains the public dispatcher, and direct
legacy handler imports, output streams, exit codes, schema-v2/Sol example policy, and no-replace behavior remain stable.

Read-only `validate`, `audit-structure`, `audit-context`, and `doctor` registration/handling comes from
`agent_starter.cli_app.inspection_commands`. The public dispatcher retains direct handler exports, while canonical
validation/audit/doctor modules continue owning report construction, redaction, provider logic, and safety bounds.
Generated context measurement is owned by `agent_starter.context_budget`; it reads only bounded non-symlink Markdown,
reports suggested budgets and duplicate fingerprints, and never changes or blocks a project.

Repo-local `$agentkit` skill status/install/update/uninstall registration and CLI presentation comes from
`agent_starter.cli_app.skill_commands`. `codex_skill.py` remains the authority for project confinement, managed-file
recognition, atomic writes, backups, and refusal to replace or delete user-owned content.

Sandbox doctor/preflight/clean CLI registration and presentation comes from `agent_starter.cli_app.sandbox_commands`.
Preflight and project-command callables remain explicit injected parser boundaries. Fingerprinting, atomic stamps,
freshness state, image inspection, and doctor/build/check sequencing come from
`agent_starter.cli_app.sandbox_orchestration`, with direct `agent_starter.cli` exports preserving launch/status callers.

Local workspace status, GitHub-readiness evidence, and rsync mirror planning come from
`agent_starter.cli_app.readiness_commands`. GitHub readiness is advisory and local-only; rsync prints exact argv and
does nothing unless `--run` is explicit. Direct `agent_starter.cli` exports preserve existing callers and tests.

Continuation-prompt rendering and interactive CLI presentation come from `agent_starter.cli_app.prompt_commands`.
The module adapts canonical `task_composer.py` packets/contracts into the established Edit answers / Approve prompt
loop. Approval releases copy/paste prompt text only; it does not authorize execution, contact Codex, or launch it.

Assessment-only local-model inventory, scoring, override review, and handoff presentation come from
`agent_starter.cli_app.local_model_commands`. It may inspect installed Ollama metadata through bounded argv-only calls,
but it does not install models, contact a model service, alter `primary_agent`, add authentication, or launch anything.

Official Codex authorization and validated launch presentation come from `agent_starter.cli_app.agent_commands`.
Status-only auth does not install or log in; launch validates metadata/files and active sandbox preflight before adapter
access. GUI and compatibility callers continue importing the same direct `agent_starter.cli.launch_agent` object.

Project creation/generation presentation comes from `agent_starter.cli_app.generation_commands`. It preserves strict
answers loading, credential rejection, custom-command approval, dry-run/conflict/backup reporting, and the existing
`new`/`init`/`generate` entry points. Only the interactive wizard may reach the separately reviewed GitHub-remote choice;
answers-file generation never creates a GitHub repository or remote.

Reusable wizard question presentation comes from `agent_starter.guided.questions`. It rejects credential-like free text,
turns EOF/Ctrl-C into the established cancellation result, and normalizes only reviewed language/database choices.
Advisor snapshot/prompt rendering, recommendation and capability-decision presentation, deterministic fallback, and
explicit Codex readiness support come from `agent_starter.guided.advisor`. `agent_starter.wizard` retains direct
compatibility aliases plus host/provider/cache orchestration and the overall Guided/Advanced state-transition flow.

Generated artifact membership and manifest rendering come from `agent_starter.generation.registry`. This registry renders
text and metadata only; it cannot write files, initialize Git, launch Codex, or execute generated scripts. The established
`agent_starter.generator` names remain direct aliases, while its orchestration retains confinement and safe-write policy.

Generated-workspace validation comes from `agent_starter.generation.validation`. It is read-only apart from executing
bounded `bash -n` syntax checks against known generated scripts, and it never launches those scripts. CLI, GUI, launch,
readiness, provider tests, and generation continue using the direct `agent_starter.generator.validate_project` alias.

Safe generation orchestration comes from `agent_starter.generation.service`. It reparses configuration canonically,
confines every destination, refuses symlinked parents, writes atomically, preserves conflicts as proposals, backs up
before forced replacement, and reports mutation only after observed change. `agent_starter.generator` remains the direct
compatibility facade and grants no additional command or remote authority.

`agent-starter prompt /path/to/project --interactive` and the GUI Task Composer use the same typed task definitions and validated packet. They offer feature, fix, behavior-change, code-review, tests/docs, and deployment-plan choices, then ask only relevant questions. Both show the same five-section task contract before an explicit Edit answers or Approve prompt action. Approval releases prompt text only; it does not contact or launch Codex. Deployment-plan contracts explicitly prohibit deployment and remote/production changes.

All mapped GUI backend failures use the shared diagnostic contract: a stable code/severity, plain explanation, explicit project-files-changed value, safe next action, and bounded redacted technical details. The desktop launcher may record the same re-redacted, path-free data in its private bounded XDG-state log. This is presentation/audit data only and grants no retry, filesystem, subprocess, login, or launch authority.

Optional GUI draft sessions retain incomplete project/task presentation data in private user-local application storage. A resumed task is still unapproved and a resumed project is still unvalidated. Save, resume, list, discard, and export never contact Codex or invoke a project command; export writes only a new explicitly named local file.

The GUI is operable through native keyboard controls and step buttons, announces textual current/error/change state, and manages focus when the visible question changes. Reviewed remediation commands may be selected or copied but are never executed by the copy action. Prompt approval, local-draft deletion, and generation confirmations state the exact consequence; these are presentation gates and do not authorize launch or broader Codex actions.

GUI launch requires a successful current review of the generated project rather than task-prompt approval. The review names the target, exact or inherited model policy, reasoning, sandbox/approval policy, and project versus command network state. The bridge verifies generated Codex TOML, fingerprints the summary in memory, then revalidates/recomputes and consumes it before invoking the established launcher. Sol/medium remains the default explicit implementation policy; reviewed overrides and inherited-global selection are preserved exactly, never silently downgraded.

The shared CLI launcher repeats full project validation before sandbox preflight or Codex adapter/auth access, so direct CLI launch cannot bypass invalid-workspace blocking.

The prompt reinforces the Codex-only workflow, phase-sized changes, regression testing, `./scripts/check.sh`, implementation-note updates, handoff updates, and explicit approval requirements for privileged, destructive, credential, publish, deploy, remote-push, or external actions.

## Repo-local Agent Kit skill

Generated projects can include a concise Codex skill at `.agents/skills/agentkit/SKILL.md`. Users invoke it inside Codex with `$agentkit ...` or select it with `/skills`; it is not a custom slash command. The skill is intentionally instruction-only. It does not fake keyboard input, run a daemon, add MCP, modify `~/.codex/config.toml`, contact OpenAI/GitHub, or bypass approvals.

The skill turns a short request into a full implementation brief by telling Codex to run:

```bash
agent-starter idea-prompt --from-codex --arguments "<user request>" --json
```

Codex should pass the user request safely as an argument, read the returned `prompt_path`, and follow that generated prompt as the authoritative task brief. Prompt files are written under `docs/agent-prompts/`.

The skill is versioned by `.agents/skills/agentkit/agentkit-skill.json`, not nonstandard `SKILL.md` front matter. `agent-starter codex skill-status`, `update-agentkit-skill`, and `uninstall-agentkit-skill` inspect and manage only Agent Kit-managed files, with backups before replacement. Users may need to restart Codex if a newly installed or updated skill does not appear immediately.

## Rootless Podman sandbox workflow

Generated projects can optionally include rootless Podman files under `.agent-starter/sandbox/` and `scripts/sandbox/`. The default `toolchain` mode is host Codex editing the local project files, with project build/test/toolchain commands run through Podman against the mounted `/workspace`. Codex-inside-container mode is explicit and uses a project-specific Codex home volume rather than mounting host `~/.codex`.

The source command `agent-starter sandbox doctor /path/to/project` and generated `scripts/sandbox/doctor` check readiness without running `sudo` or installing packages. Missing CachyOS tools are printed as reviewable commands only. `agent-starter sandbox preflight /path/to/project` runs generated host-side `doctor`, `build`, and `check` wrappers before Codex launch and writes `.agent-starter/sandbox/preflight.json` after success. `agent-starter launch` and generated `START_AGENT.sh` run that preflight automatically for active `toolchain` and `codex` sandbox modes.

When sandbox metadata exists, `agent-starter idea-prompt` adds sandbox-aware guidance: host-side Podman preflight belongs before Codex starts. If `.agent-starter/sandbox/preflight.json` reports `"status": "passed"`, an already-open constrained Codex session should not rerun `scripts/sandbox/doctor` or `scripts/sandbox/build`. Codex may run `scripts/sandbox/check` only when the current Codex sandbox/approval policy permits rootless Podman access. Codex must not request `danger-full-access`, host full-access, privileged containers, or Podman socket mounts to make Podman bootstrap work. If Codex is already running inside the container, it should not run host-side `scripts/sandbox/*` launchers; it should run direct project commands such as `./scripts/check.sh`, `npm test`, or `python3 -m unittest` from `/workspace`. If verification fails from a constrained host Codex session, Codex should record the exact failure and stop with `BLOCKED_ENVIRONMENT`, telling the human to run verification from a normal host terminal or use Codex-inside-container mode. Game projects get container-safe headless checks plus host playtesting guidance.

The sandbox workflow does not send keystrokes to a terminal, run Codex login automatically, copy host sessions, mount host SSH keys, create remotes, deploy, or bypass Codex approvals. For container migration, generated projects include `docs/agent-prompts/create-container-handoff.md`, which asks Codex to write a concise no-secrets `docs/CODEX-HANDOFF.md` instead of importing raw session transcripts.

## Ollama readiness check

`agent-starter ollama-check /path/to/project --request "..."` is an assessment and prompt-generation gate for users who want to experiment with a local Ollama model after the Codex workspace exists. It is not an alternate agent adapter, generated launcher, authentication path, or `.codex/config.toml` rewrite.

The command inspects local Ollama metadata with `ollama list` and `ollama show <model> --json`. It looks for confirmed context length and code-capable model signals, then classifies the selected model as suitable, borderline, or inadvisable. Only suitable models produce a local-model handoff prompt by default. Borderline or inadvisable models require `--override`, and the generated prompt keeps the warning in front of the user.

The check never pulls models, installs packages, sends project content to Ollama, executes model output, changes Codex authorization, or launches a local model against the repository.

The warning baseline is the quality-first `GPT-5.6-SOL` policy with medium reasoning. Ollama readiness remains a heuristic based on local metadata, so users should keep local-model tasks narrow even when the gate passes.
