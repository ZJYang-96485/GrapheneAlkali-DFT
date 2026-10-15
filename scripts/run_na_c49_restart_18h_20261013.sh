#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20261013_na_c49_restart_18h}
run_id=${RUN_ID:-20261013a}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
# Seventeen hours of QE time leaves one hour inside the approved 18-hour
# billing ceiling for boot, validation, archiving, and control-plane shutdown.
window_seconds=${WINDOW_SECONDS:-61200}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_relax_restart.in"
manifest="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_restart_manifest.json"
source_root="results/cloud/20261012_na_c49_deadline_24h"
source_output="${source_root}/na_c49_vacancy_20261012a_relax.out"
scratch="qe_scratch/adsorption/na_c49_vacancy_20261012a_relax"
prefix="na_c49_vacancy_20261012a_relax"
exit_file="${scratch}/${prefix}.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle=${BUNDLE_PATH:-/workspace/${run_tag}_results_bundle.tar.gz}

if [[ -e "${result_root}" ]]; then
  printf 'Refusing existing result root: %s\n' "${result_root}" >&2
  exit 73
fi
mkdir -p "${result_root}"
# Append directly to persistent storage so the supervisor cannot receive
# SIGPIPE when the SSH session closes.
exec >>"${result_root}/supervisor.log" 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

mount_source=$(findmnt -n -o SOURCE /workspace)
if [[ "${mount_source}" != *"${volume_id}"* ]]; then
  stamp "ERROR: expected volume ${volume_id}; found ${mount_source}"
  exit 2
fi
for required in "${pw}" "${input}" "${manifest}" "${source_output}"; do
  [[ -s "${required}" ]] || { stamp "ERROR: missing ${required}"; exit 3; }
done
if pgrep -x pw.x >/dev/null 2>&1; then
  stamp 'ERROR: another pw.x process is active'
  exit 72
fi

source_state=$(tr -d '[:space:]' <"${source_root}/state.txt" 2>/dev/null || printf 'missing')
source_qe_exit=$(tr -d '[:space:]' \
  <"${source_root}/na_c49_vacancy_20261012a_relax_diagnostics/qe_exit_code.txt" \
  2>/dev/null || printf 'missing')
if [[ "${source_state}" != "window_exhausted_restartable" || "${source_qe_exit}" != "0" ]]; then
  stamp "ERROR: source gate state=${source_state} qe_exit=${source_qe_exit}"
  exit 5
fi
python3 scripts/parse_qe_output.py --allow-incomplete "${source_output}" \
  >"${result_root}/source_progress_recheck.json" \
  2>"${result_root}/source_progress_recheck_error.txt"
if ! grep -q '"gpu_acceleration_active": true' "${result_root}/source_progress_recheck.json" || \
   ! grep -q '"electronic_failed_cycles": 0' "${result_root}/source_progress_recheck.json"; then
  stamp 'ERROR: source output failed GPU/electronic recheck'
  exit 6
fi
if grep -q '"ionic_convergence_reached": true' "${result_root}/source_progress_recheck.json"; then
  stamp 'PASS: source run was already ionically converged; continuation unnecessary'
  printf 'already_converged\n' >"${result_root}/state.txt"
  printf 'ready_to_stop_pod\n' >"${result_root}/READY_TO_STOP_POD.txt"
  sync
  exit 0
fi

for checkpoint in \
  "${scratch}/${prefix}.wfc1" \
  "${scratch}/${prefix}.save/data-file-schema.xml" \
  "${scratch}/${prefix}.save/charge-density.dat" \
  "${scratch}/${prefix}.bfgs"
do
  if [[ ! -s "${checkpoint}" ]]; then
    stamp "ERROR: missing restart checkpoint: ${checkpoint}"
    printf 'missing_restart_checkpoint\n' >"${result_root}/state.txt"
    exit 7
  fi
done

if [[ -e "${exit_file}" ]]; then
  mv "${exit_file}" "${result_root}/stale_exit_before_start.txt"
fi

deadline_epoch=$(( $(date +%s) + window_seconds ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/qe_safety_deadline.txt"
printf '%s\n' "${window_seconds}" >"${result_root}/window_seconds.txt"
{
  date --iso-8601=seconds
  findmnt /workspace
  nvidia-smi
  free -h
  sha256sum "${input}" "${manifest}" "${pw}"
  md5sum pseudopotentials/C.pbe-n-kjpaw_psl.1.0.0.UPF \
    pseudopotentials/na_pbe_v1.5.uspp.F.UPF
} >"${result_root}/supervisor_preflight.txt" 2>&1
stamp "START Na/C49 checkpoint continuation; safety deadline $(cat "${result_root}/qe_safety_deadline.txt")"

(
  sleep "${window_seconds}"
  if pgrep -x pw.x >/dev/null 2>&1; then
    printf 'Requested by the 17-hour QE safety guard at %s\n' \
      "$(date --iso-8601=seconds)" >"${exit_file}"
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
for segment in 1 2 3 4 5; do
  remaining=$(( deadline_epoch - $(date +%s) ))
  if (( remaining < 900 )); then
    stamp "STOP: only ${remaining} seconds remain before the safety deadline"
    printf 'window_exhausted_restartable\n' >"${result_root}/state.txt"
    break
  fi

  segment_tag=$(printf 'segment%02d' "${segment}")
  output="${result_root}/na_c49_vacancy_${run_id}_${segment_tag}.out"
  diagnostics="${result_root}/na_c49_vacancy_${run_id}_${segment_tag}_diagnostics"
  stamp "START ${segment_tag}; ${remaining} seconds remain"

  QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
    "${input}" "${output}" "${diagnostics}"
  runner_exit=$?
  qe_exit=$(tr -d '[:space:]' <"${diagnostics}/qe_exit_code.txt" 2>/dev/null || printf 'missing')
  printf 'runner_exit=%s\nqe_exit=%s\n' "${runner_exit}" "${qe_exit}" \
    >"${result_root}/${segment_tag}_gate.txt"

  if [[ ${runner_exit} -eq 0 ]]; then
    stamp "PASS: Na/C49 strictly converged in ${segment_tag}"
    printf 'converged\n' >"${result_root}/state.txt"
    overall_exit=0
    break
  fi
  if [[ "${qe_exit}" != "0" ]]; then
    stamp "ERROR: QE exited ${qe_exit} in ${segment_tag}; refusing another restart"
    printf 'qe_failure\n' >"${result_root}/state.txt"
    break
  fi

  if [[ -e "${exit_file}" ]]; then
    mv "${exit_file}" "${result_root}/${segment_tag}_exit_request.txt"
  fi
  for checkpoint in \
    "${scratch}/${prefix}.wfc1" \
    "${scratch}/${prefix}.save/charge-density.dat" \
    "${scratch}/${prefix}.bfgs"
  do
    if [[ ! -s "${checkpoint}" ]]; then
      stamp "ERROR: checkpoint vanished after ${segment_tag}: ${checkpoint}"
      printf 'checkpoint_failure\n' >"${result_root}/state.txt"
      break 2
    fi
  done
  stamp "${segment_tag} ended cleanly but remains incomplete; continuing from checkpoint"
done

cleanup_guard
trap - EXIT INT TERM

find "${scratch}" -maxdepth 2 -type f \
  -printf '%TY-%Tm-%TdT%TH:%TM:%TS %s %p\n' \
  | sort >"${result_root}/checkpoint_inventory.txt"

rm -f "${bundle}"
archive_members=(
  "${result_root}"
  "${input}"
  "${manifest}"
  "scripts/run_na_c49_restart_18h_20261013.sh"
  "scripts/run_runpod_qe_case.sh"
  "scripts/parse_qe_output.py"
)
for checkpoint_file in \
  "${scratch}/${prefix}.bfgs" \
  "${scratch}/${prefix}.update" \
  "${scratch}/${prefix}.restart_k" \
  "${scratch}/${prefix}.restart_scf" \
  "${scratch}/${prefix}.save/data-file-schema.xml" \
  "${scratch}/${prefix}.save/charge-density.dat" \
  "${scratch}/${prefix}.save/paw.txt"
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
