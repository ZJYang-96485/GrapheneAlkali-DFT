# Phase 5 Li/C49 lower-memory recovery plan

Prepared September 23, 2026. This document plans one calculation; it does not
authorize or launch it.

## Evidence behind the change

The two neutral-Li/C49 fixed-geometry pilots at 65/520 Ry and 6x6x1 are
scientifically reproducible. Both converged in 18 SCF iterations to
`-918.02816369 Ry`, total magnetization `1.01` Bohr magnetons per cell, total
force `0.073052 Ry/bohr`, and `JOB DONE`. Their largest force-component
difference is only `1.8e-7 Ry/bohr`.

They are not operationally safe for a multi-step relaxation. The first pilot
peaked at 93.89% GPU memory and logged a WSL `dxgkio_make_resident -12` error.
After a clean Windows restart, the explicit `disk_io='medium'` repeat reduced
maximum process RSS from 15,380,380 to 4,379,544 KiB, but GPU usage rose to
97.65% (15,920/16,303 MiB), the residency error recurred, and Windows recorded
a new `LiveKernelEvent 141` watchdog dump. Therefore, `disk_io` solves the
host-RAM component but not the GPU-residency risk.

The validated pristine-C50 data show peak GPU memory of 11,249 MiB at 65/520,
10,370 MiB at 60/480, and 9,212 MiB at 55/440. Extrapolating these reductions
to Li/C49 is only an inference, but 60/480 may not provide enough margin below
the predeclared 90% gate; 55/440 is the first tested setting with a materially
smaller FFT grid and approximately 2 GiB lower pristine-GPU peak than 65/520.

## Next run: one fixed-geometry 55/440 pilot

Run one GPU-only SCF using the exact accepted Li/C49 starting geometry and the
same settings as the converged 65/520 pilot, except:

- `ecutwfc = 55 Ry`
- `ecutrho = 440 Ry`
- `disk_io = 'medium'`
- fresh prefix, scratch, output, status, and persistent resource logs

Retain PBE, DFT-D3(BJ), the approved C and Li pseudopotentials, neutral charge,
the existing spin seeds, `assume_isolated='2D'`, 6x6x1 unshifted k points,
Marzari-Vanderbilt smearing at 0.01 Ry, `conv_thr=1.0d-8`, `mixing_beta=0.3`,
CG diagonalization, and the CUDA-enabled `pw.x`. Do not launch a relaxation or
another cutoff automatically.

Expected wall time is roughly 1.5 to 2 hours. The supervisor should request a
clean stop if GPU allocation remains at or above 95% in three consecutive
samples or if the 2.5-hour wall limit is reached.

## Acceptance gates

The pilot passes the scientific gate only with active GPU acceleration, no
failed electronic cycle, full SCF convergence, final energy and forces,
magnetization, and `JOB DONE`.

The 55/440 force field is provisionally acceptable for geometry search only if:

- the largest Cartesian force-component difference from the 65/520 result is
  no more than `4.0e-4 Ry/bohr`;
- total magnetization differs by no more than `0.05` Bohr magnetons per cell;
- peak GPU memory stays below 90%; and
- there is no new WSL GPU-residency error, Windows watchdog dump, or unclean
  WSL/Windows restart.

The absolute 55/440 energy difference is recorded but is not an adsorption
energy and cannot establish adsorbate cutoff convergence by itself.

## Conditional continuation

If every gate passes, use 55/440 only for a monitored, segmented Li/C49 ionic
relaxation. The final geometry must later receive a fixed-geometry 65/520 SCF
and force check if the host can safely complete it; matched bare-substrate and
isolated-atom references must use the same final energy settings. If the final
65/520 force exceeds the accepted force threshold, the geometry remains
provisional.

If the resource gate or force comparison fails, do not launch the Li/C49
relaxation locally. Continue with low-risk isolated Li/Na reference jobs and
narrow the deadline report to the validated subset unless safer hardware
becomes available.

This compromise does not overturn the pristine cutoff decision: 65/520 met
the project's approximately 1 meV/C criterion, whereas 55/440 differed from
70/560 by 3.6986 meV/C. The lower cutoff is being tested solely as a geometry
search level necessitated by observed host limits. Quantum ESPRESSO defines
`ecutwfc` as the wavefunction kinetic-energy cutoff, requires cutoff testing
for the charge-density grid, and documents that `disk_io='medium'` moves
multi-k-point wavefunctions to disk without changing the physical model:
https://www.quantum-espresso.org/Doc/INPUT_PW.html
