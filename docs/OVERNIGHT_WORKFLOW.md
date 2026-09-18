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

First audit the final vacancy reconstruction, forces, energy, magnetization, and
resource logs, then finish the Phase 4 report and GitHub cleanup. Stop there for
review. Li/Na adsorption structures or calculations require a separately approved,
literature-supported Phase 5 plan.
