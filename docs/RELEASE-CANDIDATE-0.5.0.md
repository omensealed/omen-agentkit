# Omen AgentKit 0.5.0 release candidate evidence

## Candidate status

This is a local unpublished candidate prepared from the protected working tree on 2026-07-19. It is evidence for review and burn-in, not a stable release. Before separate commit authorization, no commit, tag, push, release, or publication was performed, and the binding verifier returned `dirty_release_source` as expected. The human subsequently authorized one local candidate commit. That authorization does not include a tag, push, workflow dispatch, release, or publication; current cleanliness must be checked directly rather than inferred from this historical evidence.

The candidate version is aligned at `0.5.0` in `VERSION`, `pyproject.toml`, `agent_starter.__version__`, and `ProjectConfig.kit_version`. `CHANGELOG.md` has an empty Unreleased section and one dated 0.5.0 section.

## Local artifacts

The definitive local candidate artifacts are built into a new non-repository directory with `python3 -m build --no-isolation`. They receive create-only SHA-256/SPDX evidence and isolated no-index wheel/sdist smoke installation.

- `cli_ai_agent_starter_kit-0.5.0-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.0.tar.gz`

Exact digests and sizes are recorded beside the built artifacts in `SHA256SUMS` and `release.spdx.json`, and in the final maintainer handoff. They are intentionally not hard-coded into source because embedding the sdist digest in a file contained by that sdist would change the digest. Both artifact checksums must verify and exact isolated wheel/sdist smoke must pass. The sdist explicitly contains this evidence page, migration, audience, burn-in, security, maintainer documentation, and the manual issue form.

## Automated evidence

- The final included-source `./scripts/check.sh` passed 406 tests in 21.603s: 405 passed and the intentional preloaded-container check skipped. Fresh-user journeys, existing-project fixtures, security/deployment gates, provider matrices, generated checks, installer ownership, and isolated artifact smoke passed.
- Candidate-specific tests align versions/changelog, require user-submitted-only burn-in, prove the dirty-tree release block, retain compatibility windows, and check sdist routing.
- The release workflow remains manual, exact-tag-bound, and default-off for publication. A local candidate never grants tag or publication authority.

## Burn-in and compatibility

Burn-in intake is defined by [BURN-IN.md](BURN-IN.md) and the manual GitHub issue form. There is no telemetry. At candidate preparation time, no user-submitted burn-in report has been received in this local workspace; absence of reports is not evidence of correctness.

Compatibility shims remain required through 0.5.0 and the following minor stable release. Deprecated schema-v1 and saved advisor fields remain loadable under the [migration report](GPT-5.6-SOL-MIGRATION-REPORT.md) timeline.

## Human-only next gates

Before any stable release, a maintainer must resolve blocking user-submitted regressions, confirm the reviewed candidate commit and clean tree, and explicitly decide whether to create/push `v0.5.0`. Verification-only workflow dispatch should precede any separately approved publication attempt. The local commit authorization does not grant any of those later actions.
