#!/usr/bin/env bash
# Run KGc backtracking milestone tests with presentation-friendly output.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/kgc_test_report.py "$@"
