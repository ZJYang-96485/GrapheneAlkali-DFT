# Numerical-convergence evidence collected for the report

## Pristine C50

The complete pristine cutoff, k-point, and smearing sweeps are kept in the canonical prepared-data files:

- `../plot_data/cutoff_convergence.csv`
- `../plot_data/kpoint_convergence.csv`
- `../plot_data/smearing_sensitivity.csv`

They are combined in `figures/report/fig05_pristine_convergence.png` and `.pdf` by `scripts/plot_fig5_pristine_convergence.py`.

## Vacancy-containing systems

The repository does not contain complete cutoff, k-point, and smearing sweeps for C49, Li/C49, or Na/C49. The defensible existing evidence is collected here:

- `vacancy_cutoff_check.csv`: Li/C49 fixed-geometry 55/440 and 65/520 Ry pilot values.
- `vacancy_cutoff_comparison.csv`: derived energy, force, and magnetization differences for that two-point cutoff comparison.
- `vacancy_kpoint_refinement.csv`: 6 x 6 x 1 final relaxation-step and 9 x 9 x 1 fixed-geometry final-SCF energies for C49, Li/C49, and Na/C49.
- `vacancy_validation_coverage.csv`: explicit record of which vacancy checks exist and which were not calculated.

`scripts/collect_vacancy_numerical_checks.py` regenerates these files from the raw QE outputs and checks GPU use, electronic convergence, `JOB DONE`, input settings, and geometry identity. `scripts/plot_figs2_vacancy_numerical_checks.py` produces the supplementary report figure `figures/report/figS2_vacancy_numerical_checks.png` and `.pdf`.

## Safe interpretation

The Li/C49 55/440-to-65/520 test shows that 55/440 Ry differs by 2.736 meV/C from the 65/520 Ry reference, while the force-field and magnetization pilot tolerances pass. The fixed-geometry 9 x 9 x 1 minus 6 x 6 x 1 total-energy changes are -0.020 meV/C for C49, +0.026 meV/C for Li/C49, and +0.014 meV/C for Na/C49. These data support the numerical stability of the selected vacancy calculations, but they do not constitute full vacancy convergence sweeps or establish 65/520-to-70/560 Ry vacancy adsorption-energy convergence.
