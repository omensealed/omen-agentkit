# Answers-file reference

Use `agent-starter example-answers --output answers.json` to create the current schema, edit it, then run:

```bash
agent-starter generate --answers answers.json
```

Schema v2 is current. Unknown keys are ignored with structured warnings for forward compatibility. Common credential-looking values are rejected. Boolean values must be JSON `true` or `false` without quotes; strings such as `"false"` are rejected. Custom executable command arrays require the additional `--allow-custom-commands` flag after manual review.

Migrate an old file without changing it:

```bash
agent-starter config migrate --input answers-v1.json
agent-starter config migrate --input answers-v1.json --output answers-v2.json
```

The first command is a stdout preview. The second creates a separate new file and refuses to replace either the source or an existing output.

## Project and scope fields

- `project_name`, `project_slug`, `project_path`: display name, safe identifier, and destination.
- `project_mode`: `new` or `existing`.
- `project_stage`: normally `idea`, `prototype`, `active`, or `renovation`.
- `project_type`: for example `cli`, `web`, `game`, `desktop`, `library`, or `other`.
- `description`, `goals`, `non_goals`, `target_users`: requirements context.
- `target_platforms`, `packaging_targets`: operating and distribution targets.

## Stack and data fields

- `stack_strategy`: `manual` or `ai`.
- `languages`: normalized toolchain names such as `python`, `javascript`, `rust`, `go`, `php`, `cpp`, `java`, `godot`, or `shell`.
- `stack_notes`: constraints or technology rationale.
- `minimal_dependencies`: preference for a small dependency surface.
- `database`: `none`, `sqlite`, `mariadb`, `postgresql`, `existing`, or `undecided`.
- `database_notes`: expected data volume, existing schema, migration limits, and similar non-secret context.
- `network_access`, `user_accounts`, `handles_personal_data`, `handles_payments`: security-relevant booleans.
- `security_notes`: additional non-secret risk requirements.

## Codex fields

- `primary_agent`: must be `codex`; it is a fixed compatibility invariant.
- `setup_agent_now`: whether the interactive wizard should offer installation/login.
- `agent_sandbox`: descriptive generated-project policy; the supported default is `builtin-safe`.
- `use_ai_advisor`: whether Codex stack advice was requested.
- `codex_agentkit_skill`: whether to generate the repo-local `$agentkit` Codex skill. Defaults to `true` for backward compatibility and beginner convenience.
- `model_policy`: typed Codex selection. The default explicit policy uses `model_id: "gpt-5.6-sol"`, `display_label: "GPT-5.6-SOL"`, `reasoning_effort: "medium"`, `selection: "explicit"`, and `fallback_behavior: "ask"`. Set `selection` to `inherit` to omit project model/reasoning keys. Explicit overrides are accepted only as reviewed exact IDs; no fallback is selected automatically.

## Sandbox fields

`sandbox` is optional. Old answers files that omit it still load and default to no generated Podman sandbox.

```json
"sandbox": {
  "enabled": true,
  "engine": "podman",
  "mode": "toolchain",
  "image_profile": "arch-toolchain",
  "codex_inside_container": false,
  "rootless_required": true,
  "install_agentkit_skill": true,
  "first_run_autonomous_prompt": false,
  "gui_passthrough": false
}
```

- `enabled`: generate rootless Podman sandbox files.
- `engine`: must be `podman`.
- `mode`: `none`, `toolchain`, `codex`, or `files-only`.
- `image_profile`: explicit tested `arch-toolchain` or `debian-toolchain` container image policy. It defaults to `arch-toolchain` for old v2 files and is independent of host detection and project target platforms.
- `codex_inside_container`: when true, generate project-scoped Codex container launch/login/resume scripts and use a project-specific Codex home volume.
- `rootless_required`: records that the generated sandbox expects rootless Podman.
- `install_agentkit_skill`: records whether sandbox-aware `$agentkit` prompt flow should be available with the project.
- `first_run_autonomous_prompt`: generates `FIRST_RUN_AUTONOMOUS.md`; keep this false unless the workspace is disposable/local and the user explicitly wants it.
- `gui_passthrough`: advanced opt-in for game/Godot projects. When true, generate a `scripts/sandbox/playtest-gui` helper that exposes selected host Wayland, GPU, PipeWire audio, and input/controller interfaces to the project container for interactive local playtesting.

The sandbox does not install packages, run Podman, run Codex login, mount host `~/.codex`, mount host `~/.ssh`, or copy host sessions during generation. GUI/audio/controller passthrough is never enabled unless `gui_passthrough` is explicitly true.

## Git, test, and toolchain fields

- `git_enabled`: initialize a local repository when one does not exist.
- `github_actions`: generate `.github/workflows/ci.yml`. Starter examples default this to `false` for a local-first workflow; set it to `true` after local checks prove the project is ready for CI.
- `github_remote`: `none`, `later`, `create-private`, or `create-public`; repository creation is interactive-only and never pushes.
- `default_branch`, `license_name`: repository defaults. The default generated license is `AGPL-3.0-or-later`. Built-in license files are generated for `MIT`, `Apache-2.0`, `BSD-3-Clause`, `GPL-3.0-or-later`, `AGPL-3.0-or-later`, and `MPL-2.0`; use `Undecided` to skip license generation. AGPL generation includes the full AGPL-3.0-or-later text plus an SPDX identifier.
- `tests`, `browser_tests`, `quality_checks`: expected verification layers.
- `extra_packages_by_provider`: provider-scoped extra package intent. Supported generated bootstrap keys are `arch`, `debian`, and `ubuntu`. Values enter only that provider's generated package array. v1 `cachyos_packages` migrates only to `extra_packages_by_provider.arch`; Arch package names are never treated as Debian/Ubuntu package names.
- `advisor.recommended_capabilities`: capability-first advisor data. Each item contains a known `capability_id`, bounded `purpose` and `rationale`, `requirement` (`required` or `optional`), and `confidence` (`high`, `medium`, or `low`). This data is untrusted intent, never executable argv.
- `advisor.architecture_notes`: bounded plain-language architecture-fit notes from the reviewed advisor contract.
- `advisor.toolchain_capabilities`: compatibility projection of provider-neutral IDs. Legacy `advisor.toolchain_packages` and advisor command arrays remain loadable for old projects as documentation-only data, but the live advisor schema no longer accepts package names or setup/build/test/lint commands.
- `advisor.source`: provenance input for the shared review label. `local-fallback` is displayed as a local deterministic default that is not AI-reviewed; `manual-seed` is local/manual; `saved` does not claim known AI review; `codex-cache` identifies a revalidated cached AI-reviewed structured recommendation. Other sources represent successfully parsed live advisor results. The user cache is runtime state and is never embedded in an answers file.
- `capability_decisions`: project-owned per-capability choices stored separately from `advisor`. Each closed object has `capability_id`, `decision`, `requirement`, and `limitation`. Optional capabilities use `accepted` or `rejected`. Required capabilities use `accepted` or `challenged`; a challenge requires a plain-language limitation. Deterministic baseline capabilities cannot be relabeled optional. Decisions never authorize installation or execution.
- `cachyos_packages`: deprecated v1-compatible input field; use the provider-scoped field in new v2 files.
- `custom_setup_commands`, `custom_build_commands`, `custom_test_commands`, `custom_lint_commands`: executable content requiring explicit opt-in.
- `open_questions`: unresolved items carried into project documentation.

Timestamps, schema/kit versions, and the normalized `advisor` object may also be present in saved metadata.

Example decision records:

```json
"capability_decisions": [
  {
    "capability_id": "language.python",
    "decision": "accepted",
    "requirement": "required",
    "limitation": ""
  },
  {
    "capability_id": "optional.shellcheck",
    "decision": "rejected",
    "requirement": "optional",
    "limitation": ""
  }
]
```

## Path override

`--path` overrides `project_path` without modifying the source JSON:

```bash
agent-starter generate --answers answers.json --path /tmp/review-project
```

## Existing files

Without `--force`, conflicting generated content is written beneath `.agent-starter/proposals/` and the original stays untouched. With `--force`, the original is copied beneath `.agent-starter/backups/` before replacement.
