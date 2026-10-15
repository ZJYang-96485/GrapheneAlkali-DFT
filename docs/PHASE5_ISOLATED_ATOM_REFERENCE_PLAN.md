# Phase 5 isolated-atom reference plan

Prepared September 23, 2026 (America/Chicago). This plan responds to the
failed local Li/C49 GPU-resource gate by moving to a low-memory calculation.
It does not authorize another adsorbate relaxation.

## Purpose and energy convention

The deadline analysis defines

`E_ads = E(C_n+M) - E(C_n) - E(M_atom)`,

where `M` is a neutral Li or Na atom. More negative values mean stronger
binding relative to a neutral isolated atom; they do not establish stability
against bulk-metal plating. The isolated atom must use the same PBE functional
and approved pseudopotential as the adsorbed calculation, but its spin,
occupation, box, isolation, and k-point treatment require a separate finite-
system justification.

## First calculation: neutral Li, 18 Angstrom box

Run one fixed-atom SCF with:

- the verified `li_pbe_v1.4.uspp.F.UPF` pseudopotential;
- PBE and DFT-D3(BJ), for consistency with the adsorption calculations (the
  dispersion correction has no interatomic pair in a one-atom cell);
- `ecutwfc=65 Ry` and `ecutrho=520 Ry`;
- a neutral cell, `nspin=2`, and `tot_magnetization=1.0`, corresponding to the
  neutral Li doublet represented by the three-valence-electron UPF;
- fixed occupations, rather than metallic smearing;
- an 18 Angstrom cubic cell with the atom at its center;
- Martyna-Tuckerman isolated-cluster electrostatics and `K_POINTS gamma`;
- `conv_thr=1.0d-8`, `mixing_beta=0.3`, and CG diagonalization;
- a fresh prefix, scratch directory, output, status, and resource logs.

The 18 Angstrom cell is deliberately larger than the 12 Angstrom cubic
vacuum box used for isolated alkali atoms by Datta *et al.* It is only the
first box point: do not promote its energy to the final reference until a
separately reviewed larger-box calculation agrees within a declared energy
tolerance.

## Acceptance and stop gates

Accept the pilot only if GPU acceleration is active, the electronic cycle
converges, a final total energy and magnetization are printed, `JOB DONE` is
present, and the total magnetization is `1.0` Bohr magneton per cell within
parser precision. The supervisor requests a clean stop if GPU allocation is
at or above 80% in three consecutive checks or the one-hour wall limit is
reached. Do not launch the larger-box Li point or any Na job automatically.

After completion, compare the Windows watchdog set and WSL kernel messages
with their pre-run values. If the pilot is clean and comfortably below the
resource limit, prepare a 24 Angstrom Li box point with otherwise identical
settings. A final atom energy will be selected only after the box comparison;
Na will receive the same staged treatment with its own verified UPF and
spin-appropriate neutral-atom state.

## September 23 resource-gate update and cost-aware recovery

The 18 Angstrom pilot was stopped cleanly during SCF iteration 6 after GPU
allocation reached `13,731/16,303 MiB` (`84.224%`), above its declared 80%
limit. It produced no converged total energy and therefore supplies no value
that can bias the revised box-convergence threshold. No WSL residency error,
new Windows watchdog dump, or unclean restart accompanied the stop.

The revised sequence preserves every physical and electronic setting while
reducing FFT-grid cost through smaller cubic boxes:

1. Run 12 Angstrom and review all scientific and 80% resource gates.
2. Only after that review, run 14 Angstrom with an independently fresh
   identity and the same settings.
3. If `|E(14)-E(12)| <= 1 meV` (`7.349864e-5 Ry`), accept the 14 Angstrom
   result as the isolated-Li reference and skip 16 Angstrom.
4. If the first difference exceeds 1 meV, run 16 Angstrom and require
   `|E(16)-E(14)| <= 1 meV`. If this also fails, do not extrapolate or run the
   known-unsafe 18 Angstrom case locally.

This conditional sequence costs less than automatically running 12, 14, and
16 Angstrom. The 12 Angstrom starting point also matches the published vacuum
box size cited below, while Martyna-Tuckerman isolation remains enabled. Each
point is reviewed before the next launch; no runner contains an automatic
follow-up.

## Neutral Na sequence

Approved after completion of the Li sequence. Neutral Na uses the verified
`na_pbe_v1.5.uspp.F.UPF`, whose nine valence electrons represent
`2s2 2p6 3s1`. It is therefore treated as a neutral spin doublet with
`nspin=2`, fixed occupations, and `tot_magnetization=1.0`, analogous to the
accepted neutral-Li treatment. PBE, DFT-D3(BJ), 65/520 Ry, Gamma-only
sampling, Martyna-Tuckerman isolation, the SCF threshold, mixing, and CG
diagonalization remain unchanged.

The same cost-aware rule applies independently to Na: run and review 12
Angstrom, then 14 Angstrom; accept 14 and skip 16 if the difference is no more
than 1 meV. Run 16 Angstrom only if needed, and accept it only if the 14-to-16
difference is no more than 1 meV. Stop the local sequence if any scientific,
80% GPU-memory, WSL, Windows-watchdog, or restart gate fails. Each conditional
launch follows a completed review; the runners do not chain jobs themselves.

## References

- R. Datta *et al.*, "Adsorption and migration of alkali metals (Li, Na, and
  K) on pristine and defective graphene surfaces," *Nanoscale* **11**,
  11185-11197 (2019), https://doi.org/10.1039/C8NR10383F. This paper defines
  the isolated-neutral-atom adsorption reference and reports a 12 Angstrom
  cubic atom box; its numerical energies are not copied into this project.
- N. Dimakis *et al.*, "Li and Na Adsorption on Graphene and Graphene Oxide
  Examined by Density Functional Theory, Quantum Theory of Atoms in Molecules,
  and Electron Localization Function," *Molecules* **24**, 754 (2019),
  https://doi.org/10.3390/molecules24040754. Context for the pristine-versus-
  defective comparison; it does not validate this project's atom settings.
- Quantum ESPRESSO, `pw.x` input description,
  https://www.quantum-espresso.org/Doc/INPUT_PW.html. This documents
  Martyna-Tuckerman isolation, fixed total magnetization, fixed occupations,
  and the memory-reduced Gamma-point implementation.
- Materials Cloud, SSSP 1.0 PBE efficiency library,
  https://archive.materialscloud.org/records/1dygy-1xb93. Source of the Li and
  Na pseudopotentials and checksums retained in `pseudopotentials/README.md`.
