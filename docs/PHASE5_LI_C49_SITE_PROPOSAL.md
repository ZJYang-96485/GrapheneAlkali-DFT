# Li/C49 vacancy-site proposal — prepared, not launched

The accepted spin-polarized C49 relaxation is the substrate for one neutral-Li
starting-site hypothesis. Its three vacancy-neighbor carbons (the QE `C1`
species) form an asymmetric reconstructed triangle: pair separations are
2.0898, 2.5518, and 2.5536 angstrom. Their centroid is
`(3.69033581, 4.98188374, 9.00000000)` angstrom. The proposed Li starts
2.0 angstrom above that centroid at
`(3.69033581, 4.98188374, 11.00000000)` angstrom; initial Li-to-neighbor-C
distances are 2.3860, 2.3866, and 2.5320 angstrom. These are **starting**
distances, not relaxed-bond results.

This vacancy-centred site is motivated by Li/Na adsorption on defective
graphene in [Dimakis et al., *Molecules* 24, 754 (2019)](https://doi.org/10.3390/molecules24040754).
That literature does not determine the minimum for this exact reconstructed
C49 cell. An off-centre placement toward the under-coordinated neighbor is a
plausible competing hypothesis if time permits; no such second input has been
prepared or tested. One converged relaxation cannot establish a global site or
spin ground state.

The prepared [manifest](../qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260920a_manifest.json)
ties the source structure/output and both inputs to SHA-256 hashes. The
[pilot](../qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260920a_pilot.in)
and [relaxation](../qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260920a_relax.in)
inputs use the accepted C49 cell/coordinates, two carbon labels mapped to the
same approved C UPF, neutral Li using the verified Li UPF, `nspin=2`, the
existing C and C1 spin seeds plus an unconstrained Li seed, PBE+D3(BJ),
2D isolation, 65/520 Ry, unshifted 6x6x1 points, MV smearing at 0.01 Ry,
CG diagonalization, and fresh stage-specific prefixes/scratch. The pilot is
a fixed-geometry SCF; the second input is BFGS relaxation.

No QE program was launched. Because the last Li/C50 GPU validation coincided
with repeated Windows WATCHDOG reports and a WSL `dxgkio_make_resident`
warning, the GPU queue remains paused. Before any future launch, recheck
input hashes, the Windows/WSL resource state, and whether the host-stability
gate has been explicitly cleared. A passed pilot alone would not resolve the
adsorbate-containing cutoff/k-point uncertainty or provide an adsorption
energy without matched C49 and isolated-Li references.
