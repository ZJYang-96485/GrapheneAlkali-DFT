#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
cd /workspace/GrapheneAlkali-DFT

if pgrep -fa '[p]w.x|[r]un_final_scf_campaign_20261014' >/tmp/final_recovery_active.txt; then
  printf '%s\n' 'ABORT: a QE or final-SCF campaign process is active'
  cat /tmp/final_recovery_active.txt
  exit 20
fi

scratch='qe_scratch/final_scf/final9_na_c49_20261014'
checkpoint="${scratch}/final9_na_c49_20261014.save"
distributed="${scratch}/final9_na_c49_20261014.wfc1"
test -s "${checkpoint}/data-file-schema.xml"
portable_count=$(find "${checkpoint}" -maxdepth 1 -type f -name 'wfc*.dat' | wc -l)
test "${portable_count}" -gt 0
test -f "${distributed}"

distributed_inventory=$(stat -c '%s %y %n' "${distributed}")
relax_inventory=$(find \
  qe_scratch/adsorption/na_c49_vacancy_20261012a_relax \
  qe_scratch/checkpoint_snapshots/na_c49_step43_20261013 \
  -type f \( -name 'wfc*.dat' -o -name '*.wfc[0-9]*' \) \
  -printf '%s %y %p\n' 2>/dev/null || true)

rm -f -- \
  scripts/run_final_scf_campaign_20261014.sh.upload-20261016 \
  "${distributed}"
find \
  qe_scratch/adsorption/na_c49_vacancy_20261012a_relax \
  qe_scratch/checkpoint_snapshots/na_c49_step43_20261013 \
  -type f \( -name 'wfc*.dat' -o -name '*.wfc[0-9]*' \) -delete 2>/dev/null || true
sync

mkdir -p results/cloud/20261014_final_scf/na_c49
{
  printf 'cleanup_utc=%s\n' "$(date --iso-8601=seconds)"
  printf 'portable_checkpoint_files_preserved=%s\n' "${portable_count}"
  printf '%s\n' "${distributed_inventory}"
  printf '%s\n' "${relax_inventory}"
} >results/cloud/20261014_final_scf/na_c49/recovery_cleanup_inventory.txt
printf '%s\n' "$(date --iso-8601=seconds)" \
  >results/cloud/20261014_final_scf/relax_collected_wfc_cleanup_complete
printf '%s\n' "$(date --iso-8601=seconds)" \
  >results/cloud/20261014_final_scf/na_c49/attempt02_distributed_wfc_cleanup_complete

test -s "${checkpoint}/data-file-schema.xml"
test "$(find "${checkpoint}" -maxdepth 1 -type f -name 'wfc*.dat' | wc -l)" -eq "${portable_count}"
printf 'RECOVERY_CLEANUP_OK portable_checkpoint_files=%s\n' "${portable_count}"
du -sh qe_scratch "${scratch}" results/cloud/20261014_final_scf
exit
REMOTE
