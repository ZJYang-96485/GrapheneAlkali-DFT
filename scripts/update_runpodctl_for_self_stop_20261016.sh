#!/usr/bin/env bash
set -euo pipefail

proxy="7qnzdeswypoz58-644122fa@ssh.runpod.io"
key="${HOME}/.ssh/runpod_qe_ed25519"

ssh -tt -i "${key}" -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${proxy}" <<'REMOTE'
set -euo pipefail
test -n "${RUNPOD_API_KEY:-}"
test -n "${RUNPOD_POD_ID:-}"
runpodctl update
runpodctl version
runpodctl pod stop --help | head -n 40
runpodctl pod get "${RUNPOD_POD_ID}"
exit
REMOTE
