# Neutral isolated-Na reference

Accepted September 23, 2026 (America/Chicago).

## Selected result

The neutral isolated-Na energy selected for the project's atom-referenced
adsorption-energy convention is:

`E(Na_atom) = -95.26886282 Ry`

This value comes from a spin-polarized (`nspin=2`) neutral Na doublet with
fixed total magnetization `1.0` Bohr magneton, fixed occupations, PBE,
DFT-D3(BJ), the verified SSSP Na UPF, 65/520 Ry cutoffs,
Martyna-Tuckerman isolation, and Gamma-only sampling in a 16 Angstrom cubic
cell. It must be combined only with compatible PBE/D3(BJ)/UPF adsorption and
bare-substrate energies under the declared equation
`E_ads = E(C_n+Na) - E(C_n) - E(Na_atom)`.

## Cost-aware box sequence

| Box (Angstrom) | Energy (Ry) | Change from preceding point | Peak GPU | Result |
| ---: | ---: | ---: | ---: | --- |
| 12 | -95.26918121 | -- | 33.227% | Accepted box point |
| 14 | -95.26891558 | 3.614080 meV | 51.849% | Accepted point; tolerance not yet met |
| 16 | -95.26886282 | 0.717836 meV | 63.314% | Accepted final reference |

The predeclared threshold was 1 meV between consecutive box points. Because
the 14-to-16 difference passes, no larger Na box was run. Every point used GPU
acceleration, converged electronically, printed magnetization `1.00`, printed
`JOB DONE`, exited with status zero, and produced no new WSL GPU-residency
error, Windows watchdog dump, swap event, or unclean restart.

## Provenance and references

- Method and stopping rule: `docs/PHASE5_ISOLATED_ATOM_REFERENCE_PLAN.md`
- Na pseudopotential: `na_pbe_v1.5.uspp.F.UPF`, MD5
  `44600605ef58000f06b90626533354dc`
- R. Datta *et al.*, *Nanoscale* **11**, 11185-11197 (2019),
  https://doi.org/10.1039/C8NR10383F
- N. Dimakis *et al.*, *Molecules* **24**, 754 (2019),
  https://doi.org/10.3390/molecules24040754
- Quantum ESPRESSO `pw.x` input documentation,
  https://www.quantum-espresso.org/Doc/INPUT_PW.html
- SSSP 1.0 PBE efficiency archive,
  https://archive.materialscloud.org/records/1dygy-1xb93
