#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'Usage: scripts/release-artifact-smoke.sh DIST_DIRECTORY' >&2
  exit 2
fi
DIST=$1
if [ ! -d "$DIST" ] || [ -L "$DIST" ]; then
  printf '%s\n' 'Release artifact directory must be a non-symlink directory.' >&2
  exit 2
fi
WHEEL_COUNT=$(find "$DIST" -maxdepth 1 -type f -name '*.whl' | wc -l)
SDIST_COUNT=$(find "$DIST" -maxdepth 1 -type f -name '*.tar.gz' | wc -l)
if [ "$WHEEL_COUNT" -ne 1 ] || [ "$SDIST_COUNT" -ne 1 ]; then
  printf '%s\n' 'Expected exactly one regular wheel and one regular source distribution.' >&2
  exit 2
fi
WHEEL=$(find "$DIST" -maxdepth 1 -type f -name '*.whl' -print -quit)
SDIST=$(find "$DIST" -maxdepth 1 -type f -name '*.tar.gz' -print -quit)
test -f "$DIST/SHA256SUMS"
test ! -L "$DIST/SHA256SUMS"
test -f "$DIST/release.spdx.json"
test ! -L "$DIST/release.spdx.json"
(cd "$DIST" && sha256sum --check SHA256SUMS)

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python3 -m venv "$TMP/wheel-venv"
python3 -m venv --system-site-packages "$TMP/sdist-venv"
"$TMP/wheel-venv/bin/python" -m pip install --no-index --no-deps "$WHEEL" >/dev/null
"$TMP/sdist-venv/bin/python" -m pip install --no-index --no-deps --no-build-isolation "$SDIST" >/dev/null

cd "$TMP"
"$TMP/wheel-venv/bin/python" - "$ROOT" <<'PY'
import importlib
from importlib.metadata import distribution
from pathlib import Path
import pkgutil
import sys
import agent_starter

root = Path(sys.argv[1])
assert Path(agent_starter.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
installed = {item.name for item in pkgutil.walk_packages(agent_starter.__path__, "agent_starter.")}
installed.add("agent_starter")
expected = {
    ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(".__init__")
    for path in (root / "agent_starter").rglob("*.py")
}
missing = sorted(expected - installed)
if missing:
    raise SystemExit(f"release wheel omitted modules/packages: {missing}")
for name in sorted(installed - {"agent_starter.__main__"}):
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
EXPECTED_VERSION=$(tr -d '\n' <"$ROOT/VERSION")
test "$("$TMP/wheel-venv/bin/agent-starter" --version)" = "agent-starter $EXPECTED_VERSION"
test "$("$TMP/sdist-venv/bin/agent-starter" --version)" = "agent-starter $EXPECTED_VERSION"
"$TMP/wheel-venv/bin/agent-starter" --help >/dev/null
"$TMP/wheel-venv/bin/agent-starter-gui" --help >/dev/null
"$TMP/sdist-venv/bin/agent-starter" --help >/dev/null
"$TMP/sdist-venv/bin/agent-starter-gui" --help >/dev/null
printf '%s\n' 'Exact release wheel/sdist smoke test passed.'
