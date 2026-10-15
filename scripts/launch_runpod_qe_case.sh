#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'Usage: %s INPUT OUTPUT DIAGNOSTICS_DIR\n' "$0" >&2
  exit 64
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
input=$(realpath -m "$1")
output=$(realpath -m "$2")
diagnostics=$(realpath -m "$3")

mkdir -p "${diagnostics}" "$(dirname "${output}")"
if [[ -s "${output}" ]]; then
  printf 'Refusing to overwrite nonempty output: %s\n' "${output}" >&2
  exit 73
fi

nohup "${repo_root}/scripts/run_runpod_qe_case.sh" \
  "${input}" "${output}" "${diagnostics}" \
  >"${diagnostics}/launcher.log" 2>&1 </dev/null &
worker_pid=$!
printf '%s\n' "${worker_pid}" >"${diagnostics}/worker.pid"
printf 'Launched PID %s\n' "${worker_pid}"
