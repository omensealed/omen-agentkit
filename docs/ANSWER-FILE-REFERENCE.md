# Answers-file reference

Use `agent-starter example-answers --output answers.json` to create the current schema, edit it, then run:

```bash
agent-starter generate --answers answers.json
```

Unknown keys are rejected. Common credential-looking values are rejected. Custom executable command arrays require the additional `--allow-custom-commands` flag after manual review.

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

## Sandbox fields

`sandbox` is optional. Old answers files that omit it still load and default to no generated Podman sandbox.

```json
"sandbox": {
  "enabled": true,
  "engine": "podman",
  "mode": "toolchain",
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
- `cachyos_packages`: extra package names after validation.
- `custom_setup_commands`, `custom_build_commands`, `custom_test_commands`, `custom_lint_commands`: executable content requiring explicit opt-in.
- `open_questions`: unresolved items carried into project documentation.

Timestamps, schema/kit versions, and the normalized `advisor` object may also be present in saved metadata.

## Path override

`--path` overrides `project_path` without modifying the source JSON:

```bash
agent-starter generate --answers answers.json --path /tmp/review-project
```

## Existing files

Without `--force`, conflicting generated content is written beneath `.agent-starter/proposals/` and the original stays untouched. With `--force`, the original is copied beneath `.agent-starter/backups/` before replacement.
