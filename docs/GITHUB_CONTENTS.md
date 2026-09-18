# GitHub content policy

This repository should contain the compact, reproducible scientific record,
not machine-specific runtime state.

## Include

- `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`, and
  `requirements.txt`
- `config/`
- `docs/GPU_SETUP.md`, `docs/OVERNIGHT_WORKFLOW.md`, and `docs/codex_prompts/`
- `scripts/`
- `structures/pristine/`, `structures/monovacancy/`, and
  `structures/relaxed/`
- `qe_inputs/convergence/` and `qe_inputs/relaxation/`
- `results/convergence/`: small raw QE outputs and generated CSV/Markdown
  summaries
- `results/relaxation/`: production raw outputs and compact reports
- `results/phase4/ledger.md` and the monovacancy symmetry pre-flight report
- `figures/convergence/`
- `pseudopotentials/README.md`, which documents how to obtain the external UPF

## Exclude

- `qe_scratch/`, `*.save/`, wavefunctions, charge densities, restart files,
  and other regenerable QE binary state
- pseudopotential binaries (`*.UPF`/`*.upf`)
- `results/phase4/diagnostics/`, which contains machine-specific telemetry,
  host logs, crash evidence, and duplicated scratch data
- `qe_inputs/diagnostics/` and obsolete exploratory cutoff runs
- interrupted raw outputs and obsolete duplicate convergence diagnostics; their
  conclusions remain in the compact failure report and Phase 4 ledger
- local course walkthrough files and root-level smoke-test artifacts
- Python environments/caches and editor settings

The ignored data remain on the workstation; this policy does not delete them.
The GitHub-ready source/result set is small enough for ordinary Git and keeps
the scientific decisions traceable through inputs, raw text outputs, summaries,
figures, and the Phase 4 ledger.

Before publishing, review with:

```bash
git status --short
git add --dry-run .
```

Do not commit or push machine-specific diagnostic material or licensed
pseudopotential binaries.
