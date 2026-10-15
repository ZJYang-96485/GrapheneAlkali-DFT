# Neutral isolated-Li reference

Accepted September 23, 2026 (America/Chicago).

## Selected result

The neutral isolated-Li energy selected for the project's atom-referenced
adsorption-energy convention is:

`E(Li_atom) = -14.35806979 Ry`

This value comes from a spin-polarized (`nspin=2`) neutral Li doublet with
fixed total magnetization `1.0` Bohr magneton, fixed occupations, PBE,
DFT-D3(BJ), the verified SSSP Li UPF, 65/520 Ry cutoffs,
Martyna-Tuckerman isolation, and Gamma-only sampling in a 16 Angstrom cubic
cell. It must be combined only with compatible PBE/D3(BJ)/UPF adsorption and
bare-substrate energies under the declared equation
`E_ads = E(C_n+Li) - E(C_n) - E(Li_atom)`.

## Cost-aware box sequence

| Box (Angstrom) | Energy (Ry) | Change from preceding accepted point | Peak GPU | Result |
| ---: | ---: | ---: | ---: | --- |
| 12 | -14.35830245 | -- | 33.828% | Accepted box point |
| 14 | -14.35809242 | 2.857604 meV | 37.662% | Accepted point; tolerance not yet met |
| 16 | -14.35806979 | 0.307897 meV | 62.032% | Accepted final reference |

The predeclared threshold was 1 meV between consecutive box points. Because
the 14-to-16 difference passes, no larger Li box was run. An earlier 18
Angstrom resource diagnostic was stopped before convergence at the 80% GPU
gate and is excluded from the table and scientific result.

Every accepted point used GPU acceleration, converged electronically, printed
magnetization `1.00`, printed `JOB DONE`, exited with status zero, and produced
no new WSL GPU-residency error, Windows watchdog dump, swap event, or unclean
restart.

## Provenance and references

- Method and stopping rule: `docs/PHASE5_ISOLATED_ATOM_REFERENCE_PLAN.md`
- Li pseudopotential: `li_pbe_v1.4.uspp.F.UPF`, MD5
  `e912e257baa3777c20ea3d68f190483c`
- R. Datta *et al.*, *Nanoscale* **11**, 11185-11197 (2019),
  https://doi.org/10.1039/C8NR10383F
- N. Dimakis *et al.*, *Molecules* **24**, 754 (2019),
  https://doi.org/10.3390/molecules24040754
- Quantum ESPRESSO `pw.x` input documentation,
  https://www.quantum-espresso.org/Doc/INPUT_PW.html
- SSSP 1.0 PBE efficiency archive,
  https://archive.materialscloud.org/records/1dygy-1xb93
