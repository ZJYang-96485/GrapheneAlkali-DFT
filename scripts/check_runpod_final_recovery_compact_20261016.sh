#!/usr/bin/env bash
set -u -o pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

for attempt in 1 2 3 4 5; do
  if ssh -tt -i "${key}" -o BatchMode=yes \
    -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
cd /workspace/GrapheneAlkali-DFT
printf '%s\n' '=== STATUS ==='
date -Is
pgrep -fa '[p]w.x|[r]un_final_scf_campaign_20261014|[r]un_final_campaign_20261014|[p]ostprocess_final_scf_campaign|[w]atch_and_stop_runpod_final_20261016' || true
for c in na_c49 c49 li_c49 c50 li_c50 na_c50; do
  printf '%-8s ' "${c}"
  cat "results/cloud/20261014_final_scf/${c}/state.txt" 2>/dev/null || echo not_started
done
printf 'root='; cat results/cloud/20261014_final_scf/state.txt 2>/dev/null || echo absent
printf 'postprocess='; cat results/cloud/20261014_final_scf/postprocess_state.txt 2>/dev/null || echo absent
printf 'ready='; test -s results/cloud/20261014_final_scf/READY_TO_STOP_POD.txt && echo yes || echo no

active_output=$(find results/cloud/20261014_final_scf -maxdepth 2 -type f -name '*_9x9x1_attempt*.out' \
  -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
if [[ -n "${active_output}" ]]; then
  printf '%s\n' "=== LATEST ${active_output} ==="
  stat -c 'bytes=%s modified=%y' "${active_output}"
  grep -E 'GPU acceleration is ACTIVE|iteration #|estimated scf accuracy|convergence has been achieved|!    total energy|JOB DONE|Error in routine|Maximum CPU time exceeded' \
    "${active_output}" | tail -n 24 || true
fi

printf '%s\n' '=== RESOURCES ==='
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null || true
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader 2>/dev/null || true
du -sh qe_scratch results/cloud/20261014_final_scf 2>/dev/null || true
printf 'runpod_env='; env | cut -d= -f1 | grep '^RUNPOD_' | sort | paste -sd, - || true
printf '%s\n' '=== RUNPOD SELF-STOP CAPABILITY ==='
command -v runpodctl || true
runpodctl version 2>/dev/null || true
runpodctl pod stop --help 2>/dev/null | head -n 25 || true
exit
REMOTE
  then
    exit 0
  fi
  sleep 5
done
exit 1
