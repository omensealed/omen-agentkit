#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

missing=0
for module in ruff mypy bandit coverage; do
  if ! python3 -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('$module') else 1)"; then
    printf 'Missing maintainer quality module: %s\n' "$module" >&2
    missing=1
  fi
done
if ((missing)); then
  printf '%s\n' "Install the reviewed optional extra explicitly: python3 -m pip install -e '.[quality]'" >&2
  printf '%s\n' 'This script never installs tools or contacts a package index.' >&2
  exit 2
fi

printf '%s\n' '== Ruff critical lint =='
python3 -m ruff check agent_starter tests starter.py

printf '%s\n' '== Mypy typed policy/schema seams =='
python3 -m mypy

printf '%s\n' '== Bandit medium/high static security scan =='
python3 -m bandit -q -r agent_starter -x agent_starter/gui/static -ll

printf '%s\n' '== Branch coverage =='
COVERAGE_FILE=$(mktemp /tmp/agentkit-quality-coverage.XXXXXX)
export COVERAGE_FILE
trap 'rm -f "$COVERAGE_FILE"' EXIT
python3 -m coverage run -m unittest discover -s tests -q
python3 -m coverage report

printf '%s\n' 'Optional maintainer quality checks passed.'
