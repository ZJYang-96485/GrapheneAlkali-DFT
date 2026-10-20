#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"
root='results/cloud/20261014_final_scf'
campaign='results/cloud/20261014_final_campaign'
final_root='results/final_project/20261015_final_scf'
log="${root}/automatic_stop.log"
state_file="${root}/automatic_stop_state.txt"
pod_id=${RUNPOD_POD_ID:-}

mkdir -p "${root}" "${campaign}"
exec 9>"${root}/automatic_stop.lock"
flock -n 9 || exit 75
exec >>"${log}" 2>&1
stamp() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }

[[ -n "${pod_id}" && -n "${RUNPOD_API_KEY:-}" ]] || {
  stamp 'ERROR: RunPod pod-scoped credentials are unavailable'
  printf 'credential_failure\n' >"${state_file}"
  exit 2
}
command -v runpodctl >/dev/null || {
  stamp 'ERROR: runpodctl is unavailable'
  printf 'cli_failure\n' >"${state_file}"
  exit 2
}
if ! runpodctl version 2>&1 | grep -Eq 'runpodctl (2\.|3\.)'; then
  stamp 'updating transient runpodctl for authenticated self-stop support'
  runpodctl update || {
    stamp 'ERROR: runpodctl update failed'
    printf 'cli_failure\n' >"${state_file}"
    exit 2
  }
fi

strict_gate() {
  python3 - <<'PY'
import json
import re
from pathlib import Path

root = Path("results/cloud/20261014_final_scf")
cases = ("na_c49", "c49", "li_c49", "c50", "li_c50", "na_c50")
for case in cases:
    case_root = root / case
    if (case_root / "state.txt").read_text().strip() != "accepted":
        raise SystemExit(1)
    output = Path((case_root / "accepted_output.txt").read_text().strip())
    match = re.search(r"_(attempt\d\d)\.out$", output.name)
    if not match:
        raise SystemExit(1)
    result_path = case_root / f"{match.group(1)}_diagnostics" / "strict_result.json"
    result = json.loads(result_path.read_text())
    required = (
        result.get("job_completed") is True,
        result.get("gpu_acceleration_active") is True,
        result.get("all_electronic_cycles_converged") is True,
        result.get("final_total_energy_ry") is not None,
    )
    if not all(required):
        raise SystemExit(1)

summary = json.loads(
    Path("results/final_project/20261015_final_scf/final_scf_summary.json").read_text()
)
if len(summary.get("scf_results", [])) != 6:
    raise SystemExit(1)
if len(summary.get("adsorption_results", [])) != 4:
    raise SystemExit(1)
for result in summary["scf_results"]:
    if not (
        result.get("job_completed") is True
        and result.get("gpu_acceleration_active") is True
        and result.get("all_electronic_cycles_converged") is True
    ):
        raise SystemExit(1)
PY
}

request_stop() {
  reason=$1
  stamp "STOP GATE: ${reason}"
  runpodctl pod get "${pod_id}" >"${root}/pod_before_automatic_stop.json" || {
    stamp 'ERROR: pre-stop pod read failed; refusing unverified stop request'
    printf 'pre_stop_read_failure\n' >"${state_file}"
    return 1
  }
  printf '%s\n' "${reason}" >"${root}/automatic_stop_reason.txt"
  printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/automatic_stop_requested_utc.txt"
  printf 'stop_requested\n' >"${state_file}"
  sync
  runpodctl pod stop "${pod_id}" >"${root}/automatic_stop_response.json" 2>&1
}

printf 'monitoring\n' >"${state_file}"
monitor_started_epoch=$(date +%s)
stamp "monitoring pod ${pod_id} for strict completion or terminal failure"

while true; do
  root_state=$([[ -f "${root}/state.txt" ]] && tr -d '[:space:]' <"${root}/state.txt" || true)
  post_state=$([[ -f "${root}/postprocess_state.txt" ]] && tr -d '[:space:]' <"${root}/postprocess_state.txt" || true)
  campaign_state=$([[ -f "${campaign}/state.txt" ]] && tr -d '[:space:]' <"${campaign}/state.txt" || true)
  campaign_state_mtime=$(stat -c '%Y' "${campaign}/state.txt" 2>/dev/null || printf '0')
  post_state_mtime=$(stat -c '%Y' "${root}/postprocess_state.txt" 2>/dev/null || printf '0')

  if [[ "${root_state}" == 'complete' && "${post_state}" == 'complete' && \
        "${campaign_state}" == 'complete' && \
        -s "${root}/READY_TO_STOP_POD.txt" && \
        -s "${campaign}/READY_TO_STOP_POD.txt" && \
        -s "${campaign}/final_scf_report_bundle_20261015.tar.gz" && \
        -s "${campaign}/final_scf_report_bundle_20261015.sha256" ]]; then
    if ! pgrep -x pw.x >/dev/null 2>&1 && \
       sha256sum -c "${campaign}/final_scf_report_bundle_20261015.sha256" && \
       tar -tzf "${campaign}/final_scf_report_bundle_20261015.tar.gz" >/dev/null && \
       strict_gate; then
      printf 'validated_complete\n' >"${state_file}"
      sync
      request_stop 'validated_complete'
      exit $?
    fi
    stamp 'WARNING: completion markers exist but the strict stop gate did not pass'
  fi

  if [[ "${campaign_state}" == 'final_scf_incomplete_or_failed' || \
        "${post_state}" == 'failed' ]]; then
    if [[ "${campaign_state_mtime}" -ge "${monitor_started_epoch}" || \
          "${post_state_mtime}" -ge "${monitor_started_epoch}" ]] && \
       ! pgrep -x pw.x >/dev/null 2>&1; then
      printf 'validated_terminal_failure\n' >"${state_file}"
      sync
      request_stop 'validated_terminal_failure'
      exit $?
    fi
  fi
  sleep 60
done
