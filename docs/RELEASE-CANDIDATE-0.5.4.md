# Omen AgentKit 0.5.4 corrective release candidate evidence

## Candidate status

This is a local unpublished corrective candidate prepared on 2026-07-19. Tags `v0.5.0` through `v0.5.3` remain immutable fail-closed evidence; no draft or GitHub release was created from them.

The 0.5.3 verification-only workflow succeeded. Its publication run repeated all verification, artifact, checksum, smoke, upload, and attestation gates, then GitHub CLI rejected the combination of explicit checkout-free `--repo` selection and `--notes-from-tag`. Version 0.5.4 uses explicit bounded notes that direct maintainers to the changelog at the exact tag. It retains the checkout-free final job and does not broaden permissions.

The candidate version is aligned at `0.5.4` in all four source owners, Unreleased is empty, and the changelog preserves each corrective step.

## Local artifacts

- `cli_ai_agent_starter_kit-0.5.4-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.4.tar.gz`

Artifacts use the no-install sdist-to-wheel frontend. Exact evidence remains in `SHA256SUMS` and `release.spdx.json`; digests are not hard-coded into source. Isolated smoke remains mandatory.

## Burn-in and compatibility

No user-submitted migration-burn-in report or unresolved reported regression was found. Absence is not proof; mandatory journeys, fixtures, migration, security, clean-checkout, and artifact evidence remain the basis.

Compatibility shims remain required through 0.5.4 and the following minor stable release.

## Release sequence

Use a new immutable `v0.5.4`, verification-only dispatch, and separate publication dispatch. The final checkout-free job must bind the repository explicitly, use bounded explicit notes, publish only the verified assets, and retain final-job-only write authority.
