#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

root='results/cloud/20261017_adsorbate_cutoff_70_560'
summary_root='results/final_project/20261017_adsorbate_cutoff_validation'
input_root='qe_inputs/convergence/adsorbate_cutoff/20261017'
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
campaign_log="${root}/campaign.log"
state_file="${root}/state.txt"
deadline_file="${root}/deadline_epoch.txt"

mkdir -p "${root}" "${summary_root}"
exec 9>"${root}/campaign.lock"
flock -n 9 || exit 75
exec >>"${campaign_log}" 2>&1
stamp() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }
set_state() { printf '%s\n' "$1" >"${state_file}"; sync; }

if [[ -f "${state_file}" ]] && [[ $(tr -d '[:space:]' <"${state_file}") == complete ]]; then
  stamp 'campaign already complete'
  exit 0
fi

if [[ ! -f "${deadline_file}" ]]; then
  printf '%s\n' "$(( $(date +%s) + 43200 ))" >"${deadline_file}"
fi
deadline_epoch=$(tr -d '[:space:]' <"${deadline_file}")
printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/last_launch_utc.txt"
set_state running
stamp "starting cutoff-validation campaign; hard deadline epoch=${deadline_epoch}"

fail() {
  message=$1
  stamp "TERMINAL FAILURE: ${message}"
  printf '%s\n' "${message}" >"${root}/terminal_error.txt"
  set_state terminal_failure
  return 1
}

[[ -x "${pw}" ]] || { fail "pw.x is not executable: ${pw}"; exit 1; }
if pgrep -x pw.x >/dev/null 2>&1; then
  fail 'another pw.x process is already active'
  exit 1
fi

python3 scripts/build_adsorbate_cutoff_validation_20261017.py \
  --repo-root "${repo_root}" --output-root "${input_root}" || {
    fail 'input generation or audit failed'
    exit 1
  }

{
  date --iso-8601=seconds
  uname -a
  free -h
  df -h /workspace
  nvidia-smi
  printf 'pw.x=%s\n' "$(readlink -f "${pw}")"
  git -C /workspace/q-e-7.6 rev-parse HEAD
  ldd "${pw}"
} >"${root}/campaign_preflight.txt" 2>&1 || {
  fail 'hardware/QE preflight failed'
  exit 1
}

printf '%s\n' \
  '8e281b34a927efac7e739263a90d7aed  pseudopotentials/C.pbe-n-kjpaw_psl.1.0.0.UPF' \
  'e912e257baa3777c20ea3d68f190483c  pseudopotentials/li_pbe_v1.4.uspp.F.UPF' \
  '44600605ef58000f06b90626533354dc  pseudopotentials/na_pbe_v1.5.uspp.F.UPF' \
  >"${root}/pseudopotential_md5.expected"
md5sum -c "${root}/pseudopotential_md5.expected" \
  >"${root}/pseudopotential_md5.check" 2>&1 || {
    fail 'pseudopotential checksum audit failed'
    exit 1
  }
sha256sum "${input_root}"/*.in "${input_root}/manifest.json" \
  >"${root}/input_sha256.txt" || {
    fail 'input checksum recording failed'
    exit 1
  }

strict_gate() {
  result=$1
  python3 - "${result}" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
required = (
    result.get("job_completed") is True,
    result.get("gpu_acceleration_active") is True,
    result.get("all_electronic_cycles_converged") is True,
    result.get("final_total_energy_ry") is not None,
)
raise SystemExit(0 if all(required) else 1)
PY
}

run_case() {
  case_name=$1
  input="${input_root}/${case_name}_ecut70_560.in"
  case_root="${root}/${case_name}"
  scratch="qe_scratch/cutoff_validation_20261017/cut70_${case_name}_20261017"
  mkdir -p "${case_root}" "${scratch}"

  if [[ -f "${case_root}/state.txt" ]] && \
     [[ $(tr -d '[:space:]' <"${case_root}/state.txt") == accepted ]]; then
    stamp "${case_name}: already accepted"
    return 0
  fi

  if (( $(date +%s) >= deadline_epoch )); then
    printf 'deadline_reached\n' >"${case_root}/state.txt"
    fail "12-hour deadline reached before ${case_name}"
    return 1
  fi

  for attempt in 01 02; do
    output="${case_root}/${case_name}_ecut70_560_attempt${attempt}.out"
    diagnostics="${case_root}/attempt${attempt}_diagnostics"
    strict="${diagnostics}/strict_result.json"

    if [[ -s "${strict}" ]] && strict_gate "${strict}"; then
      printf '%s\n' "${output}" >"${case_root}/accepted_output.txt"
      printf 'accepted\n' >"${case_root}/state.txt"
      stamp "${case_name}: recovered accepted attempt ${attempt}"
      return 0
    fi

    if [[ -s "${output}" ]]; then
      stamp "${case_name}: preserving incomplete attempt ${attempt}; trying next slot"
      continue
    fi

    printf '%s\n' "${case_name}" >"${root}/active_case.txt"
    printf '%s\n' "${attempt}" >"${root}/active_attempt.txt"
    printf 'running\n' >"${case_root}/state.txt"
    stamp "${case_name}: launching attempt ${attempt}"
    QE_PW="${pw}" scripts/run_runpod_qe_case.sh \
      "${input}" "${output}" "${diagnostics}"
    run_exit=$?
    if [[ ${run_exit} -ne 0 ]]; then
      printf 'failed\n' >"${case_root}/state.txt"
      fail "${case_name} attempt ${attempt} failed strict QE validation"
      return 1
    fi
    if ! strict_gate "${strict}"; then
      printf 'failed\n' >"${case_root}/state.txt"
      fail "${case_name} attempt ${attempt} did not satisfy strict acceptance"
      return 1
    fi

    printf '%s\n' "${output}" >"${case_root}/accepted_output.txt"
    printf 'accepted\n' >"${case_root}/state.txt"
    sync
    stamp "${case_name}: accepted attempt ${attempt}"
    return 0
  done

  printf 'failed\n' >"${case_root}/state.txt"
  fail "${case_name} has no unused attempt slot after an interrupted recovery"
  return 1
}

# The short C50 job proves the full periodic GPU path first.  Atomic references
# follow, then the more expensive adsorbed systems.
for case_name in c50 li_atom na_atom li_c50 na_c50; do
  run_case "${case_name}" || exit 1
done
rm -f "${root}/active_case.txt" "${root}/active_attempt.txt"

python3 scripts/summarize_adsorbate_cutoff_validation_20261017.py \
  --root "${root}" --output-dir "${summary_root}" || {
    fail 'strict scientific summarization failed'
    exit 1
  }

bundle="${root}/adsorbate_cutoff_validation_20261017.tar.gz"
bundle_tmp="${bundle}.tmp"
rm -f "${bundle_tmp}"
tar -czf "${bundle_tmp}" \
  "${input_root}" "${summary_root}" \
  "${root}/campaign_preflight.txt" \
  "${root}/pseudopotential_md5.expected" \
  "${root}/pseudopotential_md5.check" \
  "${root}/input_sha256.txt" \
  "${root}/c50" "${root}/li_atom" "${root}/na_atom" \
  "${root}/li_c50" "${root}/na_c50" || {
    fail 'result bundle creation failed'
    exit 1
  }
mv "${bundle_tmp}" "${bundle}"
sha256sum "${bundle}" >"${root}/adsorbate_cutoff_validation_20261017.sha256"
sha256sum -c "${root}/adsorbate_cutoff_validation_20261017.sha256"
tar -tzf "${bundle}" >/dev/null
printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/completed_utc.txt"
printf 'Strictly validated 70/560 Ry cutoff campaign is complete.\n' \
  >"${root}/READY_TO_STOP_POD.txt"
set_state complete
stamp 'campaign complete and bundle verified'
exit 0
