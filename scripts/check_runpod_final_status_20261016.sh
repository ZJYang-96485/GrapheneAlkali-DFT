#!/usr/bin/env bash
set -u -o pipefail

pod_proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

for attempt in 1 2 3 4 5; do
  if ssh -tt -i "${key}" \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=20 \
    "${pod_proxy}" <<'REMOTE'
cd /workspace/GrapheneAlkali-DFT
printf '%s\n' '=== TIME/PROCESSES ==='
date -Is
ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd | grep -E '[p]w.x|[r]un_final|[p]ostprocess_final|[r]un_runpod_qe_case' || true
printf '%s\n' '=== CASE STATES ==='
for c in na_c49 c49 li_c49 c50 li_c50 na_c50; do
  printf '%-8s ' "${c}"
  cat "results/cloud/20261014_final_scf/${c}/state.txt" 2>/dev/null || echo not_started
done
printf 'root_state='
cat results/cloud/20261014_final_scf/state.txt 2>/dev/null || echo absent
printf 'ready_marker='
test -s results/cloud/20261014_final_scf/READY_TO_STOP_POD.txt && echo yes || echo no
printf 'postprocess='
cat results/cloud/20261014_final_scf/postprocess_state.txt 2>/dev/null || echo absent
printf '%s\n' '=== SUPERVISOR TAIL ==='
tail -n 35 results/cloud/20261014_final_scf/supervisor.log 2>/dev/null || true
printf '%s\n' '=== POSTPROCESS TAIL ==='
tail -n 30 results/cloud/20261014_final_scf/postprocess.log 2>/dev/null || true
printf '%s\n' '=== CAMPAIGN TAIL ==='
tail -n 30 results/cloud/20261014_final_campaign/campaign.log 2>/dev/null || true
printf '%s\n' '=== OUTPUT INVENTORY ==='
find results/cloud/20261014_final_scf -maxdepth 3 -type f -name '*.out' \
  -printf '%TY-%Tm-%TdT%TH:%TM:%TS %s %p\n' | sort
printf '%s\n' '=== STORAGE ==='
du -sh qe_scratch results/cloud/20261014_final_scf \
  results/final_project/20261015_final_scf 2>/dev/null || true
df -h /workspace
printf '%s\n' '=== NA/C49 ATTEMPT02 TAIL ==='
tail -n 140 results/cloud/20261014_final_scf/na_c49/na_c49_9x9x1_attempt02.out 2>/dev/null || true
printf '%s\n' '=== NA/C49 DIAGNOSTICS ==='
find results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics \
  -maxdepth 2 -type f -printf '%s %TY-%Tm-%TdT%TH:%TM:%TS %p\n' 2>/dev/null | sort || true
for diagnostic in \
  results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/qe_exit_code.txt \
  results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/strict_validation_exit_code.txt \
  results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/strict_result.json \
  results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/time_verbose.txt; do
  if [[ -f "${diagnostic}" ]]; then
    printf '%s\n' "--- ${diagnostic} ---"
    tail -n 120 "${diagnostic}"
  fi
done
printf '%s\n' '=== NA/C49 STATE/SCRATCH ==='
stat results/cloud/20261014_final_scf/na_c49/state.txt 2>/dev/null || true
od -An -tx1 -c results/cloud/20261014_final_scf/na_c49/state.txt 2>/dev/null || true
find qe_scratch/final_scf/final9_na_c49_20261014 -maxdepth 2 -type f \
  -printf '%s %TY-%Tm-%TdT%TH:%TM:%TS %p\n' 2>/dev/null | sort | tail -n 30 || true
printf '%s\n' '=== SCRATCH SIZE BREAKDOWN ==='
du -h --max-depth=2 qe_scratch 2>/dev/null | sort -h | tail -n 40 || true
printf '%s\n' '=== LARGE SCRATCH FILES ==='
find qe_scratch -type f -size +100M -printf '%s %TY-%Tm-%TdT%TH:%TM:%TS %p\n' \
  2>/dev/null | sort -n | tail -n 80 || true
printf '%s\n' '=== RESOURCE LOG TAILS ==='
tail -n 8 results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/gpu.csv 2>/dev/null || true
tail -n 8 results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/vmstat.txt 2>/dev/null || true
tail -n 15 results/cloud/20261014_final_scf/na_c49/attempt02_diagnostics/processes.txt 2>/dev/null || true
exit
REMOTE
  then
    exit 0
  fi
  printf 'SSH attempt %s failed; retrying.\n' "${attempt}" >&2
  sleep 5
done

exit 1
