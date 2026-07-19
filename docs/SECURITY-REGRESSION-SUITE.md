# Security regression suite

`./scripts/security-regression-check.sh` is the focused, standard-library-only security regression gate. It installs nothing, uses no network, launches no Codex process, and makes no remote or production change. The normal `./scripts/check.sh` gate also discovers the same tests through `unittest`.

The suite locks the following boundaries to their existing production APIs:

- unsafe generation roots, path traversal, and symlink-parent refusal before external writes;
- answer-file credential-pattern rejection without value echo;
- structured schema/type and package-identifier validation;
- rejection of AI command/prompt-injection payloads without process execution;
- same-day idea-prompt collision suffixing with preservation of prior content;
- GUI diagnostic secret redaction without tracebacks;
- stale-plan and wrong-target deployment rejection before staging mutation, plus closed redacted audit output;
- project-only sandbox mounts, default-off network, dropped capabilities, and no host credential/runtime socket mounts.

These tests are synthetic and temporary-directory confined. They must never be changed to read credentials, run proposed commands, install packages, pull images, access a deployment target, weaken approval/sandbox/network policy, or replace an existing file silently. A newly failing assertion is a security compatibility signal: fix the smallest responsible production boundary or document a deliberate reviewed contract change; do not loosen the assertion merely to obtain a pass.
