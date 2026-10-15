#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "run_relax.sh is now GPU-only; forwarding to run_relax_gpu.sh." >&2
exec bash "$SCRIPT_DIR/run_relax_gpu.sh" "$@"
