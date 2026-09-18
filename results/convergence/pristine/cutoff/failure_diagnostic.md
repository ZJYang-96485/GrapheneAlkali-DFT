# Cutoff-stage execution failure diagnostic

## Completed points

| Ecutwfc/Ecutrho (Ry) | Final energy (Ry) | Final energy (eV) | Energy per C (eV) | SCF iterations | Wall time (s) | GPU active | JOB DONE |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 40/320 | -922.48885213 | -12551.10023146 | -251.02200463 | 10 | 151.52 | yes | yes |
| 45/360 | -922.50403227 | -12551.30676779 | -251.02613536 | 11 | 171.78 | yes | yes |

The energy lowering from 40/320 to 45/360 is 4.1307 meV per carbon atom. This is not a convergence decision because the required 55/440 reference did not run.

## Reproducible 50/400 failure

The 50/400 calculation was attempted three times from empty, isolated scratch directories. All three raw outputs are preserved:

- `ecutwfc_50_ecutrho_400.interrupted_wsl_exit1_20260914T003038.out`
- `ecutwfc_50_ecutrho_400.retry1_interrupted_terminal_exit1_20260914T003638.out`
- `ecutwfc_50_ecutrho_400.retry2_reproducible_wsl_shutdown_20260914T004203.out`

Each attempt followed the same deterministic SCF sequence. Iteration 12 printed an estimated SCF accuracy below `1.0d-8 Ry` and the intermediate energy `-922.50748272 Ry`. The output then printed the iteration-13 header and stopped abruptly. No attempt printed a final exclamation-mark total energy, electronic-convergence confirmation, timing footer, or `JOB DONE`. Therefore the intermediate energy is not accepted as a calculation result.

At each failure, the enclosing `wsl.exe` terminated with exit code 1 and Ubuntu restarted. The restarted kernel journal reported an unclean shutdown. Searches found no QE `CRASH` file and no contemporaneous Windows System/Application error from WSL, Hyper-V, NVIDIA, WHEA, or Display. After restart, the GPU, filesystem, RAM, and swap were available normally. These observations do not establish a root cause, but the exact iteration-level reproducibility makes a transient terminal timeout unlikely.

## Stop decision

At this point in the investigation, the 55/440 cutoff point, k-point sweep, smearing sweep, and all production relaxations had not started. This followed the Phase 4 policy requiring a stop for an incomplete output or missing `JOB DONE`.

## Proposed diagnostic requiring approval

Create one separately labeled 50/400 diagnostic input that changes only the electronic diagonalization algorithm from QE's default Davidson method to:

```text
diagonalization = 'cg'
```

The diagnostic would retain PBE, DFT-D3(BJ), the approved carbon PAW, 50/400 Ry, 6x6x1, 0.01 Ry MV smearing, `conv_thr = 1.0d-8`, `mixing_beta = 0.3`, the fixed C50 geometry, and a new prefix/outdir. It would not be treated as convergence data unless it completes with GPU active, electronic convergence, and `JOB DONE`. No CPU fallback, MPI change, physical-method change, or infrastructure rebuild is proposed.

## Approved diagnostic result

The user approved the one-point CG diagnostic. It completed successfully with:

- final converged total energy: `-922.50748258 Ry`;
- SCF iterations: 11;
- wall time: 681.77 s;
- smearing contribution: `-0.00036458 Ry`;
- Fermi energy: `-4.2001 eV`;
- GPU acceleration active: yes;
- electronic convergence achieved: yes;
- `JOB DONE`: yes.

The CG final energy differs from the final intermediate Davidson estimate before the repeated shutdowns by only `0.0000381 meV/C`, supporting that both solvers approached the same SCF solution. The CG result is numerically valid, but applying CG to the 55/440 reference or production calculations remains a documented workflow decision because it is substantially slower than Davidson on this system.

The user subsequently approved one 55/440 CG reference. Its launch caused another unclean WSL restart before QE flushed a banner, leaving a zero-byte raw output and no scratch files. See `results/convergence/pristine/cutoff_reference/failure_diagnostic.md`. No 50/400-to-55/440 comparison is possible.
