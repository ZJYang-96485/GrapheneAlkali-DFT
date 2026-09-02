import argparse
from pathlib import Path

import numpy as np
from ase.build import graphene
from ase.io import write


# ============================================================
# User-configurable structure parameters
# ============================================================

SUPERCELL_SIZE = 5
LATTICE_CONSTANT_ANG = 2.46

# Total empty spacing between periodic graphene sheets.
# ASE's vacuum argument is applied on both sides, so use half.
VACUUM_GAP_ANG = 18.0

ROOT = Path(__file__).resolve().parents[1]


def build_pristine_graphene(
    size=SUPERCELL_SIZE,
    lattice_constant_ang=LATTICE_CONSTANT_ANG,
    vacuum_gap_ang=VACUUM_GAP_ANG,
):
    """Build a periodic N x N pristine graphene supercell."""

    if size < 1:
        raise ValueError("Supercell size must be a positive integer.")
    if vacuum_gap_ang < 0:
        raise ValueError("Vacuum gap must be non-negative.")

    atoms = graphene(
        a=lattice_constant_ang,
        size=(size, size, 1),
        # ASE applies vacuum on both sides of the sheet.  Half of
        # the requested total gap therefore goes on each side.
        vacuum=vacuum_gap_ang / 2.0,
    )

    # Quantum ESPRESSO uses a fully periodic plane-wave cell.  The
    # 18 Å c-axis supplies the vacuum between periodic graphene sheets.
    atoms.pbc = (True, True, True)

    return atoms


def find_central_atom(atoms):
    """
    Find the carbon atom closest to the in-plane center
    of the periodic supercell.

    The center is taken as the geometric center of the two in-plane
    cell vectors, so this remains robust for graphene's non-orthogonal
    in-plane lattice vectors.
    """

    cell = atoms.cell.array
    center = 0.5 * (cell[0] + cell[1])
    distances = np.linalg.norm(atoms.positions[:, :2] - center[:2], axis=1)

    return int(np.argmin(distances))


def build_monovacancy(pristine):
    """Create a monovacancy by removing the central C atom."""

    vacancy = pristine.copy()

    index = find_central_atom(vacancy)
    removed_position = vacancy[index].position.copy()

    del vacancy[index]

    return vacancy, index, removed_position


def save_structure(atoms, directory, stem):
    """
    Save structures in formats convenient for both visualization
    and later computational workflows.
    """

    directory.mkdir(parents=True, exist_ok=True)

    # Human-readable / easy visualization
    write(directory / f"{stem}.xyz", atoms)

    # Retains periodic cell information; convenient for VESTA
    write(directory / f"{stem}.cif", atoms)

    # ASE-native format; best for later Python workflows
    write(directory / f"{stem}.traj", atoms)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate pristine and monovacancy graphene structures."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=SUPERCELL_SIZE,
        help=f"N for the N x N graphene supercell (default: {SUPERCELL_SIZE})",
    )
    parser.add_argument(
        "--lattice-constant",
        type=float,
        default=LATTICE_CONSTANT_ANG,
        help=(
            "Graphene lattice constant in Angstrom "
            f"(default: {LATTICE_CONSTANT_ANG})"
        ),
    )
    parser.add_argument(
        "--vacuum-gap",
        type=float,
        default=VACUUM_GAP_ANG,
        help=(
            "Total out-of-plane vacuum gap in Angstrom "
            f"(default: {VACUUM_GAP_ANG})"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "structures",
        help="Root directory for generated structures.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    pristine = build_pristine_graphene(
        size=args.size,
        lattice_constant_ang=args.lattice_constant,
        vacuum_gap_ang=args.vacuum_gap,
    )

    vacancy, removed_index, removed_position = build_monovacancy(
        pristine
    )

    pristine_dir = args.output_root / "pristine"
    vacancy_dir = args.output_root / "monovacancy"
    pristine_stem = f"graphene_{args.size}x{args.size}_pristine"
    vacancy_stem = f"graphene_{args.size}x{args.size}_monovacancy"

    save_structure(
        pristine,
        pristine_dir,
        pristine_stem,
    )

    save_structure(
        vacancy,
        vacancy_dir,
        vacancy_stem,
    )

    print("Structure generation complete.")
    print(f"Supercell size:              {args.size} x {args.size}")
    print(f"Lattice constant (Å):       {args.lattice_constant:.4f}")
    print(f"Total vacuum gap (Å):       {args.vacuum_gap:.4f}")
    print(f"Pristine graphene atoms:    {len(pristine)}")
    print(f"Monovacancy graphene atoms: {len(vacancy)}")
    print(f"Removed atom index:          {removed_index}")
    print(
        "Removed atom position (Å):  "
        f"{removed_position[0]:.4f}, "
        f"{removed_position[1]:.4f}, "
        f"{removed_position[2]:.4f}"
    )

    assert len(vacancy) == len(pristine) - 1, (
        "Expected exactly one carbon atom to be removed."
    )

    if args.size == 5:
        assert len(pristine) == 50, (
            "Expected 50 C atoms for 5x5 pristine graphene."
        )
        assert len(vacancy) == 49, (
            "Expected 49 C atoms after creating one vacancy."
        )


if __name__ == "__main__":
    main()
