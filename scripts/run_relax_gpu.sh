#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QE_REQUIRE_CALCULATION=relax exec bash "$SCRIPT_DIR/run_pw_gpu.sh" "$@"
