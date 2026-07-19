# Omen AgentKit 0.5.3 corrective release candidate evidence

## Candidate status

This is a local unpublished corrective candidate prepared on 2026-07-19. Tags `v0.5.0`, `v0.5.1`, and `v0.5.2` remain immutable records of fail-closed workflow attempts; no release or draft was created from them.

The 0.5.2 verification-only workflow succeeded completely. Its separately dispatched publication run repeated and passed exact intent, 409 tests, no-install sdist-to-wheel build, checksums, smoke, candidate upload, and attestation. The final command then failed because the intentionally checkout-free publication job did not pass an explicit repository to `gh release`. Version 0.5.3 binds both create and edit commands to `GITHUB_REPOSITORY`; it does not add checkout credentials or broaden job permissions.

The candidate version is aligned at `0.5.3` in `VERSION`, `pyproject.toml`, `agent_starter.__version__`, and `ProjectConfig.kit_version`. Unreleased is empty and the changelog preserves each corrective step.

## Local artifacts

Artifacts are built without installing packages through `python3 -m agent_starter.build_frontend --root . --outdir PATH`, which creates an sdist and builds the wheel from its validated temporary extraction.

- `cli_ai_agent_starter_kit-0.5.3-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.3.tar.gz`

Exact SHA-256/SPDX evidence in `SHA256SUMS` and `release.spdx.json` plus isolated wheel/sdist smoke remain mandatory. Digests are not hard-coded into source; they stay beside the artifacts.

## Burn-in and compatibility

No user-submitted migration-burn-in report or unresolved reported regression was found. Absence is not proof; the stable decision continues to rely on the mandatory journeys, fixtures, migration, security, clean-checkout, and artifact evidence.

Compatibility shims remain required through 0.5.3 and the following minor stable release.

## Release sequence

Commit and push only after local checks, create new immutable `v0.5.3`, run verification-only, then separately run publication. The checkout-free publication job must use the explicit repository, retain final-job-only `contents: write`, create a draft with verified assets, and publish it only as the final operation.
