# C49 monovacancy symmetry pre-flight

## Decision

**STOP before production relaxation. Explicit approval is required for a
symmetry-breaking starting perturbation.**

The present C49 input is chemically and numerically coherent, but its three
vacancy-neighbor atoms are exactly symmetry-equivalent. Launching it unchanged
risks trapping the relaxation in the high-symmetry vacancy configuration.

## Audited setup

- 49 carbon atoms; no Li or Na
- spin-polarized (`nspin = 2`)
- three vacancy-neighbor atoms labeled `C1`
- both `C` and `C1` use the same approved carbon UPF
- `starting_magnetization(C) = 0.0` and
  `starting_magnetization(C1) = 0.1`; these are initial seeds, not constraints
- PBE+D3(BJ), 2D isolation, 65/520 Ry, 6x6x1 unshifted k points, MV 0.01 Ry,
  CG diagonalization, fixed-cell BFGS
- QE symmetry is enabled because `nosym` is absent and defaults to false

## Geometry evidence

The three `C1` coordinates are:

1. `(2.46000000, 4.26084499, 9.00000000)` angstrom
2. `(4.92000000, 4.26084499, 9.00000000)` angstrom
3. `(3.69000000, 6.39126748, 9.00000000)` angstrom

Their pair distances are `2.4600000000`, `2.4599999971`, and
`2.4599999971 angstrom`. Each lies `1.42028166 angstrom` from the missing-site
centroid `(3.69000000, 4.97098582, 9.00000000)`. The triangle is equilateral at
the precision of the input. Giving all three atoms the same `C1` type and spin
seed preserves that equivalence for QE's symmetry detection.

The official QE documentation states that symmetry is used by default and the
charge density is symmetrized; `nosym = .true.` disables this and expands an
automatic grid over the Brillouin zone:
<https://www.quantum-espresso.org/Doc/INPUT_PW.html>.

Primary experimental/theoretical work reports the lower-energy asymmetric
graphene monovacancy and its Jahn-Teller reconstruction:
<https://pubs.acs.org/doi/10.1021/nn401113r>. First-principles vacancy work also
finds defect magnetic moments that depend on defect concentration:
<https://doi.org/10.1103/PhysRevB.75.125408>.

## Proposed minimal change

If approved, shift only vacancy neighbor 1 by `+0.01000000 angstrom` along x,
toward vacancy neighbor 2:

```text
C1   2.47000000  4.26084499  9.00000000
```

All other coordinates and all physical/numerical settings would remain
unchanged. This 0.01 angstrom seed is large relative to QE's symmetry tolerance
but only about 0.4% of the initial neighbor-pair separation. It selects one of
the three symmetry-equivalent reconstruction directions without imposing the
final bond length.

Leave `nosym` unset for the first proposal: the deliberately perturbed geometry
should cause QE to detect the reduced symmetry automatically. Before launch,
inspect QE's reported symmetry and k-point reduction. If QE still reports an
operation that maps the three vacancy neighbors, stop and separately propose
`nosym = .true.` rather than silently changing it.

Because reduced symmetry plus `nspin = 2` may increase computational and GPU
memory cost, the approved run should use fresh scratch and full resource
monitoring. No vacancy coordinate has been changed and no vacancy calculation
has been launched during this pre-flight.
