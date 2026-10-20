#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

campaign_root="results/cloud/20261014_final_scf"
final_root="results/final_project/20261015_final_scf"
state_file="${campaign_root}/postprocess_state.txt"
log="${campaign_root}/postprocess.log"

exec 9>"${campaign_root}/postprocess.lock"
flock -n 9 || exit 75
exec >>"${log}" 2>&1
printf 'waiting\n' >"${state_file}"
printf '[%s] waiting for six-case final-SCF gate\n' "$(date --iso-8601=seconds)"

while [[ ! -s "${campaign_root}/READY_TO_STOP_POD.txt" ]]; do
  if [[ -s "${campaign_root}/state.txt" ]] && \
     [[ "$(tr -d '[:space:]' <"${campaign_root}/state.txt")" != "complete" ]]; then
    printf '[%s] ERROR: final-SCF campaign reached a non-complete terminal state\n' \
      "$(date --iso-8601=seconds)"
    printf 'failed\n' >"${state_file}"
    exit 1
  fi
  sleep 60
done

printf 'running\n' >"${state_file}"
python3 scripts/summarize_final_scf_campaign.py

bundle="results/cloud/20261014_final_campaign/final_scf_report_bundle_20261015.tar.gz"
manifest="results/cloud/20261014_final_campaign/final_scf_report_bundle_20261015.sha256"
tar -czf "${bundle}" \
  "${campaign_root}" \
  "${final_root}" \
  qe_inputs/final_scf/20261014 \
  scripts/build_final_scf_from_relax.py \
  scripts/run_final_scf_campaign_20261014.sh \
  scripts/summarize_final_scf_campaign.py
sha256sum "${bundle}" >"${manifest}"

printf 'complete\n' >"${state_file}"
printf '[%s] PASS: summary, OVITO structures, and report bundle complete\n' \
  "$(date --iso-8601=seconds)"
sync
