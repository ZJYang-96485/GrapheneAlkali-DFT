#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"
root="results/cloud/20261014_final_campaign"
mkdir -p "${root}"
exec 7>"${root}/campaign.lock"
flock -n 7 || exit 75
exec >>"${root}/campaign.log" 2>&1
printf 'running\n' >"${root}/state.txt"
printf '[%s] campaign invocation start\n' "$(date --iso-8601=seconds)"

if ! pgrep -fa '[p]ostprocess_final_scf_campaign_20261015' >/dev/null; then
  nohup bash scripts/postprocess_final_scf_campaign_20261015.sh </dev/null \
    >/dev/null 2>&1 &
  printf '%s\n' "$!" >"${root}/postprocess_watcher_pid.txt"
fi

if pgrep -x pw.x >/dev/null 2>&1; then
  printf '[%s] ERROR: unexpected pw.x before campaign start\n' "$(date --iso-8601=seconds)"
  exit 72
fi

scripts/run_na_c49_resilient_20261014.sh
na_exit=$?
if [[ ${na_exit} -ne 0 ]]; then
  printf '[%s] STOP: Na/C49 stage exit %s\n' "$(date --iso-8601=seconds)" "${na_exit}"
  printf 'na_c49_incomplete_or_failed\n' >"${root}/state.txt"
  exit "${na_exit}"
fi

scripts/run_final_scf_campaign_20261014.sh
scf_exit=$?
if [[ ${scf_exit} -ne 0 ]]; then
  printf '[%s] STOP: final-SCF stage exit %s\n' "$(date --iso-8601=seconds)" "${scf_exit}"
  printf 'final_scf_incomplete_or_failed\n' >"${root}/state.txt"
  exit "${scf_exit}"
fi

printf 'complete\n' >"${root}/state.txt"
printf 'ready_to_stop_pod\n' >"${root}/READY_TO_STOP_POD.txt"
printf '[%s] campaign complete; pod can be stopped\n' "$(date --iso-8601=seconds)"
sync
