# Standardized 9x9x1 final-SCF results

All six entries passed strict parsing: GPU acceleration, electronic convergence,
a final energy, clean completion, and `JOB DONE`. Adsorption energies use
`E_ads = E(M/Cn) - E(Cn) - E(M_atom)`; negative values are exothermic.

| System | Total energy (Ry) | SCF iterations | Magnetization (mu_B) |
| --- | ---: | ---: | ---: |
| na_c49 | -998.91885389 | 16 | 1.01 |
| c49 | -903.50183184 | 20 | 1.64 |
| li_c49 | -918.05962748 | 19 | 0.95 |
| c50 | -922.52210437 | 11 | n/a |
| li_c50 | -936.96584225 | 12 | -0.0 |
| na_c50 | -1017.83224564 | 29 | 0.15 |

| Adsorption system | E_ads (eV) |
| --- | ---: |
| li_c50 | -1.165574 |
| na_c50 | -0.561622 |
| li_c49 | -2.717409 |
| na_c49 | -2.015809 |

The `structures_extxyz` directory contains the exact fixed geometries used
for the final SCFs and can be opened directly in OVITO.
