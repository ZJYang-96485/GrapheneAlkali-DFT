# Phase 5: 12-hour overnight plan to the October 16 deadline

Plan recorded September 19, 2026 (America/Chicago). This schedule is a target,
not a claim that any individual calculation will converge in 12 hours. The
scientific target is one neutral Li or Na atom on each of pristine C50 and
reconstructed-monovacancy C49 graphene. The minimum acceptable submission is
the **validated subset actually completed** by the data freeze, with missing
cases and uncertainty stated explicitly; no unfinished output becomes a result.

The first Li/C50 window, `li_c50_hollow_20260919b_12h`, is now accepted:
GPU acceleration, all six electronic cycles, ionic convergence, final energy
and forces, and `JOB DONE` were checked. Its status is
`results/phase5/diagnostics/li_c50_hollow_20260919b_12h/status.json`.
The earlier Li run's unclean scratch was preserved but not used as a QE restart.

September 20 update: use the released Li/C50 continuation time for the
Li-containing numerical check `li_c50_fixed_validation_20260920a`. It holds
the accepted Li/C50 geometry fixed and runs a 65/520 Ry, 4x4x1 SCF, then a
70/560 Ry, 4x4x1 SCF only if the first has GPU acceleration, complete
electronic convergence, final energy, and `JOB DONE`, finishes within six
hours, and peaks below 88% GPU memory. Both inputs were audited before launch;
each has its own prefix, scratch, output, and resource logs. Status is at
`results/phase5/diagnostics/li_c50_fixed_validation_20260920a/status.json`.
This paired calculation measures **cutoff sensitivity at 4x4x1 only**. It
neither proves 65/520 Ry convergence at 6x6x1 nor substitutes for the planned
Li-containing k-point check or matched adsorption-energy references. Do not
promote the 4x4x1 energies to production adsorption energies. Review the
completed pair and Windows graphics diagnostics before assigning another GPU
window; the Na pseudopotential audit was completed during the subsequent
offline host pause, but no Na calculation has been run.

September 20 host gate: the 65/520 Ry, 4x4x1 SCF converged and printed
`JOB DONE`, but peaked at 93.76% GPU memory. The planned 70/560 Ry follow-up
was automatically skipped at the 88% gate. Four distinct Windows
`LiveKernelEvent 141` WATCHDOG dumps are timestamped within the final five
minutes of the SCF. A WSL `dxgkio_make_resident` `-12` warning coincided with
a jump from 12,220 to 15,211 MiB logged GPU memory at 15:54:30-31; WSL free
memory was still about 7 GiB with no process swaps. These observations raise
a GPU-residency concern, but their causal relationship to QE is unresolved. The GPU
queue is therefore **paused** under the repeated-timeout rule below; offline
provenance, structure, input, and report work can proceed. Do not count this
single SCF as a completed cutoff comparison. Local evidence is summarized in
`results/phase5/diagnostics/li_c50_fixed_validation_20260920a/host_review_20260920.md`.

Offline progress during the pause: the exact SSSP 1.0 PBE efficiency Na UPF
was obtained and verified (MD5 `44600605ef58000f06b90626533354dc`, PBE,
ultrasoft, nine valence electrons). A neutral Li/C49 vacancy-centred pilot
and relaxation proposal was generated from the accepted reconstructed C49
geometry at `qe_inputs/adsorption/li_monovacancy/`; it preserves the approved
`C1` carbon mapping and spin seeds. Neither proposed QE input has been run.
The vacancy-centred position is an initial hypothesis, not an established
ground state; its geometry and limitations are in
`docs/PHASE5_LI_C49_SITE_PROPOSAL.md`. Resume the GPU queue only after a
separate host/resource review.

September 23 recovery decision: two Li/C49 65/520 Ry fixed-geometry pilots
converged to identical energy, forces, and magnetization, but both produced a
WSL GPU-residency error. The clean-restart `disk_io='medium'` repeat peaked at
97.65% GPU memory and was followed by a newly named Windows
`LiveKernelEvent 141` watchdog dump. No 65/520 Li/C49 relaxation is approved.
The next proposed run is one 55/440 Ry, 6x6x1 fixed-geometry force/resource
comparison under the strict gates in `docs/PHASE5_LI_C49_55RY_RECOVERY_PLAN.md`.
It is a proposed geometry-search compromise, not a revised final-energy cutoff
or an adsorbate convergence claim, and no relaxation may start automatically.

September 23 late update: the Li/C49 55/440 Ry pilot passed its electronic,
force-field, and magnetization checks, but peaked at 96.39% GPU memory and
therefore failed the predeclared resource gate. No local Li/C49 relaxation is
approved. The schedule moved forward the low-risk neutral isolated-Li
reference work that was originally reserved for the reference window. A first
18 Angstrom point was cleanly stopped before convergence at its 80% GPU gate.
The subsequently predeclared cost-aware 12-to-14-to-16 Angstrom sequence used
the unchanged 65/520 Ry, PBE+D3(BJ), spin-doublet, fixed-occupation,
Martyna-Tuckerman, Gamma-only method. The 12-to-14 energy change was 2.857604
meV, requiring 16 Angstrom; the 14-to-16 change was 0.307897 meV, passing the
1 meV stopping rule. The accepted neutral isolated-Li energy is
`-14.35806979 Ry` from the 16 Angstrom cell. This completes only the Li atom
reference: compatible adsorbed and bare-substrate energies are still required
before computing an adsorption energy, and no Na calculation was launched
automatically.

September 23 Na-reference update: after explicit approval, the same
predeclared cost-aware sequence was applied to neutral Na with the verified
nine-valence-electron Na UPF and a fixed `1.0` Bohr-magneton doublet. The
12-to-14 Angstrom energy change was 3.614080 meV, requiring the conditional 16
Angstrom point; the 14-to-16 change was 0.717836 meV, below the 1 meV stopping
threshold. The accepted neutral isolated-Na energy is `-95.26886282 Ry` from
the 16 Angstrom cell. All three Na points passed the GPU, SCF, magnetization,
`JOB DONE`, and host-stability gates; the largest GPU peak was 63.314%. Both
neutral-atom references are now complete, but no adsorption energy can be
reported until compatible adsorbed and bare-substrate energies exist.

September 24 Na/C50 resource-gate update: the first neutral-Na/C50 production
candidate used the literature-motivated central hollow site with Na initially
2.5 angstrom above the accepted C50 plane and retained the locked 65/520 Ry,
6x6x1, PBE-D3(BJ), spin-polarized methodology. During initialization the fixed
geometry pilot reached 15,894 of 16,303 MiB GPU memory (97.49%), exceeding the
predeclared 90% gate. The supervisor requested a clean QE stop; `JOB DONE` was
printed, no electronic cycle had completed, no process swap or new WSL
`dxgkio_make_resident` error was found, and no new Windows watchdog report or
unexpected-shutdown event appeared. The Na/C50 relaxation was therefore not
launched. This is a resource-gate outcome, not SCF-convergence evidence and not
an adsorption result.

## One overnight window

- Use **one GPU calculation at a time**, with a unique input, prefix, scratch
  directory, raw output, manifest, and persistent RAM/GPU/process logs.
- Plan for approximately 12 hours of wall time. Start a clean stop by about
  10–10.5 hours, leaving 1.5–2 hours for QE to finish and write restart data.
  `max_seconds` is QE CPU time, not a strict wall-clock limit. Do not hard-kill
  an otherwise healthy run at hour 12 merely to meet the schedule.
- Each morning check `pw.x` process state, GPU-active marker, every electronic
  cycle, final energy and forces, ionic-convergence marker, and `JOB DONE`;
  inspect GPU-memory and Windows graphics-error logs. Only all required markers
  permit acceptance of a relaxation.
- If QE stopped cleanly before ionic convergence, continue **only after
  verifying the clean stop** using the same prefix/outdir and QE
  `restart_mode='restart'`. If Windows or WSL crashed, do **not** restart from
  that scratch; start a fresh, documented calculation from the last usable
  printed geometry. Preserve prior raw output and scratch in either case.
- If another full Windows graphics crash occurs, or repeated `0x141` graphics
  timeouts coincide with a run, pause the GPU queue for review. Leaving the
  laptop unused does not remove that observed risk.

QE documents clean stops through `max_seconds` or `prefix.EXIT`, and restricts
`restart_mode='restart'` to properly stopped calculations:
<https://www.quantum-espresso.org/Doc/pw_user_guide/node20.html>.

## Night allocation and morning gate

Dates are local start dates. A case can release unused nights to the next row;
an unfinished case can use the reserved overflow nights, not steal report time.
No later job is automatically launched without its input/resource audit.

| Window | Target work | Morning deliverable / decision |
| --- | --- | --- |
| Sep 19 (night 1) | Active Li/C50 12-hour segment | Accept only if ionic convergence and `JOB DONE`; otherwise classify clean stop versus crash. |
| Sep 20–21 (nights 2–3) | Up to two Li/C50 continuation segments; release spare nights to validation | Final Li/C50 geometry or a clearly documented incomplete state. |
| Sep 22–23 (nights 4–5) | Small Li- and Na-containing cutoff/k-point checks, after Na UPF provenance and checksum audit | Document whether 65/520 Ry and 6×6×1 are adequate for the intended **qualitative** comparison; if not, flag the uncertainty before quantitative claims. |
| Sep 24–26 (nights 6–8) | Li/C49 vacancy-site pilot and relaxation, up to three 12-hour segments | Accepted Li/C49 geometry or a documented continuation decision. |
| Sep 27–28 (nights 9–10) | Na/C50 hollow-site pilot and relaxation, up to two segments | Accepted Na/C50 geometry or a documented continuation decision. |
| Sep 29–Oct 1 (nights 11–13) | Na/C49 vacancy-site pilot and relaxation, up to three segments | Accepted Na/C49 geometry or a documented continuation decision. |
| Oct 2–4 (nights 14–16) | Reserve for whichever primary relaxation is unfinished; otherwise start reference SCFs | By Oct 4, know which of the four primary geometries are realistically attainable. |
| Oct 5–8 (nights 17–20) | Matched bare C50/C49 references, neutral isolated Li/Na references, and any needed 6×6×1 single-point adsorbate energies; continue only essential missing cases | Compute adsorption energies only from compatible, converged references with a declared sign convention. |
| Oct 9–10 (nights 21–22) | Final validation or contingency; freeze the data set by Oct 10 | Lock tables, provenance, uncertainties, and the list of completed systems. No new long relaxation after this gate. |
| Oct 11–15 | No planned production nights | Analyze structures and magnetization, make figures, write methods/results/limitations, verify links and submission package. |
| Oct 16 | Submission | Submit the validated result, even if the four-case target was not fully achieved. |

The implied maximum is about 22 overnight windows before the data freeze,
including three explicit overflow nights. The earlier bare C49 relaxation took
about 43 hours and the interrupted first Li/C50 relaxation ran for about 21
hours, so a 1-night-per-system plan would not be credible. These allocations
are budgets, not predicted convergence times.

## Work that must happen between GPU windows

1. By Sep 23, obtain the course rubric; verify the Na PBE pseudopotential's
   source, checksum, valence, and cutoff guidance. Review the actual relaxed
   C49 geometry and primary Li/Na adsorption literature before fixing its
   candidate vacancy site. Keep the one-adatom cells neutral; do not substitute
   Li+ for neutral Li.
2. Before each new case, audit element labels, pseudopotentials, charge, spin
   seed, cell, 2D isolation, PBE+D3(BJ), 65/520 Ry, 6×6×1 mesh, smearing,
   convergence thresholds, and starting geometry. Do not alter a parameter
   silently to reduce runtime.
3. Define and retain `E_ads = E(C_n+M) - E(C_n) - E(M_atom)` in eV. Use matched
   periodic-cell numerical settings for each bare/adsorbed pair, and a
   separately justified spin/box treatment for each neutral isolated atom.
   More negative means stronger binding relative to isolated atoms, **not**
   proven resistance to bulk-metal plating.
4. After every accepted relaxation, save the final geometry and structure
   metrics, then update one evidence table: GPU active, SCF cycles all
   converged, force, ionic convergence, final energy, `JOB DONE`, peak VRAM,
   input/output hashes, and any host errors.
5. Use 6×6×1 internally consistent energies for the deadline if the denser
   9×9×1 option fails the memory or time gate. A denser calculation is optional
   only after the four primary cases and references are secure; it is not a
   reason to miss the report deadline.
6. Draft the methods, provenance table, and figure templates during daytime
   reviews throughout the schedule; October 11 should not be the first day of
   report writing.

Candidate-site and interpretation checkpoint: N. Dimakis et al., *Molecules*
**24**, 754 (2019), <https://doi.org/10.3390/molecules24040754>. This paper
studies Li/Na on pristine and defective graphene but does not validate this
project's local supercell, spin state, or numerical convergence. The broader
scientific scope and reference list remain in
`docs/codex_prompts/oct16_2026_final_project_scope.md`.

## Outside this deadline

Do not spend these overnight windows on CI-NEB/diffusion, DOS/PDOS, exhaustive
site or spin-state searches, multiple adatoms/coverages, bulk-metal plating
claims, battery voltage/capacity, or phonons unless the course rubric makes one
mandatory and the schedule is explicitly revised. Revisit them after October
16. If hardware instability consumes the reserve, narrow the claim to the
validated subset rather than labeling an unfinished run as a completed result.
