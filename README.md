# GrapheneAlkali-DFT

First-principles study of Li and Na adsorption and diffusion on pristine and
vacancy-defective graphene using Quantum ESPRESSO.

## Current stage: bare-substrate relaxation

This stage prepares fixed-cell `relax` calculations for the validated 5 x 5
graphene substrates:

- pristine graphene: C50, `nspin = 1`;
- monovacancy graphene: C49, `nspin = 2`, with a local initial spin seed on
  the three vacancy-adjacent carbon atoms.

The lattice and 18 angstrom out-of-plane cell dimension remain fixed. No Li or
Na atoms are present at this stage.

## Locked methodology

- Quantum ESPRESSO 7.x `pw.x`
- PBE exchange-correlation with DFT-D3 Becke-Johnson damping
- SSSP Efficiency PBE pseudopotentials
- 50 Ry wavefunction and 400 Ry charge-density cutoffs
- Marzari-Vanderbilt smearing: 0.01 Ry for relaxation and 0.005 Ry for final SCF
- k-point meshes: 6 x 6 x 1 relaxation, 9 x 9 x 1 final SCF, 12 x 12 x 1 DOS/PDOS
- `conv_thr = 1.0d-8`, `forc_conv_thr = 4.0d-4`, `mixing_beta = 0.3`
- 2D Coulomb isolation and fixed-cell BFGS ionic relaxation
- GPU-only execution target: one NVIDIA GPU through WSL2 Ubuntu
- `nbnd` left unset so QE selects it automatically

The 9 x 9 x 1 final-SCF and 12 x 12 x 1 DOS/PDOS settings are recorded for
later stages; this milestone generates only relaxation inputs.

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

After manually confirming that `pw.x` is a CUDA-enabled build, run pristine
graphene first:

```bash
QE_GPU_CONFIRMED=1 OMP_NUM_THREADS=4 bash scripts/run_relax_gpu.sh qe_inputs/relaxation/pristine/relax_pristine.in
```

The runner deliberately launches one `pw.x` process and has no CPU fallback.
Monitor `nvidia-smi` during a small test and verify that QE output reports GPU
acceleration before treating the build as production-ready.

Completed output can be summarized with:

```bash
python scripts/parse_qe_output.py qe_inputs/relaxation/pristine/relax_pristine.out
```

## Future stages (not yet completed)

- Li and Na adsorption structures and relaxations
- 9 x 9 x 1 final-SCF energies
- 12 x 12 x 1 DOS/PDOS calculations
- 7-image CI-NEB diffusion with 6 x 6 x 1 path optimization and 9 x 9 x 1
  single-point energies on converged images

No adsorption, final-SCF, DOS/PDOS, or NEB input is generated in this phase.
