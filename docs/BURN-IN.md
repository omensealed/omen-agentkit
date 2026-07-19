# 0.5.0 migration burn-in

The 0.5.0 candidate uses an opt-in, user-submitted issue process. AgentKit adds no telemetry, background reporting, analytics, crash upload, or automatic host inventory. Running AgentKit does not create an issue or contact GitHub.

## What to exercise

When practical, try one bounded journey on a disposable or backed-up project:

- user-local installation or direct source execution without `sudo`;
- `doctor` on CachyOS/Arch, Debian, or Ubuntu;
- a fresh project or an existing-project renovation;
- schema-v1 migration preview and separate-output write;
- deterministic or reviewed AI-assisted capability recommendations;
- generated project validation and local checks;
- task-composer feature or fix flow;
- optional local deployment plan/check/build evidence without apply.

Do not run package installation, Codex login, a push, publication, deployment, database migration, or destructive replacement solely for burn-in. Existing-project testing should use a backup or disposable copy and retain proposals/backups for review.

## Submit a report manually

Use the repository's **0.5.0 migration burn-in report** issue form. Every report is user-submitted; there is no automatic collection. Include the smallest reproduction, expected and actual behavior, host family, Python version, and whether the project was fresh or existing.

Do not include credentials, OAuth tokens, API keys, cookies, session data, browser or keyring contents, SSH material, private repository URLs, secret values, raw environment dumps, usernames, home paths, or proprietary project content. Replace paths and project names with neutral placeholders. Review every pasted command and log line first.

Useful safe evidence may include the AgentKit version, a redacted `doctor --json` result, validation issue codes, the schema migration warning, and a synthetic answers file. Do not attach an entire home directory, `.env`, `.codex`, `.ssh`, browser profile, or diagnostic store.

## Triage and stable-release gate

Maintainers classify submitted reports as migration, provider, packaging/install, safety, documentation, or unrelated. A reproducible regression in schema preservation, provider selection, artifact discovery, unsafe-path handling, approvals, credential boundaries, or deployment authority blocks stable release until fixed and covered by a regression test.

Absence of submitted reports is not proof that a platform works. The checked-in synthetic journeys, existing-project fixtures, security suite, and artifact smoke remain required evidence. Burn-in reports supplement those gates; they never replace them.

Compatibility shims remain required through 0.5.0 and the following minor stable release, as defined in the [migration report](GPT-5.6-SOL-MIGRATION-REPORT.md). User-submitted evidence may extend that window but cannot shorten it.
