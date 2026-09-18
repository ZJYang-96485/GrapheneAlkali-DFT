#!/usr/bin/env python3
"""Audit every generated Phase 4 pristine convergence input before execution."""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from ase.io import read

from generate_qe_inputs import ROOT, UNRESOLVED
from validate_qe_inputs import card_rows, namelist_integer, require_patterns
from validate_structures import EXPECTED_CELL, validate_atoms


FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def numeric_setting(text, name):
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*({FLOAT})\s*,",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing numeric setting: {name}")
    return float(match.group(1).replace("D", "E").replace("d", "e"))


def quoted_setting(text, name):
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]\s*,",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing quoted setting: {name}")
    return match.group(1)


def validate_record(record, structure):
    path = ROOT / record["input"]
    if not path.is_file():
        raise ValueError(f"missing generated input: {record['input']}")
    text = path.read_text(encoding="utf-8")
    label = f"{record['study']}/{record['tag']}"

    if UNRESOLVED in text:
        raise ValueError(f"{label}: unresolved placeholder")
    if re.search(r"^\s*&IONS\b", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError(f"{label}: fixed-geometry SCF must not contain &IONS")
    if re.search(r"vc-relax", text, re.IGNORECASE):
        raise ValueError(f"{label}: vc-relax is forbidden")
    if re.search(r"^\s*(Li|Na)\s+", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError(f"{label}: Li or Na appeared in Phase 4 convergence input")

    require_patterns(
        text,
        (
            ("SCF calculation", r"^\s*calculation\s*=\s*['\"]scf['\"]\s*,"),
            ("fresh restart", r"^\s*restart_mode\s*=\s*['\"]from_scratch['\"]\s*,"),
            ("PBE", r"^\s*input_dft\s*=\s*['\"]PBE['\"]\s*,"),
            ("DFT-D3", r"^\s*vdw_corr\s*=\s*['\"]dft-d3['\"]\s*,"),
            ("BJ damping", r"^\s*dftd3_version\s*=\s*4\s*,"),
            ("D3 three-body", r"^\s*dftd3_threebody\s*=\s*\.true\.\s*,"),
            ("2D isolation", r"^\s*assume_isolated\s*=\s*['\"]2D['\"]\s*,"),
            ("spin-unpolarized pristine", r"^\s*nspin\s*=\s*1\s*,"),
            ("smearing occupations", r"^\s*occupations\s*=\s*['\"]smearing['\"]\s*,"),
            ("MV smearing", r"^\s*smearing\s*=\s*['\"]mv['\"]\s*,"),
            ("SCF threshold", r"^\s*conv_thr\s*=\s*1\.0d-8\s*,"),
            ("mixing beta", r"^\s*mixing_beta\s*=\s*0\.3\s*,"),
            ("explicit cell units", r"^CELL_PARAMETERS\s+angstrom\s*$"),
            ("explicit coordinate units", r"^ATOMIC_POSITIONS\s+angstrom\s*$"),
            ("automatic k-points", r"^K_POINTS\s+automatic\s*$"),
        ),
        label,
    )

    if namelist_integer(text, "ibrav") != 0:
        raise ValueError(f"{label}: ibrav must be 0")
    if namelist_integer(text, "nat") != 50 or namelist_integer(text, "ntyp") != 1:
        raise ValueError(f"{label}: expected nat=50 and ntyp=1")
    if not np.isclose(numeric_setting(text, "ecutwfc"), record["ecutwfc_ry"]):
        raise ValueError(f"{label}: ecutwfc differs from manifest")
    if not np.isclose(numeric_setting(text, "ecutrho"), record["ecutrho_ry"]):
        raise ValueError(f"{label}: ecutrho differs from manifest")
    if not np.isclose(numeric_setting(text, "degauss"), record["degauss_ry"]):
        raise ValueError(f"{label}: degauss differs from manifest")
    if quoted_setting(text, "prefix") != record["prefix"]:
        raise ValueError(f"{label}: prefix differs from manifest")
    if quoted_setting(text, "outdir") != record["outdir"]:
        raise ValueError(f"{label}: outdir differs from manifest")
    if record.get("diagonalization"):
        if quoted_setting(text, "diagonalization") != record["diagonalization"]:
            raise ValueError(f"{label}: diagonalization differs from manifest")
    elif re.search(r"^\s*diagonalization\s*=", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError(f"{label}: unrequested diagonalization override")

    species = card_rows(text, "ATOMIC_SPECIES", 1)[0].split()
    if species[0] != "C" or species[2] != "C.pbe-n-kjpaw_psl.1.0.0.UPF":
        raise ValueError(f"{label}: incorrect carbon ATOMIC_SPECIES record")

    cell = np.asarray(
        [[float(value) for value in row.split()] for row in card_rows(text, "CELL_PARAMETERS", 3)]
    )
    if not np.array_equal(cell, EXPECTED_CELL):
        raise ValueError(f"{label}: fixed cell changed")

    position_rows = card_rows(text, "ATOMIC_POSITIONS", 50)
    if any(row.split()[0] != "C" or len(row.split()) != 4 for row in position_rows):
        raise ValueError(f"{label}: expected exactly 50 carbon coordinate records")
    positions = np.asarray([[float(value) for value in row.split()[1:4]] for row in position_rows])
    if not np.allclose(positions, structure.positions, atol=1.0e-8):
        raise ValueError(f"{label}: coordinates differ from fixed pristine structure")

    k_rows = card_rows(text, "K_POINTS", 1)[0].split()
    expected_k = [str(value) for value in (*record["k_mesh"], *record["k_shift"])]
    if k_rows != expected_k:
        raise ValueError(f"{label}: k-point row {k_rows} differs from {expected_k}")

    print(
        f"{label}: PASS - {record['ecutwfc_ry']}/{record['ecutrho_ry']} Ry; "
        f"k={tuple(record['k_mesh'])}; degauss={record['degauss_ry']} Ry"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "qe_inputs/convergence/pristine/manifest.json",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        help="Optional exact record count; by default the manifest is authoritative.",
    )
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.expected_count is not None and len(manifest) != args.expected_count:
            raise ValueError(
                f"expected {args.expected_count} convergence points, found {len(manifest)}"
            )
        # One completed 65/520, 6x6x1, 0.010 Ry calculation is deliberately
        # reused in the cutoff, k-point, and smearing views. A prefix/outdir may
        # therefore repeat only when every execution-defining field, including
        # the input and output paths, is identical.
        for shared_field in ("prefix", "outdir"):
            groups = {}
            for record in manifest:
                identity = {
                    key: value
                    for key, value in record.items()
                    if key not in ("study", "tag")
                }
                groups.setdefault(record[shared_field], set()).add(
                    json.dumps(identity, sort_keys=True)
                )
            conflicting = [key for key, identities in groups.items() if len(identities) > 1]
            if conflicting:
                raise ValueError(
                    f"{shared_field} is reused by non-identical runs: {conflicting}"
                )

        structure = read(ROOT / "structures/pristine/graphene_5x5_pristine.traj")
        validate_atoms(structure, "pristine")
        for record in manifest:
            validate_record(record, structure)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"convergence input validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"All {len(manifest)} pristine convergence inputs passed the Phase 4 audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
