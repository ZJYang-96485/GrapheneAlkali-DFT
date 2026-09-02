#!/usr/bin/env python3
"""Validate the fixed Phase 1 graphene structures before QE input use."""

from pathlib import Path

import numpy as np
from ase.io import read


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CELL = np.array(
    [
        [12.30000000, 0.00000000, 0.00000000],
        [-6.15000000, 10.65211247, 0.00000000],
        [0.00000000, 0.00000000, 18.00000000],
    ]
)
EXPECTED_COUNTS = {"pristine": 50, "monovacancy": 49}


class StructureValidationError(ValueError):
    """Raised when a Phase 1 structure does not match the fixed model."""


def validate_atoms(atoms, label):
    """Validate one ASE Atoms object and return a short summary."""

    expected_count = EXPECTED_COUNTS[label]
    if len(atoms) != expected_count:
        raise StructureValidationError(
            f"{label}: expected {expected_count} atoms, found {len(atoms)}."
        )

    symbols = set(atoms.get_chemical_symbols())
    if symbols != {"C"}:
        raise StructureValidationError(
            f"{label}: expected only carbon atoms, found {sorted(symbols)}."
        )

    if not np.array_equal(np.asarray(atoms.pbc, dtype=bool), [True, True, True]):
        raise StructureValidationError(
            f"{label}: expected fully periodic PBC (True, True, True), "
            f"found {tuple(bool(value) for value in atoms.pbc)}."
        )

    if not np.allclose(atoms.cell.array, EXPECTED_CELL, atol=1.0e-7):
        raise StructureValidationError(
            f"{label}: cell does not match the validated Phase 1 cell."
        )

    if not np.isclose(atoms.cell.lengths()[2], 18.0, atol=1.0e-7):
        raise StructureValidationError(
            f"{label}: expected c = 18.0 Å, found {atoms.cell.lengths()[2]:.8f} Å."
        )

    if not np.isclose(np.ptp(atoms.positions[:, 2]), 0.0, atol=1.0e-7):
        raise StructureValidationError(f"{label}: atoms are not coplanar in z.")

    return {
        "label": label,
        "atoms": len(atoms),
        "cell_lengths": atoms.cell.lengths(),
        "pbc": tuple(bool(value) for value in atoms.pbc),
    }


def validate_structure_file(label, path):
    """Read and validate a structure file using ASE."""

    path = Path(path)
    if not path.is_file():
        raise StructureValidationError(f"{label}: structure not found: {path}")

    try:
        atoms = read(path)
    except Exception as exc:  # pragma: no cover - depends on ASE reader errors
        raise StructureValidationError(
            f"{label}: ASE could not read {path}: {exc}"
        ) from exc

    return validate_atoms(atoms, label)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate the fixed pristine and monovacancy graphene structures."
    )
    parser.add_argument(
        "--pristine",
        type=Path,
        default=ROOT / "structures/pristine/graphene_5x5_pristine.traj",
    )
    parser.add_argument(
        "--monovacancy",
        type=Path,
        default=ROOT / "structures/monovacancy/graphene_5x5_monovacancy.traj",
    )
    args = parser.parse_args()

    try:
        for label, path in (
            ("pristine", args.pristine),
            ("monovacancy", args.monovacancy),
        ):
            summary = validate_structure_file(label, path)
            print(
                f"{label}: {summary['atoms']} C atoms; "
                f"cell c = {summary['cell_lengths'][2]:.8f} Å; "
                f"pbc = {summary['pbc']}"
            )
    except StructureValidationError as exc:
        parser.error(str(exc))

    print("Structure validation passed.")


if __name__ == "__main__":
    main()
