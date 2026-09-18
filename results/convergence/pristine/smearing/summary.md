# Pristine C50 convergence summary

Working energy-convergence criterion: 1.0 meV per carbon atom.
All reported energies are the final converged QE total energies marked with `!`.

## Smearing sensitivity

| Point | Ecutwfc/rho (Ry) | k mesh | degauss (Ry) | Final F (Ry) | Delta (meV/C) | -TS (Ry) | Internal E=F+TS (Ry) | Fermi (eV) | SCF iterations | Wall (s) | GPU/JOB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| degauss_0p005 | 65/520 | 6x6x1 | 0.005 | -922.5214839000 | +0.0496 | -0.00018232 | -922.52130158 | -4.2099 | 11 | 800.82 | yes |
| degauss_0p010 | 65/520 | 6x6x1 | 0.010 | -922.5216662300 | +0.0000 | -0.00036458 | -922.52130165 | -4.2004 | 11 | 863.57 | yes |
| degauss_0p020 | 65/520 | 6x6x1 | 0.020 | -922.5218632900 | -0.0536 | 0.00073163 | -922.52259492 | -4.2386 | 11 | 802.98 | yes |

## Decisions

- 0.01 Ry smearing reasonable for pristine relaxation: **yes** (absolute difference from 0.005 Ry: 0.0496 meV/C).

Smearing contributions and Fermi energies are transcribed from QE when present; no undocumented internal-energy quantity is introduced.
