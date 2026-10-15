#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20261001_na_c49_vacancy_pilot}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
guard_seconds=${GUARD_SECONDS:-3600}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261001a_cloud_pilot.in"
manifest="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261001a_cloud_pilot_manifest.json"
output="${result_root}/na_c49_vacancy_20261001a_cloud_pilot.out"
diagnostics="${result_root}/na_c49_vacancy_20261001a_cloud_pilot_diagnostics"
scratch="qe_scratch/adsorption/na_c49_vacancy_20261001a_pilot"
exit_file="${scratch}/na_c49_vacancy_20261001a_pilot.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle="/workspace/na_c49_20261001a_pilot_results_bundle.tar.gz"

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
if [[ -e "${scratch}" || -e "${exit_file}" || -e "${output}" || -e "${diagnostics}" ]]; then
  stamp 'ERROR: fresh-prefix gate failed for the Na/C49 pilot'
  exit 73
fi

deadline_epoch=$(( $(date +%s) + guard_seconds ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/safety_deadline.txt"
stamp "Na/C49 pilot safety deadline: $(cat "${result_root}/safety_deadline.txt")"

(
  sleep "${guard_seconds}"
  if pgrep -f "${pw}.*${input}" >/dev/null 2>&1; then
    mkdir -p "${scratch}"
    printf 'Requested by 9 AM pilot safety guard at %s\n' \
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

stamp 'START conditional Na/C49 fixed-geometry cloud pilot'
QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
  "${input}" "${output}" "${diagnostics}"
runner_exit=$?
printf '%s\n' "${runner_exit}" >"${result_root}/supervisor_exit_code.txt"

rm -f "${bundle}"
tar -czf "${bundle}" \
  "${result_root}" "${input}" "${manifest}" \
  "scripts/run_na_c49_cloud_pilot_until0900.sh" \
  "scripts/run_runpod_qe_case.sh" "scripts/parse_qe_output.py"
archive_exit=$?
if [[ ${archive_exit} -eq 0 ]]; then
  sha256sum "${bundle}" >"${result_root}/results_bundle.sha256"
  stamp "ARCHIVE $(cat "${result_root}/results_bundle.sha256")"
else
  stamp "ERROR: result archive failed with exit ${archive_exit}"
fi

printf 'runner_exit=%s\narchive_exit=%s\ncompleted=%s\n' \
  "${runner_exit}" "${archive_exit}" "$(date --iso-8601=seconds)" \
  >"${result_root}/supervisor_complete.txt"
sync

if [[ ${runner_exit} -eq 0 ]]; then
  stamp 'PASS conditional Na/C49 fixed-geometry pilot'
else
  stamp "STOP conditional Na/C49 pilot; validation exit ${runner_exit}"
fi

if [[ ${archive_exit} -ne 0 ]]; then
  exit "${archive_exit}"
fi
exit "${runner_exit}"
