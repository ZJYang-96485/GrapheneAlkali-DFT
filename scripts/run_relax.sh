#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 INPUT.in [OUTPUT.out]" >&2
    echo "Optional environment: QE_BIN=pw.x MPI_NP=<processes>" >&2
    exit 2
fi

INPUT_ARG="$1"
if [[ -f "$INPUT_ARG" ]]; then
    INPUT_PATH="$(cd "$(dirname "$INPUT_ARG")" && pwd)/$(basename "$INPUT_ARG")"
else
    INPUT_PATH="$ROOT_DIR/$INPUT_ARG"
fi

if [[ ! -f "$INPUT_PATH" ]]; then
    echo "Input file not found: $INPUT_ARG" >&2
    exit 2
fi

if grep -q '__QE_UNRESOLVED__' "$INPUT_PATH"; then
    echo "Refusing to run: unresolved DFT choices remain in $INPUT_PATH" >&2
    echo "Edit config/qe.yaml, regenerate the input, and review it before running." >&2
    exit 2
fi

if ! grep -Eq "calculation[[:space:]]*=[[:space:]]*['\"]relax['\"]" "$INPUT_PATH"; then
    echo "Refusing to run: input is not explicitly marked calculation='relax'." >&2
    exit 2
fi

if grep -Eqi "calculation[[:space:]]*=[[:space:]]*['\"]vc-relax['\"]" "$INPUT_PATH"; then
    echo "Refusing to run: vc-relax is outside the fixed-cell Phase 2 workflow." >&2
    exit 2
fi

if [[ $# -eq 2 ]]; then
    OUTPUT_ARG="$2"
    if [[ "$OUTPUT_ARG" = /* ]]; then
        OUTPUT_PATH="$OUTPUT_ARG"
    else
        OUTPUT_PATH="$ROOT_DIR/$OUTPUT_ARG"
    fi
else
    OUTPUT_PATH="${INPUT_PATH%.in}.out"
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"
QE_BIN="${QE_BIN:-pw.x}"

cd "$ROOT_DIR"
if [[ -n "${MPI_NP:-}" ]]; then
    command -v mpirun >/dev/null 2>&1 || {
        echo "MPI_NP is set but mpirun was not found in PATH." >&2
        exit 2
    }
    mpirun -np "$MPI_NP" "$QE_BIN" -in "$INPUT_PATH" >"$OUTPUT_PATH" 2>&1
else
    "$QE_BIN" -in "$INPUT_PATH" >"$OUTPUT_PATH" 2>&1
fi

echo "QE run complete: $OUTPUT_PATH"
