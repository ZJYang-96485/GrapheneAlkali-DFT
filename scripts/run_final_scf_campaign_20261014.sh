#!/usr/bin/env bash
set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"
root="results/cloud/20261014_final_scf"
pw=${QE_PW:-/workspace/q-e-7.6/bin/pw.x}
mkdir -p "${root}" "qe_inputs/final_scf/20261014"

exec 8>"${root}/campaign.lock"
flock -n 8 || exit 75
exec >>"${root}/supervisor.log" 2>&1
stamp() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }

na_c49_relax=$(tr -d '\r\n' <results/cloud/20261014_na_c49_resilient/accepted_output.txt)

# The accepted relaxation output is the durable scientific record.  Preserve
# XML/charge/BFGS metadata but remove the now-redundant 11 GB relaxation
# wavefunctions and rollback copy before creating 9x9 wavefunctions on a 50 GB
# volume.
cleanup_log="${root}/large_scratch_cleanup.txt"
if [[ ! -e "${root}/relax_wfc_cleanup_complete" ]]; then
  {
    date --iso-8601=seconds
    stat -c '%s %y %n' \
      qe_scratch/adsorption/na_c49_vacancy_20261012a_relax/na_c49_vacancy_20261012a_relax.wfc1 \
      qe_scratch/checkpoint_snapshots/na_c49_step43_20261013/na_c49_vacancy_20261012a_relax.wfc1 \
      2>/dev/null || true
  } >>"${cleanup_log}"
  rm -f \
    qe_scratch/adsorption/na_c49_vacancy_20261012a_relax/na_c49_vacancy_20261012a_relax.wfc1 \
    qe_scratch/checkpoint_snapshots/na_c49_step43_20261013/na_c49_vacancy_20261012a_relax.wfc1
  sync
  printf '%s\n' "$(date --iso-8601=seconds)" >"${root}/relax_wfc_cleanup_complete"
fi

# Order maximizes usable science if the campaign is interrupted: complete the
# missing Na/C49 pair first, then the already accepted Li/C49 and pristine pairs.
cases=(na_c49 c49 li_c49 c50 li_c50 na_c50)
for case_name in "${cases[@]}"; do
  case "${case_name}" in
    na_c49)
      template="qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_relax_restart.in"
      relax="${na_c49_relax}"
      ;;
    c49)
      template="qe_inputs/relaxation/monovacancy/relax_monovacancy.in"
      relax="results/relaxation/monovacancy/relax_monovacancy_65_520_cg_seed001_c1_20260917.out"
      ;;
    li_c49)
      template="qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261001a_cloud_segment2_restart.in"
      relax="results/cloud/20261008_li_c49_vacancy_18h_cont2/li_c49_vacancy_20261008a_segment03.out"
      ;;
    c50)
      template="qe_inputs/relaxation/pristine/relax_pristine.in"
      relax="results/relaxation/pristine/relax_pristine_65_520_cg_20260916.out"
      ;;
    li_c50)
      template="qe_inputs/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.in"
      relax="results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.out"
      ;;
    na_c50)
      template="qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax_restart2.in"
      relax="results/cloud/20260930_blackwell48_restart2/na_c50_hollow_20260924a_relax_restart2.out"
      ;;
  esac

  case_root="${root}/${case_name}"
  mkdir -p "${case_root}"
  if [[ -s "${case_root}/state.txt" ]]; then
    state=$(tr -d '[:space:]' <"${case_root}/state.txt")
  else
    state='new'
  fi
  if [[ "${state}" == "accepted" ]]; then
    stamp "SKIP ${case_name}: already accepted"
    continue
  fi
  [[ -s "${template}" && -s "${relax}" ]] || { stamp "ERROR ${case_name}: missing template or relaxation"; printf 'missing_source\n' >"${case_root}/state.txt"; exit 3; }

  prefix="final9_${case_name}_20261014"
  scratch_dir="qe_scratch/final_scf/${prefix}"
  mkdir -p "${scratch_dir}"
  fresh_input="qe_inputs/final_scf/20261014/${case_name}_9x9x1.in"
  restart_input="qe_inputs/final_scf/20261014/${case_name}_9x9x1_restart.in"
  if [[ ! -s "${fresh_input}" ]]; then
    python3 scripts/build_final_scf_from_relax.py --template "${template}" \
      --relax-output "${relax}" --prefix "${prefix}" --output "${fresh_input}"
  fi
  if [[ ! -s "${restart_input}" ]]; then
    python3 scripts/build_final_scf_from_relax.py --template "${template}" \
      --relax-output "${relax}" --prefix "${prefix}" --restart-mode restart \
      --output "${restart_input}"
  fi

  printf 'running\n' >"${case_root}/state.txt"
  for attempt in 1 2 3; do
    tag=$(printf 'attempt%02d' "${attempt}")
    output="${case_root}/${case_name}_9x9x1_${tag}.out"
    diagnostics="${case_root}/${tag}_diagnostics"
    if [[ -s "${diagnostics}/strict_result.json" ]]; then
      stamp "PASS ${case_name}: pre-existing ${tag} is accepted"
      printf 'accepted\n' >"${case_root}/state.txt"
      printf '%s\n' "${output}" >"${case_root}/accepted_output.txt"
      break
    fi
    if [[ -s "${output}" ]]; then
      stamp "PRESERVE ${case_name}: incomplete ${tag}; advancing without overwrite"
      continue
    fi
    selected="${fresh_input}"
    # Only request an SCF restart when QE actually wrote a restartable XML
    # checkpoint.  A pre-SCF failure (for example, an unavailable outdir)
    # leaves no checkpoint and must be relaunched from the fresh input.
    if [[ ${attempt} -gt 1 && -s "${scratch_dir}/${prefix}.save/data-file-schema.xml" ]]; then
      selected="${restart_input}"
    fi
    stamp "START ${case_name} ${tag} with $(basename "${selected}")"
    QE_PW="${pw}" scripts/run_runpod_qe_case.sh "${selected}" "${output}" "${diagnostics}"
    runner_exit=$?
    qe_exit=$(tr -d '[:space:]' <"${diagnostics}/qe_exit_code.txt" 2>/dev/null || printf 'missing')
    if [[ ${runner_exit} -eq 0 ]]; then
      printf 'accepted\n' >"${case_root}/state.txt"
      printf '%s\n' "${output}" >"${case_root}/accepted_output.txt"
      stamp "PASS ${case_name} ${tag}"
      break
    fi
    if [[ "${qe_exit}" != "0" ]]; then
      printf 'qe_failure\n' >"${case_root}/state.txt"
      stamp "ERROR ${case_name}: QE exit ${qe_exit}; no blind retry"
      exit 1
    fi
    stamp "RESTARTABLE ${case_name}: clean incomplete ${tag}"
    sync
  done
  state=$(tr -d '[:space:]' <"${case_root}/state.txt")
  [[ "${state}" == "accepted" ]] || { stamp "ERROR ${case_name}: attempt limit exhausted"; exit 1; }
  scf_wfc="qe_scratch/final_scf/${prefix}/${prefix}.wfc1"
  if [[ -f "${scf_wfc}" ]]; then
    stat -c '%s %y %n' "${scf_wfc}" >"${case_root}/removed_wfc_inventory.txt"
    rm -f "${scf_wfc}"
    sync
  fi
done

printf 'complete\n' >"${root}/state.txt"
printf 'ready_to_stop_pod\n' >"${root}/READY_TO_STOP_POD.txt"
sync
stamp 'PASS: all six standardized final SCFs accepted'
