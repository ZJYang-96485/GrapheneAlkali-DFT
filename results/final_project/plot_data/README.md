# Plot-ready final-project data

Prepared on 2026-10-17 without launching any new Quantum ESPRESSO calculation.

## Selection rules

- The common four-system comparison uses the internally consistent 65/520 Ry,
  9x9x1 final-SCF adsorption energies for Li/C50, Na/C50, Li/C49, and Na/C49.
- The 70/560 Ry rows are a separate fixed-geometry cutoff check for the two
  pristine adsorption systems. They are not substituted into the four-system
  defect comparison.
- Adsorption energies use
  `E_ads = E(M/Cn) - E(Cn) - E(M_atom)`; a more negative value means stronger
  exothermic adsorption relative to a neutral isolated atom.
- Structural heights, magnetizations, and residual forces come from the
  accepted 65/520 Ry, 6x6x1 relaxations. Relaxation total energies must not be
  mixed with the 9x9x1 final-SCF energies to recompute adsorption energies.
- Literature values are labeled by comparability. Differences in code, basis,
  supercell, coverage, k-point sampling, and magnetic minimum remain relevant
  even when the same PBE+D3(BJ) functional is used.

## Files

- `adsorption_energies.csv`: all accepted 65/520 and 70/560 final-SCF
  adsorption-energy records.
- `derived_comparisons.csv`: Li-versus-Na and pristine-versus-vacancy energy
  differences calculated from the common 65/520 data set.
- `relaxed_geometry_properties.csv`: adsorption heights, magnetizations, and
  force checks from the accepted relaxations.
- `cutoff_convergence.csv`, `kpoint_convergence.csv`, and
  `smearing_sensitivity.csv`: compact pristine-graphene numerical validation.
- `literature_comparison.csv`: project-to-literature numerical comparisons.
- `literature_sources.csv`: primary-source bibliography and extraction notes.
- `plot_manifest.csv`: planned report figures and their input files.

## Provenance note

The pristine, bare-monovacancy, Li/C50, and Na/C50 relaxation outputs and the
pristine convergence outputs are present in this checkout. The Li/C49 and
Na/C49 raw relaxation outputs, accepted 9x9x1 final-SCF campaign bundle, and
70/560 cutoff campaign bundle are not currently synchronized into this local
checkout. Their numerical values are preserved here from the strict campaign
summaries and are also encoded in `scripts/summarize_final_scf_campaign.py`
and `scripts/summarize_adsorbate_cutoff_validation_20261017.py`. Sync the
verified campaign bundles before claiming that every final raw output is
archived in the repository.

