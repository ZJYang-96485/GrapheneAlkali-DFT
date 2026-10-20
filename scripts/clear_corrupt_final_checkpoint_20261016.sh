#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
cd /workspace/GrapheneAlkali-DFT
if pgrep -fa '[p]w.x|[r]un_final_scf_campaign_20261014|[r]un_final_campaign_20261014' >/tmp/final_clear_active.txt; then
  printf '%s\n' 'ABORT: final campaign is active'
  cat /tmp/final_clear_active.txt
  exit 20
fi

target='qe_scratch/final_scf/final9_na_c49_20261014'
resolved=$(realpath "${target}")
expected='/workspace/GrapheneAlkali-DFT/qe_scratch/final_scf/final9_na_c49_20261014'
[[ "${resolved}" == "${expected}" ]]
test -s results/cloud/20261014_final_scf/na_c49/na_c49_9x9x1_attempt02.out
test -s results/cloud/20261014_final_scf/na_c49/na_c49_9x9x1_attempt03.out

inventory=$(find "${target}" -mindepth 1 -type f -printf '%s %y %p\n' 2>/dev/null || true)
find "${target}" -mindepth 1 -delete
sync
test -d "${target}"
test -z "$(find "${target}" -mindepth 1 -print -quit)"
{
  printf 'cleared_utc=%s\n' "$(date --iso-8601=seconds)"
  printf 'reason=attempt03_read_past_end_wfcup39\n'
  printf '%s\n' "${inventory}"
} >results/cloud/20261014_final_scf/na_c49/corrupt_checkpoint_cleanup_inventory.txt
printf '%s\n' 'CORRUPT_CHECKPOINT_CLEARED'
du -sh qe_scratch results/cloud/20261014_final_scf
exit
REMOTE
