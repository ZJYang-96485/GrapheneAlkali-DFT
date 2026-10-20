#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
cd /workspace/GrapheneAlkali-DFT
bash -n scripts/watch_and_stop_runpod_final_20261016.sh
command -v runpodctl >/dev/null
test -n "${RUNPOD_API_KEY:-}"
test "${RUNPOD_POD_ID:-}" = '7qnzdeswypoz58'
if ! pgrep -fa '[w]atch_and_stop_runpod_final_20261016' >/dev/null; then
  nohup bash scripts/watch_and_stop_runpod_final_20261016.sh </dev/null >/dev/null 2>&1 &
  printf '%s\n' "$!" >results/cloud/20261014_final_scf/automatic_stop_pid.txt
fi
sleep 3
pgrep -fa '[w]atch_and_stop_runpod_final_20261016'
cat results/cloud/20261014_final_scf/automatic_stop_state.txt
tail -n 8 results/cloud/20261014_final_scf/automatic_stop.log
exit
REMOTE
