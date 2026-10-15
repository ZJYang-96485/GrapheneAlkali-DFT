# Three-day completion plan: October 12-15, 2026

The October 16 submission is time-boxed to the four primary neutral-adatom
systems: Li/C50, Na/C50, Li/C49, and Na/C49. Li/C50, Na/C50, and Li/C49 are
strictly converged at the validated 6x6x1 relaxation settings; Na/C49 is the
only missing primary geometry. The isolated neutral Li and Na references are
also accepted. Diffusion, DOS/PDOS, competing-site searches, coverages, and
bulk-metal references remain future work.

Execution began at 2026-10-12 00:44 CDT on the 48 GB RunPod GPU. The guarded
QE stop request is 2026-10-12 23:44 CDT and the full workflow deadline is
2026-10-13 00:44 CDT. At $1.29 per hour, the 24-hour compute ceiling is $30.96;
an earlier strict convergence result ends the scientific workflow sooner.

## Day 1: October 12-13 — complete or checkpoint Na/C49

- Run a fresh fixed-geometry Na/C49 GPU pilot using the documented
  vacancy-centred starting site, then automatically start one fixed-cell BFGS
  relaxation only if the pilot passes strict GPU, SCF, energy, force, and
  `JOB DONE` gates.
- Keep PBE+D3(BJ), 65/520 Ry, 6x6x1, 0.01 Ry MV smearing, spin polarization,
  2D isolation, CG diagonalization, and the approved C/C1/Na pseudopotentials.
- Use a guarded 24-hour RunPod window. Do not stop for a memory-percentage
  threshold on the 48 GB GPU. Stop only for strict convergence, a fatal QE
  failure, or the clean wall-time checkpoint boundary.
- Preserve raw outputs, telemetry, strict parser results, the QE checkpoint,
  and a checksum-verified results bundle on the persistent volume.

## Day 2: October 13-14 — close the four-system data set

- If Na/C49 is incomplete but healthy, continue only that checkpoint until it
  converges; do not restart its geometry from scratch.
- If it converged, audit all four adsorption relaxations uniformly: GPU marker,
  every SCF cycle, BFGS convergence, final energy and force components,
  magnetization, `JOB DONE`, final coordinates, adsorption height, and nearest
  C-metal distances.
- Compute the internally consistent 6x6x1 adsorption energies using
  `E_ads = E(C_n+M) - E(C_n) - E(M_atom)`, with more negative values denoting
  stronger binding. Use only matched PBE+D3(BJ), 65/520 Ry, 6x6x1, and 0.01 Ry
  periodic energies. Do not mix in 9x9x1 or 0.005 Ry values.
- Freeze the four-row primary data table. Any missing or failed case is stated
  explicitly rather than replaced by an unconverged value.

## Day 3: October 14-15 — analysis and submission package

- Prioritize the methods section, provenance/checksum table, convergence table,
  four-system comparison, adsorption-energy table, structure figures, and
  limitations before launching optional calculations.
- Run matched 9x9x1, 0.005 Ry fixed-geometry SCFs only if all six periodic
  inputs (bare C50/C49 plus four adsorbed cells) can finish as one internally
  consistent set. Otherwise retain the defensible 6x6x1 results and label the
  dense final-SCF study as future work.
- Correct or omit the known historical wall-time parser anomaly, update the
  repository summaries, run validation tests, and commit only curated inputs,
  compact results, structures, plots, and documentation. Exclude scratch,
  wavefunctions, telemetry, and large bundles from GitHub.
- Leave October 15-16 as a submission buffer; do not begin NEB, DOS/PDOS,
  alternative-site, or multi-day calculations.

## Acceptance rule

A periodic calculation is a scientific result only when GPU acceleration is
active, every reported electronic cycle converges, the required ionic or SCF
convergence marker appears, final energy and forces are present, and `JOB DONE`
is printed. The literature references and scope limitations remain those in
`docs/codex_prompts/oct16_2026_final_project_scope.md`.
