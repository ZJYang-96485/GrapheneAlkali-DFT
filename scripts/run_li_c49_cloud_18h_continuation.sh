#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20261007_li_c49_vacancy_18h}
run_id=${RUN_ID:-20261007a}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
window_seconds=${WINDOW_SECONDS:-61200}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261001a_cloud_segment2_restart.in"
manifest=${MANIFEST:-qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261007a_cloud_18h_manifest.json}
scratch="qe_scratch/adsorption/li_c49_vacancy_20260930a_relax"
prefix="li_c49_vacancy_20260930a_relax"
exit_file="${scratch}/${prefix}.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle=${BUNDLE_PATH:-/workspace/${run_tag}_results_bundle.tar.gz}

if [[ -e "${result_root}" ]]; then
  printf 'Refusing existing result root: %s\n' "${result_root}" >&2
  exit 73
fi
mkdir -p "${result_root}"
exec > >(tee -a "${result_root}/supervisor.log") 2>&1

stamp() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

mount_source=$(findmnt -n -o SOURCE /workspace)
if [[ "${mount_source}" != *"${volume_id}"* ]]; then
  stamp "ERROR: expected volume ${volume_id}; found ${mount_source}"
  exit 2
fi
test -x "${pw}" || exit 3
test -s "${input}" || exit 4
test -s "${manifest}" || exit 5
if pgrep -x pw.x >/dev/null 2>&1; then
  stamp 'ERROR: another pw.x process is already active'
  exit 72
fi

for prior_output in \
  results/cloud/20260930_li_c49_vacancy_segment1/li_c49_vacancy_20260930a_cloud_segment1.out \
  results/cloud/20261001_li_c49_vacancy_segment2/li_c49_vacancy_20261001a_cloud_segment2.out
do
  [[ -s "${prior_output}" ]] || continue
  prior_name=$(basename "${prior_output}" .out)
  if python3 scripts/parse_qe_output.py "${prior_output}" \
      >"${result_root}/${prior_name}_strict_recheck.json" \
      2>"${result_root}/${prior_name}_strict_recheck_error.txt"; then
    if grep -q '"ionic_convergence_reached": true' \
        "${result_root}/${prior_name}_strict_recheck.json"; then
      stamp "PASS: prior Li/C49 relaxation is already strictly converged: ${prior_output}"
      printf 'already_converged\n' >"${result_root}/state.txt"
      printf 'ready_to_stop_pod\n' >"${result_root}/READY_TO_STOP_POD.txt"
      sync
      exit 0
    fi
  fi
done

for checkpoint in \
  "${scratch}/${prefix}.wfc1" \
  "${scratch}/${prefix}.save/charge-density.dat" \
  "${scratch}/${prefix}.bfgs"
do
  if [[ ! -s "${checkpoint}" ]]; then
    stamp "ERROR: missing restart checkpoint: ${checkpoint}"
    printf 'missing_restart_checkpoint\n' >"${result_root}/state.txt"
    exit 6
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
} >"${result_root}/supervisor_preflight.txt" 2>&1
stamp "START Li/C49 continuation; safety deadline $(cat "${result_root}/qe_safety_deadline.txt")"

(
  sleep "${window_seconds}"
  if pgrep -x pw.x >/dev/null 2>&1; then
    printf 'Requested by the QE safety guard at %s\n' \
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
    printf 'window_exhausted\n' >"${result_root}/state.txt"
    break
  fi

  segment_tag=$(printf 'segment%02d' "${segment}")
  output="${result_root}/li_c49_vacancy_${run_id}_${segment_tag}.out"
  diagnostics="${result_root}/li_c49_vacancy_${run_id}_${segment_tag}_diagnostics"
  stamp "START ${segment_tag}; ${remaining} seconds remain"

  QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
    "${input}" "${output}" "${diagnostics}"
  runner_exit=$?
  qe_exit=$(tr -d '[:space:]' <"${diagnostics}/qe_exit_code.txt" 2>/dev/null || printf 'missing')
  printf 'runner_exit=%s\nqe_exit=%s\n' "${runner_exit}" "${qe_exit}" \
    >"${result_root}/${segment_tag}_gate.txt"

  if [[ ${runner_exit} -eq 0 ]]; then
    stamp "PASS: Li/C49 strictly converged in ${segment_tag}"
    printf 'converged\n' >"${result_root}/state.txt"
    overall_exit=0
    break
  fi
  if [[ "${qe_exit}" != "0" ]]; then
    stamp "ERROR: QE exited ${qe_exit} in ${segment_tag}; refusing another restart"
    printf 'qe_failure\n' >"${result_root}/state.txt"
    overall_exit=1
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
      overall_exit=1
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
  "scripts/run_li_c49_cloud_18h_continuation.sh"
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
