# Architecture

## Design

The kit is a single Python 3.11+ package with no runtime dependencies outside the standard library. It has one external AI boundary: the official OpenAI Codex CLI.

- `cli.py` parses subcommands and coordinates generation, validation, Codex account setup, optional GitHub setup, and launch.
- `wizard.py` owns terminal questions, project modeling, secret-like-input rejection, Codex advisor prompts, recommendation review, and deterministic fallback advice.
- `agents.py` is the Codex process boundary. It invokes documented CLI commands and never reads token files, browser state, or keyrings.
- `models.py` contains serializable project configuration and advisor-result dataclasses.
- `toolchains.py` maps selected languages/databases to CachyOS packages, known commands, ignore entries, and CI setup.
- `templates.py` renders the generated project contract, numbered docs, shell helpers, and workflow.
- `sandbox.py` renders optional rootless Podman sandbox files and read-only sandbox diagnostics.
- `generator.py` verifies safe paths, renders the file map, writes atomically, preserves conflicts/backups, optionally initializes Git, and validates the result.

`ollama-check` is an assessment-only local-model handoff gate. It inspects installed Ollama model metadata and can generate a warning-rich handoff prompt, but it does not add an alternate agent adapter, generated launcher, authentication path, or Codex configuration rewrite.

Optional rootless Podman sandbox support is generated project infrastructure, not an orchestration layer. It can create project-scoped toolchain/test scripts and explicit Codex-inside-container launch helpers, but it does not run Podman during generation, install host packages, mount host credentials, copy Codex sessions, or change the Codex-only agent invariant.

## Data flow

```text
interactive answers or reviewed JSON
                |
                v
       ProjectConfig (non-secret)
                |
                +--> optional Codex read-only advisor
                |          |
                |          v
                |   validated JSON recommendation
                |   (commands remain advisory)
                v
          template file map
                |
                v
 safe writer / proposals / backups / manifest
                |
                v
     generated workspace validation
                |
                v
 optional official Codex OAuth and project launch
```

The `primary_agent` metadata field is a fixed `codex` invariant, not a client-selection mechanism. It lets validation reject workspaces from incompatible editions instead of attempting an unsafe launch.

## Trust boundaries

Untrusted inputs include terminal answers, answers JSON, existing files, model output, project paths, and tool output. Privileged or external boundaries include `sudo pacman`, Codex OAuth/browser handling, GitHub network operations, and Codex tool execution inside a generated project.

Authority is minimized by generating and validating before launch, requiring explicit approval for system installation, using Codex sandbox/approval settings, keeping advice calls read-only, and delegating all account credentials to the official client.

When enabled, the rootless Podman sandbox adds a second containment layer for project toolchain work. It still treats the project bind mount as writable user data, keeps host secrets unmounted by default, and documents that containers reduce host filesystem risk without making untrusted code safe.

## Architecture decision — local model handoff gate

The Codex-only edition may help a user evaluate whether an installed Ollama model is likely to continue a project safely, but Codex remains the only built-in launch and authorization path. The local-model gate must:

- inspect only local Ollama metadata unless the user separately runs Ollama;
- require confirmed context length and coding-capability signals before treating a model as suitable, using Codex's recommended complex-coding model (`gpt-5.5` in the current manual) as the quality baseline rather than assuming local parity;
- refuse handoff-prompt generation for borderline or inadvisable models unless `--override` is supplied;
- preserve warnings inside generated local-model handoff prompts;
- avoid editing `.codex/config.toml`, generated `START_AGENT.sh`, generated helper scripts, project metadata `primary_agent`, or Codex OAuth behavior.

This keeps local-model experimentation explicit and reversible without making generated projects unusable for the supported Codex workflow.
