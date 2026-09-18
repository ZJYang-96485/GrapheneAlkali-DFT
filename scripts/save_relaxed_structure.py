#!/usr/bin/env python3
"""Save a strictly accepted QE relaxation and summarize structural changes."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from ase.geometry import find_mic
from ase.io import read, write

from generate_qe_inputs import infer_vacancy_neighbors
from parse_qe_output import QEOutputParseError, parse_output


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qe_output", type=Path)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output-stem", type=Path, required=True)
    parser.add_argument(
        "--pristine",
        type=Path,
        help="Pristine reference used to identify the three vacancy neighbors.",
    )
    parser.add_argument("--analysis-json", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        parsed = parse_output(args.qe_output, calculation="relax")
    except (OSError, QEOutputParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    coordinates = parsed["final_coordinates"]
    template = read(args.template)
    if len(coordinates) != len(template):
        print(
            f"error: QE has {len(coordinates)} final coordinates but the template "
            f"has {len(template)} atoms.",
            file=sys.stderr,
        )
        return 2
    units = {entry["units"].strip().lower() for entry in coordinates}
    if units != {"angstrom"}:
        print(f"error: expected angstrom final coordinates, found {sorted(units)}.", file=sys.stderr)
        return 2

    relaxed = template.copy()
    initial_positions = template.positions.copy()
    relaxed.positions = np.array(
        [[entry["x"], entry["y"], entry["z"]] for entry in coordinates],
        dtype=float,
    )

    displacements, displacement_lengths = find_mic(
        relaxed.positions - initial_positions,
        relaxed.cell,
        pbc=relaxed.pbc,
    )
    analysis = {
        "qe_output": str(args.qe_output),
        "qe_output_sha256": sha256(args.qe_output),
        "template": str(args.template),
        "template_sha256": sha256(args.template),
        "atom_count": len(relaxed),
        "maximum_displacement_angstrom": float(displacement_lengths.max()),
        "rms_displacement_angstrom": float(
            np.sqrt(np.mean(np.square(displacement_lengths)))
        ),
        "maximum_out_of_plane_displacement_angstrom": float(
            np.max(np.abs(displacements[:, 2]))
        ),
        "qe_result": parsed,
    }

    if args.pristine:
        pristine = read(args.pristine)
        neighbor_indices, vacancy_position, initial_neighbor_distances = (
            infer_vacancy_neighbors(pristine, template)
        )
        pairs = [
            (neighbor_indices[0], neighbor_indices[1]),
            (neighbor_indices[0], neighbor_indices[2]),
            (neighbor_indices[1], neighbor_indices[2]),
        ]
        analysis["vacancy"] = {
            "position_angstrom": [float(value) for value in vacancy_position],
            "neighbor_indices_zero_based": list(neighbor_indices),
            "neighbor_indices_qe_one_based": [index + 1 for index in neighbor_indices],
            "initial_neighbor_to_vacancy_distances_angstrom": list(
                initial_neighbor_distances
            ),
            "final_neighbor_pair_distances_angstrom": [
                float(relaxed.get_distance(first, second, mic=True))
                for first, second in pairs
            ],
        }

    traj_path = args.output_stem.with_suffix(".traj")
    xyz_path = args.output_stem.with_suffix(".xyz")
    targets = [traj_path, xyz_path]
    if args.analysis_json:
        targets.append(args.analysis_json)
    existing = [path for path in targets if path.exists()]
    if existing:
        print(
            "error: refusing to overwrite existing output(s): "
            + ", ".join(str(path) for path in existing),
            file=sys.stderr,
        )
        return 2

    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
    write(traj_path, relaxed)
    write(xyz_path, relaxed)
    analysis["relaxed_traj"] = str(traj_path)
    analysis["relaxed_traj_sha256"] = sha256(traj_path)
    analysis["relaxed_xyz"] = str(xyz_path)
    analysis["relaxed_xyz_sha256"] = sha256(xyz_path)
    if args.analysis_json:
        args.analysis_json.write_text(
            json.dumps(analysis, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(analysis, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
