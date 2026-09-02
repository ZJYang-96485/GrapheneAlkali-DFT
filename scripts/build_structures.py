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
PRISTINE_DIR = ROOT / "structures" / "pristine"
VACANCY_DIR = ROOT / "structures" / "monovacancy"


def build_pristine_graphene():
    """Build a periodic N x N pristine graphene supercell."""

    atoms = graphene(
        a=LATTICE_CONSTANT_ANG,
        size=(SUPERCELL_SIZE, SUPERCELL_SIZE, 1),
        vacuum=VACUUM_GAP_ANG / 2.0,
    )

    atoms.pbc = (True, True, False)

    return atoms


def find_central_atom(atoms):
    """
    Find the carbon atom closest to the in-plane center
    of the periodic supercell.

    Fractional coordinates are used so this remains robust
    for graphene's non-orthogonal in-plane lattice vectors.
    """

    scaled = atoms.get_scaled_positions(wrap=True)

    # Distance from fractional center in x-y.
    delta = scaled[:, :2] - np.array([0.5, 0.5])

    # Apply periodic wrapping in-plane.
    delta -= np.round(delta)

    cell = atoms.cell.array

    # Convert fractional in-plane displacement to Cartesian.
    cartesian_delta = (
        delta[:, 0, None] * cell[0]
        + delta[:, 1, None] * cell[1]
    )

    distances = np.linalg.norm(cartesian_delta[:, :2], axis=1)

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


def main():
    pristine = build_pristine_graphene()

    vacancy, removed_index, removed_position = build_monovacancy(
        pristine
    )

    save_structure(
        pristine,
        PRISTINE_DIR,
        "graphene_5x5_pristine",
    )

    save_structure(
        vacancy,
        VACANCY_DIR,
        "graphene_5x5_monovacancy",
    )

    print("Structure generation complete.")
    print(f"Pristine graphene atoms:    {len(pristine)}")
    print(f"Monovacancy graphene atoms: {len(vacancy)}")
    print(f"Removed atom index:          {removed_index}")
    print(
        "Removed atom position (Å):  "
        f"{removed_position[0]:.4f}, "
        f"{removed_position[1]:.4f}, "
        f"{removed_position[2]:.4f}"
    )

    assert len(pristine) == 50, (
        "Expected 50 C atoms for 5x5 pristine graphene."
    )

    assert len(vacancy) == 49, (
        "Expected 49 C atoms after creating one vacancy."
    )


if __name__ == "__main__":
    main()