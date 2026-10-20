# Report outline, remaining work, and limitations

**Project:** Neutral Li and Na adsorption on pristine and monovacancy graphene from first-principles calculations  
**Purpose of this note:** Writing plan and checklist for the final term-project report.  
**Current source of truth:** Use the final prepared tables in `results/final_project/plot_data/`, the vacancy numerical checks in `results/final_project/convergence_collection/`, and the report figures in `figures/report/`. Do not copy provisional numerical values from older progress checkpoints when they disagree with the final tables.

## Recommended central question

How does a graphene monovacancy change the adsorption strength, equilibrium geometry, and magnetic response of neutral Li and Na atoms compared with pristine graphene?

## Main conclusion to develop

The calculations predict that a monovacancy is a substantially stronger adsorption site than pristine graphene for both neutral Li and neutral Na. Li binds more strongly and sits closer to graphene than Na on both substrates. The vacancy also creates a magnetic response that is reduced, but not eliminated, following alkali adsorption. These conclusions are supported by internally consistent PBE-D3(BJ) calculations, complete pristine-graphene convergence tests, targeted vacancy numerical checks, and comparison with published trends.

## Report outline

The required main text is 5--8 pages, excluding figures and bibliography. A practical target is approximately 6 pages of main text.

### 1. Abstract

Write one compact paragraph of approximately 180--250 words containing:

- The problem: alkali adsorption on pristine and defective graphene.
- The approach: spin-polarized plane-wave DFT with PBE, DFT-D3(BJ), Quantum ESPRESSO, a C50/C49 5 x 5 supercell, relaxed structures, and final fixed-geometry SCF calculations.
- The four systems: Li/C50, Na/C50, Li/C49, and Na/C49.
- The principal adsorption energies: -1.166, -0.562, -2.717, and -2.016 eV, respectively.
- The main finding: a monovacancy strengthens adsorption by 1.552 eV for Li and 1.454 eV for Na.
- The physical interpretation: Li binds more strongly and closer to the sheet, while vacancy adsorption retains a magnetic moment near 1 Bohr magneton per cell.
- One limitation: vacancy-specific convergence was checked with targeted two-point calculations rather than complete parameter sweeps.

### 2. Introduction

#### 2.1 Motivation

- Explain why graphene and defective graphene are relevant to adsorption, energy storage, sensing, and alkali-metal anchoring.
- Explain that pristine graphene interacts comparatively weakly with alkali atoms, whereas vacancies provide under-coordinated and electronically active binding sites.
- Motivate the comparison of Li with Na using their different atomic size and adsorption behavior.

#### 2.2 Research question and hypothesis

- State the central question given above.
- Hypothesis: a monovacancy should make adsorption more exothermic, preserve or modify vacancy magnetism, and favor Li more strongly than Na.

#### 2.3 Literature context

- Use Olsson *et al.* for pristine Li/Na adsorption energies and heights.
- Use Cottom *et al.* for Li/Na adsorption at graphene monovacancies.
- Use Yazyev and Helm and/or Padmanabhan and Nanda for monovacancy magnetism.
- Explain before presenting comparisons that different codes, basis sets, supercells, dispersion treatments, and reference conventions can shift absolute adsorption energies.

### 3. Methods

#### 3.1 Structural models

- Describe the fixed C50 5 x 5 pristine graphene supercell and the C49 monovacancy produced by removing one carbon atom.
- State that the simulation cell contains vacuum normal to the sheet and uses `assume_isolated = '2D'`.
- Identify the pristine hollow site and the vacancy-centered site.
- State explicitly that the adsorbates are neutral Li and Na atoms, not Li+ or Na+ ions.

#### 3.2 Electronic-structure method

- Quantum ESPRESSO `pw.x` with GPU acceleration for the accepted calculations.
- PBE exchange-correlation functional and DFT-D3(BJ) dispersion correction.
- Approved pseudopotentials and plane-wave cutoffs of 65 Ry for wavefunctions and 520 Ry for charge density.
- Marzari--Vanderbilt smearing with `degauss = 0.01 Ry`.
- Spin treatment: describe the spin-polarized vacancy calculations and the accepted magnetic initialization without implying that every possible magnetic state was searched.

#### 3.3 Relaxation and final SCF protocol

- Ionic relaxations: 6 x 6 x 1 unshifted k-point mesh with fixed cell.
- Acceptance requirements: electronic convergence in every completed SCF cycle, ionic convergence, final total energy, force criterion, and `JOB DONE`.
- Final energies: fixed relaxed geometries recalculated using a 9 x 9 x 1 mesh.
- Explain that structural heights and relaxation magnetizations come from the accepted 6 x 6 x 1 relaxations, while adsorption energies use the internally consistent 9 x 9 x 1 final-SCF dataset.

#### 3.4 Adsorption-energy definition

Use

`E_ads = E(M/C_n) - E(C_n) - E(M_atom)`.

State that negative values mean exothermic adsorption relative to a neutral isolated atom. Use the same cutoff, pseudopotential, and compatible numerical protocol for each combined system, substrate, and isolated-atom reference.

#### 3.5 Numerical convergence and reproducibility

- Present Figure 5 as the complete pristine C50 cutoff, k-point, and smearing study.
- State the predefined approximately 1 meV/C total-energy criterion.
- Explain the selected 65/520 Ry cutoff, 6 x 6 x 1 relaxation mesh, 9 x 9 x 1 final-SCF mesh, and 0.01 Ry smearing.
- Present Figure S2 as targeted vacancy numerical checks, not as a complete vacancy convergence study.
- Mention that all plotted numerical-check outputs used GPU acceleration, converged electronically, and printed `JOB DONE`.

### 4. Results and Discussion

#### 4.1 Numerical convergence

- **Figure 5:** Show the complete pristine convergence study.
- Report that 65/520 Ry differs from 70/560 Ry by 0.9769 meV/C for pristine C50.
- Report that 6 x 6 x 1 and 9 x 9 x 1 differ from 12 x 12 x 1 by 0.1375 and 0.0183 meV/C, respectively.
- Report the very small smearing sensitivity around 0.01 Ry.
- **Figure S2:** Report that the Li/C49 55/440 Ry result is 2.736 meV/C above 65/520 Ry and therefore does not meet the 1 meV/C energy criterion.
- Report the signed 9 x 9 x 1 minus 6 x 6 x 1 changes of -0.020, +0.026, and +0.014 meV/C for C49, Li/C49, and Na/C49.

#### 4.2 Relaxed structures

- **Figure 1:** Show Li/C50, Na/C50, Li/C49, and Na/C49 using identical rendering conventions.
- Describe vacancy reconstruction and the different local coordination of the adsorbates.
- Report that Li is closer to the sheet than Na.

#### 4.3 Adsorption energies and literature comparison

- **Figure 2:** Present the four common-protocol 65/520 Ry adsorption energies and literature markers.
- Li/C50: -1.1656 eV.
- Na/C50: -0.5616 eV.
- Li/C49: -2.7174 eV.
- Na/C49: -2.0158 eV.
- Explain that the pristine results agree closely with the selected literature values, while the vacancy results reproduce the strong-binding trend but are approximately 0.50 eV less exothermic than the selected vacancy literature values.
- Attribute differences cautiously to methodology and finite-size effects rather than treating the literature as an exact benchmark.

#### 4.4 Vacancy enhancement and Li--Na selectivity

- **Figure 3:** Show derived energy differences.
- The vacancy strengthens adsorption by 1.5518 eV for Li and 1.4542 eV for Na.
- Li binds more strongly than Na by 0.6040 eV on pristine graphene and 0.7016 eV at the vacancy.
- Discuss these differences as robust, electron-volt-scale trends that are much larger than the measured numerical sensitivities.

#### 4.5 Adsorption height and magnetism

- **Figure 4:** Compare relaxed heights and total magnetizations.
- Heights: 1.691 and 2.249 Angstrom for Li/C50 and Na/C50; 1.795 and 2.270 Angstrom for Li/C49 and Na/C49.
- Magnetizations: approximately 0.00, 0.13, 0.96, and 1.00 Bohr magnetons per cell for Li/C50, Na/C50, Li/C49, and Na/C49.
- Compare the adsorbed vacancy systems with the bare-C49 value of 1.60 Bohr magnetons per cell.
- Interpret adsorption as reducing, but not eliminating, the vacancy-associated magnetic moment.

#### 4.6 Numerical uncertainty and scope

- **Figure 6:** Show the pristine adsorbate-specific cutoff checks and explicitly mark unavailable vacancy 70/560 Ry values.
- Raising the cutoff from 65/520 to 70/560 Ry changes the pristine adsorption energies by -2.10 meV for Li/C50 and -10.59 meV for Na/C50.
- Explain that these shifts are small relative to the 0.6--1.6 eV conclusions, but they prohibit claims based on energy differences of only a few meV.
- State every limitation listed in the required limitations section below.

### 5. Conclusions

- Answer the research question directly.
- State that a monovacancy strongly enhances adsorption for both metals.
- State that Li binds more strongly and closer to graphene than Na.
- State that vacancy adsorption retains a significant magnetic moment.
- Emphasize that the electron-volt-scale trends are stronger than the observed numerical sensitivities.
- End with one future-work sentence covering vacancy-specific convergence, supercell-size tests, additional adsorption sites/magnetic seeds, and charge-transfer or diffusion calculations.

### 6. Bibliography

- Include the primary Quantum ESPRESSO reference, PBE, DFT-D3(BJ), pseudopotential/SSSP source, and the graphene adsorption and vacancy-magnetism papers used in the comparison table.
- Verify every bibliographic field and DOI against the original paper before submission.
- Cite literature values in the text and captions rather than only listing the papers in the bibliography.

## Figure plan

| Figure | Placement | Purpose |
| --- | --- | --- |
| Figure 1 | Main text | Four relaxed adsorption structures |
| Figure 2 | Main text | Adsorption energies with literature comparison |
| Figure 3 | Main text | Vacancy strengthening and Li--Na selectivity |
| Figure 4 | Main text | Adsorption height and magnetic response |
| Figure 5 | Main text, Methods or beginning of Results | Complete pristine numerical convergence |
| Figure 6 | Main text or supplementary, depending on space | Available adsorbate-specific cutoff validation and missing vacancy points |
| Figure S1 | Supplementary | Residual-force acceptance check |
| Figure S2 | Supplementary or convergence subsection | Available two-point vacancy numerical checks |

If the report must be shortened, retain Figures 1--5 in the main report. Move Figures 6, S1, and S2 to an appendix or supplementary section, but summarize their numerical findings and limitations in the main text.

## Required limitations and imperfections to disclose

### Vacancy convergence coverage

A complete cutoff, k-point, and smearing sweep was not repeated for every vacancy-containing system. The available vacancy evidence consists of a two-point fixed-geometry Li/C49 cutoff test and 6 x 6 x 1-to-9 x 9 x 1 fixed-geometry final-energy checks for C49, Li/C49, and Na/C49. No vacancy smearing sweep and no 70/560 Ry vacancy adsorption-energy calculation were performed. Therefore, describe Figure S2 as **targeted numerical checks**, not as a complete vacancy convergence study.

### Cutoff sensitivity of adsorption energies

The common four-system comparison uses 65/520 Ry so all systems are treated consistently. The additional pristine checks change the Li/C50 and Na/C50 adsorption energies by -2.10 and -10.59 meV when the cutoff is raised to 70/560 Ry. These changes are small compared with the main electron-volt-scale trends, but the results should not be used to resolve energy differences at the few-meV scale.

### Limited configuration sampling

The project compares the pristine hollow site with one vacancy-centered structure for each neutral metal. It does not exhaustively sample bridge, top, off-center vacancy, subsurface, clustered, or multiple-adsorbate configurations. It also does not prove that every alternative vacancy reconstruction or spin initialization leads to a higher-energy state.

### Finite-size and method dependence

Only one 5 x 5 supercell size was used; no systematic vacancy-concentration or vacuum-size convergence study was performed. PBE-D3(BJ), the selected pseudopotentials, smearing, supercell, and isolated-neutral-atom reference convention introduce systematic method dependence. The approximately 0.50 eV differences from the selected vacancy literature values should therefore be discussed as method- and cell-size-sensitive rather than as disagreement caused by statistical error.

### Charge state and kinetic properties

The adsorbates are neutral atoms. The calculations do not directly model Li+ or Na+ in an electrochemical environment, solvent, external potential, or charged cell. Charge transfer, diffusion barriers, desorption barriers, finite-temperature dynamics, and electrochemical voltage were not calculated, so the results describe zero-temperature binding trends rather than complete battery kinetics or operating conditions.

### Error bars and numerical uncertainty

The DFT energies are deterministic, so conventional statistical error bars are not available. Their absence must not be described as zero uncertainty: numerical convergence, finite-size effects, structural sampling, and exchange-correlation approximations remain sources of systematic uncertainty.

## Ready-to-use limitation paragraph

> A complete cutoff, k-point, and smearing sweep was performed for pristine C50 graphene and used to select the common numerical settings. Repeating every sweep for each vacancy-containing and adsorbate system would have substantially increased the computational cost because these spin-polarized structures required much longer SCF and ionic relaxations. Transferability was therefore evaluated using targeted two-point checks: the Li/C49 cutoff test showed that 55/440 Ry was insufficient relative to 65/520 Ry, while the 6 x 6 x 1-to-9 x 9 x 1 energy changes for C49, Li/C49, and Na/C49 were all below 0.026 meV/C. These results support the numerical stability of the selected calculations, but the absence of a higher-cutoff vacancy adsorption calculation means that the cutoff uncertainty of the vacancy adsorption energies cannot be quantified as rigorously as for pristine graphene. Complete vacancy-specific cutoff and smearing sweeps, larger-supercell tests, and broader sampling of adsorption and magnetic configurations are therefore reserved for future work.

## Remaining work before submission

No additional simulation is required to support the current term-project conclusion. The remaining work is report preparation and final quality control:

- Draft the report using the outline above and keep the main text within 5--8 pages, excluding figures and bibliography.
- Verify the literature citations and build the final bibliography from primary sources.
- Insert the final PNG or PDF figures and their existing caption files from `figures/report/`.
- Check every figure against the course requirements: readable axis and tick labels, quantity and unit on each axis, consistent decimal places, major ticks and subticks, visible data symbols, colorblind-safe colors, and a caption that states the main finding.
- Include the adsorption-energy equation and sign convention in the Methods section.
- Keep the 65/520 Ry common four-system values separate from the 70/560 Ry pristine validation values.
- State the limitations above explicitly; do not imply complete vacancy convergence, exhaustive site sampling, or electrochemical Li+/Na+ behavior.
- Cross-check all numbers in the prose against `adsorption_energies.csv`, `derived_comparisons.csv`, and `relaxed_geometry_properties.csv`.
- Confirm that final inputs, prepared CSV files, scripts, figures, captions, and the bibliography are included in the submission archive or repository.
- Proofread for consistent notation: C50, C49, Li/C50, Na/C50, Li/C49, Na/C49, eV, meV/C, Ry, Angstrom, and Bohr magnetons per cell.

## Optional future calculations, not required for the present deadline

1. Compute 70/560 Ry vacancy substrate, adsorbate, and isolated-atom references to obtain vacancy adsorption energies at the higher cutoff.
2. Perform a vacancy-specific smearing sweep and a fuller k-point sweep.
3. Test a larger graphene supercell to quantify vacancy-concentration and image-interaction effects.
4. Explore additional adsorption sites, vacancy reconstructions, and magnetic initializations.
5. Calculate charge transfer, charge-density differences, density of states, and diffusion barriers.
6. Extend the model to charged adsorbates or an electrochemical environment only if the scientific question is changed accordingly.

These items should be presented as future work, not as missing requirements for the current, deliberately scoped term project.
