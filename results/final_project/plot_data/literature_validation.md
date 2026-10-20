# Literature validation of the final data set

## Assessment

The final results are physically credible and reproduce the main published
trends: hollow-site adsorption on pristine graphene, stronger Li adsorption
than Na adsorption, substantially stronger adsorption at a monovacancy, and a
magnetic bare monovacancy. The agreement is strongest for pristine graphene.
The vacancy values agree qualitatively and semi-quantitatively, but the larger
spread means they should not be presented as benchmark-precision numbers.

## Pristine graphene

Olsson et al. used PBE+D3(BJ), a neutral isolated-atom reference, and reported
hollow-site adsorption energies of -1.22 eV for Li and -0.62 eV for Na, with
heights of 1.68 and 2.18 angstrom, respectively. The project 70/560 Ry values
are -1.1677 and -0.5722 eV, only 0.0523 and 0.0478 eV less exothermic. The
project heights of 1.691 and 2.249 angstrom differ by 0.011 and 0.069 angstrom.
This is close agreement given the different code, cell, pseudopotentials, and
sampling.

Primary source: E. Olsson et al., *Nanoscale* **11**, 5274-5284 (2019),
https://doi.org/10.1039/C8NR10383F.

## Monovacancy graphene

Cottom et al. used spin-polarized PBE+D3(BJ) in a 308-site graphene supercell
(307 C atoms after creating one vacancy) and
reported single-atom vacancy binding energies of -3.23 eV for Li and -2.52 eV
for Na. The project values are -2.7174 and -2.0158 eV, about 0.51 and 0.50 eV
less exothermic. Both data sets nevertheless show the same ordering and strong
vacancy anchoring. The difference is plausible for a C49 cell versus a
much larger cell and for different codes, basis sets, k-point treatments,
relaxed structures, and magnetic solutions; it is not evidence by itself of a
failed calculation.

Primary source: J. Cottom et al., *Sustainable Energy & Fuels* **9**,
2813-2826 (2025), https://doi.org/10.1039/D5SE00130G.

## Vacancy magnetism

The calculated bare-C49 moment is 1.60 muB. Yazyev and Helm reported
1.12-1.53 muB per vacancy depending on defect concentration, while Padmanabhan
and Nanda reported a 1.5 muB planar ground state and a competing nonplanar,
nonmagnetic state. The project value is therefore consistent with the expected
magnetic scale, though it is slightly above the first range and does not prove
that all structural or spin minima were found.

Primary sources: O. V. Yazyev and L. Helm, *Physical Review B* **75**, 125408
(2007), https://doi.org/10.1103/PhysRevB.75.125408; H. Padmanabhan and
B. R. K. Nanda, *Physical Review B* **93**, 165403 (2016),
https://doi.org/10.1103/PhysRevB.93.165403.

## Report-safe conclusion

The calculations are validated for the report as a controlled comparison of
the four tested neutral-adatom configurations. They do not establish a global
adsorption-site or spin ground state, bulk-metal plating stability, voltage,
capacity, diffusion barriers, or finite-temperature behavior. The
adsorbate-specific 70/560 Ry check changed pristine Li and Na adsorption by
2.10 and 10.59 meV, respectively, so the reported Li/Na and
pristine/monovacancy differences are much larger than the observed pristine
cutoff sensitivity.
