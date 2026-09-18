# Pristine C50 production relaxation

## Status

Accepted. The fixed-cell QE 7.6 relaxation completed with GPU acceleration active,
electronic and ionic convergence, exit status 0, and `JOB DONE`.

## Locked method

- Structure: pristine C50 graphene, fixed 18 angstrom cell
- Functional/dispersion: PBE + DFT-D3(BJ), including the D3 three-body term
- Carbon pseudopotential: `C.pbe-n-kjpaw_psl.1.0.0.UPF`, MD5
  `8e281b34a927efac7e739263a90d7aed`
- Slab treatment: `assume_isolated = '2D'`
- Cutoffs: 65/520 Ry
- K points: 6x6x1, shift 0 0 0
- Occupations: Marzari-Vanderbilt smearing, `degauss = 0.01 Ry`
- Electronic settings: `conv_thr = 1.0d-8 Ry`, `mixing_beta = 0.3`,
  `diagonalization = 'cg'`, `nspin = 1`
- Ionic settings: fixed-cell `calculation = 'relax'`, BFGS,
  `forc_conv_thr = 4.0d-4 Ry/Bohr`

## Result

- Final energy: `-922.5216662254 Ry`
- Electronic convergence: 11 iterations; final estimated error `7.3e-9 Ry`
- Ionic convergence: 1 SCF cycle and 0 BFGS displacement steps
- Total force: `7.0e-6 Ry/Bohr`
- Maximum reported force component: `2.07e-6 Ry/Bohr`
- SCF force correction: `3.0e-6 Ry/Bohr`
- QE wall time: 948.78 s (15m48.78s)
- The 11 electronic total-energy estimates were monotonically non-increasing.

The ideal starting sheet was already within the force criterion, so zero BFGS
displacement steps is a valid converged result. All 50 final coordinates match the
source coordinates exactly at the printed precision; the maximum difference is
`0 angstrom`. The cell remained fixed because this was `relax`, not `vc-relax`.

QE printed `SCF correction compared to forces is large` because the physical
residual forces are exceptionally small. The correction is nevertheless more than
100 times below the approved force threshold, and the largest force component is
about 193 times below it. QE's official input documentation defines BFGS force
convergence by requiring every force component to be smaller than
`forc_conv_thr`: <https://www.quantum-espresso.org/Doc/INPUT_PW.html>.

## Execution evidence

- CUDA QE executable: `/home/joe_yang/q-e/bin/pw.x`
- Isolated prefix: `graphene_pristine_relax_65_520_cg`
- Isolated scratch: `qe_scratch/relaxation/pristine_65_520_cg_20260916`
- Input SHA-256: `16597a86cd4c75642480c5bacf0db85da8216ca2f161df6d7e94305256fe25b8`
- Original structure SHA-256 remained
  `5fd901b075b51c91125c8c1001c4268a585ae5a885f5ff240ece19ac4a7251a8`
- Maximum process RSS: 6,293,456 KiB; process swaps: 0
- WSL free memory never fell below 8,290,888 KiB; `swpd` stayed at the
  pre-existing 268 KiB
- Peak GPU memory: 15,858/16,303 MiB; peak temperature: 69 C; peak power:
  120.90 W
- WSL boot ID was unchanged:
  `42be07e2-6985-4950-b84c-542932d06ab7`
- No WSL kernel OOM, GPU Xid, CUDA, filesystem, or crash event was observed.
- Windows logged one corrected WHEA PCIe endpoint warning during the run for
  `PCI\\VEN_8086&DEV_272B` (the Intel wireless endpoint identified in the earlier
  stabilization report). It did not terminate or alter the QE/WSL run. This is
  recorded as a host-maintenance observation, not assigned as a QE root cause.

## Artifacts

- QE input: `qe_inputs/relaxation/pristine/relax_pristine.in`
- Raw output: `results/relaxation/pristine/relax_pristine_65_520_cg_20260916.out`
- Resource logs: `results/phase4/diagnostics/pristine_relax_65_520_cg_20260916_*`
- Relaxed ASE structure: `structures/relaxed/pristine/graphene_5x5_pristine_relaxed.traj`
- Relaxed XYZ structure: `structures/relaxed/pristine/graphene_5x5_pristine_relaxed.xyz`

The relaxed artifacts are exact copies of the original formats because QE converged
without moving any atom. The original structure files were not overwritten. No
final 9x9x1 SCF, monovacancy relaxation, adsorption, DOS/PDOS, band, or NEB run was
started.
