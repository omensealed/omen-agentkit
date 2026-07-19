# Omen AgentKit 0.5.1 corrective release candidate evidence

## Candidate status

This is a local unpublished corrective candidate prepared on 2026-07-19 after the verification-only `v0.5.0` workflow failed closed. No 0.5.0 artifact or GitHub release was published. The remote 0.5.0 tag remains immutable at its reviewed commit; it is not moved, overwritten, or reused.

The failure exposed a source-checkout/package mismatch: private local `docs/IMPLEMENTATION-NOTES.md` and `docs/PROGRESS.md` files masked public documentation links and package-manifest entries that could not resolve in a clean GitHub checkout. Version 0.5.1 preserves their intentional ignored/private status, removes public dependencies on them, and adds source-checkout regression coverage while preserving all 0.5.0 compatibility behavior.

The candidate version is aligned at `0.5.1` in `VERSION`, `pyproject.toml`, `agent_starter.__version__`, and `ProjectConfig.kit_version`. `CHANGELOG.md` has an empty Unreleased section and dated 0.5.1 and 0.5.0 sections.

## Local artifacts

The definitive candidate artifacts must be built into a new non-repository directory with `python3 -m build --no-isolation`, receive create-only SHA-256/SPDX evidence, and pass isolated no-index wheel/sdist smoke installation.

- `cli_ai_agent_starter_kit-0.5.1-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.1.tar.gz`

Exact digests and sizes remain beside the artifacts in `SHA256SUMS` and `release.spdx.json`, not hard-coded into source. The sdist must contain this candidate page, migration/burn-in/security documentation, and the manual issue form; it must not claim the intentionally private maintainer ledgers.

## Burn-in and compatibility

The repository issue query found no user-submitted migration-burn-in reports and therefore no reported regression requiring resolution. Absence is not proof; the mandatory synthetic journeys, existing-project fixtures, v1 migration tests, security/deployment gates, source-checkout tests, and exact artifact smoke remain required.

Compatibility shims remain required through 0.5.1 and the following minor stable release. Deprecated schema-v1 and saved advisor fields remain loadable under the migration report timeline.

## Release sequence

The maintainer explicitly authorized the gated tag and release sequence. After a clean full check and exact local artifact smoke, commit and push the correction, create a new immutable `v0.5.1` tag, run `release.yml` with `publish: false`, and only after success dispatch `publish: true`. Any failure stops the sequence before publication.
