# Contributing

Read `AGENTS.md` and `docs/DEVELOPMENT.md`. Keep changes focused, add regression tests, run `./scripts/check.sh`, inspect generated output, and update documentation plus `docs/IMPLEMENTATION-NOTES.md`.

Do not include credentials, captured model tokens, keyring data, production data, generated test workspaces, caches, or unrelated formatting changes. Runtime dependencies require an explicit architecture decision; the normal answer is to use the Python standard library.

The optional maintainer gate is `./scripts/quality-check.sh` after a human explicitly installs `.[quality]`. It does
not replace `./scripts/check.sh`, install its own tools, or authorize repository-wide formatting. Record missing optional
tools honestly; never weaken runtime dependency or network boundaries to make the optional gate available.

Packaging or installer changes must run both `./scripts/package-smoke-test.sh` and `./scripts/install-smoke-test.sh`.
Keep wheel/sdist environments separate, import every discovered safe module, exercise CLI and dependency-free GUI help,
and preserve owned/pre-marker/unowned/symlink path behavior. Never weaken ownership checks to simplify an upgrade.
