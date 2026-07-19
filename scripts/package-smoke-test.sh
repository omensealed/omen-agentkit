#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 -m agent_starter.build_frontend --root "$ROOT" --outdir "$TMP/dist" >/dev/null
test "$(find "$TMP/dist" -maxdepth 1 -name '*.whl' | wc -l)" -eq 1
test "$(find "$TMP/dist" -maxdepth 1 -name '*.tar.gz' | wc -l)" -eq 1

WHEEL=$(find "$TMP/dist" -maxdepth 1 -name '*.whl' -print -quit)
SDIST=$(find "$TMP/dist" -maxdepth 1 -name '*.tar.gz' -print -quit)
python3 -m venv "$TMP/wheel-venv"
"$TMP/wheel-venv/bin/python" -m pip install --no-index --no-deps "$WHEEL" >/dev/null
python3 -m venv --system-site-packages "$TMP/sdist-venv"
"$TMP/sdist-venv/bin/python" -m pip install --no-index --no-deps --no-build-isolation "$SDIST" >/dev/null
cd "$TMP"
"$TMP/wheel-venv/bin/python" - "$ROOT" <<'PY'
import importlib
from importlib.metadata import distribution
import pkgutil
from pathlib import Path
import sys
import agent_starter

root = Path(sys.argv[1])
assert Path(agent_starter.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
names = {item.name for item in pkgutil.walk_packages(agent_starter.__path__, "agent_starter.")}
names.add("agent_starter")
expected = {
    ".".join(path.relative_to(root).with_suffix("").parts)
    for path in (root / "agent_starter").rglob("*.py")
}
expected = {name.removesuffix(".__init__") for name in expected}
missing = sorted(expected - names)
if missing:
    raise SystemExit(f"wheel omitted discovered modules/packages: {missing}")
excluded_imports = {"agent_starter.__main__"}
if not excluded_imports <= names:
    raise SystemExit("wheel omitted agent_starter.__main__")
for name in sorted(names - excluded_imports):
    importlib.import_module(name)
entry_points = {
    item.name: item.value
    for item in distribution("cli-ai-agent-starter-kit").entry_points
    if item.group == "console_scripts"
}
assert entry_points == {
    "agent-starter": "agent_starter.cli:main",
    "agent-starter-gui": "agent_starter.gui.app:main",
}
PY
"$TMP/sdist-venv/bin/python" - <<'PY'
from pathlib import Path
import sys
import agent_starter
import agent_starter.gui.app

assert Path(agent_starter.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
PY
"$TMP/sdist-venv/bin/agent-starter" --help >/dev/null
"$TMP/sdist-venv/bin/agent-starter-gui" --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter-gui" --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" prompt --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" audit-structure --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" audit-structure "$ROOT" --json >/dev/null
"$TMP/wheel-venv/bin/agent-starter" audit-context --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" deployment --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" deployment plan --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" deployment check --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" deployment build --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter" example-answers --output "$TMP/answers.json" >/dev/null
"$TMP/wheel-venv/bin/python" - "$TMP/answers.json" "$TMP/project" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["project_path"] = sys.argv[2]
data["git_enabled"] = False
data["sandbox"]["enabled"] = False
data["sandbox"]["mode"] = "none"
path.write_text(json.dumps(data), encoding="utf-8")
PY
"$TMP/wheel-venv/bin/agent-starter" generate --answers "$TMP/answers.json" >/dev/null
"$TMP/wheel-venv/bin/python" - "$TMP/project/deployment-target.json" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({
    "schema_version": 1,
    "target": "static-site",
    "environment": "staging",
    "target_identifier": "artifact-smoke",
    "artifact_output": "dist/site.zip",
    "local_writes": ["dist/site.zip"],
    "remote_writes": [],
    "commands": [["./scripts/build.sh"]],
    "network_destinations": [],
    "credential_references": [],
    "health_checks": ["Inspect the locally rendered static artifact."],
    "rollback_steps": ["Retain the previously reviewed artifact digest."],
}), encoding="utf-8")
source = Path(sys.argv[1]).parent / "public"
source.mkdir()
(source / "index.html").write_text("<h1>Artifact smoke</h1>\n", encoding="utf-8")
PY
git -C "$TMP/project" init -q
git -C "$TMP/project" add .
git -C "$TMP/project" -c user.name=Test -c user.email=test@example.invalid commit -qm baseline
"$TMP/wheel-venv/bin/agent-starter" deployment plan "$TMP/project" --profile deployment-target.json --format json --output .agent-starter/deployment-plans/smoke.json >/dev/null
"$TMP/wheel-venv/bin/agent-starter" deployment build "$TMP/project" --plan .agent-starter/deployment-plans/smoke.json --source public --format json >"$TMP/deployment-build.json"
if "$TMP/wheel-venv/bin/agent-starter" deployment check "$TMP/project" --plan .agent-starter/deployment-plans/smoke.json --format json >"$TMP/deployment-check.json"; then
    printf '%s\n' 'deployment check unexpectedly reported complete readiness' >&2
    exit 1
else
    test "$?" -eq 1
fi
"$TMP/wheel-venv/bin/python" - "$TMP/deployment-check.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["ready"] is False
assert data["authority"]["target_contacted"] is False
assert data["authority"]["credentials_accessed"] is False
assert data["authority"]["project_commands_executed"] is False
assert data["authority"]["writes_performed"] is False
statuses = {item["check_id"]: item["status"] for item in data["findings"]}
assert statuses["artifact_checksum"] == "passed"
assert statuses["artifact_reproducibility"] == "passed"
PY
"$TMP/wheel-venv/bin/agent-starter" validate "$TMP/project" >/dev/null
"$TMP/wheel-venv/bin/agent-starter" audit-context "$TMP/project" --json >/dev/null
printf '%s\n' 'Wheel/sdist isolated install smoke test passed.'
