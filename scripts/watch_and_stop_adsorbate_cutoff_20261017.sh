#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"
root='results/cloud/20261017_adsorbate_cutoff_70_560'
summary_root='results/final_project/20261017_adsorbate_cutoff_validation'
log="${root}/automatic_stop.log"
watch_state="${root}/automatic_stop_state.txt"
pod_id=${RUNPOD_POD_ID:-}

mkdir -p "${root}"
exec 8>"${root}/automatic_stop.lock"
flock -n 8 || exit 75
exec >>"${log}" 2>&1
stamp() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }

[[ -n "${pod_id}" && -n "${RUNPOD_API_KEY:-}" ]] || {
  stamp 'ERROR: pod-scoped RunPod credentials are unavailable'
  printf 'credential_failure\n' >"${watch_state}"
  exit 2
}
command -v runpodctl >/dev/null 2>&1 || {
  stamp 'ERROR: runpodctl is unavailable'
  printf 'cli_failure\n' >"${watch_state}"
  exit 2
}
if ! runpodctl version 2>&1 | grep -Eq 'runpodctl (2\.|3\.)'; then
  stamp 'updating transient runpodctl for authenticated self-stop support'
  runpodctl update || {
    stamp 'ERROR: runpodctl update failed'
    printf 'cli_failure\n' >"${watch_state}"
    exit 2
  }
fi

request_stop() {
  reason=$1
  stamp "STOP GATE: ${reason}"
  runpodctl pod get "${pod_id}" >"${root}/pod_before_automatic_stop.json" || {
    stamp 'ERROR: pre-stop pod read failed; refusing unverified stop request'
    printf 'pre_stop_read_failure\n' >"${watch_state}"
    return 1
  }
  printf '%s\n' "${reason}" >"${root}/automatic_stop_reason.txt"
  printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/automatic_stop_requested_utc.txt"
  printf 'stop_requested\n' >"${watch_state}"
  sync
  runpodctl pod stop "${pod_id}" >"${root}/automatic_stop_response.json" 2>&1
}

strict_complete_gate() {
  [[ -s "${root}/READY_TO_STOP_POD.txt" ]] || return 1
  [[ -s "${root}/adsorbate_cutoff_validation_20261017.tar.gz" ]] || return 1
  [[ -s "${root}/adsorbate_cutoff_validation_20261017.sha256" ]] || return 1
  [[ -s "${summary_root}/cutoff_validation_summary.json" ]] || return 1
  ! pgrep -x pw.x >/dev/null 2>&1 || return 1
  sha256sum -c "${root}/adsorbate_cutoff_validation_20261017.sha256" || return 1
  tar -tzf "${root}/adsorbate_cutoff_validation_20261017.tar.gz" >/dev/null || return 1
  python3 - "${root}" "${summary_root}" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
summary_root = Path(sys.argv[2])
for case in ("c50", "li_atom", "na_atom", "li_c50", "na_c50"):
    case_root = root / case
    if (case_root / "state.txt").read_text().strip() != "accepted":
        raise SystemExit(1)
    accepted = Path((case_root / "accepted_output.txt").read_text().strip())
    match = re.search(r"_attempt(\d\d)\.out$", accepted.name)
    if not match:
        raise SystemExit(1)
    result = json.loads(
        (case_root / f"attempt{match.group(1)}_diagnostics" / "strict_result.json").read_text()
    )
    if not (
        result.get("job_completed") is True
        and result.get("gpu_acceleration_active") is True
        and result.get("all_electronic_cycles_converged") is True
        and result.get("final_total_energy_ry") is not None
    ):
        raise SystemExit(1)
summary = json.loads((summary_root / "cutoff_validation_summary.json").read_text())
if len(summary.get("scf_results", [])) != 5:
    raise SystemExit(1)
if len(summary.get("adsorption_comparison", [])) != 2:
    raise SystemExit(1)
PY
}

printf 'monitoring\n' >"${watch_state}"
stamp "monitoring pod ${pod_id} for completion, terminal failure, or 12-hour guard"

while true; do
  state=$([[ -f "${root}/state.txt" ]] && tr -d '[:space:]' <"${root}/state.txt" || true)
  deadline=$([[ -f "${root}/deadline_epoch.txt" ]] && tr -d '[:space:]' <"${root}/deadline_epoch.txt" || printf '0')
  now=$(date +%s)

  if [[ "${state}" == complete ]] && strict_complete_gate; then
    printf 'validated_complete\n' >"${watch_state}"
    sync
    request_stop validated_complete
    exit $?
  fi

  if [[ "${state}" == terminal_failure ]] && ! pgrep -x pw.x >/dev/null 2>&1; then
    printf 'validated_terminal_failure\n' >"${watch_state}"
    sync
    request_stop validated_terminal_failure
    exit $?
  fi

  if [[ "${deadline}" =~ ^[0-9]+$ ]] && (( deadline > 0 && now >= deadline )); then
    printf 'hard_deadline_reached\n' >"${watch_state}"
    printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/hard_deadline_reached_utc.txt"
    sync
    request_stop hard_12_hour_deadline
    exit $?
  fi
  sleep 60
done
