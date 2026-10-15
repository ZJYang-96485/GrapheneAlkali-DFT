#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20260929_blackwell48}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
stop_utc=${STOP_UTC:-2026-09-30T03:30:00Z}
result_root="results/cloud/${run_tag}"
status_log="${result_root}/orchestrator.log"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}

mkdir -p "${result_root}"
exec > >(tee -a "${status_log}") 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

mount_source=$(findmnt -n -o SOURCE /workspace)
if [[ "${mount_source}" != *"${volume_id}"* ]]; then
  stamp "ERROR: /workspace is not mounted from expected volume ${volume_id}: ${mount_source}"
  exit 2
fi
test -x "${pw}"
stamp "Persistent volume verified: ${mount_source}"
stamp "QE binary: ${pw}"

guard_pid=''
cleanup_guard() {
  if [[ -n "${guard_pid}" ]]; then
    kill "${guard_pid}" 2>/dev/null || true
    wait "${guard_pid}" 2>/dev/null || true
  fi
}
trap cleanup_guard EXIT INT TERM

relax_exit_file="qe_scratch/adsorption/na_c50_hollow_20260924a_relax/na_c50_hollow_20260924a_relax.EXIT"
(
  stop_epoch=$(date -d "${stop_utc}" +%s)
  now_epoch=$(date +%s)
  wait_seconds=$((stop_epoch - now_epoch))
  if ((wait_seconds > 0)); then
    sleep "${wait_seconds}"
  fi
  mkdir -p "$(dirname "${relax_exit_file}")"
  printf 'Requested by 12-hour RunPod safety guard at %s\n' "$(date --iso-8601=seconds)" >"${relax_exit_file}"
  sync
) &
guard_pid=$!
stamp "Safety guard PID ${guard_pid}; QE .EXIT deadline ${stop_utc}"

run_case() {
  local label=$1
  local input=$2
  local output=$3
  local diagnostics=$4
  if [[ -e "${output}" || -e "${diagnostics}" ]]; then
    stamp "ERROR: refusing to reuse existing artifacts for ${label}"
    return 73
  fi
  stamp "START ${label}"
  scripts/run_runpod_qe_case.sh "${input}" "${output}" "${diagnostics}"
  sync
  stamp "PASS ${label}"
}

mkdir -p qe_scratch/convergence/pristine/cutoff/ecutwfc_40_ecutrho_320
run_case \
  smoke_40_320 \
  qe_inputs/convergence/pristine/cutoff/ecutwfc_40_ecutrho_320.in \
  "${result_root}/smoke_40_320.out" \
  "${result_root}/smoke_40_320_diagnostics"

mkdir -p qe_scratch/adsorption/na_c50_hollow_20260924a_pilot
run_case \
  na_c50_pilot \
  qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_pilot.in \
  "${result_root}/na_c50_hollow_20260924a_pilot.out" \
  "${result_root}/na_c50_hollow_20260924a_pilot_diagnostics"

mkdir -p qe_scratch/adsorption/na_c50_hollow_20260924a_relax
run_case \
  na_c50_relax \
  qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax.in \
  "${result_root}/na_c50_hollow_20260924a_relax.out" \
  "${result_root}/na_c50_hollow_20260924a_relax_diagnostics"

stamp 'ALL STAGES PASSED'
