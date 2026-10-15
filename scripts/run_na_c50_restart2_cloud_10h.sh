#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

run_tag=${RUN_TAG:-20260930_blackwell48_restart2}
volume_id=${RUNPOD_VOLUME_ID:-ikljhz724r}
guard_seconds=${GUARD_SECONDS:-36900}
result_root="results/cloud/${run_tag}"
input="qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax_restart2.in"
output="${result_root}/na_c50_hollow_20260924a_relax_restart2.out"
diagnostics="${result_root}/na_c50_hollow_20260924a_relax_restart2_diagnostics"
scratch="qe_scratch/adsorption/na_c50_hollow_20260924a_relax"
exit_file="${scratch}/na_c50_hollow_20260924a_relax.EXIT"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
bundle="/workspace/na_c50_20260930_restart2_results_bundle.tar.gz"

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
test -s "${scratch}/na_c50_hollow_20260924a_relax.wfc1" || exit 4
test -s "${scratch}/na_c50_hollow_20260924a_relax.save/charge-density.dat" || exit 5
test -s "${scratch}/na_c50_hollow_20260924a_relax.bfgs" || exit 6
if [[ -e "${exit_file}" || -e "${output}" || -e "${diagnostics}" ]]; then
  stamp 'ERROR: stale EXIT file or existing continuation artifacts detected'
  exit 73
fi

deadline_epoch=$(( $(date +%s) + guard_seconds ))
date -d "@${deadline_epoch}" --iso-8601=seconds >"${result_root}/safety_deadline.txt"
stamp "Persistent restart checkpoint verified on ${mount_source}"
stamp "Safety deadline: $(cat "${result_root}/safety_deadline.txt")"

(
  sleep "${guard_seconds}"
  printf 'Requested by 10-hour continuation safety guard at %s\n' \
    "$(date --iso-8601=seconds)" >"${exit_file}"
  sync
) &
guard_pid=$!

cleanup_guard() {
  kill "${guard_pid}" 2>/dev/null || true
  wait "${guard_pid}" 2>/dev/null || true
}
trap cleanup_guard EXIT INT TERM

stamp 'START restart continuation 2'
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
  "scripts/run_na_c50_restart2_cloud_10h.sh"
)
for checkpoint_file in \
  "${scratch}/na_c50_hollow_20260924a_relax.bfgs" \
  "${scratch}/na_c50_hollow_20260924a_relax.update" \
  "${scratch}/na_c50_hollow_20260924a_relax.restart_k" \
  "${scratch}/na_c50_hollow_20260924a_relax.restart_scf" \
  "${scratch}/na_c50_hollow_20260924a_relax.save/data-file-schema.xml" \
  "${scratch}/na_c50_hollow_20260924a_relax.save/charge-density.dat" \
  "${scratch}/na_c50_hollow_20260924a_relax.save/paw.txt"
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
sync

if [[ ${runner_exit} -eq 0 ]]; then
  stamp 'PASS restart continuation 2'
else
  stamp "STOP restart continuation 2; validation exit ${runner_exit}"
fi

if [[ ${archive_exit} -ne 0 ]]; then
  exit "${archive_exit}"
fi
exit "${runner_exit}"
