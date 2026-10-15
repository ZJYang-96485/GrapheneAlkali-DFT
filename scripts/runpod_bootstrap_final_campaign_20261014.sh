#!/usr/bin/env bash
set -u -o pipefail

repo=/workspace/GrapheneAlkali-DFT
log="${repo}/results/cloud/20261014_final_campaign/bootstrap.log"
mkdir -p "$(dirname "${log}")"
exec >>"${log}" 2>&1
printf '[%s] container bootstrap pid=%s\n' "$(date --iso-8601=seconds)" "$$"

cd "${repo}"
if ! command -v python3 >/dev/null 2>&1 || \
   ! command -v vmstat >/dev/null 2>&1 || \
   [[ ! -x /usr/bin/time ]] || \
   ldd /workspace/q-e-7.6/bin/pw.x 2>/dev/null | grep -q 'not found'; then
  printf '[%s] installing transient container dependencies\n' "$(date --iso-8601=seconds)"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 git procps time util-linux ca-certificates rsync \
    libfftw3-dev libopenblas-dev
fi
chmod +x scripts/run_*20261014.sh scripts/run_runpod_qe_case.sh
scripts/run_final_campaign_20261014.sh
exit_code=$?
printf '[%s] campaign exit=%s; entering idle hold for inspection\n' \
  "$(date --iso-8601=seconds)" "${exit_code}"

# Keep the container stable after either completion or a gated failure.  The
# persistent READY/state files tell the user/Codex when to stop the Pod.
exec sleep infinity
