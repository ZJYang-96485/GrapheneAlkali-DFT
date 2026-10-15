#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20261001_li_c49_vacancy_segment2}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
guard_seconds=${GUARD_SECONDS:-15600}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261001a_cloud_segment2_restart.in"
manifest="qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261001a_cloud_segment2_manifest.json"
output="${result_root}/li_c49_vacancy_20261001a_cloud_segment2.out"
diagnostics="${result_root}/li_c49_vacancy_20261001a_cloud_segment2_diagnostics"
scratch="qe_scratch/adsorption/li_c49_vacancy_20260930a_relax"
exit_file="${scratch}/li_c49_vacancy_20260930a_relax.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle="/workspace/li_c49_20261001_segment2_results_bundle.tar.gz"

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
test -s "${scratch}/li_c49_vacancy_20260930a_relax.wfc1" || exit 6
test -s "${scratch}/li_c49_vacancy_20260930a_relax.save/charge-density.dat" || exit 7
test -s "${scratch}/li_c49_vacancy_20260930a_relax.bfgs" || exit 8
if [[ -e "${exit_file}" || -e "${output}" || -e "${diagnostics}" ]]; then
  stamp 'ERROR: stale EXIT file or existing continuation artifacts detected'
  exit 73
fi

deadline_epoch=$(( $(date +%s) + guard_seconds ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/safety_deadline.txt"
stamp "Restart checkpoint verified on ${mount_source}"
stamp "Continuation safety deadline: $(cat "${result_root}/safety_deadline.txt")"

(
  sleep "${guard_seconds}"
  if pgrep -f "${pw}.*${input}" >/dev/null 2>&1; then
    printf 'Requested by 9 AM continuation safety guard at %s\n' \
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

stamp 'START Li/C49 cloud relaxation segment 2 restart'
QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
  "${input}" "${output}" "${diagnostics}"
runner_exit=$?
printf '%s\n' "${runner_exit}" >"${result_root}/supervisor_exit_code.txt"

find "${scratch}" -maxdepth 2 -type f \
  -printf '%TY-%Tm-%TdT%TH:%TM:%TS %s %p\n' \
  | sort >"${result_root}/checkpoint_inventory.txt"

rm -f "${bundle}"
archive_members=(
  "${result_root}"
  "${input}"
  "${manifest}"
  "scripts/run_li_c49_cloud_segment2_until0900.sh"
  "scripts/chain_li_c49_segment2_until0900.sh"
  "scripts/run_runpod_qe_case.sh"
  "scripts/parse_qe_output.py"
)
for checkpoint_file in \
  "${scratch}/li_c49_vacancy_20260930a_relax.bfgs" \
  "${scratch}/li_c49_vacancy_20260930a_relax.update" \
  "${scratch}/li_c49_vacancy_20260930a_relax.restart_k" \
  "${scratch}/li_c49_vacancy_20260930a_relax.restart_scf" \
  "${scratch}/li_c49_vacancy_20260930a_relax.save/data-file-schema.xml" \
  "${scratch}/li_c49_vacancy_20260930a_relax.save/charge-density.dat" \
  "${scratch}/li_c49_vacancy_20260930a_relax.save/paw.txt"
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

printf 'runner_exit=%s\narchive_exit=%s\ncompleted=%s\n' \
  "${runner_exit}" "${archive_exit}" "$(date --iso-8601=seconds)" \
  >"${result_root}/supervisor_complete.txt"
sync

if [[ ${runner_exit} -eq 0 ]]; then
  stamp 'PASS Li/C49 cloud relaxation segment 2'
else
  stamp "STOP Li/C49 cloud relaxation segment 2; validation exit ${runner_exit}"
fi

if [[ ${archive_exit} -ne 0 ]]; then
  exit "${archive_exit}"
fi
exit "${runner_exit}"
