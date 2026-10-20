#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
cd /workspace/GrapheneAlkali-DFT
bash -n scripts/postprocess_final_scf_campaign_20261015.sh
if ! pgrep -fa '[p]ostprocess_final_scf_campaign_20261015' >/dev/null; then
  nohup bash scripts/postprocess_final_scf_campaign_20261015.sh </dev/null >/dev/null 2>&1 &
  printf '%s\n' "$!" >results/cloud/20261014_final_campaign/postprocess_watcher_pid.txt
fi
sleep 3
pgrep -fa '[p]ostprocess_final_scf_campaign_20261015'
cat results/cloud/20261014_final_scf/postprocess_state.txt
tail -n 6 results/cloud/20261014_final_scf/postprocess.log
exit
REMOTE
