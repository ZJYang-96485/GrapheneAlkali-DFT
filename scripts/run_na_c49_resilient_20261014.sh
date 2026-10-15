#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

result_root="results/cloud/20261014_na_c49_resilient"
input="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_relax_restart.in"
scratch="qe_scratch/adsorption/na_c49_vacancy_20261012a_relax"
prefix="na_c49_vacancy_20261012a_relax"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
mkdir -p "${result_root}"

exec 9>"${result_root}/campaign.lock"
if ! flock -n 9; then
  printf 'Na/C49 continuation is already supervised.\n'
  exit 75
fi
exec >>"${result_root}/supervisor.log" 2>&1

stamp() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }
state_file="${result_root}/state.txt"
if [[ -s "${state_file}" ]]; then
  state=$(tr -d '[:space:]' <"${state_file}")
else
  state='new'
fi
if [[ "${state}" == "converged" ]]; then
  stamp 'SKIP: Na/C49 is already strictly converged'
  exit 0
fi
if [[ "${state}" == "qe_failure" || "${state}" == "checkpoint_failure" ]]; then
  stamp "STOP: prior terminal state ${state} requires review"
  exit 2
fi

mount_source=$(findmnt -n -o SOURCE /workspace)
[[ "${mount_source}" == *ikljhz724r* ]] || { stamp "ERROR wrong volume: ${mount_source}"; exit 2; }
[[ -x "${pw}" && -s "${input}" ]] || { stamp 'ERROR missing QE or input'; exit 3; }
pgrep -x pw.x >/dev/null 2>&1 && { stamp 'ERROR another pw.x is active'; exit 72; }

for checkpoint in \
  "${scratch}/${prefix}.wfc1" \
  "${scratch}/${prefix}.save/data-file-schema.xml" \
  "${scratch}/${prefix}.save/charge-density.dat" \
  "${scratch}/${prefix}.bfgs"
do
  [[ -s "${checkpoint}" ]] || { stamp "ERROR missing checkpoint ${checkpoint}"; printf 'checkpoint_failure\n' >"${state_file}"; exit 7; }
done

# Preserve the known-good step-43 checkpoint once.  The large wavefunction is
# intentionally retained on the network volume so an interrupted write cannot
# destroy the only restart state.
snapshot="qe_scratch/checkpoint_snapshots/na_c49_step43_20261013"
if [[ ! -e "${snapshot}/SNAPSHOT_COMPLETE" ]]; then
  stamp 'SNAPSHOT: preserving the step-43 restart state'
  mkdir -p "${snapshot}/${prefix}.save"
  if ! cp -a --reflink=auto "${scratch}/${prefix}.wfc1" "${snapshot}/" || \
     ! cp -a --reflink=auto "${scratch}/${prefix}.bfgs" "${scratch}/${prefix}.update" "${snapshot}/" || \
     ! cp -a --reflink=auto "${scratch}/${prefix}.save/data-file-schema.xml" \
       "${scratch}/${prefix}.save/charge-density.dat" "${scratch}/${prefix}.save/paw.txt" \
       "${snapshot}/${prefix}.save/"; then
    stamp 'ERROR: checkpoint snapshot copy failed'
    printf 'checkpoint_failure\n' >"${state_file}"
    exit 7
  fi
  sync || { stamp 'ERROR: checkpoint snapshot sync failed'; exit 7; }
  printf '%s\n' "$(date --iso-8601=seconds)" >"${snapshot}/SNAPSHOT_COMPLETE"
  stamp 'SNAPSHOT complete'
fi

rm -f "${scratch}/${prefix}.EXIT"
printf 'running\n' >"${state_file}"

for iteration in $(seq 1 20); do
  last=$(find "${result_root}" -maxdepth 1 -type f -name 'na_c49_segment*.out' -printf '%f\n' \
    | sed -n 's/^na_c49_segment\([0-9][0-9][0-9]\)\.out$/\1/p' | sort -n | tail -1)
  next=$((10#${last:-000} + 1))
  tag=$(printf 'segment%03d' "${next}")
  output="${result_root}/na_c49_${tag}.out"
  diagnostics="${result_root}/na_c49_${tag}_diagnostics"
  stamp "START ${tag} from persistent checkpoint"
  QE_PW="${pw}" scripts/run_runpod_qe_case.sh "${input}" "${output}" "${diagnostics}"
  runner_exit=$?
  qe_exit=$(tr -d '[:space:]' <"${diagnostics}/qe_exit_code.txt" 2>/dev/null || printf 'missing')
  printf 'runner_exit=%s\nqe_exit=%s\n' "${runner_exit}" "${qe_exit}" >"${result_root}/${tag}_gate.txt"

  if [[ ${runner_exit} -eq 0 ]]; then
    stamp "PASS: Na/C49 strictly converged in ${tag}"
    printf 'converged\n' >"${state_file}"
    printf '%s\n' "${output}" >"${result_root}/accepted_output.txt"
    sync
    exit 0
  fi
  if [[ "${qe_exit}" != "0" ]]; then
    stamp "ERROR: QE exit ${qe_exit}; no blind retry"
    printf 'qe_failure\n' >"${state_file}"
    sync
    exit 1
  fi
  rm -f "${scratch}/${prefix}.EXIT"
  stamp "RESTARTABLE: ${tag} ended cleanly before ionic convergence"
  sync
done

stamp 'STOP: twenty clean segments exhausted without ionic convergence'
printf 'segment_limit\n' >"${state_file}"
exit 1
