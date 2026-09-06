#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 INPUT.in [OUTPUT.out]" >&2
    echo "Environment: QE_BIN=pw.x OMP_NUM_THREADS=<threads> CUDA_VISIBLE_DEVICES=0 QE_GPU_CONFIRMED=1" >&2
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
    echo "Refusing to run: unresolved values remain in $INPUT_PATH" >&2
    exit 2
fi
if ! grep -Eq "calculation[[:space:]]*=[[:space:]]*['\"]relax['\"]" "$INPUT_PATH"; then
    echo "Refusing to run: input is not explicitly calculation='relax'." >&2
    exit 2
fi
if grep -Eqi "calculation[[:space:]]*=[[:space:]]*['\"]vc-relax['\"]" "$INPUT_PATH"; then
    echo "Refusing to run: vc-relax is outside this fixed-cell workflow." >&2
    exit 2
fi

if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi >/dev/null 2>&1; then
    echo "Refusing to run: WSL cannot access an NVIDIA GPU through nvidia-smi." >&2
    exit 2
fi

QE_BIN="${QE_BIN:-pw.x}"
if ! command -v "$QE_BIN" >/dev/null 2>&1; then
    echo "Refusing to run: Quantum ESPRESSO executable not found: $QE_BIN" >&2
    exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Refusing to run: Python executable not found: $PYTHON_BIN" >&2
    exit 2
fi
if ! "$PYTHON_BIN" "$ROOT_DIR/scripts/check_pseudopotentials.py"; then
    echo "Refusing to run: the required carbon pseudopotential is unavailable." >&2
    exit 2
fi

if [[ "${QE_GPU_CONFIRMED:-0}" != "1" ]]; then
    echo "Refusing to run: this script cannot prove that $QE_BIN is CUDA-enabled." >&2
    echo "After manually verifying the QE build and a monitored GPU benchmark, set QE_GPU_CONFIRMED=1." >&2
    exit 2
fi

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
if [[ "$CUDA_VISIBLE_DEVICES" == *,* ]]; then
    echo "Refusing to run: configure exactly one CUDA device, not '$CUDA_VISIBLE_DEVICES'." >&2
    exit 2
fi
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

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

input_outdir="$(sed -nE "s/^[[:space:]]*outdir[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/p" "$INPUT_PATH" | head -n 1)"
if [[ -z "$input_outdir" ]]; then
    echo "Refusing to run: no quoted outdir was found in $INPUT_PATH" >&2
    exit 2
fi
if [[ "$input_outdir" = /* ]]; then
    mkdir -p "$input_outdir"
else
    mkdir -p "$ROOT_DIR/${input_outdir#./}"
fi
mkdir -p "$(dirname "$OUTPUT_PATH")"
cd "$ROOT_DIR"
echo "Starting single-process/single-GPU QE relaxation."
echo "QE_BIN=$QE_BIN CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES OMP_NUM_THREADS=$OMP_NUM_THREADS"
"$QE_BIN" -in "$INPUT_PATH" >"$OUTPUT_PATH" 2>&1
echo "QE run complete: $OUTPUT_PATH"
