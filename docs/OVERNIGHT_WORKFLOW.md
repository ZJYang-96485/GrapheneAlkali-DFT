# Overnight QE workflow

Long Quantum ESPRESSO calculations should run as one foreground `pw.x` process
inside the monitored runner, with a separate read-only supervisor. The supervisor
updates a compact JSON heartbeat and post-processes a relaxation only after the
strict completion gates pass.

## Safety rules

- Keep Windows connected to AC power.
- The computer may be locked and the display may turn off, but Windows sleep and
  hibernation must remain disabled while QE is running.
- Do not close the lid if the configured lid action suspends the computer.
- Do not launch another QE process, change the input, tune CPU/GPU clocks, restart
  WSL, or run Windows repair/update operations during the calculation.
- The supervisor does not auto-restart an interrupted calculation and does not
  queue a later scientific stage. It preserves the evidence and reports failure.

## Current monovacancy run

The current run was already launched before this supervisor was added. Do not
launch it again. Its compact status can be inspected with:

```bash
cd ~/GrapheneAlkali-DFT
python3 -m json.tool \
  results/phase4/diagnostics/monovacancy_relax_65_520_cg_seed001_c1_20260917_overnight_status.json
```

The raw QE output remains:

```text
results/relaxation/monovacancy/relax_monovacancy_65_520_cg_seed001_c1_20260917.out
```

On successful completion, the supervisor requires GPU activation, every explicit
SCF cycle to have converged, BFGS convergence, a final energy and forces, and
`JOB DONE`. It then creates, without overwriting existing files:

```text
structures/relaxed/monovacancy/graphene_5x5_monovacancy_relaxed.traj
structures/relaxed/monovacancy/graphene_5x5_monovacancy_relaxed.xyz
results/relaxation/monovacancy/final_structure_analysis.json
```

If any gate fails, no relaxed structure is accepted. Review the status JSON, raw
output, and ignored resource logs before deciding whether a restart is safe.

## After the overnight run

For the historical vacancy run, first audit the final reconstruction, forces,
energy, magnetization, and resource logs. Its accepted result is not permission
to launch arbitrary Li/Na jobs; the one separately approved Phase 5 job is
specified below.

## First neutral Li/C50 adsorption run

The first Phase 5 Li run was separately approved. Its source list and scientific
scope are kept in `docs/codex_prompts/oct16_2026_final_project_scope.md`.
`scripts/prepare_li_pristine_hollow.py` records the verified central hollow
geometry, pseudopotential MD5, and both input hashes in a run manifest.
`scripts/run_li_pristine_hollow_overnight.py` runs a fresh fixed-geometry GPU
pilot and starts **one** fixed-cell relaxation only if the strict pilot and
GPU-memory gates pass. No Na or vacancy job is queued. Check a run with:

```bash
cd ~/GrapheneAlkali-DFT
python3 -m json.tool \
  results/phase5/diagnostics/li_c50_hollow_20260919a/status.json
```

The per-second GPU, RAM/swap, and process logs live beside `status.json` and
are ignored by Git. Pilot raw output is diagnostic only. The production raw
relaxation output is under `results/adsorption/li_pristine_hollow/` and must
not be interpreted as an adsorption energy before matched reference and
adsorbate-convergence checks.
