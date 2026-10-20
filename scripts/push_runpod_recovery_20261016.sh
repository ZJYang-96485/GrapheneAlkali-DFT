#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

files=(
  scripts/run_final_campaign_20261014.sh
)

for relative in "${files[@]}"; do
  local_file="${repo_root}/${relative}"
  payload=$(base64 -w 0 "${local_file}")
  local_sha=$(sha256sum "${local_file}" | awk '{print $1}')
  remote="/workspace/GrapheneAlkali-DFT/${relative}"
  remote_tmp="${remote}.upload-20261016"
  uploaded=0
  for attempt in 1 2 3 4 5; do
    if ssh -tt -i "${key}" -o BatchMode=yes \
      -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<REMOTE
set -e
printf '%s' '${payload}' | base64 -d > '${remote_tmp}'
chmod --reference='${remote}' '${remote_tmp}' 2>/dev/null || chmod 755 '${remote_tmp}'
mv -f '${remote_tmp}' '${remote}'
test "\$(sha256sum '${remote}' | awk '{print \$1}')" = '${local_sha}'
printf 'SYNCED %s %s\n' '${local_sha}' '${relative}'
exit
REMOTE
    then
      uploaded=1
      break
    fi
    sleep 5
  done
  [[ ${uploaded} -eq 1 ]] || { printf 'Upload failed: %s\n' "${relative}" >&2; exit 1; }
done
