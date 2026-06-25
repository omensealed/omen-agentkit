# Implementation notes

This is the starter kit’s durable engineering journal. Add a dated entry after every meaningful phase. Record files changed, design decisions, exact commands, results, implications, unresolved issues, and the next concrete step.

## 2026-06-23T00:00:00Z — initial implementation

- Objective/phase: Build the first complete beginner-oriented CLI agent project wizard for CachyOS.
- Files/subsystems changed: Python package, templates, examples, tests, install helpers, generated-project scripts, security documentation, and source documentation.
- Behavior/design decisions: Use Python standard library only; delegate account authorization to official clients; preserve existing files through proposals/backups; make package installation explicit; require generated implementation notes.
- Commands and tests run: Python unit/integration suite, shell syntax checks, fresh-project generation/validation, generated checks, and isolated install/uninstall smoke test.
- Results: Initial release workflow completed.
- Security/data/performance/UX implications: No credential storage; no automatic privileged installation; no silent existing-file replacement; beginner prompts include security and test planning.
- Unresolved problems: Live account authorization remains an external acceptance step because automated tests intentionally cannot access user credentials.
- Exact next step: Refine the package as real project usage reveals workflow gaps.

## 2026-06-24T00:00:00Z — Codex-only refactor

- Objective/phase: Make the starter kit one-to-one with OpenAI Codex CLI and remove every alternate-agent workflow.
- Files/subsystems changed: Agent adapter registry, CLI commands, wizard, project model validation, generator, templates, examples, tests, root documentation, and all maintainer docs.
- Behavior/design decisions: Keep `primary_agent` as a fixed `codex` metadata invariant; expose one OAuth path, one advisor, one launch path, and one generated `.codex` configuration; eliminate agent-selection questions and compatibility files.
- Commands and tests run: `python3 -m compileall -q agent_starter tests starter.py`; `python3 -m unittest discover -s tests -v`; full `./scripts/check.sh`; clean-extraction verification before packaging.
- Results: All 34 unit/integration tests passed; source and clean-extraction `./scripts/check.sh` runs passed; new Python/SQLite and existing PHP/MariaDB generated workspaces validated; existing source preservation and Codex-only output checks passed.
- Security/data/performance/UX implications: Smaller attack and maintenance surface; fewer confusing choices for beginners; credentials remain entirely controlled by the official Codex CLI; existing safe-write and explicit-install boundaries remain intact.
- Unresolved problems: Live ChatGPT OAuth cannot be exercised in automated packaging tests and must be completed by the end user through `codex login`.
- Exact next step: Distribute the version 0.2.0 archive and checksum, then collect feedback from the first real CachyOS/Codex project run.

## 2026-06-24T15:05:47Z — maintainer orientation baseline

- Objective/phase: Establish a verified baseline before feature work by reading the maintainer contract, documentation, implementation, tests, scripts, examples, and generated output.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only; runtime code, templates, tests, examples, and shell scripts were inspected but not modified.
- Behavior/design decisions: Confirmed the current architecture remains Codex-only, Python-standard-library at runtime, review-first for CachyOS package installation, and protective of existing project files through proposals/backups instead of silent replacement.
- Commands and tests run: `git status --short` and `git log -5 --oneline` failed because this extracted directory is not a Git repository; `./scripts/check.sh` passed before this note; generated and inspected `/tmp/tmp.leP7HW0477/new-python-sqlite` from `examples/cli-python-sqlite-codex.json`; generated and inspected `/tmp/tmp.leP7HW0477/existing-php-mariadb` from `examples/existing-php-mariadb-renovation.json` with a preexisting `README.md`, confirming a proposal was created and the original file remained untouched.
- Results: Source checks passed before the note with 34 unit/integration tests passing, shell syntax validation passing, generation smoke passing, and isolated install/uninstall smoke passing; generated Python/SQLite and existing PHP/MariaDB workspaces validated successfully.
- Security/data/performance/UX implications: No Codex login, OpenAI network call, package installation, `sudo`, GitHub publication, remote push, deployment, production-data access, credential-store inspection, or AI-suggested command execution was performed.
- Unresolved problems: The workspace has no Git metadata, so branch, dirty state, and recent commit history cannot be verified from this directory; live Codex OAuth remains an external acceptance item.
- Exact next step: Rerun `./scripts/check.sh` after this documentation-only note, then begin feature planning from the verified baseline.

## 2026-06-24T15:12:27Z — Codex continuation prompt generator

- Objective/phase: Add a user-facing way to generate a well-formed copy/paste Codex prompt for the next project phase or a requested feature without launching Codex automatically.
- Files/subsystems changed: `agent_starter/cli.py`, `tests/test_cli.py`, `README.md`, `docs/USER-GUIDE.md`, `docs/AGENT-INTEGRATION.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `agent-starter prompt [project] --request "..."` with optional `--phase`, `--output`, and `--force`; the command loads generated metadata, rejects credential-like request text, prints to stdout by default, and refuses to overwrite output files unless `--force` is supplied.
- Commands and tests run: `python3 -m unittest tests.test_cli -v` passed with 7 tests; `./agent-starter prompt /tmp/tmp.leP7HW0477/new-python-sqlite --request "Add CSV import"` produced a focused continuation prompt; `./scripts/check.sh` passed with 36 unit/integration tests plus syntax checks, CLI smoke, generation smoke, generated-project check, and install/uninstall smoke.
- Results: Continuation prompt generation is covered by regression tests and documented for users; full source verification passed.
- Security/data/performance/UX implications: The prompt generator uses project metadata and document paths rather than copying raw project docs into the prompt; it reinforces sandboxing, approval prompts, no credential access, no automatic command execution, no `sudo`, no remote pushes, and no destructive/publish/deploy actions without explicit approval.
- Unresolved problems: The command does not yet offer an interactive questionnaire for shaping ambiguous feature requests; users provide the request string directly.
- Exact next step: Rerun `./scripts/check.sh` after this note and then consider whether generated projects should also include a local helper script for continuation prompts.

## 2026-06-24T15:21:03Z — Ollama local-model readiness gate

- Objective/phase: Add a guarded way for users to assess whether installed Ollama models are plausible local handoff targets before generating a continuation prompt.
- Files/subsystems changed: `AGENTS.md`, `agent_starter/cli.py`, `tests/test_cli.py`, `README.md`, `docs/USER-GUIDE.md`, `docs/AGENT-INTEGRATION.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY-MODEL.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `agent-starter ollama-check [project]` with optional `--model`, `--request`, `--output`, `--force`, and `--override`; the command inspects `ollama list` plus `ollama show <model> --json`, extracts confirmed context length when available, scores model-name coding suitability, and refuses borderline/inadvisable handoff prompt generation without explicit override.
- Commands and tests run: OpenAI Codex manual helper was attempted for current product/model context but failed with DNS resolution for `developers.openai.com`; `python3 -m unittest tests.test_cli -v` passed with 10 tests; `./scripts/check.sh` passed with 39 unit/integration tests plus syntax checks, CLI smoke, generation smoke, generated-project check, and install/uninstall smoke.
- Results: Local-model handoff is assessment-only and covered by mocked Ollama regression tests for suitable, blocked, and override paths.
- Security/data/performance/UX implications: The feature does not install Ollama, pull models, send repository content to Ollama, execute local-model output, rewrite `.codex/config.toml`, alter `primary_agent`, or add an alternate generated launcher/auth path; warnings remain embedded in override-generated handoff prompts.
- Unresolved problems: Context and coding suitability are based on local Ollama metadata and model-name heuristics, not a live benchmark; current OpenAI model specifics were not verified because official docs were unreachable from this environment.
- Exact next step: Rerun `./scripts/check.sh` after this note, then consider whether an optional generated-project helper should wrap `agent-starter ollama-check` when the starter is installed.

## 2026-06-24T15:23:32Z — Codex manual baseline verification

- Objective/phase: Use the freshly available Codex manual cache to verify the local-model handoff baseline.
- Files/subsystems changed: `agent_starter/cli.py`, `docs/USER-GUIDE.md`, `docs/AGENT-INTEGRATION.md`, `docs/ARCHITECTURE.md`, and this implementation note.
- Behavior/design decisions: Added `gpt-5.5` as the explicit Codex reference baseline in `ollama-check` output and local-model handoff prompts because the Codex manual lists it as the recommended model for complex coding work; kept Ollama readiness as a conservative metadata heuristic rather than a claim of local parity.
- Commands and tests run: Read `/tmp/openai-docs-cache/codex-manual.outline.md`; read manual sections for config basics, model selection, sandboxing, and `AGENTS.md` discovery.
- Results: Confirmed project `.codex/config.toml` scoping, `workspace-write` plus `on-request` as a lower-risk local automation posture, `AGENTS.md` instruction discovery, and `gpt-5.5` as the current recommended Codex model.
- Security/data/performance/UX implications: The starter still does not rewrite Codex configuration, add an alternate launcher, or send project content to Ollama; users get a clearer comparison baseline before overriding local-model warnings.
- Unresolved problems: Ollama model capability still cannot be guaranteed without task-specific evaluation; context length and model-name signals remain only a readiness screen.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T17:28:15Z — AGPL generated license option

- Objective/phase: Add `AGPL-3.0-or-later` as a built-in license choice for generated projects.
- Files/subsystems changed: `agent_starter/wizard.py`, `agent_starter/generator.py`, `agent_starter/templates.py`, `tests/test_templates.py`, `tests/test_generator.py`, `docs/ANSWER-FILE-REFERENCE.md`, `docs/USER-GUIDE.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: The wizard now offers MIT, AGPL-3.0-or-later, and Undecided. The generator writes a concise AGPL notice with `SPDX-License-Identifier: AGPL-3.0-or-later` and the official GNU AGPL URL instead of embedding a large license body template.
- Commands and tests run: `python3 -m unittest tests.test_templates tests.test_generator -v` passed with 17 tests.
- Results: AGPL project license generation is covered by template and generator regression tests.
- Security/data/performance/UX implications: No runtime dependency or external command was added; existing MIT and Undecided behavior remains intact.
- Unresolved problems: The generated AGPL file is a notice and URL, not the full AGPL text.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T17:29:39Z — AGPL generated-output inspection

- Objective/phase: Inspect a freshly generated AGPL project after adding the license option.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: Used the existing Python/SQLite example as the base and changed only destination, project name, Git initialization, and `license_name` to `AGPL-3.0-or-later`.
- Commands and tests run: Generated `/tmp/tmp.8Ea4HeRbSK/agpl-project`; inspected `LICENSE`; checked metadata for `license_name` and `primary_agent`; ran `bash -n` on generated scripts; ran `./agent-starter validate /tmp/tmp.8Ea4HeRbSK/agpl-project --verbose`; ran `/tmp/tmp.8Ea4HeRbSK/agpl-project/scripts/check.sh`.
- Results: Generated workspace created 43 files, validation passed, generated shell syntax passed, and generated `scripts/check.sh` passed. `LICENSE` contained the AGPL title, SPDX identifier, and GNU license URL. Metadata preserved `license_name: AGPL-3.0-or-later` and `primary_agent: codex`.
- Security/data/performance/UX implications: No network, Codex login, package installation, `sudo`, GitHub action, or external model execution was performed.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T17:31:33Z — full AGPL license text

- Objective/phase: Resolve the AGPL license-quality gap by generating the full AGPL-3.0-or-later license text instead of only a short notice.
- Files/subsystems changed: `agent_starter/templates.py`, `tests/test_templates.py`, and this implementation note.
- Behavior/design decisions: Embedded the local SPDX `AGPL-3.0-or-later.txt` license text from `/usr/share/licenses/spdx/AGPL-3.0-or-later.txt`, preceded by `SPDX-License-Identifier: AGPL-3.0-or-later`. Removed the unused short-notice helper left from the prior implementation.
- Commands and tests run: Inspected the local SPDX license file; verified the template returns 237 lines and includes section 13.
- Results: Generated AGPL projects will now include the full AGPL text plus SPDX identifier in `LICENSE`.
- Security/data/performance/UX implications: No network lookup, runtime dependency, or generated command behavior changed.
- Unresolved problems: Need focused tests, generated-output inspection, and full source check after this note.
- Exact next step: Run focused template/generator tests and inspect a fresh AGPL output.

## 2026-06-24T17:33:50Z — full AGPL verification

- Objective/phase: Verify the full AGPL license text change end to end.
- Files/subsystems changed: `docs/ANSWER-FILE-REFERENCE.md` and this implementation note.
- Behavior/design decisions: Preserved the short SPDX notice helper for Apache, BSD, GPL, and MPL license outputs while making AGPL the only generated license that embeds the full text.
- Commands and tests run: `python3 -m unittest tests.test_templates tests.test_generator -v` passed with 18 tests; generated `/tmp/tmp.2MvKE096r7/agpl-project`; ran `./agent-starter validate /tmp/tmp.2MvKE096r7/agpl-project`; ran `/tmp/tmp.2MvKE096r7/agpl-project/scripts/check.sh`; inspected generated `LICENSE` with `wc -l` and `rg`; ran `./scripts/check.sh`, which passed with 42 tests plus syntax checks, CLI smoke, generation smoke, generated-project check, and install/uninstall smoke.
- Results: The generated AGPL `LICENSE` is 237 lines and includes `SPDX-License-Identifier: AGPL-3.0-or-later`, `GNU AFFERO GENERAL PUBLIC LICENSE`, and section 13. Full source verification passed.
- Security/data/performance/UX implications: No network, package installation, Codex login, `sudo`, GitHub action, or external model execution was performed.
- Unresolved problems: None for this AGPL license substep.
- Exact next step: Rerun `./scripts/check.sh` after this note.

## 2026-06-24T17:35:26Z — license option matrix inspection

- Objective/phase: Verify every built-in license option through actual project generation and validation.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: Confirmed the interactive wizard already exposes the same built-in license choices supported by the generator and answer-file docs: MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-or-later, AGPL-3.0-or-later, MPL-2.0, and Undecided.
- Commands and tests run: Generated and validated temporary projects under `/tmp/tmp.j0LRs4yT7s` for all seven license modes; inspected `LICENSE` markers for each generated license; confirmed Undecided generated no `LICENSE`; ran `/tmp/tmp.j0LRs4yT7s/agpl-3-0-or-later/scripts/check.sh`.
- Results: All license-mode workspaces generated and validated successfully. AGPL emitted a 237-line full license, MIT emitted 21 lines, Apache/BSD/GPL/MPL emitted 8-line SPDX notices, and Undecided omitted `LICENSE` as expected. Representative generated check passed.
- Security/data/performance/UX implications: No network, package installation, Codex login, `sudo`, GitHub action, or external model execution was performed.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T17:38:32Z — beginner license guidance

- Objective/phase: Reduce beginner uncertainty during license selection.
- Files/subsystems changed: `agent_starter/wizard.py`, `tests/test_wizard.py`, `docs/USER-GUIDE.md`, and this implementation note.
- Behavior/design decisions: Added a short license quick guide immediately before the wizard license choice, explaining permissive licenses, copyleft licenses, AGPL network-service source-sharing obligations, MPL file-level copyleft, and Undecided as the safe choice when unsure.
- Commands and tests run: `python3 -m unittest tests.test_wizard -v` passed with 4 tests.
- Results: Interactive users now see plain-language license guidance before choosing from the built-in license options.
- Security/data/performance/UX implications: No generated file contract, runtime dependency, external command, or licensing behavior changed; the update is user guidance only.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T18:02:14Z — GitHub AI-local artifact hygiene

- Objective/phase: Keep GitHub uploads focused on core project source, durable docs, and scripts by excluding local AI/runtime artifacts from generated Git tracking.
- Files/subsystems changed: `agent_starter/toolchains.py`, `tests/test_toolchains.py`, `tests/test_generator.py`, `README.md`, `docs/TEMPLATE-CATALOG.md`, `docs/USER-GUIDE.md`, and this implementation note.
- Behavior/design decisions: Expanded generated `.gitignore` to exclude local Codex logs/session files, starter runtime state, proposal and backup directories, saved continuation prompts, and local-model handoff drafts. Durable project memory such as `AGENTS.md`, numbered docs, scripts, `.codex/config.toml`, and `.agent-starter/project.json` remains trackable because it is part of the generated workspace contract.
- Commands and tests run: `python3 -m unittest tests.test_toolchains tests.test_generator -v` passed with 13 tests; generated `/tmp/tmp.EVq58TZuTA/project`; used `git check-ignore` to verify local AI artifacts were ignored and core files were not ignored.
- Results: Generated Git-enabled projects now ignore AI-local artifacts while preserving trackability for the core project contract.
- Security/data/performance/UX implications: Reduces accidental upload of prompts, local handoff drafts, Codex logs, session JSONL, runtime state, backups, and conflict proposals. No GitHub remote, push, network call, Codex login, package installation, or `sudo` was used.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T18:10:09Z — local-first GitHub defaults

- Objective/phase: Reduce beginner GitHub/CI noise by deferring GitHub Actions and remote setup until local checks prove the project is worth publishing or backing up remotely.
- Files/subsystems changed: `agent_starter/wizard.py`, `agent_starter/models.py`, `agent_starter/cli.py`, `examples/*.json`, `scripts/smoke-test.sh`, `tests/test_wizard.py`, `README.md`, `docs/USER-GUIDE.md`, `docs/SECURITY-MODEL.md`, `docs/ANSWER-FILE-REFERENCE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Local Git remains default-on, but interactive and example defaults now keep `github_actions` false and `github_remote` none. The wizard prints a local-first recommendation before asking about GitHub Actions. Explicit `github_actions: true` answers still generate `.github/workflows/ci.yml`.
- Commands and tests run: `python3 -m unittest tests.test_wizard tests.test_cli tests.test_release -v` passed with 15 tests; `./scripts/smoke-test.sh` passed and confirmed default examples do not generate GitHub Actions; generated an explicit-CI project with `github_actions: true`, confirmed `.github/workflows/ci.yml` exists and calls `./scripts/check.sh`, and validated the workspace.
- Results: New users get a calmer local-first path, while CI remains available by explicit opt-in.
- Security/data/performance/UX implications: Reduces premature GitHub Actions noise, token use, and remote-platform distraction. No GitHub remote, push, network call, Codex login, package installation, or `sudo` was used.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:21:45Z — Phase A first-run clarity

- Objective/phase: Fill the first beginner-usability gap in the sandbox manager maturity plan by generating an explicit post-generation next-steps guide.
- Files/subsystems changed: `agent_starter/generator.py`, `agent_starter/templates.py`, `agent_starter/cli.py`, `tests/test_generator.py`, `tests/test_templates.py`, `tests/test_cli.py`, `scripts/smoke-test.sh`, `README.md`, `docs/USER-GUIDE.md`, `docs/TEMPLATE-CATALOG.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added required root `NEXT_STEPS.md` to generated projects, made CLI completion output point at it, and changed placeholder `build`, `lint`, and `test` scripts to state clearly that no real app harness exists yet. `NEXT_STEPS.md` keeps the first session local-first, explains Codex setup and launch, preserves the GitHub pause, and points to continuation prompt and Ollama assessment helpers without adding alternate-agent configuration.
- Commands and tests run: `python3 -m unittest tests.test_templates tests.test_generator tests.test_cli -v` passed with 30 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./scripts/smoke-test.sh` passed; generated `/tmp/tmp.ZvuycuFJdU/python-sqlite` from `examples/cli-python-sqlite-codex.json`; generated `/tmp/tmp.ZvuycuFJdU/existing-renovation` from `examples/existing-php-mariadb-renovation.json` after seeding an existing `index.php`; validated both workspaces; ran Bash syntax checks across both generated script sets; inspected `NEXT_STEPS.md`, `AGENTS.md`, and `FIRST_PROMPT.md` for Codex-specific and implementation-note contracts.
- Results: Focused tests, smoke generation, representative generated workspace validation, and generated shell syntax all passed. Generated `NEXT_STEPS.md` is required by validation and uses new-project placeholder wording only for new projects, with separate existing-project guidance for renovation workspaces.
- Security/data/performance/UX implications: Improves beginner guidance without running Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution. Existing safe-write, conflict proposal, backup, symlink, traversal, and Codex-only constraints remain unchanged.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:24:00Z — Phase A verification

- Objective/phase: Record the final verification result for the Phase A first-run clarity change.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 44 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution.
- Unresolved problems: None for this Phase A substep.
- Exact next step: Review the diff, then move to the next maturity-plan phase when ready.

## 2026-06-24T22:32:37Z — Phase B workspace status command

- Objective/phase: Add the first Phase B readiness feature so beginners can ask the starter what state a generated workspace is in and what to do next.
- Files/subsystems changed: `agent_starter/cli.py`, `agent_starter/templates.py`, `tests/test_cli.py`, `tests/test_templates.py`, `scripts/smoke-test.sh`, `README.md`, `docs/USER-GUIDE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added read-only `agent-starter status /path/to/project`. The command loads non-secret project metadata, validates required generated files, checks Codex install/auth status through the official CLI status boundary, summarizes local Git and GitHub Actions state, verifies key AI-local `.gitignore` protections, and prints one next recommended action. Generated `NEXT_STEPS.md` now includes `agent-starter status .`.
- Commands and tests run: `python3 -m unittest tests.test_cli tests.test_templates tests.test_generator -v` passed with 32 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./scripts/smoke-test.sh` passed and exercised `agent-starter status` on a generated workspace; `python3 -m unittest tests.test_cli tests.test_templates -v` passed with 23 tests after the smoke-test update.
- Results: The new status command reports healthy generated workspaces, missing metadata failures, Codex readiness, Git/GitHub posture, ignored AI-local artifact posture, and next action guidance without mutating the project.
- Security/data/performance/UX implications: No credential files are inspected, no OAuth token is read, no login is started, no package installation or `sudo` is run, and no GitHub remote/push/deploy action is performed. The command may invoke `codex --version` and `codex login status` only when the Codex executable exists.
- Unresolved problems: The second Phase B feature, `agent-starter github-ready /path/to/project`, remains to be implemented.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:33:02Z — Phase B status verification

- Objective/phase: Record final verification for the `agent-starter status` readiness command.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 46 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test including `agent-starter status`, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution.
- Unresolved problems: `agent-starter github-ready /path/to/project` remains the next Phase B gap.
- Exact next step: Implement the GitHub readiness gate.

## 2026-06-24T22:35:58Z — Phase B GitHub readiness gate

- Objective/phase: Complete Phase B by adding a local-first readiness gate before users create GitHub remotes, enable CI, or push.
- Files/subsystems changed: `agent_starter/cli.py`, `agent_starter/templates.py`, `tests/test_cli.py`, `tests/test_templates.py`, `scripts/smoke-test.sh`, `README.md`, `docs/USER-GUIDE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `agent-starter github-ready /path/to/project`. The command loads generated metadata, validates required files, runs `./scripts/check.sh` unless `--skip-check` is supplied, checks that local Git exists and is clean, verifies AI-local artifact ignore patterns, and inspects the GitHub Actions workflow when present. It reports a recommendation but never creates a repository, enables CI, pushes, installs packages, deploys, or contacts GitHub.
- Commands and tests run: `python3 -m unittest tests.test_cli tests.test_templates -v` passed with 25 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; generated `/tmp/tmp.Ai4FjEXQvb/project` from `examples/cli-python-sqlite-codex.json`; ran `agent-starter github-ready` before committing and confirmed it blocked on uncommitted Git state; made a local-only baseline commit in that temporary project; reran `agent-starter github-ready` and confirmed it passed with GitHub Actions still optional/deferred.
- Results: The readiness gate blocks premature GitHub work when local state is dirty or incomplete and allows a clean local baseline without requiring GitHub Actions.
- Security/data/performance/UX implications: The command runs only local validation and the project-local check script. It does not read credentials, start Codex or GitHub login, call OpenAI/GitHub, run `sudo`, install packages, create remotes, push, or deploy. Users can pass `--skip-check` for static-only inspection.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:36:25Z — Phase B GitHub readiness verification

- Objective/phase: Record final verification for the completed Phase B GitHub readiness gate.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 48 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test with `status` and generated `github-ready` guidance, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution.
- Unresolved problems: None for Phase B.
- Exact next step: Move to Phase C guided continuation prompts when ready.

## 2026-06-24T22:38:32Z — Phase C interactive continuation prompts

- Objective/phase: Start Phase C by giving beginners a guided way to generate Codex continuation prompts without hand-writing the whole request.
- Files/subsystems changed: `agent_starter/cli.py`, `agent_starter/templates.py`, `tests/test_cli.py`, `tests/test_templates.py`, `README.md`, `docs/USER-GUIDE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `agent-starter prompt --interactive`. The guided mode asks for task type, requested outcome, what changed since the last session, likely affected surfaces, risk/concerns, expected verification, and phase label. It folds those answers into the existing Codex-safe continuation prompt rather than adding a new agent path. Existing `--request` behavior remains unchanged for scripts and answerable one-liners.
- Commands and tests run: `python3 -m unittest tests.test_cli tests.test_templates -v` passed with 27 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./scripts/smoke-test.sh` passed.
- Results: Interactive prompt generation produces structured task context, rejects credential-like entries before they enter the generated prompt, and generated `NEXT_STEPS.md` now advertises the guided prompt path.
- Security/data/performance/UX implications: The command is local text generation only. It does not launch Codex, read credentials, run OpenAI requests, install packages, use `sudo`, create GitHub resources, push, deploy, or execute generated commands.
- Unresolved problems: Phase C prompt templates for bug fix, feature, cleanup, docs, test-baseline, and release-prep work remain to be implemented.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:38:54Z — Phase C interactive prompt verification

- Objective/phase: Record final verification for the guided continuation prompt mode.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 50 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution.
- Unresolved problems: Prompt templates for named task categories remain the next Phase C gap.
- Exact next step: Add prompt templates for bug fix, feature, cleanup, docs, test-baseline, and release-prep work.

## 2026-06-24T22:41:01Z — Phase C named prompt templates

- Objective/phase: Complete Phase C by adding named Codex continuation prompt templates for common beginner workflows.
- Files/subsystems changed: `agent_starter/cli.py`, `agent_starter/templates.py`, `tests/test_cli.py`, `tests/test_templates.py`, `README.md`, `docs/USER-GUIDE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `agent-starter prompt --template` with `feature`, `bug`, `cleanup`, `docs`, `test-baseline`, and `release-prep` choices. Templates add static guidance sections to the existing Codex-safe continuation prompt; they do not execute commands or change agent configuration. Interactive prompt generation now maps its task-type answer to the same template set.
- Commands and tests run: `python3 -m unittest tests.test_cli tests.test_templates -v` passed with 28 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./scripts/smoke-test.sh` passed.
- Results: Named templates render the expected task-specific sections, interactive bug prompts include the bug-fix template, and generated `NEXT_STEPS.md` documents the available template names.
- Security/data/performance/UX implications: This is local prompt text generation only. It does not run Codex, read credentials, make OpenAI or GitHub requests, install packages, use `sudo`, push, deploy, or execute generated commands.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T22:41:24Z — Phase C template verification

- Objective/phase: Record final verification for named prompt templates and Phase C completion.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 51 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, or external model execution.
- Unresolved problems: None for Phase C.
- Exact next step: Move to Phase D local backup/mirror planning when ready.

## 2026-06-24T23:43:53Z — Phase D rsync mirror planning

- Objective/phase: Complete Phase D by adding review-first local/SSH source mirror support.
- Files/subsystems changed: `agent_starter/cli.py`, `agent_starter/generator.py`, `agent_starter/templates.py`, `tests/test_cli.py`, `tests/test_generator.py`, `tests/test_templates.py`, `scripts/smoke-test.sh`, `README.md`, `docs/USER-GUIDE.md`, `docs/TEMPLATE-CATALOG.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added generated `.agent-starter/rsync-excludes` and `agent-starter rsync-plan PROJECT TARGET`. The command prints the exact `rsync` argv by default and only executes with `--run`. It refuses local targets inside the project root, supports local paths and SSH-style rsync targets, and has explicit `--delete` for target-side deletion. The exclude file mirrors source and durable docs while skipping `.git/`, credentials, local databases, caches, Codex session/log files, prompt drafts, starter runtime state, proposals, and backups.
- Commands and tests run: `python3 -m unittest tests.test_cli tests.test_generator tests.test_templates -v` passed with 40 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./scripts/smoke-test.sh` passed and exercised plan-only `rsync-plan` on a generated project.
- Results: Generated projects now include 44 files, validation requires `.agent-starter/rsync-excludes`, rsync plans are review-only by default, and explicit `--run` is covered with mocked subprocess execution.
- Security/data/performance/UX implications: The default command does not copy files. Execution requires `--run`; deletion requires `--delete`. No Codex login, OpenAI request, package installation, `sudo`, GitHub creation, remote push, deploy, or credential inspection was performed.
- Unresolved problems: Full source check still needs to run after this note.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T23:44:18Z — Phase D rsync verification

- Objective/phase: Record final verification for Phase D local mirror planning.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 54 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test with generated `.agent-starter/rsync-excludes` and plan-only `rsync-plan`, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, deployment, or real rsync execution.
- Unresolved problems: None for Phase D.
- Exact next step: Reassess the project roadmap and decide whether to cut a release or add another maturity phase.

## 2026-06-24T23:45:22Z — roadmap reassessment after Phase D

- Objective/phase: Reassess the completed sandbox manager maturity plan and define the next concrete phase.
- Files/subsystems changed: `docs/PROGRESS.md` and this implementation note.
- Behavior/design decisions: All Phase A-D maturity-plan items are complete, so the next responsible step is release readiness rather than adding another feature. Added Phase E with gates for version decision, representative generated-output inspection, source-tree full check, clean archive extraction verification, and archive/checksum handoff after approval.
- Commands and tests run: Pending full source check after this note.
- Results: Phase E is now the active next plan; no runtime behavior changed.
- Security/data/performance/UX implications: Documentation-only roadmap update. No Codex login, OpenAI request, package installation, `sudo`, GitHub creation, remote push, deployment, archive publication, or credential inspection was performed.
- Unresolved problems: Release version, archive build, clean extraction verification, and checksum publication remain pending.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T23:45:44Z — Phase E planning verification

- Objective/phase: Verify the documentation-only Phase E release-readiness plan.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 54 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test with 44 generated files, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, deployment, archive publication, or real rsync execution.
- Unresolved problems: Phase E release version decision and clean archive verification remain pending.
- Exact next step: Decide the next release version and update version files together if release approval is granted.

## 2026-06-24T23:46:42Z — Phase E version decision

- Objective/phase: Complete the first Phase E gate by selecting and applying the next release version.
- Files/subsystems changed: `VERSION`, `agent_starter/__init__.py`, `agent_starter/models.py`, `pyproject.toml`, `tests/test_cli.py`, `CHANGELOG.md`, `docs/PROGRESS.md`, and this implementation note.
- Behavior/design decisions: Selected `0.3.0` because the changes since `0.2.0` add several user-facing commands and generated workspace contracts: next-steps guidance, status/readiness gates, guided prompt generation, prompt templates, local-model assessment, license additions, local-first GitHub defaults, AI-local artifact hygiene, and rsync mirror planning. Moved accumulated changelog entries from Unreleased into `0.3.0 — 2026-06-24`.
- Commands and tests run: `python3 -m unittest tests.test_release tests.test_cli -v` passed with 21 tests; `python3 -m compileall -q agent_starter tests starter.py` passed; `bash -n install.sh uninstall.sh scripts/*.sh` passed; `./agent-starter --version` printed `agent-starter 0.3.0`.
- Results: Version sources are synchronized at `0.3.0`, and the release consistency test passes.
- Security/data/performance/UX implications: No Codex login, OpenAI request, package installation, `sudo`, GitHub creation, remote push, deployment, archive build, archive publication, or credential inspection was performed.
- Unresolved problems: Representative generated-output inspection, full source check after this note, clean archive extraction verification, and checksum handoff remain pending.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T23:47:05Z — Phase E version verification

- Objective/phase: Record full source verification after the `0.3.0` version update.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 54 unit/integration tests, shell syntax checks, source-tree CLI version check showing `agent-starter 0.3.0`, generation smoke test with 44 generated files, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, deployment, archive publication, or real rsync execution.
- Unresolved problems: Representative generated-output inspection, clean archive extraction verification, and checksum handoff remain pending.
- Exact next step: Inspect one new Python/SQLite generated project and one existing-project renovation after the 0.3.0 version update.

## 2026-06-24T23:49:26Z — Phase E generated-output inspection

- Objective/phase: Complete the representative generated-output inspection gate for the 0.3.0 release.
- Files/subsystems changed: `agent_starter/toolchains.py`, `tests/test_toolchains.py`, `docs/PROGRESS.md`, and this implementation note.
- Behavior/design decisions: Generated and inspected `/tmp/tmp.hBO3KlRedo/new-python-sqlite-final` from `examples/cli-python-sqlite-codex.json` and `/tmp/tmp.hBO3KlRedo/existing-renovation-final` from `examples/existing-php-mariadb-renovation.json` with a preexisting `README.md`. During inspection, the existing-project check exposed that JavaScript and Composer defaults could fail when `package.json` or `composer.json` did not exist. Fixed those generated defaults so manifest-based npm/composer commands skip with clear messages during discovery instead of failing the whole check.
- Commands and tests run: Generated both representative projects; validated both with `agent-starter validate --verbose`; ran `bash -n` over both generated script sets; ran both generated `scripts/check.sh`; ran `agent-starter status` on both projects; ran plan-only `agent-starter rsync-plan` on both projects; confirmed the existing README remained untouched and a proposal was created; ran `python3 -m unittest tests.test_toolchains tests.test_generator -v`, which passed with 14 tests.
- Results: The new Python/SQLite project generated 44 files, validated, and passed generated checks with placeholder messages. The existing PHP/MariaDB renovation preserved the preexisting README, created one proposal, validated with the expected proposal warning, and passed generated checks after manifest guards were added. Both projects included `NEXT_STEPS.md`, `.agent-starter/rsync-excludes`, Codex-only `AGENTS.md`, `docs/11-IMPLEMENTATION-NOTES.md`, and 0.3.0 implementation-note metadata.
- Security/data/performance/UX implications: Existing-project users no longer get a failing check merely because a selected stack has no manifest yet. No Codex login flow was started, no OpenAI request was made, no package installation or `sudo` was run, no GitHub repository was created, no remote push or deployment happened, and rsync remained plan-only.
- Unresolved problems: Full source check after this fix, clean archive extraction verification, and checksum handoff remain pending.
- Exact next step: Run `./scripts/check.sh`.

## 2026-06-24T23:49:54Z — Phase E generated-output verification

- Objective/phase: Record full source verification after the representative generated-output inspection and manifest-guard fix.
- Files/subsystems changed: `docs/IMPLEMENTATION-NOTES.md` only.
- Behavior/design decisions: No behavior changed in this follow-up; it records the completed verification gate.
- Commands and tests run: `./scripts/check.sh`.
- Results: Passed. The check ran Python syntax compilation, 55 unit/integration tests, shell syntax checks, source-tree CLI version check showing `agent-starter 0.3.0`, generation smoke test with 44 generated files, generated project `scripts/check.sh`, and user-local install/uninstall smoke test.
- Security/data/performance/UX implications: Verification did not run Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, deployment, archive publication, or real rsync execution.
- Unresolved problems: Clean archive extraction verification and checksum handoff remain pending.
- Exact next step: Build a clean 0.3.0 archive for extraction verification without caches, local Git metadata, generated workspaces, or credentials.

## 2026-06-24T23:59:58Z — Phase E clean archive verification

- Objective/phase: Build and verify a clean 0.3.0 release archive.
- Files/subsystems changed: `docs/PROGRESS.md` and this implementation note. Release artifacts were written under `/tmp`.
- Behavior/design decisions: Built `/tmp/cli-ai-agent-starter-kit-codex-0.3.0.tar.gz` with local `.git`, `.agents`, `.codex`, Python caches, and `.pyc` files excluded. Extracted it to `/tmp/tmp.FIw04Om7rQ/cli-ai-agent-starter-kit-codex-0.3.0` and verified the extracted CLI reports `agent-starter 0.3.0`.
- Commands and tests run: Listed archive contents; checked the tar listing for excluded cache/local metadata names; extracted the archive; ran `./scripts/check.sh` from the extracted archive; generated `/tmp/cli-ai-agent-starter-kit-codex-0.3.0.tar.gz.sha256`.
- Results: Extracted archive `./scripts/check.sh` passed with 55 unit/integration tests, shell syntax checks, source-tree CLI version check, generation smoke test with 44 generated files, generated project `scripts/check.sh`, and user-local install/uninstall smoke test. The final checksum is recorded in the sidecar file rather than embedded here so the archive can include these notes without a self-referential checksum.
- Security/data/performance/UX implications: No Codex login, OpenAI requests, package installation, `sudo`, GitHub creation, remote push, deployment, archive publication, or real rsync execution was performed. The archive excludes local agent metadata and cache files.
- Unresolved problems: Final archive/checksum handoff or publication remains pending explicit approval.
- Exact next step: Hand off `/tmp/cli-ai-agent-starter-kit-codex-0.3.0.tar.gz` and `/tmp/cli-ai-agent-starter-kit-codex-0.3.0.tar.gz.sha256`, or publish them only after explicit approval.

## 2026-06-25T00:04:56Z — Phase E local release handoff

- Objective/phase: Complete Phase E by preparing local 0.3.0 release artifacts for handoff.
- Files/subsystems changed: `docs/PROGRESS.md` and this implementation note. Release artifacts are written under ignored `dist/` and mirrored under `/tmp`.
- Behavior/design decisions: Treated the user's proceed request as approval for local artifact handoff only, not publication. No GitHub release, remote upload, package publication, or deployment is performed. The checksum is intentionally kept in the sidecar file rather than embedded in this note so the release archive can include completed release notes without a self-referential checksum.
- Commands and tests run: Pending final archive rebuild and clean extraction check after this note.
- Results: Phase E is marked complete for local handoff; final artifact paths and checksum will be reported in the final response.
- Security/data/performance/UX implications: Local handoff only. No Codex login, OpenAI request, package installation, `sudo`, GitHub creation, remote push, deployment, or credential inspection is performed.
- Unresolved problems: External acceptance remains pending: live Codex OAuth on CachyOS and a real generated project carried through its first Codex implementation phase.
- Exact next step: Rebuild the 0.3.0 archive with these final notes, regenerate checksum sidecar, and rerun clean extraction verification.

## 2026-06-25T03:10:22Z — External acceptance local dry-run

- Objective/phase: Exercise the local half of external acceptance with a disposable generated project before any real Codex task.
- Files/subsystems changed: `docs/PROGRESS.md` and this implementation note.
- Behavior/design decisions: Generated `/tmp/agent-starter-acceptance-small` from `examples/cli-python-sqlite-codex.json` with `--path` override. This validates the beginner path for a small idea without launching Codex, making an OpenAI request, publishing to GitHub, installing packages, or copying files with rsync.
- Commands and tests run: `./agent-starter generate --answers examples/cli-python-sqlite-codex.json --path /tmp/agent-starter-acceptance-small`; `./agent-starter validate /tmp/agent-starter-acceptance-small`; `./agent-starter status /tmp/agent-starter-acceptance-small`; `./agent-starter github-ready /tmp/agent-starter-acceptance-small`; `./agent-starter prompt /tmp/agent-starter-acceptance-small --template feature --phase "first implementation" --request "Build the smallest useful version of the CLI idea and keep the generated docs current."`; `./agent-starter rsync-plan /tmp/agent-starter-acceptance-small /tmp/agent-starter-acceptance-small-backup`.
- Results: Generation created 44 files, initialized local Git without a commit or remote, and passed starter validation. `status` reported Codex CLI installed and authorized through the CLI status surface, required generated files present, Git on `main` with uncommitted starter files, no origin remote, GitHub Actions deferred, AI-local artifacts ignored, and `NEXT_STEPS.md` as the next action. `github-ready` correctly exited nonzero and recommended against creating a GitHub repository or pushing because the local repo still had uncommitted files, while local checks passed. `prompt` generated a Codex-specific feature continuation prompt that instructs the agent to inspect docs/code, update tests and implementation notes, preserve safety boundaries, and report verification. `rsync-plan` printed a reviewable command and remained plan-only without copying data.
- Security/data/performance/UX implications: This verifies the intended local-first beginner workflow and GitHub pause behavior. No real Codex launch, Codex login, OpenAI request, package installation, `sudo`, GitHub creation, remote push, deployment, real rsync execution, or credential inspection was performed.
- Unresolved problems: Live external acceptance remains pending: a user completes `codex login` with the intended account on CachyOS, launches Codex from a generated project, and carries the first real implementation phase through `docs/11-IMPLEMENTATION-NOTES.md`.
- Follow-up verification: `./scripts/check.sh` passed after this note was added. The check ran Python syntax compilation, 55 unit/integration tests, shell syntax checks, source-tree CLI version check showing `agent-starter 0.3.0`, generation smoke test with 44 generated files, generated project `scripts/check.sh`, and user-local install/uninstall smoke test. The 0.3.0 archive was rebuilt with this note, scanned for excluded local/cache paths, extracted to `/tmp/agent-starter-release-check.fTG4Yg/cli-ai-agent-starter-kit-codex-0.3.0`, and its extracted `./scripts/check.sh` also passed with 55 tests and smoke checks. The refreshed checksum sidecar verified with `sha256sum -c`.
- Exact next step: Perform live external acceptance only when a human is ready to run Codex: confirm the intended account with `codex login`, launch Codex from a generated project, complete the first real implementation phase, and inspect the generated `docs/11-IMPLEMENTATION-NOTES.md` handoff.

## 2026-06-25T04:58:15Z — GitHub publication preparation

- Objective/phase: Prepare the source tree for an explicit GitHub repository and release publication request.
- Files/subsystems changed: `.gitignore`, `CHANGELOG.md`, and this implementation note.
- Behavior/design decisions: Added `.agents/` and `.codex/` to the source repository ignore rules before staging the initial release commit. This keeps local AI workspace metadata out of the GitHub repository while preserving the checked release source and generated project templates.
- Commands and tests run: `gh --version`; `gh auth status`; `./scripts/check.sh`; `git init -b main`; `git add .`; `git diff --cached --name-only`; staged-name scan for `.agents/`, `.codex/`, `dist/`, caches, `.pyc`, and env files.
- Results: `gh` is installed, but `gh auth status` reported the stored `omensealed` token is invalid and must be refreshed before remote repository creation can proceed. `./scripts/check.sh` passed with 55 tests and smoke checks after the ignore update. The staged-name scan found no local AI metadata, release artifacts, caches, bytecode, or env files in the index.
- Security/data/performance/UX implications: This is a publication hygiene change only. No GitHub repository, release, remote push, package publication, deployment, Codex login, OpenAI request, package installation, `sudo`, or credential inspection was performed.
- Unresolved problems: GitHub publication is blocked until the human refreshes GitHub CLI authentication for `omensealed`.
- Exact next step: After `gh auth refresh -h github.com` succeeds for `omensealed`, commit the staged release source, create `omensealed/omen-agentkit`, push `main`, and publish the `v0.3.0` release with the tarball and checksum.
