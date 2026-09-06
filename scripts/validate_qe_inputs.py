#!/usr/bin/env python3
"""Validate the generated Phase 2C bare-substrate QE inputs."""

import re
import sys
from pathlib import Path

import numpy as np
from ase.io import read

from generate_qe_inputs import (
    QE_VACANCY_C_LABEL,
    UNRESOLVED,
    infer_vacancy_neighbors,
    load_config,
)
from validate_structures import EXPECTED_CELL, validate_atoms


ROOT = Path(__file__).resolve().parents[1]


def validate_configuration():
    config = load_config(ROOT / "config/qe.yaml")
    expected_pseudos = {
        "C": "C.pbe-n-kjpaw_psl.1.0.0.UPF",
        "Li": "li_pbe_v1.4.uspp.F.UPF",
        "Na": "na_pbe_v1.5.uspp.F.UPF",
    }
    if config["pseudopotentials"]["files"] != expected_pseudos:
        raise ValueError("configuration: unexpected pseudopotential filenames")
    if config["final_scf"]["k_points"] != {"mesh": [9, 9, 1], "shift": [0, 0, 0]}:
        raise ValueError("configuration: incorrect final-SCF k-points")
    if float(config["final_scf"]["degauss_ry"]) != 0.005:
        raise ValueError("configuration: incorrect final-SCF degauss")
    if config["dos"]["k_points"] != {"mesh": [12, 12, 1], "shift": [0, 0, 0]}:
        raise ValueError("configuration: incorrect DOS k-points")
    print("configuration: PASS - locked relaxation, final-SCF, DOS, and pseudopotential values")


def namelist_integer(text, name):
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(\d+)\s*,", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing integer setting: {name}")
    return int(match.group(1))


def card_rows(text, card, row_count):
    match = re.search(rf"^{re.escape(card)}[^\n]*\n", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing card: {card}")
    rows = text[match.end() :].splitlines()[:row_count]
    if len(rows) != row_count or any(not row.strip() for row in rows):
        raise ValueError(f"{card}: expected {row_count} data rows")
    return rows


def require_patterns(text, patterns, label):
    for description, pattern in patterns:
        if not re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            raise ValueError(f"{label}: missing or incorrect {description}")


def validate_one(label, expected_atoms, expected_nspin):
    path = ROOT / f"qe_inputs/relaxation/{label}/relax_{label}.in"
    text = path.read_text(encoding="utf-8")
    if UNRESOLVED in text:
        raise ValueError(f"{label}: unresolved placeholder found")
    if re.search(r"vc-relax", text, re.IGNORECASE):
        raise ValueError(f"{label}: vc-relax is forbidden")
    if re.search(r"^\s*nbnd\s*=", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError(f"{label}: nbnd must remain automatic/unset")
    if re.search(
        r"^\s*(?:tot_magnetization|constrained_magnetization|fixed_magnetization)\s*=",
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        raise ValueError(f"{label}: final magnetization must remain unconstrained")

    ntyp = 2 if label == "monovacancy" else 1
    if namelist_integer(text, "nat") != expected_atoms:
        raise ValueError(f"{label}: incorrect nat")
    if namelist_integer(text, "ntyp") != ntyp:
        raise ValueError(f"{label}: incorrect ntyp")
    if namelist_integer(text, "nspin") != expected_nspin:
        raise ValueError(f"{label}: incorrect nspin")

    common = (
        ("fixed-cell relax", r"^\s*calculation\s*=\s*['\"]relax['\"]\s*,"),
        ("PBE", r"^\s*input_dft\s*=\s*['\"]PBE['\"]\s*,"),
        ("DFT-D3", r"^\s*vdw_corr\s*=\s*['\"]dft-d3['\"]\s*,"),
        ("BJ damping", r"^\s*dftd3_version\s*=\s*4\s*,"),
        ("2D isolation", r"^\s*assume_isolated\s*=\s*['\"]2D['\"]\s*,"),
        ("wavefunction cutoff", r"^\s*ecutwfc\s*=\s*50\s*,"),
        ("density cutoff", r"^\s*ecutrho\s*=\s*400\s*,"),
        ("MV smearing", r"^\s*smearing\s*=\s*['\"]mv['\"]\s*,"),
        ("relaxation smearing width", r"^\s*degauss\s*=\s*0\.01\s*,"),
        ("SCF threshold", r"^\s*conv_thr\s*=\s*1\.0d-8\s*,"),
        ("force threshold", r"^\s*forc_conv_thr\s*=\s*4\.0d-4\s*,"),
        ("mixing beta", r"^\s*mixing_beta\s*=\s*0\.3\s*,"),
        ("BFGS ions", r"^\s*ion_dynamics\s*=\s*['\"]bfgs['\"]\s*,"),
        ("6x6x1 Gamma-centered grid", r"^\s*6\s+6\s+1\s+0\s+0\s+0\s*$"),
    )
    require_patterns(text, common, label)

    cell = np.array([[float(value) for value in row.split()] for row in card_rows(text, "CELL_PARAMETERS", 3)])
    if not np.array_equal(cell, EXPECTED_CELL):
        raise ValueError(f"{label}: cell changed")

    species_rows = card_rows(text, "ATOMIC_SPECIES", ntyp)
    species = [row.split() for row in species_rows]
    expected_species_labels = {"C", QE_VACANCY_C_LABEL} if label == "monovacancy" else {"C"}
    if {row[0] for row in species} != expected_species_labels:
        raise ValueError(f"{label}: incorrect ATOMIC_SPECIES labels")
    if {row[2] for row in species} != {"C.pbe-n-kjpaw_psl.1.0.0.UPF"}:
        raise ValueError(f"{label}: carbon species must share the locked C pseudopotential")

    position_rows = card_rows(text, "ATOMIC_POSITIONS", expected_atoms)
    labels = [row.split()[0] for row in position_rows]
    positions = np.array([[float(value) for value in row.split()[1:4]] for row in position_rows])
    structure = read(ROOT / f"structures/{label}/graphene_5x5_{label}.traj")
    if not np.allclose(positions, structure.positions, atol=1.0e-8):
        raise ValueError(f"{label}: rendered coordinates differ from ASE structure")

    if label == "pristine":
        if set(labels) != {"C"}:
            raise ValueError("pristine: unexpected atomic-type label")
    else:
        monovacancy = structure
        pristine = read(ROOT / "structures/pristine/graphene_5x5_pristine.traj")
        expected_neighbors, vacancy_position, distances = infer_vacancy_neighbors(pristine, monovacancy)
        actual_neighbors = tuple(index for index, atom_label in enumerate(labels) if atom_label == QE_VACANCY_C_LABEL)
        if set(actual_neighbors) != set(expected_neighbors):
            raise ValueError("monovacancy: local spin labels do not match geometric neighbors")
        require_patterns(
            text,
            (
                ("bulk-C spin seed", r"^\s*starting_magnetization\(1\)\s*=\s*0(?:\.0)?\s*,"),
                ("vacancy-neighbor spin seed", r"^\s*starting_magnetization\(2\)\s*=\s*0\.1\s*,"),
            ),
            label,
        )
        print(
            "monovacancy geometry: missing site at "
            f"({vacancy_position[0]:.8f}, {vacancy_position[1]:.8f}, {vacancy_position[2]:.8f}) angstrom; "
            f"neighbor indices (0-based)={expected_neighbors}; distances={tuple(round(x, 8) for x in distances)}"
        )

    print(f"{label}: PASS - nat={expected_atoms}, ntyp={ntyp}, nspin={expected_nspin}")


def main():
    try:
        validate_configuration()
        pristine = read(ROOT / "structures/pristine/graphene_5x5_pristine.traj")
        monovacancy = read(ROOT / "structures/monovacancy/graphene_5x5_monovacancy.traj")
        validate_atoms(pristine, "pristine")
        validate_atoms(monovacancy, "monovacancy")
        validate_one("pristine", 50, 1)
        validate_one("monovacancy", 49, 2)
    except (OSError, ValueError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    print("Generated QE input validation passed; no pw.x calculation was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
