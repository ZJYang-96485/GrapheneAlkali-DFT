#!/usr/bin/env bash
set -u -o pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
cd /workspace/GrapheneAlkali-DFT
root='results/cloud/20261014_final_scf/na_c49'
printf '%s\n' '=== ATTEMPT03 TAIL ==='
tail -n 120 "${root}/na_c49_9x9x1_attempt03.out" 2>/dev/null || true
printf '%s\n' '=== DIAGNOSTICS ==='
find "${root}/attempt03_diagnostics" -maxdepth 1 -type f \
  -printf '%s %TY-%Tm-%TdT%TH:%TM:%TS %p\n' 2>/dev/null | sort || true
for file in qe_exit_code.txt strict_validation_exit_code.txt strict_result.json time.txt time_verbose.txt; do
  if [[ -f "${root}/attempt03_diagnostics/${file}" ]]; then
    printf '%s\n' "--- ${file} ---"
    tail -n 100 "${root}/attempt03_diagnostics/${file}"
  fi
done
printf '%s\n' '=== CAMPAIGN LOGS ==='
tail -n 25 results/cloud/20261014_final_scf/supervisor.log 2>/dev/null || true
tail -n 25 results/cloud/20261014_final_campaign/campaign.log 2>/dev/null || true
printf 'campaign_state='; cat results/cloud/20261014_final_campaign/state.txt 2>/dev/null || echo absent
printf '%s\n' '=== STOP GUARD ==='
cat results/cloud/20261014_final_scf/automatic_stop_state.txt 2>/dev/null || true
tail -n 30 results/cloud/20261014_final_scf/automatic_stop.log 2>/dev/null || true
cat results/cloud/20261014_final_scf/automatic_stop_reason.txt 2>/dev/null || true
exit
REMOTE
