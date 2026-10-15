#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20260930_blackwell48_restart1}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
guard_seconds=${GUARD_SECONDS:-42300}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax_restart1.in"
output="${result_root}/na_c50_hollow_20260924a_relax_restart1.out"
diagnostics="${result_root}/na_c50_hollow_20260924a_relax_restart1_diagnostics"
scratch="qe_scratch/adsorption/na_c50_hollow_20260924a_relax"
exit_file="${scratch}/na_c50_hollow_20260924a_relax.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}

mkdir -p "${result_root}"
exec > >(tee -a "${result_root}/supervisor.log") 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

mount_source=$(findmnt -n -o SOURCE /workspace)
if [[ "${mount_source}" != *"${volume_id}"* ]]; then
  stamp "ERROR: expected volume ${volume_id}; found ${mount_source}"
  exit 2
fi

test -x "${pw}" || exit 3
test -s "${scratch}/na_c50_hollow_20260924a_relax.wfc1" || exit 4
test -s "${scratch}/na_c50_hollow_20260924a_relax.save/charge-density.dat" || exit 5
test -s "${scratch}/na_c50_hollow_20260924a_relax.bfgs" || exit 6
if [[ -e "${exit_file}" || -e "${output}" || -e "${diagnostics}" ]]; then
  stamp 'ERROR: stale EXIT file or existing continuation artifacts detected'
  exit 73
fi

deadline_epoch=$(( $(date +%s) + guard_seconds ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/safety_deadline.txt"
stamp "Persistent restart checkpoint verified on ${mount_source}"
stamp "Safety deadline: $(cat "${result_root}/safety_deadline.txt")"

(
  sleep "${guard_seconds}"
  printf 'Requested by 12-hour continuation safety guard at %s\n' \
    "$(date --iso-8601=seconds)" >"${exit_file}"
  sync
) &
guard_pid=$!

cleanup_guard() {
  kill "${guard_pid}" 2>/dev/null || true
  wait "${guard_pid}" 2>/dev/null || true
}
trap cleanup_guard EXIT INT TERM

stamp 'START restart continuation 1'
QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
  "${input}" "${output}" "${diagnostics}"
runner_exit=$?
printf '%s\n' "${runner_exit}" >"${result_root}/supervisor_exit_code.txt"
sync

if [[ ${runner_exit} -eq 0 ]]; then
  stamp 'PASS restart continuation 1'
else
  stamp "STOP restart continuation 1; validation exit ${runner_exit}"
fi
exit "${runner_exit}"
