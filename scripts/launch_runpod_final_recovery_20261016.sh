#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
cd /workspace/GrapheneAlkali-DFT

if pgrep -fa '[p]w.x|[r]un_final_scf_campaign_20261014|[r]un_final_campaign_20261014' >/tmp/final_relaunch_active.txt; then
  printf '%s\n' 'ABORT: a QE or final campaign process is already active'
  cat /tmp/final_relaunch_active.txt
  exit 20
fi

bash -n scripts/run_final_scf_campaign_20261014.sh
python3 -m py_compile scripts/build_final_scf_from_relax.py
scratch='qe_scratch/final_scf/final9_na_c49_20261014'
test -d "${scratch}"
test -z "$(find "${scratch}" -mindepth 1 -print -quit)"

mkdir -p results/cloud/20261014_final_campaign
nohup bash scripts/run_final_campaign_20261014.sh </dev/null \
  >>results/cloud/20261014_final_campaign/recovery_launch_20261016.log 2>&1 &
launcher_pid=$!
printf '%s\n' "${launcher_pid}" \
  >results/cloud/20261014_final_campaign/recovery_launcher_pid.txt
sleep 8
kill -0 "${launcher_pid}"
pgrep -fa '[p]w.x|[r]un_final_scf_campaign_20261014|[r]un_final_campaign_20261014'
grep -n "disk_io[[:space:]]*=[[:space:]]*'nowf'" \
  qe_inputs/final_scf/20261014/na_c49_9x9x1.in
tail -n 12 results/cloud/20261014_final_scf/supervisor.log
printf 'RECOVERY_LAUNCH_OK pid=%s\n' "${launcher_pid}"
exit
REMOTE
