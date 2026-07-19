#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

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

printf '%s\n' '== Wheel/sdist install smoke test =='
./scripts/package-smoke-test.sh

printf '%s\n' 'All starter-kit checks passed.'
