#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 INPUT.in [OUTPUT.out]" >&2
    echo "Environment: QE_BIN=pw.x PYTHON_BIN=python3 CUDA_VISIBLE_DEVICES=0 QE_GPU_CONFIRMED=1" >&2
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

calculation="$(sed -nE "s/^[[:space:]]*calculation[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/p" "$INPUT_PATH" | head -n 1)"
case "$calculation" in
    scf|relax) ;;
    *)
        echo "Refusing to run: supported calculations are scf and fixed-cell relax, found '$calculation'." >&2
        exit 2
        ;;
esac
if [[ -n "${QE_REQUIRE_CALCULATION:-}" && "$calculation" != "$QE_REQUIRE_CALCULATION" ]]; then
    echo "Refusing to run: expected calculation='$QE_REQUIRE_CALCULATION', found '$calculation'." >&2
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
    echo "Refusing to run: the required carbon pseudopotential failed its audit." >&2
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
if [[ -e "$OUTPUT_PATH" && "${QE_OVERWRITE_OUTPUT:-0}" != "1" ]]; then
    echo "Refusing to overwrite existing raw output: $OUTPUT_PATH" >&2
    exit 2
fi

input_outdir="$(sed -nE "s/^[[:space:]]*outdir[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/p" "$INPUT_PATH" | head -n 1)"
if [[ -z "$input_outdir" ]]; then
    echo "Refusing to run: no quoted outdir was found in $INPUT_PATH" >&2
    exit 2
fi
if [[ "$input_outdir" = /* ]]; then
    SCRATCH_PATH="$input_outdir"
else
    SCRATCH_PATH="$ROOT_DIR/${input_outdir#./}"
fi
if [[ -d "$SCRATCH_PATH" ]] && find "$SCRATCH_PATH" -mindepth 1 -print -quit | grep -q .; then
    if [[ "${QE_ALLOW_REUSE_SCRATCH:-0}" != "1" ]]; then
        echo "Refusing to reuse nonempty scratch: $SCRATCH_PATH" >&2
        exit 2
    fi
fi
mkdir -p "$SCRATCH_PATH"
mkdir -p "$(dirname "$OUTPUT_PATH")"

cd "$ROOT_DIR"
echo "Starting single-process/single-GPU QE $calculation calculation."
echo "QE_BIN=$QE_BIN CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES OMP_NUM_THREADS=$OMP_NUM_THREADS"
set +e
"$QE_BIN" -in "$INPUT_PATH" >"$OUTPUT_PATH" 2>&1 &
qe_pid=$!
while kill -0 "$qe_pid" 2>/dev/null; do
    sleep 20
    if kill -0 "$qe_pid" 2>/dev/null; then
        latest_iteration="$(grep -E '^[[:space:]]*iteration[[:space:]]+#' "$OUTPUT_PATH" | tail -n 1 | sed -E 's/^[[:space:]]+//' || true)"
        echo "QE heartbeat: ${latest_iteration:-initializing}"
    fi
done
wait "$qe_pid"
status=$?
set -e
if (( status != 0 )); then
    echo "QE exited unsuccessfully with status $status; inspect $OUTPUT_PATH" >&2
    exit "$status"
fi
if ! grep -Eqi 'GPU acceleration is[[:space:]]+ACTIVE' "$OUTPUT_PATH"; then
    echo "QE output does not confirm active GPU acceleration: $OUTPUT_PATH" >&2
    exit 3
fi
if ! grep -Eq 'convergence has been achieved|End of self-consistent calculation' "$OUTPUT_PATH"; then
    echo "QE output does not confirm electronic convergence: $OUTPUT_PATH" >&2
    exit 3
fi
if ! grep -Eq 'JOB DONE\.' "$OUTPUT_PATH"; then
    echo "QE output is missing JOB DONE: $OUTPUT_PATH" >&2
    exit 3
fi
echo "QE run complete and basic output gates passed: $OUTPUT_PATH"
