# QE checkpoint, backup, and restart design

Status: design only (2026-09-20). No GPU run is authorized by this document.
The Phase 5 GPU queue remains paused pending the host/resource review in
`docs/PHASE5_12H_OVERNIGHT_PLAN.md`.

## Purpose and limits

Use the same laptop for multiple overnight segments without losing a *cleanly
stopped* QE relaxation. Store an immutable copy on `D:\WSL-Backups`, then
restore it to the WSL filesystem before a later segment. The D: copy is on the
same computer, so it is not protection against loss of the entire computer.
It does not reduce the GPU memory required by the resumed calculation, and it
does not turn an abrupt Windows/WSL crash into a valid QE restart.

The existing `scripts/run_li_pristine_hollow_12h.py` already requests a clean
stop at about 10.5 hours of wall time or high observed GPU-memory use, sets
`max_seconds = 36000` (QE **CPU** time), and preserves scratch. This design
adds explicit clean-stop classification, archive verification, and a guarded
resume path. It does not change cutoffs, k points, charge, spin, smearing,
convergence thresholds, pseudopotentials, or any other scientific setting.

## Per-run data

Keep QE's active `outdir` under the Linux filesystem, e.g.
`qe_scratch/adsorption/<run_id>_relax`, with a unique `prefix`. Do not compute
directly from the D: backup archive. For each run, preserve:

- the entire `outdir` (not just `prefix.save`), including wavefunctions and
  restart files; if `wfcdir` is ever set separately, preserve that too;
- the exact input, pseudopotentials, raw QE output, runner status, resource
  logs, original run manifest, and any accepted structure;
- the QE executable path and hash, launch command, environment/parallelization,
  `prefix`, `outdir`, stop reason, and timestamps in a checkpoint manifest.

Do not put scratch or checkpoint archives in GitHub; the existing `.gitignore`
excludes `qe_scratch/`. Curated inputs, final results, structures, and methods
remain separate from machine-specific restart data.

## End-of-segment decision

| Outcome | Action |
| --- | --- |
| Ionic convergence and strict result gates, including `JOB DONE` | Accept the final result. Archive provenance; no QE restart is needed. |
| QE cleanly stops before ionic convergence | Wait for `pw.x` to exit and scratch writes to finish. Verify the output and restart files, then mark `checkpoint_ready` and make an immutable archive. |
| Windows/WSL/QE crashes or checkpoint evidence is ambiguous | Mark `unclean`; preserve output and scratch for diagnosis, but never use `restart_mode='restart'` from it. A later attempt may start a *new* run from the last verified accepted geometry with a fresh prefix/outdir. |

QE permits a restart only after a proper stop using `max_seconds` or
`prefix.EXIT` (placed in the working directory or `outdir`). The stop and disk
write may take time; the runner must not hard-kill QE at the 12-hour target.
The current 12-hour runner's `stopped_unconverged`/`incomplete` labels are not
by themselves proof that a checkpoint is valid. Confirm the exact clean-stop
markers with a small controlled test before automating `checkpoint_ready`.

## Archive transaction after a verified clean stop

1. Confirm no `pw.x` process is using that `outdir`; record output and scratch
   sizes, free space on D:, and the run manifest. Refuse an archive when space
   is insufficient. Never overwrite an existing run ID.
2. Package the complete run data from the WSL filesystem into a new file under
   `D:\WSL-Backups\QE-checkpoints\<run_id>\` using a `.partial` name. A single
   tar archive avoids copying many tiny QE files individually across WSL/D:.
3. Hash the finished archive with SHA-256, record its byte count and file list
   in a manifest, test that the archive can be listed/read, then rename the
   `.partial` file to its final name. Only after this verification set status
   to `checkpoint_backed_up`.
4. Keep the original WSL scratch until the resumed run is accepted and the
   backup has been checked. Never delete it automatically to make space.

An incomplete `.partial` file is not a checkpoint. Backups should not be made
while QE is still writing, because a mixed-time archive may be unusable.

## Resume gate (manual approval per scientific run)

1. Confirm the archive checksum and manifest match; ensure the original run
   was classified as a clean stop, not merely a successful copy.
2. Restore to the *same* WSL `outdir` path specified by the original input.
   Refuse to overwrite an existing nonempty scratch directory. Keep the
   original archive immutable.
3. Use a copy of the original input with only `restart_mode='restart'` and, if
   necessary, the next time-box setting changed. Retain the same `prefix`,
   `outdir`, physical/numerical settings, QE build, processor count, and
   parallelization. Verify that no stale `prefix.EXIT` will immediately stop
   the resumed run.
4. Recheck GPU visibility and the separate host/resource gate. Start one QE
   process with the normal per-second RAM/GPU logging; preserve each segment's
   raw output separately. Never append to or overwrite the first segment.
5. Accept the final relaxation only after all electronic cycles converge,
   ionic convergence, final energy/forces, GPU activation, and `JOB DONE` are
   verified across the relevant outputs.

Restarting will reallocate essentially the same GPU working set. The completed
Li/C50 65/520, 4x4x1 SCF peaked at 93.76% VRAM and coincided with graphics
watchdog reports; its planned 70/560 follow-up was skipped. Backups therefore
solve interruption/recovery, **not** the current GPU-memory/host-stability
gate. No new GPU run should be launched solely to test this design.

## Implementation and test order

1. Add read-only inspection and archive/restore commands or scripts with
   `--check-only`; refuse overwrites and verify hashes before extraction.
2. Validate clean-stop and resume behavior on a tiny, already validated QE
   smoke test after the host gate is reopened; do not use production scratch
   as the first test.
3. Integrate the verified classifier and archive transaction into future
   overnight runners, without auto-resuming after crashes or auto-launching
   another scientific case.

QE references: [restart guide](https://www.quantum-espresso.org/Doc/pw_user_guide/node20.html)
and [pw.x input reference](https://www.quantum-espresso.org/Doc/INPUT_PW.html).
