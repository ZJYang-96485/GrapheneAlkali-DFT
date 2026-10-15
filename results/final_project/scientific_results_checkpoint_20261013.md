# Scientific results checkpoint — 2026-10-13

## Scope and convention

The project compares neutral Li and Na adsorption on pristine C50 graphene and
on a relaxed C49 monovacancy. All production structures use PBE + DFT-D3(BJ),
the approved pseudopotentials, 65/520 Ry cutoffs, a 6x6x1 unshifted k-point
mesh, Marzari-Vanderbilt smearing with `degauss = 0.01 Ry`, and a fixed cell
with `assume_isolated = '2D'`.

Atom-referenced adsorption energies use

`E_ads = E(C_n + M) - E(C_n) - E(M_atom)`.

Negative `E_ads` therefore means exothermic binding relative to a neutral
isolated atom. The accepted isolated-atom energies are `-14.35806979 Ry` for Li
and `-95.26886282 Ry` for Na.

## Accepted numerical results

| System | Status | Total energy (Ry) | E_ads (eV) | Metal height above mean C plane (Angstrom) | Total magnetization (mu_B/cell) | Max force component (Ry/Bohr) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Li/C50 hollow | Strictly converged | -936.96660595 | -1.182 | 1.691 | 0.00 | 0.00031647 |
| Na/C50 hollow | Strictly converged | -1017.83308343 | -0.579 | 2.249 | 0.13 | 0.00036846 |
| Li/C49 vacancy | Strictly converged | -918.05971984 | -2.720 | 1.795 | 0.96 | 0.00036398 |

The corresponding accepted bare-substrate energies are `-922.52166623 Ry`
for pristine C50 and `-903.50175873 Ry` for relaxed C49. Every accepted
adsorption result has GPU acceleration, electronic convergence in every SCF
cycle, ionic convergence, a final total energy, and `JOB DONE`.

## Supported comparisons

- Li binds more strongly than Na on pristine graphene by about `0.603 eV`.
- The vacancy strengthens Li adsorption by about `1.538 eV` relative to the
  pristine hollow site.
- Li sits closer to pristine graphene than Na (`1.691` versus `2.249 Angstrom`),
  consistent with the smaller Li atom and its stronger calculated binding.
- The bare C49 monovacancy has a total magnetization of `1.60 mu_B/cell`;
  Li adsorption lowers it to `0.96 mu_B/cell`, so the vacancy-related magnetic
  state is modified but not completely quenched.

These are direct comparisons within this calculation protocol. They are not a
claim that every adsorption site, magnetic initialization, charge state, or
finite-size effect has been exhaustively sampled.

## Na/C49 result remains incomplete

The October 13 checkpoint continuation advanced the relaxation from BFGS step
29 through the completed step 43. Every completed electronic cycle converged on
the GPU, with no electronic-convergence failure. The latest complete ionic
point has energy `-998.91881929 Ry`, total force `0.004143 Ry/Bohr`, maximum
force component `0.00126934 Ry/Bohr`, and total magnetization `1.00 mu_B/cell`.
Its provisional atom-referenced adsorption energy is about `-2.016 eV`.

This is not an accepted relaxed result: the maximum force component remains
above the `0.0004 Ry/Bohr` criterion, ionic convergence was not printed, and
there is no final `JOB DONE` for the relaxation. RunPod's system log records a
new container start at `2026-10-13 17:38:51 UTC`; segment 3 ends mid-SCF at the
same event. The last completed BFGS/XML/charge-density checkpoint was preserved
in `20261013_na_c49_restart_18h_interrupted_results_bundle.tar.gz` and copied to
`D:\GrapheneAlkali-DFT-backups\runpod-results`; its SHA-256 is
`bcbc015b163adcbab141df14e65a09918b73de9de84837f93d4239f39b1a05b9`.

## Numerical validation already completed

- `65/520 Ry` is within `0.9769 meV/C` of `70/560 Ry` for pristine C50.
- `6x6x1` is within `0.1375 meV/C` of `12x12x1` and is accepted for relaxation.
- `9x9x1` is within `0.0183 meV/C` of `12x12x1` and is supported for a final SCF.
- Changing `degauss` from `0.01` to `0.005 Ry` changes the pristine free energy
  by only `0.0496 meV/C`.

## Primary provenance

- Pristine convergence: `results/convergence/pristine/summary.md`
- Pristine C50 relaxation: `results/relaxation/pristine/summary.md`
- C49 relaxation: `results/relaxation/monovacancy/relax_monovacancy_65_520_cg_seed001_c1_20260917.out`
- Li/C50 result: `results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_analysis.json`
- Li and Na atomic references: `results/references/isolated_atoms/li_reference_summary.md` and `na_reference_summary.md`
- Cloud Na/C50 strict output: `results/cloud/20260930_blackwell48_restart2/na_c50_hollow_20260924a_relax_restart2.out`
- Cloud Li/C49 strict output: `results/cloud/20261008_li_c49_vacancy_18h_cont2/li_c49_vacancy_20261008a_segment03.out`

## Extended final campaign launched 2026-10-14

The RunPod campaign first resumes Na/C49 from the preserved step-43 checkpoint
in four-hour QE segments.  It requires GPU acceleration, clean QE exit status,
electronic convergence, ionic convergence, a final energy, and `JOB DONE`
before accepting the fourth adsorption relaxation.  After that gate passes,
the campaign runs fixed-geometry `9x9x1` final SCFs in this order:
Na/C49, bare C49, Li/C49, bare C50, Li/C50, and Na/C50.  Those six calculations
keep PBE, DFT-D3(BJ), 65/520 Ry, 0.01 Ry Marzari-Vanderbilt smearing, CG
diagonalization, the accepted spin settings, and the exact accepted relaxed
geometries.

The persistent entry point is
`scripts/runpod_bootstrap_final_campaign_20261014.sh`.  It reinstalls transient
container dependencies after a platform rebuild, resumes from state files,
and never overwrites a prior output.  The active RunPod GPU costs $1.29/hour;
large wavefunction scratch files are removed only after strict acceptance,
while raw outputs, diagnostics, XML, charge density, and structural provenance
are retained on the 50 GB network volume.
