# Pristine C50 convergence summary

Working energy-convergence criterion: 1.0 meV per carbon atom.
All reported energies are the final converged QE total energies marked with `!`.

## Cutoff convergence

| Point | Ecutwfc/rho (Ry) | k mesh | degauss (Ry) | Final F (Ry) | Delta (meV/C) | -TS (Ry) | Internal E=F+TS (Ry) | Fermi (eV) | SCF iterations | Wall (s) | GPU/JOB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ecutwfc_40_ecutrho_320 | 40/320 | 6x6x1 | 0.010 | -922.4888521300 | +9.9060 | -0.00036458 | -922.48848755 | -4.2001 | 10 | 151.52 | yes |
| ecutwfc_45_ecutrho_360 | 45/360 | 6x6x1 | 0.010 | -922.5040322700 | +5.7753 | -0.00036458 | -922.50366769 | -4.2004 | 11 | 171.78 | yes |
| ecutwfc_50_ecutrho_400 | 50/400 | 6x6x1 | 0.010 | -922.5074825800 | +4.8364 | -0.00036458 | -922.50711800 | -4.2001 | 11 | 681.77 | yes |
| ecutwfc_55_ecutrho_440 | 55/440 | 6x6x1 | 0.010 | -922.5116642500 | +3.6986 | -0.00036458 | -922.51129967 | -4.2003 | 11 | 729.05 | yes |
| ecutwfc_60_ecutrho_480 | 60/480 | 6x6x1 | 0.010 | -922.5169287200 | +2.2660 | -0.00036458 | -922.51656415 | -4.2004 | 11 | 760.30 | yes |
| ecutwfc_65_ecutrho_520 | 65/520 | 6x6x1 | 0.010 | -922.5216662300 | +0.9769 | -0.00036458 | -922.52130165 | -4.2004 | 11 | 863.57 | yes |
| ecutwfc_70_ecutrho_560 | 70/560 | 6x6x1 | 0.010 | -922.5252561900 | +0.0000 | -0.00036458 | -922.52489161 | -4.2005 | 11 | 891.20 | yes |

## K-point convergence

| Point | Ecutwfc/rho (Ry) | k mesh | degauss (Ry) | Final F (Ry) | Delta (meV/C) | -TS (Ry) | Internal E=F+TS (Ry) | Fermi (eV) | SCF iterations | Wall (s) | GPU/JOB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| k_3x3x1 | 65/520 | 3x3x1 | 0.010 | -922.5165131600 | +1.5397 | -0.00145859 | -922.51505457 | -4.2003 | 11 | 359.21 | yes |
| k_6x6x1 | 65/520 | 6x6x1 | 0.010 | -922.5216662300 | +0.1375 | -0.00036458 | -922.52130165 | -4.2004 | 11 | 863.57 | yes |
| k_9x9x1 | 65/520 | 9x9x1 | 0.010 | -922.5221043700 | +0.0183 | -0.00013047 | -922.52197390 | -4.2026 | 11 | 1358.60 | yes |
| k_12x12x1 | 65/520 | 12x12x1 | 0.010 | -922.5221715300 | +0.0000 | 0.00009303 | -922.52226456 | -4.2294 | 11 | 2199.86 | yes |

## Smearing sensitivity

| Point | Ecutwfc/rho (Ry) | k mesh | degauss (Ry) | Final F (Ry) | Delta (meV/C) | -TS (Ry) | Internal E=F+TS (Ry) | Fermi (eV) | SCF iterations | Wall (s) | GPU/JOB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| degauss_0p005 | 65/520 | 6x6x1 | 0.005 | -922.5214839000 | +0.0496 | -0.00018232 | -922.52130158 | -4.2099 | 11 | 800.82 | yes |
| degauss_0p010 | 65/520 | 6x6x1 | 0.010 | -922.5216662300 | +0.0000 | -0.00036458 | -922.52130165 | -4.2004 | 11 | 863.57 | yes |
| degauss_0p020 | 65/520 | 6x6x1 | 0.020 | -922.5218632900 | -0.0536 | 0.00073163 | -922.52259492 | -4.2386 | 11 | 802.98 | yes |

## Decisions

- 65/520 Ry supported: **yes** (absolute difference from 70/560: 0.9769 meV/C).
- Cutoff energies monotonic within 1e-8 Ry: **yes**.
- 6x6x1 supported for relaxation: **yes** (absolute difference from 12x12x1: 0.1375 meV/C).
- 9x9x1 supported for final SCF: **yes** (absolute difference from 12x12x1: 0.0183 meV/C).
- 0.01 Ry smearing reasonable for pristine relaxation: **yes** (absolute difference from 0.005 Ry: 0.0496 meV/C).

Smearing contributions, internal energies E=F+TS, and Fermi energies are transcribed from QE when present; no undocumented internal-energy quantity is introduced.
