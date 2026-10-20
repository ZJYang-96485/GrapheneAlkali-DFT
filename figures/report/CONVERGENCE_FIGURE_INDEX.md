# Convergence figures for the term-project report

## Main-text figure

- **Figure 5 — pristine C50 convergence:** `fig05_pristine_convergence.png` and `.pdf`.
  - Panels: plane-wave cutoff, k-point mesh, and smearing width.
  - Script: `scripts/plot_fig5_pristine_convergence.py`.
  - Prepared data: `results/final_project/plot_data/cutoff_convergence.csv`, `kpoint_convergence.csv`, and `smearing_sensitivity.csv`.
  - Caption: `fig05_caption.md`.

The three earlier standalone images remain at `figures/convergence/cutoff_convergence.png`, `kpoint_convergence.png`, and `smearing_sensitivity.png`, but Figure 5 is the report-formatted consolidated version.

## Supplementary vacancy figure

- **Figure S2 — available vacancy numerical checks:** `figS2_vacancy_numerical_checks.png` and `.pdf`.
  - Panels: Li/C49 two-point fixed-geometry cutoff check and C49/Li-C49/Na-C49 two-point k-point refinement.
  - Script: `scripts/plot_figs2_vacancy_numerical_checks.py`.
  - Prepared data: `results/final_project/convergence_collection/`.
  - Caption: `figS2_caption.md`.

## Important coverage limit

There is no full vacancy cutoff sweep, vacancy smearing sweep, or 70/560 Ry vacancy adsorption-energy calculation. Figure S2 therefore uses the label **two-point numerical checks**, not **vacancy convergence study**.
