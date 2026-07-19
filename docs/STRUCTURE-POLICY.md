# Advisory source-structure policy

The structure policy identifies review signals; it does not fail builds, scan the filesystem, or decide that a
large file must be split. Cohesion, dependency direction, test seams, and maintenance responsibility matter more
than minimizing line counts or maximizing file counts. A clear 600-line protocol/template payload can be safer than
dozens of wrappers, while a short module that mixes unrelated state, UI, persistence, and networking may need work.

## Default signals

| Signal | Default review point |
| --- | --- |
| Source module size | More than 500 logical lines |
| Function size | More than 80 logical lines |
| Responsibility breadth | More than one reported unrelated category for a module or class |
| Dependency direction | A newly introduced closed module cycle |
| Growth pattern | Three or more append-only changes to a module already over the size threshold |
| Public boundary | Public module without a documented purpose |

Every finding has severity `warning` and `blocking = false`. The 500/80 values are starting signals, not universal
laws. `agent-starter audit-structure PROJECT` supplies bounded standard-library AST/token measurements and orders
hotspots by review score. Add `--json` for the versioned machine-readable report. Findings never make the command
fail; unsafe roots or malformed baseline authority do.

## Exemptions

Reviewed size exemptions are limited to generated data, static data, license text, protocol tables, and cohesive
template payloads. Each exemption requires a short reason. It may acknowledge module size and functions explicitly
measured as payload-only; executable functions still warn. It cannot hide executable complexity, mixed
responsibilities, a dependency cycle, repeated append-only growth, or an undocumented public boundary.

Record reviewed measurements and exemptions in `.agent-starter/structure-baseline.json`, or pass another regular
project-confined file with `--baseline`. The auditor only reads this file and never creates or replaces it. Schema 1
has closed top-level fields: `schema_version`, `modules`, `dependency_cycles`, and `exemptions`. Each module metric
contains exact non-negative `logical_lines`, `function_count`, `class_count`, and `append_only_changes` fields.
Cycles are closed dotted-module-name lists. Exemptions use an allowed `category` and bounded `reason`; executable
complexity cannot be exempted. Unknown fields, ambiguous types, symlinks, out-of-root paths, oversized input, and
malformed JSON fail closed. No source annotation or undocumented magic comment is recognized.

When no baseline exists, current cycles remain visible but are not claimed as newly introduced. With a loaded
baseline, the report shows module/function/class deltas, removed modules, newly introduced cycles, the supplied
append-growth count, and acknowledged exemptions. Baseline maintenance is an explicit human review action.

## Policy boundary

`agent_starter.structure.policy` contains only typed thresholds, observations, exemptions, findings, and evaluation.
`agent_starter.structure.audit` owns bounded traversal, parsing, measurement, cycle/delta analysis, and rendering.
The auditor scans regular Python source only; it does not import or execute target modules, inspect Git history, run
commands, use the network, or write the target. Symlinked inputs and standard generated/cache directories are skipped.
