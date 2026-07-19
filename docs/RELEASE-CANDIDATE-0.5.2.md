# Omen AgentKit 0.5.2 corrective release candidate evidence

## Candidate status

This is a local unpublished corrective candidate prepared on 2026-07-19 after verification-only tags `v0.5.0` and `v0.5.1` failed closed before artifact publication. Neither tag was moved or overwritten, and no GitHub release was created.

The 0.5.0 failure exposed public links to private workspace ledgers; 0.5.1 corrected that boundary. Its remote full test suite passed 407 tests, then the package smoke stopped because a clean GitHub Python environment did not provide the optional `build` frontend. Version 0.5.2 uses a narrow local frontend over the already-declared setuptools PEP 517 backend. It installs nothing and retains create-only output, exact-artifact smoke, checksum, SPDX, and attestation gates.

The candidate version is aligned at `0.5.2` in `VERSION`, `pyproject.toml`, `agent_starter.__version__`, and `ProjectConfig.kit_version`. `CHANGELOG.md` has an empty Unreleased section and dated corrective sections.

## Local artifacts

The definitive candidate artifacts are built with `python3 -m agent_starter.build_frontend --root . --outdir PATH`. The command requires the setuptools backend already declared by `pyproject.toml`; it does not install packages or contact a package index.

- `cli_ai_agent_starter_kit-0.5.2-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.2.tar.gz`

Exact digests remain beside the artifacts in `SHA256SUMS` and `release.spdx.json`, not hard-coded into source. Exact isolated wheel/sdist smoke remains mandatory.

## Burn-in and compatibility

No user-submitted migration-burn-in report or unresolved reported regression was found. Absence is not proof; synthetic journeys, existing-project fixtures, v1 migration tests, security/deployment gates, clean-checkout checks, and exact artifact smoke remain the evidence basis.

Compatibility shims remain required through 0.5.2 and the following minor stable release.

## Release sequence

After local gates pass, commit and push the correction, create new immutable tag `v0.5.2`, dispatch verification with `publish: false`, and only after success dispatch `publish: true`. Any failure stops before publication and must use a new version rather than moving a tag.
