# Figure 1 validation

## Outcome

**PASS.** All four accepted relaxed structures were found and rendered. No
starting geometry, restart-input coordinate set, incomplete ionic step, or
interrupted Na/C49 checkpoint was used. No missing-data warning applies.

Every raw relaxation output has JOB DONE, an explicit converged final total
energy, zero failed electronic cycles, explicit ionic convergence, and complete
Begin final coordinates / End final coordinates markers. The recovered
periodic EXTXYZ positions match those raw final-coordinate blocks
atom-for-atom, with a maximum absolute coordinate difference of 0.0 Å in all
four cases.

## Structure provenance

| Panel | System | Raw accepted relaxation output | SHA-256 | Atoms | Calculated height (Å) | Accepted project value (Å) |
|---|---|---|---|---:|---:|---:|
| (a) | Li/C50 | results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.out | f07f19c7847c2f81d5f0d14e28c52d1e9ce8669544f9007b4503c793315beab1 | 51 | 1.6914109357 | 1.691 |
| (b) | Na/C50 | results/cloud/20260930_blackwell48_restart2/na_c50_hollow_20260924a_relax_restart2.out | 7b896a3fb970745c42883f0746979772fa62649eff4ce2ddce15ac8bc2af7253 | 51 | 2.2487472756 | 2.249 |
| (c) | Li/C49 | results/cloud/20261008_li_c49_vacancy_18h_cont2/li_c49_vacancy_20261008a_segment03.out | feab8757bda0bb60a3526c22f8031179804a3addee0730782ef9f1061d0b78c7 | 50 | 1.7948192551 | 1.795 |
| (d) | Na/C49 | results/cloud/20261014_na_c49_resilient/na_c49_segment001.out | 44ed68bb91ab49ad1ef64266e1ffcfee214845b686fff7b361605712790a6f6b | 50 | 2.2695104401 | 2.2695104401 |

The height is calculated directly from each accepted structure as
z(metal) - mean(z(carbon atoms)). All differences from the accepted project
values are below 0.001 Å, well within the required 0.02 Å tolerance. The
machine-readable record is structures/report/fig1/provenance.csv.

## OVITO rendering settings

- OVITO application version checked: OVITO Basic 3.16.1.
- Reproducible renderer: OVITO Python API 3.16.1 with Tachyon.
- Panel resolution: 1200 × 900 pixels; orthographic projection.
- Shared camera direction: normalized (0.18, 0.42, -1.0), approximately
  24.6 degrees from the surface normal; shared field of view: 10.5; identical
  cell-centered camera placement in all panels.
- White background, ambient occlusion and shadows enabled, 16 antialiasing
  samples.
- Colors: C (0.30, 0.32, 0.34), Li (0.00, 0.45, 0.70), and Na
  (0.90, 0.56, 0.08).
- C-C bonds: pair cutoff 1.85 Å, uniform width 0.15; no metal-carbon bonds
  inferred.
- Periodic-cell outline: gray (0.58, 0.60, 0.62), line width 0.025.
- Montage: 2556 × 2260 RGB PNG with 300-dpi metadata and one-page PDF.

## Visual inspection

The final PNG was inspected at original resolution. All atoms, bonds, labels,
and complete cell boundaries are visible and unclipped; all panels use the same
camera, scale, lighting, and dimensions. Li and Na are distinguishable by both
color and radius, the C49 vacancy regions differ visibly from the pristine C50
lattices, the backgrounds are uniformly white, and no label overlaps an atom.
The panel heights agree with the accepted values after rounding to three
decimal places.

## Final file integrity

- PNG SHA-256:
  d4e749ec825e6b9d2fbc4414c92523e40d54132454f9907fbdb48cf26e1921dd
- PDF SHA-256:
  aa94bac810cd6bc88da4522829ad978187ac0b3326ae916f1911ca9bf5957e9d
- Rendering script SHA-256:
  ea0fb8a2dbc7b83d0aede9aef7b613c0a686bec167f5229ed72bc5861fd800fa
- Structure-preparation script SHA-256:
  40cc13ee5787d295b9e6723c10dad7d1fe22fd0c4675c24cb0a070acd5038926
