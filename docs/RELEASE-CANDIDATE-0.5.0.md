# Omen AgentKit 0.5.0 release candidate evidence

## Candidate status

This was prepared as a local unpublished candidate from the protected working tree on 2026-07-19. Before separate commit authorization, no commit, tag, push, release, or publication was performed, and the binding verifier returned `dirty_release_source` as expected. The reviewed candidate was subsequently committed as `bf2927a9f238d6fcb0101a5abcec02afbb6115d8`, passed the complete trusted suite again from a clean tree, and was pushed to `main` without force. The human then explicitly authorized the gated tag and release sequence.

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

Burn-in intake is defined by [BURN-IN.md](BURN-IN.md) and the manual GitHub issue form. There is no telemetry. Immediately before the stable-release decision, the repository's migration-burn-in issue query returned no reports, so there are no reported regressions to triage or resolve. Absence of reports is not treated as proof: the decision relies on the required synthetic journeys, existing-project fixtures, schema migration coverage, security/deployment gates, and exact artifact smoke, all of which passed.

Compatibility shims remain required through 0.5.0 and the following minor stable release. Deprecated schema-v1 and saved advisor fields remain loadable under the [migration report](GPT-5.6-SOL-MIGRATION-REPORT.md) timeline.

## Stable-release decision

The maintainer confirmed the clean reviewed candidate commit, found no submitted burn-in regression, and explicitly authorized creating and pushing `v0.5.0` followed by the manual release workflow. A `publish: false` verification run must succeed before a separately dispatched `publish: true` run. The exact-tag, checksum, attestation, draft-first, and final-job-only write boundaries remain binding.
