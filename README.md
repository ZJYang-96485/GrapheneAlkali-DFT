# GrapheneAlkali-DFT

First-principles study of Li and Na adsorption and diffusion on pristine and
vacancy-defective graphene using Quantum ESPRESSO.

## Current stage: validated bare-substrate calculations

This repository contains the convergence study and fixed-cell substrate
workflow for validated 5 x 5 graphene models:

- pristine graphene: C50, `nspin = 1`;
- monovacancy graphene: C49, `nspin = 2`, with a local initial spin seed on
  the three vacancy-adjacent carbon atoms.

The pristine C50 relaxation is complete. Its ideal starting geometry already
satisfied the force criterion, so BFGS converged without an ionic displacement.
The approved C49 monovacancy relaxation also completed: its seeded geometry
converged after 20 electronic cycles and 19 BFGS steps, with GPU acceleration,
final energy, and `JOB DONE` verified against the raw output. The lattice and
18 angstrom out-of-plane cell dimension remain fixed. No Li or Na atoms are
present in the completed bare-substrate calculations.

For the October 16, 2026 final-project deadline, the time-boxed target is a
four-system Li/Na single-atom adsorption comparison on C50 and C49. Diffusion
barriers and broad electronic/coverage studies are deferred. The executable
scope and fallback gates are in
`docs/codex_prompts/oct16_2026_final_project_scope.md`; the course rubric
must be checked before treating this scope as sufficient.

## Locked methodology

- Quantum ESPRESSO 7.x `pw.x`
- PBE exchange-correlation with DFT-D3 Becke-Johnson damping
- SSSP Efficiency PBE pseudopotentials
- 65 Ry wavefunction and 520 Ry charge-density cutoffs, supported against the
  70/560 Ry reference at the approximately 1 meV/C criterion
- Marzari-Vanderbilt smearing: 0.01 Ry for relaxation and 0.005 Ry for final SCF
- k-point meshes: 6 x 6 x 1 relaxation, 9 x 9 x 1 final SCF, 12 x 12 x 1 DOS/PDOS
- `conv_thr = 1.0d-8`, `forc_conv_thr = 4.0d-4`, `mixing_beta = 0.3`
- conjugate-gradient electronic diagonalization
- 2D Coulomb isolation and fixed-cell BFGS ionic relaxation
- GPU-only execution target: one NVIDIA GPU through WSL2 Ubuntu
- `nbnd` left unset so QE selects it automatically

The convergence results support 6 x 6 x 1 for relaxation and 9 x 9 x 1 for a
later final SCF; 12 x 12 x 1 is retained as the dense reference and future
DOS/PDOS mesh. See `results/convergence/pristine/summary.md` and the figures
under `figures/convergence/`.

## Prepare and validate

From the repository root:

```bash
python -m pip install -r requirements.txt
python scripts/validate_structures.py
python scripts/generate_qe_inputs.py
python scripts/validate_qe_inputs.py
python scripts/check_pseudopotentials.py
bash scripts/check_gpu_qe.sh
```

The carbon pseudopotential must be installed before either current relaxation
can run. Li and Na pseudopotentials are checked but are not required yet. See
`pseudopotentials/README.md` and `docs/GPU_SETUP.md`.

After manually confirming that `pw.x` is a CUDA-enabled build, a pristine
relaxation can be reproduced with:

```bash
QE_GPU_CONFIRMED=1 OMP_NUM_THREADS=4 bash scripts/run_relax_gpu.sh qe_inputs/relaxation/pristine/relax_pristine.in
```

The runner deliberately launches one `pw.x` process and has no CPU fallback.
Monitor `nvidia-smi` during a small test and verify that QE output reports GPU
acceleration before treating the build as production-ready.

Completed output can be summarized with:

```bash
python scripts/parse_qe_output.py \
  results/relaxation/pristine/relax_pristine_65_520_cg_20260916.out \
  --calculation relax
```

The monovacancy symmetry pre-flight and approved seed are recorded in
`results/phase4/monovacancy_symmetry_preflight.md`. Its completed raw output
and relaxed structure are under `results/relaxation/monovacancy/` and
`structures/relaxed/monovacancy/` locally; they are not yet committed. For
safe long-running jobs, see `docs/OVERNIGHT_WORKFLOW.md`.

## GitHub contents

Source files, audited inputs, small raw outputs, numerical summaries, plots,
and relaxed structures are intended for version control. QE scratch data,
pseudopotential binaries, machine telemetry, and local exploratory artifacts
are intentionally ignored. See `docs/GITHUB_CONTENTS.md` for the complete
policy.

## Remaining stages

- Before October 16: audit Li/Na pseudopotentials and adsorption methodology;
  compare one Li or Na atom on pristine C50 and reconstructed C49 at a small
  set of documented sites; compute internally consistent adsorption energies.
- If the four primary relaxations finish in time: perform matched 9 x 9 x 1
  final-SCF calculations after a resource preflight.
- After the deadline: wider site/coverage and spin-state searches, 12 x 12 x 1
  DOS/PDOS, and validated 7-image CI-NEB diffusion calculations.

No adsorption, final-SCF, DOS/PDOS, or NEB calculation has been launched.
