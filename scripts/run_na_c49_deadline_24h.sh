#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20261012_na_c49_deadline_24h}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
window_seconds=${WINDOW_SECONDS:-86400}
guard_margin_seconds=${GUARD_MARGIN_SECONDS:-3600}
result_root="results/cloud/${run_tag}"
pilot_input="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261012a_pilot.in"
relax_input="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261012a_relax.in"
manifest="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261012a_manifest.json"
pilot_output="${result_root}/na_c49_vacancy_20261012a_pilot.out"
relax_output="${result_root}/na_c49_vacancy_20261012a_relax.out"
pilot_diag="${result_root}/na_c49_vacancy_20261012a_pilot_diagnostics"
relax_diag="${result_root}/na_c49_vacancy_20261012a_relax_diagnostics"
pilot_scratch="qe_scratch/adsorption/na_c49_vacancy_20261012a_pilot"
relax_scratch="qe_scratch/adsorption/na_c49_vacancy_20261012a_relax"
relax_prefix="na_c49_vacancy_20261012a_relax"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle=${BUNDLE_PATH:-/workspace/${run_tag}_results_bundle.tar.gz}

if [[ -e "${result_root}" ]]; then
  printf 'Refusing existing result root: %s\n' "${result_root}" >&2
  exit 73
fi
mkdir -p "${result_root}"
# Keep the supervisor independent of an SSH/PTY lifetime.  A process-
# substitution through tee can receive SIGPIPE when the controlling session
# disappears, so append directly to the persistent network volume instead.
exec >>"${result_root}/supervisor.log" 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

mount_source=$(findmnt -n -o SOURCE /workspace)
if [[ "${mount_source}" != *"${volume_id}"* ]]; then
  stamp "ERROR: expected volume ${volume_id}; found ${mount_source}"
  exit 2
fi
for required in "${pw}" "${pilot_input}" "${relax_input}" "${manifest}"; do
  [[ -s "${required}" ]] || { stamp "ERROR: missing ${required}"; exit 3; }
done
if pgrep -x pw.x >/dev/null 2>&1; then
  stamp 'ERROR: another pw.x process is active'
  exit 72
fi
for fresh in "${pilot_scratch}" "${relax_scratch}" "${pilot_output}" "${relax_output}" "${pilot_diag}" "${relax_diag}"; do
  [[ ! -e "${fresh}" ]] || { stamp "ERROR: fresh identity already exists: ${fresh}"; exit 73; }
done

deadline_epoch=$(( $(date +%s) + window_seconds ))
guard_epoch=$(( deadline_epoch - guard_margin_seconds ))
guard_delay=$(( guard_epoch - $(date +%s) ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/workflow_deadline.txt"
date -d "@${guard_epoch}" --iso-8601=seconds >"${result_root}/qe_stop_request_time.txt"
{
  date --iso-8601=seconds
  findmnt /workspace
  nvidia-smi
  free -h
  sha256sum "${pilot_input}" "${relax_input}" "${manifest}"
} >"${result_root}/preflight.txt" 2>&1
stamp "START 24-hour Na/C49 workflow; QE stop request $(cat "${result_root}/qe_stop_request_time.txt")"

(
  sleep "${guard_delay}"
  if pgrep -x pw.x >/dev/null 2>&1; then
    for scratch in "${pilot_scratch}" "${relax_scratch}"; do
      if [[ -d "${scratch}" ]]; then
        printf 'Requested by 24-hour workflow guard at %s\n' "$(date --iso-8601=seconds)" \
          >"${scratch}/$(basename "${scratch}").EXIT"
      fi
    done
    sync
  fi
) &
guard_pid=$!

cleanup_guard() {
  kill "${guard_pid}" 2>/dev/null || true
  wait "${guard_pid}" 2>/dev/null || true
}
trap cleanup_guard EXIT INT TERM

overall_exit=1
stamp 'START Na/C49 fixed-geometry pilot'
QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
  "${pilot_input}" "${pilot_output}" "${pilot_diag}"
pilot_exit=$?
printf '%s\n' "${pilot_exit}" >"${result_root}/pilot_runner_exit.txt"
if [[ ${pilot_exit} -ne 0 ]]; then
  stamp "STOP: pilot validation failed with exit ${pilot_exit}"
  printf 'pilot_failed\n' >"${result_root}/state.txt"
else
  stamp 'PASS Na/C49 pilot; starting approved relaxation'
  printf 'pilot_passed_relax_running\n' >"${result_root}/state.txt"
  QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
    "${relax_input}" "${relax_output}" "${relax_diag}"
  relax_exit=$?
  qe_exit=$(tr -d '[:space:]' <"${relax_diag}/qe_exit_code.txt" 2>/dev/null || printf 'missing')
  printf 'runner_exit=%s\nqe_exit=%s\n' "${relax_exit}" "${qe_exit}" \
    >"${result_root}/relax_gate.txt"
  if [[ ${relax_exit} -eq 0 ]]; then
    stamp 'PASS Na/C49 relaxation strictly converged'
    printf 'converged\n' >"${result_root}/state.txt"
    overall_exit=0
  elif [[ "${qe_exit}" == "0" ]]; then
    stamp 'STOP: relaxation ended cleanly but remains incomplete'
    printf 'window_exhausted_restartable\n' >"${result_root}/state.txt"
  else
    stamp "ERROR: relaxation QE exit ${qe_exit}"
    printf 'qe_failure\n' >"${result_root}/state.txt"
  fi
fi

cleanup_guard
trap - EXIT INT TERM

if [[ -d "${relax_scratch}" ]]; then
  find "${relax_scratch}" -maxdepth 2 -type f \
    -printf '%TY-%Tm-%TdT%TH:%TM:%TS %s %p\n' | sort \
    >"${result_root}/checkpoint_inventory.txt"
fi

rm -f "${bundle}"
archive_members=(
  "${result_root}"
  "${pilot_input}"
  "${relax_input}"
  "${manifest}"
  "scripts/run_na_c49_deadline_24h.sh"
  "scripts/run_runpod_qe_case.sh"
  "scripts/parse_qe_output.py"
)
for checkpoint_file in \
  "${relax_scratch}/${relax_prefix}.bfgs" \
  "${relax_scratch}/${relax_prefix}.update" \
  "${relax_scratch}/${relax_prefix}.restart_k" \
  "${relax_scratch}/${relax_prefix}.restart_scf" \
  "${relax_scratch}/${relax_prefix}.save/data-file-schema.xml" \
  "${relax_scratch}/${relax_prefix}.save/charge-density.dat" \
  "${relax_scratch}/${relax_prefix}.save/paw.txt"
do
  [[ -f "${checkpoint_file}" ]] && archive_members+=("${checkpoint_file}")
done
tar -czf "${bundle}" "${archive_members[@]}"
archive_exit=$?
if [[ ${archive_exit} -eq 0 ]]; then
  sha256sum "${bundle}" >"${result_root}/results_bundle.sha256"
  stamp "ARCHIVE $(cat "${result_root}/results_bundle.sha256")"
else
  stamp "ERROR: result archive failed with exit ${archive_exit}"
fi
printf 'overall_exit=%s\narchive_exit=%s\ncompleted=%s\n' \
  "${overall_exit}" "${archive_exit}" "$(date --iso-8601=seconds)" \
  >"${result_root}/supervisor_complete.txt"
printf 'ready_to_stop_pod\n' >"${result_root}/READY_TO_STOP_POD.txt"
sync

if [[ ${archive_exit} -ne 0 ]]; then
  exit "${archive_exit}"
fi
exit "${overall_exit}"
