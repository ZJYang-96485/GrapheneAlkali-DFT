#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 INPUT.in OUTPUT.out DIAGNOSTIC_STEM" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INPUT_PATH="$ROOT_DIR/${1#./}"
OUTPUT_PATH="$ROOT_DIR/${2#./}"
STEM="$3"
DIAG_DIR="$ROOT_DIR/results/phase4/diagnostics"
QE_BIN="${QE_BIN:-$HOME/q-e/bin/pw.x}"

VMSTAT_LOG="$DIAG_DIR/${STEM}_vmstat.log"
GPU_LOG="$DIAG_DIR/${STEM}_gpu.csv"
PROCESS_LOG="$DIAG_DIR/${STEM}_processes.log"
TIME_LOG="$DIAG_DIR/${STEM}_time_v.log"
RUN_LOG="$DIAG_DIR/${STEM}_run_metadata.log"

for path in "$INPUT_PATH" "$QE_BIN"; do
    if [[ ! -f "$path" ]]; then
        echo "Required file not found: $path" >&2
        exit 2
    fi
done
for path in "$OUTPUT_PATH" "$VMSTAT_LOG" "$GPU_LOG" "$PROCESS_LOG" "$TIME_LOG" "$RUN_LOG"; do
    if [[ -e "$path" ]]; then
        echo "Refusing to overwrite diagnostic artifact: $path" >&2
        exit 2
    fi
done

input_outdir="$(sed -nE "s/^[[:space:]]*outdir[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/p" "$INPUT_PATH" | head -n 1)"
if [[ -z "$input_outdir" ]]; then
    echo "Input has no quoted outdir." >&2
    exit 2
fi
if [[ "$input_outdir" = /* ]]; then
    SCRATCH_PATH="$input_outdir"
else
    SCRATCH_PATH="$ROOT_DIR/${input_outdir#./}"
fi
if [[ -e "$SCRATCH_PATH" ]]; then
    echo "Fresh scratch path already exists: $SCRATCH_PATH" >&2
    exit 2
fi

mkdir -p "$DIAG_DIR" "$SCRATCH_PATH" "$(dirname "$OUTPUT_PATH")"

monitor_pids=()
cleanup() {
    local pid
    for pid in "${monitor_pids[@]:-}"; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in "${monitor_pids[@]:-}"; do
        wait "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT INT TERM

{
    echo "start_time=$(date -Ins)"
    echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
    echo "kernel=$(uname -a)"
    echo "qe_bin=$QE_BIN"
    echo "input=$INPUT_PATH"
    echo "input_sha256=$(sha256sum "$INPUT_PATH" | awk '{print $1}')"
    echo "output=$OUTPUT_PATH"
    echo "scratch=$SCRATCH_PATH"
    echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-0}"
    echo "omp_num_threads=${OMP_NUM_THREADS:-4}"
} >"$RUN_LOG"

stdbuf -oL -eL vmstat -w -t 1 >"$VMSTAT_LOG" 2>&1 &
monitor_pids+=("$!")

stdbuf -oL -eL nvidia-smi \
    --query-gpu=timestamp,name,pstate,temperature.gpu,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,power.draw,power.limit \
    --format=csv -l 1 >"$GPU_LOG" 2>&1 &
monitor_pids+=("$!")

(
    while :; do
        echo "timestamp=$(date -Ins)"
        ps -eo pid,ppid,state,%cpu,%mem,rss,vsz,etimes,comm,args --sort=-rss | sed -n '1,30p'
        echo
        sleep 1
    done
) >"$PROCESS_LOG" 2>&1 &
monitor_pids+=("$!")

(
    while :; do
        sync -d "$VMSTAT_LOG" "$GPU_LOG" "$PROCESS_LOG" "$RUN_LOG" "$OUTPUT_PATH" 2>/dev/null || true
        sleep 1
    done
) &
monitor_pids+=("$!")

sleep 2
sync

cd "$ROOT_DIR"
set +e
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" \
/usr/bin/time -v -o "$TIME_LOG" \
    "$QE_BIN" -in "$INPUT_PATH" >"$OUTPUT_PATH" 2>&1
status=$?
set -e

{
    echo "end_time=$(date -Ins)"
    echo "qe_exit_status=$status"
    echo "end_boot_id=$(cat /proc/sys/kernel/random/boot_id)"
} >>"$RUN_LOG"
sync

if (( status != 0 )); then
    echo "QE exited with status $status." >&2
    exit "$status"
fi
if ! grep -Eqi 'GPU acceleration is[[:space:]]+ACTIVE' "$OUTPUT_PATH"; then
    echo "Missing active-GPU marker." >&2
    exit 3
fi
if ! grep -Eq 'convergence has been achieved|End of self-consistent calculation' "$OUTPUT_PATH"; then
    echo "Missing electronic-convergence marker." >&2
    exit 3
fi
if ! grep -Eq '^![[:space:]]+total energy' "$OUTPUT_PATH"; then
    echo "Missing final total energy." >&2
    exit 3
fi
if ! grep -Eq 'JOB DONE\.' "$OUTPUT_PATH"; then
    echo "Missing JOB DONE." >&2
    exit 3
fi

grep -E 'GPU acceleration is|convergence has been achieved|^![[:space:]]+total energy|JOB DONE\.|PWSCF[[:space:]]+:' "$OUTPUT_PATH"
echo "Monitored QE diagnostic passed all output gates."
