#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

python3 -m agent_starter.performance_checks
python3 -m unittest tests.test_performance_resources -v
