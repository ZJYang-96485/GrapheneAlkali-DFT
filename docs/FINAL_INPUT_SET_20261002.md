# Final QE input set (October 2, 2026 checkpoint)

This checkpoint collects the selected Quantum ESPRESSO inputs needed to
reproduce the validated calculations and continue the unfinished primary
systems. An input's inclusion does not imply that its calculation converged;
the status table below is authoritative.

| Role | Input | Checkpoint status |
| --- | --- | --- |
| Selected cutoff | `qe_inputs/convergence/pristine/cutoff/ecutwfc_65_ecutrho_520.in` | Validated methodology point |
| Selected k mesh | `qe_inputs/convergence/pristine/kpoints/k_6x6x1.in` | Validated methodology point |
| Selected smearing | `qe_inputs/convergence/pristine/smearing/degauss_0p010.in` | Validated methodology point |
| Bare C50 relaxation | `qe_inputs/relaxation/pristine/relax_pristine.in` | Accepted |
| Bare C49 relaxation | `qe_inputs/relaxation/monovacancy/relax_monovacancy.in` | Accepted |
| Neutral isolated Li | `qe_inputs/references/isolated_atoms/li_atom_20260923d_box16.in` | Accepted final atom reference |
| Neutral isolated Na | `qe_inputs/references/isolated_atoms/na_atom_20260923c_box16.in` | Accepted final atom reference |
| Li/C50 relaxation | `qe_inputs/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.in` | Accepted |
| Na/C50 relaxation | `qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax.in` | Initial segment; not accepted |
| Na/C50 restart 1 | `qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax_restart1.in` | Continuation; not accepted |
| Na/C50 restart 2 | `qe_inputs/adsorption/na_pristine_hollow/na_c50_hollow_20260924a_relax_restart2.in` | `JOB DONE`, but ionic convergence not reached |
| Li/C49 relaxation | `qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260930a_cloud_segment1.in` | Cloud segment; final outcome requires retrieval and strict audit |
| Li/C49 restart | `qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20261001a_cloud_segment2_restart.in` | Conditional continuation; final outcome requires retrieval and strict audit |
| Na/C49 pilot | `qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261001a_cloud_pilot.in` | Prepared fixed-geometry pilot; no accepted relaxation |

All periodic production inputs use PBE, DFT-D3(BJ), 2D isolation, 65/520 Ry,
an unshifted 6x6x1 mesh, Marzari-Vanderbilt smearing at 0.01 Ry, and CG
diagonalization. The isolated-atom references use the separately documented
spin-polarized Gamma-only Martyna-Tuckerman setup.
