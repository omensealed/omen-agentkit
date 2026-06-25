# Security policy

Do not submit live credentials, OAuth artifacts, private keys, browser cookies, keyring exports, production data, or a public exploit report containing sensitive target details.

Report security issues privately to the repository owner. Include the smallest synthetic reproduction possible. The core security model is documented in `docs/SECURITY-MODEL.md`.

High-priority issues include path traversal or symlink overwrite, secret persistence, automatic execution of AI output, authorization-token exposure, unsafe `sudo`/package-manager behavior, and permission-bypass defaults.
