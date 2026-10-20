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
chmod +x scripts/run_*20261014.sh scripts/run_runpod_qe_case.sh \
  scripts/run_adsorbate_cutoff_validation_20261017.sh \
  scripts/watch_and_stop_adsorbate_cutoff_20261017.sh
scripts/run_final_campaign_20261014.sh
final_exit=$?
printf '[%s] prior final campaign exit=%s\n' \
  "$(date --iso-8601=seconds)" "${final_exit}"

# The adsorbate-specific 70/560 Ry cutoff campaign is restart-safe on the
# persistent network volume.  Its independent watcher stops the Pod after a
# strictly validated result, a terminal failure, or the 12-hour cost guard.
mkdir -p results/cloud/20261017_adsorbate_cutoff_70_560
nohup scripts/watch_and_stop_adsorbate_cutoff_20261017.sh \
  >>results/cloud/20261017_adsorbate_cutoff_70_560/watcher_launcher.log 2>&1 &
watcher_pid=$!
printf '[%s] cutoff watcher pid=%s\n' \
  "$(date --iso-8601=seconds)" "${watcher_pid}"
scripts/run_adsorbate_cutoff_validation_20261017.sh
cutoff_exit=$?
printf '[%s] cutoff campaign exit=%s; entering idle hold for inspection\n' \
  "$(date --iso-8601=seconds)" "${cutoff_exit}"

# Keep the container stable after either completion or a gated failure.  The
# persistent READY/state files tell the user/Codex when to stop the Pod.
exec sleep infinity
