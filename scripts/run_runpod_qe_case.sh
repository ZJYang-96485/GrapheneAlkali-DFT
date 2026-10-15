#!/usr/bin/env bash
set -u -o pipefail

if [[ $# -ne 3 ]]; then
  printf 'Usage: %s INPUT OUTPUT DIAGNOSTICS_DIR\n' "$0" >&2
  exit 64
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
input=$(realpath -m "$1")
output=$(realpath -m "$2")
diagnostics=$(realpath -m "$3")
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}

if [[ ! -r "${input}" ]]; then
  printf 'Input not readable: %s\n' "${input}" >&2
  exit 66
fi
if [[ ! -x "${pw}" ]]; then
  printf 'pw.x not executable: %s\n' "${pw}" >&2
  exit 69
fi
if [[ -s "${output}" ]]; then
  printf 'Refusing to overwrite nonempty output: %s\n' "${output}" >&2
  exit 73
fi

mkdir -p "$(dirname "${output}")" "${diagnostics}"
cd "${repo_root}"

sha256sum "${input}" "${pw}" >"${diagnostics}/sha256_before.txt"
git -C /workspace/q-e-7.6 rev-parse HEAD >"${diagnostics}/qe_commit.txt"
{
  date --iso-8601=seconds
  uname -a
  free -h
  nvidia-smi
  grep -E '^(CUDA_ARCH|CUDA_RUNTIME|MPIF90|F90|CC)[[:space:]]*=' \
    /workspace/q-e-7.6/make.inc
} >"${diagnostics}/preflight.txt" 2>&1

nvidia-smi \
  --query-gpu=timestamp,name,uuid,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu \
  --format=csv -l 1 >"${diagnostics}/gpu.csv" 2>&1 &
gpu_logger_pid=$!

vmstat 1 >"${diagnostics}/vmstat.txt" 2>&1 &
vmstat_pid=$!

(
  while true; do
    date --iso-8601=seconds
    ps -eo pid,ppid,stat,%cpu,%mem,rss,vsz,etimes,cmd | \
      grep -E '(^[[:space:]]*PID|pw[.]x)'
    sleep 1
  done
) >"${diagnostics}/processes.txt" 2>&1 &
process_logger_pid=$!

cleanup_loggers() {
  kill "${gpu_logger_pid}" "${vmstat_pid}" "${process_logger_pid}" 2>/dev/null || true
  wait "${gpu_logger_pid}" "${vmstat_pid}" "${process_logger_pid}" 2>/dev/null || true
}
trap cleanup_loggers EXIT INT TERM

date --iso-8601=seconds >"${diagnostics}/started.txt"
/usr/bin/time -v -o "${diagnostics}/time.txt" \
  "${pw}" -in "${input}" >"${output}" 2>&1
qe_exit=$?
date --iso-8601=seconds >"${diagnostics}/finished.txt"
printf '%s\n' "${qe_exit}" >"${diagnostics}/qe_exit_code.txt"

cleanup_loggers
trap - EXIT INT TERM
nvidia-smi >"${diagnostics}/gpu_after.txt" 2>&1

python3 scripts/parse_qe_output.py --allow-incomplete "${output}" \
  >"${diagnostics}/parsed.json" 2>"${diagnostics}/parse_error.txt" || true
python3 scripts/parse_qe_output.py "${output}" \
  >"${diagnostics}/strict_result.json" 2>"${diagnostics}/strict_error.txt"
strict_exit=$?

if [[ ${qe_exit} -ne 0 || ${strict_exit} -ne 0 ]]; then
  printf 'QE exit=%s; strict validation exit=%s\n' "${qe_exit}" "${strict_exit}" >&2
  exit 1
fi

printf 'PASS: %s\n' "${output}"
