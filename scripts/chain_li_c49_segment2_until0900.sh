#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

segment1_root="results/cloud/20260930_li_c49_vacancy_segment1"
segment1_complete="${segment1_root}/supervisor_complete.txt"
segment1_qe_exit="${segment1_root}/li_c49_vacancy_20260930a_cloud_segment1_diagnostics/qe_exit_code.txt"
segment1_strict="${segment1_root}/supervisor_exit_code.txt"
segment2_root="results/cloud/20261001_li_c49_vacancy_segment2"
chain_root="results/cloud/20261001_li_c49_vacancy_chain"
scratch="qe_scratch/adsorption/li_c49_vacancy_20260930a_relax"
exit_file="${scratch}/li_c49_vacancy_20260930a_relax.EXIT"
wait_deadline_utc="2026-10-01T10:00:00Z"
continuation_deadline_utc="2026-10-01T13:40:00Z"

mkdir -p "${chain_root}"
exec > >(tee -a "${chain_root}/chain.log") 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

launch_conditional_next_task() {
  local remaining next_exit
  remaining=$(( $(date -d "${continuation_deadline_utc}" +%s) - $(date +%s) ))
  if (( remaining < 1800 )); then
    stamp "Li/C49 converged, but only ${remaining} seconds remain; not starting Na/C49"
    printf 'li_c49_converged_insufficient_time_for_next_task\n' >"${chain_root}/chain_state.txt"
    return 0
  fi
  if pgrep -x pw.x >/dev/null 2>&1; then
    stamp 'ERROR: a pw.x process remains before the conditional Na/C49 pilot'
    printf 'unexpected_qe_process_before_next_task\n' >"${chain_root}/chain_state.txt"
    return 26
  fi
  stamp "Li/C49 strictly converged; launching the audited Na/C49 pilot with ${remaining} seconds remaining"
  printf '%s\n' "${remaining}" >"${chain_root}/na_c49_pilot_guard_seconds.txt"
  printf 'na_c49_pilot_running\n' >"${chain_root}/chain_state.txt"
  GUARD_SECONDS="${remaining}" scripts/run_na_c49_cloud_pilot_until0900.sh
  next_exit=$?
  printf '%s\n' "${next_exit}" >"${chain_root}/na_c49_pilot_exit_code.txt"
  printf 'na_c49_pilot_finished\n' >"${chain_root}/chain_state.txt"
  stamp "Conditional Na/C49 pilot supervisor exited with code ${next_exit}"
  sync
  return "${next_exit}"
}

printf '%s\n' "${wait_deadline_utc}" >"${chain_root}/segment1_wait_deadline_utc.txt"
printf '%s\n' "${continuation_deadline_utc}" >"${chain_root}/continuation_deadline_utc.txt"
stamp 'Waiting for segment 1 completion marker'

while [[ ! -s "${segment1_complete}" ]]; do
  if (( $(date +%s) >= $(date -d "${wait_deadline_utc}" +%s) )); then
    stamp 'ERROR: segment 1 did not produce a completion marker before the wait deadline'
    printf 'wait_timeout\n' >"${chain_root}/chain_state.txt"
    exit 20
  fi
  sleep 30
done

stamp 'Segment 1 completion marker found'
strict_exit=$(tr -d '[:space:]' <"${segment1_strict}" 2>/dev/null || printf 'missing')
qe_exit=$(tr -d '[:space:]' <"${segment1_qe_exit}" 2>/dev/null || printf 'missing')
printf 'segment1_strict_exit=%s\nsegment1_qe_exit=%s\n' \
  "${strict_exit}" "${qe_exit}" >"${chain_root}/segment1_gate.txt"

if [[ "${strict_exit}" == "0" ]]; then
  stamp 'Segment 1 fully converged; Li/C49 continuation is unnecessary'
  launch_conditional_next_task
  exit $?
fi

if [[ "${qe_exit}" != "0" ]]; then
  stamp "ERROR: segment 1 QE exit was ${qe_exit}; refusing automatic restart"
  printf 'segment1_qe_failure_no_continuation\n' >"${chain_root}/chain_state.txt"
  sync
  exit 21
fi

if pgrep -x pw.x >/dev/null 2>&1; then
  stamp 'ERROR: a pw.x process remains after segment 1 completion'
  printf 'unexpected_qe_process_no_continuation\n' >"${chain_root}/chain_state.txt"
  sync
  exit 22
fi

if [[ -e "${segment2_root}" ]]; then
  stamp 'ERROR: segment 2 result directory already exists'
  printf 'stale_segment2_artifacts\n' >"${chain_root}/chain_state.txt"
  sync
  exit 23
fi

if [[ -e "${exit_file}" ]]; then
  mv "${exit_file}" "${segment1_root}/segment1_exit_request.txt"
fi

for checkpoint in \
  "${scratch}/li_c49_vacancy_20260930a_relax.wfc1" \
  "${scratch}/li_c49_vacancy_20260930a_relax.save/charge-density.dat" \
  "${scratch}/li_c49_vacancy_20260930a_relax.bfgs"
do
  if [[ ! -s "${checkpoint}" ]]; then
    stamp "ERROR: required restart checkpoint is missing: ${checkpoint}"
    printf 'missing_restart_checkpoint\n' >"${chain_root}/chain_state.txt"
    sync
    exit 24
  fi
done

remaining=$(( $(date -d "${continuation_deadline_utc}" +%s) - $(date +%s) ))
if (( remaining < 600 )); then
  stamp "ERROR: only ${remaining} seconds remain before the continuation deadline"
  printf 'insufficient_time_for_continuation\n' >"${chain_root}/chain_state.txt"
  sync
  exit 25
fi

printf '%s\n' "${remaining}" >"${chain_root}/segment2_guard_seconds.txt"
printf 'segment2_running\n' >"${chain_root}/chain_state.txt"
stamp "Launching segment 2 with ${remaining} seconds to the absolute safety deadline"
GUARD_SECONDS="${remaining}" scripts/run_li_c49_cloud_segment2_until0900.sh
segment2_exit=$?
printf '%s\n' "${segment2_exit}" >"${chain_root}/segment2_exit_code.txt"
printf 'segment2_finished\n' >"${chain_root}/chain_state.txt"
stamp "Segment 2 supervisor exited with code ${segment2_exit}"
sync
if [[ ${segment2_exit} -eq 0 ]]; then
  launch_conditional_next_task
  exit $?
fi
exit "${segment2_exit}"
