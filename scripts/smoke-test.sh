#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
ANSWERS="$TMP/answers.json"
PROJECT="$TMP/generated-project"

./agent-starter example-answers --output "$ANSWERS"
python3 - "$ANSWERS" "$PROJECT" <<'PY'
import json
import sys
from pathlib import Path

answers = Path(sys.argv[1])
project = Path(sys.argv[2])
data = json.loads(answers.read_text(encoding="utf-8"))
data["project_name"] = "Starter Smoke Test"
data["project_slug"] = "starter-smoke-test"
data["project_path"] = str(project)
data["description"] = "Verify a complete fresh project generation."
data["git_enabled"] = False
data["github_remote"] = "none"
answers.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

./agent-starter generate --answers "$ANSWERS"
./agent-starter validate "$PROJECT"
./agent-starter status "$PROJECT" >"$TMP/status.txt"
./agent-starter rsync-plan "$PROJECT" "$TMP/mirror" >"$TMP/rsync-plan.txt"
"$PROJECT/scripts/check.sh"
bash -n "$PROJECT"/START_AGENT.sh "$PROJECT"/scripts/*.sh

grep -q '^# Starter Smoke Test$' "$PROJECT/README.md"
grep -q '^# Next steps$' "$PROJECT/NEXT_STEPS.md"
grep -q 'agent-starter status .' "$PROJECT/NEXT_STEPS.md"
grep -q 'agent-starter github-ready' "$PROJECT/NEXT_STEPS.md"
grep -q 'agent-starter rsync-plan' "$PROJECT/NEXT_STEPS.md"
grep -q 'Workspace status:' "$TMP/status.txt"
grep -q 'AI-local artifacts:' "$TMP/status.txt"
grep -q 'Plan only' "$TMP/rsync-plan.txt"
grep -q '.agent-starter/rsync-excludes' "$TMP/rsync-plan.txt"
grep -q 'GitHub Actions were deferred by default' "$PROJECT/NEXT_STEPS.md"
grep -q 'docs/11-IMPLEMENTATION-NOTES.md' "$PROJECT/AGENTS.md"
if [[ -e "$PROJECT/.github/workflows/ci.yml" ]]; then
  printf '%s\n' 'Default smoke answers should stay local-first and not generate GitHub Actions.' >&2
  exit 1
fi
if grep -q 'terminal noise' "$PROJECT/.agent-starter/project.json"; then
  printf '%s\n' 'Raw advisor output leaked into project metadata.' >&2
  exit 1
fi
printf '%s\n' 'Generation smoke test passed.'
