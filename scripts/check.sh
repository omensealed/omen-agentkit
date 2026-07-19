#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

SKIP_PACKAGE_SMOKE=0
if [[ ${1:-} == "--skip-package-smoke" && $# -eq 1 ]]; then
    SKIP_PACKAGE_SMOKE=1
elif [[ $# -ne 0 ]]; then
    printf '%s\n' 'Usage: ./scripts/check.sh [--skip-package-smoke]' >&2
    exit 2
fi

printf '%s\n' '== Python syntax =='
python3 -m compileall -q agent_starter tests starter.py

printf '%s\n' '== Unit and integration tests =='
python3 -m unittest discover -s tests -v

printf '%s\n' '== Shell syntax =='
bash -n install.sh uninstall.sh scripts/*.sh

printf '%s\n' '== Source-tree CLI =='
./agent-starter --version
./agent-starter toolchains >/dev/null

printf '%s\n' '== Generation smoke test =='
./scripts/smoke-test.sh

printf '%s\n' '== User-local install smoke test =='
./scripts/install-smoke-test.sh

if [[ "$SKIP_PACKAGE_SMOKE" -eq 0 ]]; then
    printf '%s\n' '== Wheel/sdist install smoke test =='
    ./scripts/package-smoke-test.sh
else
    printf '%s\n' '== Wheel/sdist install smoke test skipped by explicit CI matrix policy =='
fi

printf '%s\n' 'All starter-kit checks passed.'
