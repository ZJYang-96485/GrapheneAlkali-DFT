# October 16, 2026 final-project scope: Li/Na single-atom adsorption

This is a time-boxed execution prompt, not authorization to launch a calculation.
The October 16 deadline is assumed to be in 2026. The course grading rubric has
not been supplied; check it before treating this scope as sufficient for the
assignment. The earlier Phase 4 prompt is a historical record, not the current
instruction for what to run next.

## Scientific question and minimum result

How do Li and Na single-atom adsorption geometries and energies differ between
pristine 5x5 graphene (C50) and reconstructed monovacancy graphene (C49)?
Target four one-adatom systems: Li/C50, Na/C50, Li/C49, and Na/C49. Use the
accepted bare-substrate structures and keep one neutral adatom per cell, a
fixed 18 angstrom out-of-plane cell, PBE+D3(BJ), 2D isolation, and the
validated carbon methodology unless a documented input audit requires a
change. Do not infer that an untested adsorption site or spin state is the
ground state.

The minimum defensible report contains: the four tested geometries if they
finish, matched-reference adsorption energies in eV, adsorption heights and
relevant nearest-neighbor distances, total magnetizations, input and
pseudopotential provenance, convergence/`JOB DONE` evidence, a compact
Li-versus-Na and pristine-versus-vacancy comparison, and explicit limitations.
If fewer than four systems finish, report only the validated subset; do not
fabricate the missing comparison.

## What to study before the deadline

1. Audit the completed C49 relaxation against its raw output. It has GPU
   acceleration, 20 converged electronic cycles, 19 BFGS steps, final energy
   `-903.5017587298 Ry`, ionic convergence, and `JOB DONE`. Its saved relaxed
   structure is a starting geometry, not proof that all magnetic or structural
   minima were found. Correct the parser's nonsensical `3.6e+22 s` timing
   field or exclude that field from reported tables; QE reports `1d19h 5m`
   wall time. Preserve the raw output unchanged.
2. Obtain Li and Na pseudopotentials from a documented PBE-compatible source,
   record source/version/checksums and valence metadata, and check their
   recommended cutoffs. C, Li, and Na files are now installed and checksum-
   audited, but the 65/520 Ry convergence study was on bare C50 and does not
   by itself prove convergence for C+Li or C+Na. A fixed Li/C50 65/520 Ry,
   4x4x1 SCF passed, while its planned 70/560 Ry partner was skipped at a GPU
   memory gate; the adsorbate cutoff comparison is still incomplete. Perform
   separately documented adsorbate cutoff and k-point checks before claiming
   quantitative adsorption-energy accuracy.
3. Preselect and document a small set of physically distinct starting sites
   from primary literature and the actual relaxed C49 geometry. Prioritize a
   pristine hollow site and a vacancy-centered site for each metal. If time
   permits, test at least one competing pristine site and one off-center or
   nearby-vacancy site per metal. These are starting hypotheses, not assumed
   answers; different initial sites that relax to the same minimum should be
   identified as such. Record starting height and geometry.
4. Run controlled, monitored relaxations in fresh prefixes/outdirs. Audit
   pseudopotential mapping, species labels (especially D3-safe `C1`), cell,
   coordinates, k mesh, cutoff, smearing, spin seeds, and all other physical
   settings before launch. Preserve the accepted C49 magnetic setup; do not
   force adatom-containing cells to be nonmagnetic without a spin check.
   Accept a result only with active GPU, electronic and ionic convergence,
   final energy/forces, and `JOB DONE`. Preserve incomplete or failed runs as
   diagnostics, never as scientific data.
5. Define the energy reference and sign convention *before* comparing
   results. For a neutral isolated-atom reference, use
   `E_ads = E(C_n+M) - E(C_n) - E(M_atom)`, where `n=50` or `49` and `M=Li` or
   `Na`; more negative means stronger adsorption relative to that reference.
   Compute spin-appropriate isolated atoms and matched bare-substrate and
   adsorbed-cell energies with compatible pseudopotentials and functional.
   For each periodic bare/adsorbed pair, never mix 6x6 relaxation energies
   with 9x9 final-SCF energies, or 0.01 Ry with 0.005 Ry smearing, inside one
   energy difference. Specify and justify the isolated-atom occupation and
   spin treatment separately. An isolated-atom reference alone does not
   establish stability against bulk-metal plating.
6. If the four primary relaxations and references finish early, perform
   matched 9x9x1 final SCFs (and the required bare-substrate references)
   using the project's planned final-SCF settings, after a memory and
   convergence preflight. Otherwise present a clearly labeled, internally
   consistent 6x6x1 result and state that denser final-SCF validation is
   pending. Do not silently change numerical settings to save time.
7. Prepare a reproducible final report with a four-row results table, input
   and output links, convergence/quality checks, two or three structure and
   comparison figures, literature context, and an honest limitations section.
   Keep raw outputs, pseudopotential binaries, and WSL scratch under their
   established GitHub content policy.

## Time gates and fallback

- By September 23: verify the grading rubric, Li/Na pseudopotentials, first
  adsorption inputs, energy reference, and resource budget before production.
- By October 4: aim to complete the four primary site relaxations. If this
  slips, drop competing sites first, not pseudopotential/input validation.
- By October 10: freeze the data set for final comparisons; run denser SCFs
  only if all matched references and resource checks can finish in time.
- October 11-16: prioritize analysis, figures, methods, limitations, and final
  submission. Do not start a multi-day run that risks leaving the report
  unfinished. Mark missing results as future work.

These dates are planning gates, not permission to accept an unconverged result.
The single-GPU C49 relaxation took about 43 hours, so leave substantial
contingency for slow adsorbate relaxations and host problems.

## Not in the October 16 scope

- Seven-image CI-NEB diffusion paths or any claimed migration barrier.
- Full DOS/PDOS or band structures, unless the course rubric explicitly
  requires one and the four-system adsorption comparison is already secure.
- Exhaustive adsorption-site mapping, multiple adatoms/coverages, clusters,
  vacancy formation energies, other defects, multilayers, phonons, voltage,
  capacity, or cycle-life predictions.
- Claims about charge transfer, ground-state spin, or thermodynamic stability
  against bulk Li/Na without the additional calculations needed to support
  them.

After October 16, separately revisit alternative vacancy spin/geometry
states, a larger site and coverage survey, matched dense SCFs, DOS/PDOS,
bulk-metal references, and validated NEB diffusion paths. The current QE
installation has no `~/q-e/bin/neb.x`; NEB setup and execution are separate
future work. Quantum ESPRESSO notes that NEB cost scales approximately as
single-SCF time times image count times path iterations, so it is not a safe
last-minute addition.

## Literature checkpoints

- Before fixing candidate sites or interpreting adsorption energies, consult
  a primary Li/Na graphene adsorption study, e.g. Dimakis et al., *Molecules*
  **24**, 754 (2019), DOI: https://doi.org/10.3390/molecules24040754.
- For any future NEB stage, use the official Quantum ESPRESSO guide:
  https://www.quantum-espresso.org/Doc/neb_user_guide/node8.html.
- Use literature to motivate candidate sites and comparisons, not to copy
  energies or conclude that the local 5x5/PBE-D3(BJ) calculations are
  converged. If the rubric requires excluded work, flag the conflict and
  revise scope with the user before launching it.

## References used for the first neutral-Li run

- N. Dimakis *et al.*, "Li and Na Adsorption on Graphene and Graphene Oxide
  Examined by Density Functional Theory, Quantum Theory of Atoms in Molecules,
  and Electron Localization Function," *Molecules* **24**, 754 (2019),
  https://doi.org/10.3390/molecules24040754. Context for comparing pristine
  and vacancy graphene and for defining an isolated-neutral-atom adsorption
  energy; its numerical values are not substituted for local calculations.
- W. Wan and H. Wang, "First-Principles Investigation of Adsorption and
  Diffusion of Ions on Pristine, Defective and B-doped Graphene," *Materials*
  **8**, 6163-6178 (2015), https://doi.org/10.3390/ma8095297. Supports the
  pristine hollow-site candidate and the 2.5-angstrom initial Na height; this
  is only a starting seed, not a substitute for the local relaxation.
- M. Jin *et al.*, "Enhanced Absorption and Diffusion Properties of Lithium
  on B,N,V_C-decorated Graphene," *Scientific Reports* **6**, 37911 (2016),
  https://doi.org/10.1038/srep37911. Motivates a pristine hollow-site starting
  geometry; it does not establish the minimum for this PBE-D3(BJ) cell.
- Quantum ESPRESSO, `pw.x` input description,
  https://www.quantum-espresso.org/Doc/INPUT_PW.html. Definitions of
  `tot_charge`, `assume_isolated = '2D'`, spin initialization, D3 options,
  and relaxation settings. The first Li cell is neutral overall.
- Materials Cloud, SSSP 1.0 PBE efficiency archive and metadata,
  https://archive.materialscloud.org/records/1dygy-1xb93. Source for the
  approved C, Li, and Na pseudopotential filenames, MD5 hashes, and
  recommended cutoffs. The Li UPF MD5 is
  `e912e257baa3777c20ea3d68f190483c`; the Na UPF MD5 is
  `44600605ef58000f06b90626533354dc`. The local Na file was verified
  against the archive and has not yet been used in a QE calculation.
