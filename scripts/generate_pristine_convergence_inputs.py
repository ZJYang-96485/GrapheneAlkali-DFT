#!/usr/bin/env python3
"""Generate fixed-geometry pristine C50 QE inputs for Phase 4 convergence."""

import argparse
import json
from pathlib import Path

from ase.io import read

from generate_qe_inputs import (
    ROOT,
    cell_lines,
    load_config,
    position_lines,
    qe_relative_path,
    qe_scientific,
    quoted,
    require_mapping,
    require_value,
    scalar,
    validate_locked_methodology,
)
from validate_structures import validate_atoms


DEFAULT_OUTPUT_ROOT = ROOT / "qe_inputs/convergence/pristine"
STUDY_ORDER = ("cutoff", "kpoints", "smearing")


def convergence_points():
    points = []
    for ecutwfc, ecutrho in (
        (40, 320),
        (45, 360),
        (50, 400),
        (55, 440),
        (60, 480),
        (65, 520),
        (70, 560),
    ):
        point = {
            "study": "cutoff",
            "tag": f"ecutwfc_{ecutwfc}_ecutrho_{ecutrho}",
            "ecutwfc_ry": ecutwfc,
            "ecutrho_ry": ecutrho,
            "k_mesh": [6, 6, 1],
            "k_shift": [0, 0, 0],
            "degauss_ry": 0.01,
        }
        if ecutwfc >= 50:
            point["diagonalization"] = "cg"
        points.append(point)
    for mesh in (3, 6, 9, 12):
        points.append(
            {
                "study": "kpoints",
                "tag": f"k_{mesh}x{mesh}x1",
                "ecutwfc_ry": 65,
                "ecutrho_ry": 520,
                "k_mesh": [mesh, mesh, 1],
                "k_shift": [0, 0, 0],
                "degauss_ry": 0.01,
                "diagonalization": "cg",
            }
        )
    for label, degauss in (("0p005", 0.005), ("0p010", 0.010), ("0p020", 0.020)):
        points.append(
            {
                "study": "smearing",
                "tag": f"degauss_{label}",
                "ecutwfc_ry": 65,
                "ecutrho_ry": 520,
                "k_mesh": [6, 6, 1],
                "k_shift": [0, 0, 0],
                "degauss_ry": degauss,
                "diagonalization": "cg",
            }
        )
    return points


def cg_diagnostic_point():
    return {
        "study": "diagnostics",
        "tag": "ecutwfc_50_ecutrho_400_diagonalization_cg",
        "ecutwfc_ry": 50,
        "ecutrho_ry": 400,
        "k_mesh": [6, 6, 1],
        "k_shift": [0, 0, 0],
        "degauss_ry": 0.01,
        "diagonalization": "cg",
    }


def cg_cutoff_reference_point():
    return {
        "study": "cutoff_reference",
        "tag": "ecutwfc_55_ecutrho_440_diagonalization_cg",
        "ecutwfc_ry": 55,
        "ecutrho_ry": 440,
        "k_mesh": [6, 6, 1],
        "k_shift": [0, 0, 0],
        "degauss_ry": 0.01,
        "diagonalization": "cg",
    }


def render_scf_input(atoms, config, point):
    paths = require_mapping(config, "paths", "config")
    pseudos = require_mapping(config, "pseudopotentials", "config")
    dft = require_mapping(config, "dft", "config")
    relaxation = require_mapping(config, "relaxation", "config")
    validate_locked_methodology(dft, relaxation)

    dispersion = require_mapping(dft, "dispersion", "dft")
    pseudo_files = require_mapping(pseudos, "files", "pseudopotentials")
    carbon_pseudo = require_value(pseudo_files, "C", "pseudopotentials.files")
    prefix = f"c50_conv_{point['study']}_{point['tag']}"
    outdir = Path(paths.get("scratch_root", "qe_scratch")) / "convergence/pristine" / point["study"] / point["tag"]

    lines = [
        "! Phase 4 fixed-geometry pristine C50 convergence calculation.",
        f"! Study: {point['study']}; point: {point['tag']}",
        "! Method held fixed: PBE-D3(BJ), 2D Coulomb isolation, approved SSSP carbon PAW.",
        "",
        "&CONTROL",
        "   calculation = 'scf',",
        "   restart_mode = 'from_scratch',",
        f"   prefix = {quoted(prefix)},",
        f"   pseudo_dir = {quoted(qe_relative_path(paths['pseudo_dir']))},",
        f"   outdir = {quoted(qe_relative_path(outdir))},",
        "/",
        "",
        "&SYSTEM",
        "   ibrav = 0,",
        f"   nat = {len(atoms)},",
        "   ntyp = 1,",
        f"   input_dft = {quoted(dft['xc_functional'])},",
        f"   vdw_corr = {quoted(dispersion['qe_vdw_corr'])},",
        f"   dftd3_version = {scalar(dispersion['qe_dftd3_version'])},",
        f"   dftd3_threebody = {scalar(dispersion.get('threebody', True))},",
        f"   assume_isolated = {quoted(dft['assume_isolated'])},",
        f"   ecutwfc = {scalar(point['ecutwfc_ry'])},",
        f"   ecutrho = {scalar(point['ecutrho_ry'])},",
        "   nspin = 1,",
        f"   occupations = {quoted(dft['occupations'])},",
        f"   smearing = {quoted(dft['smearing'])},",
        f"   degauss = {scalar(point['degauss_ry'])},",
        "/",
        "",
        "&ELECTRONS",
        f"   conv_thr = {qe_scientific(dft['conv_thr'])},",
        f"   mixing_beta = {scalar(dft['mixing_beta'])},",
    ]
    if point.get("diagonalization"):
        lines.append(f"   diagonalization = {quoted(point['diagonalization'])},")
    lines.extend(
        [
            "/",
            "",
            "ATOMIC_SPECIES",
            f"C   12.011  {carbon_pseudo}",
            "",
            *cell_lines(atoms),
            "",
            *position_lines(atoms),
            "",
            "K_POINTS automatic",
            "  " + "  ".join(str(value) for value in (*point["k_mesh"], *point["k_shift"])),
            "",
        ]
    )
    return "\n".join(lines), prefix, qe_relative_path(outdir)


def generate(config_path, output_root, studies, explicit_points=None):
    config = load_config(config_path)
    pristine_config = config["systems"]["pristine"]
    structure_path = Path(pristine_config["structure"])
    if not structure_path.is_absolute():
        structure_path = ROOT / structure_path
    atoms = read(structure_path)
    validate_atoms(atoms, "pristine")

    output_root = Path(output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    selected = explicit_points or [
        point for point in convergence_points() if point["study"] in studies
    ]
    manifest = []
    for point in selected:
        content, prefix, outdir = render_scf_input(atoms, config, point)
        target_dir = output_root / point["study"]
        target_dir.mkdir(parents=True, exist_ok=True)
        input_path = target_dir / f"{point['tag']}.in"
        input_path.write_text(content, encoding="utf-8", newline="\n")
        record = dict(point)
        record.update(
            {
                "nat": len(atoms),
                "prefix": prefix,
                "outdir": outdir,
                "input": input_path.relative_to(ROOT).as_posix(),
                "output": (
                    Path("results/convergence/pristine")
                    / point["study"]
                    / f"{point['tag']}.out"
                ).as_posix(),
            }
        )
        manifest.append(record)
        print(f"Generated {record['input']}")

    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated {manifest_path.relative_to(ROOT).as_posix()}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/qe.yaml")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--study",
        action="append",
        choices=STUDY_ORDER,
        help="Generate one study; repeat as needed. Default: all studies.",
    )
    parser.add_argument(
        "--cg-diagnostic",
        action="store_true",
        help="Generate only the approved 50/400 conjugate-gradient diagnostic.",
    )
    parser.add_argument(
        "--cg-cutoff-reference",
        action="store_true",
        help="Generate only the approved 55/440 conjugate-gradient cutoff reference.",
    )
    args = parser.parse_args()
    if args.cg_diagnostic and args.cg_cutoff_reference:
        parser.error("choose only one CG special-point generator")
    if args.cg_diagnostic:
        diagnostic_root = (
            args.output_root
            if args.output_root != DEFAULT_OUTPUT_ROOT
            else ROOT / "qe_inputs/diagnostics/pristine"
        )
        generate(
            args.config,
            diagnostic_root,
            ("diagnostics",),
            explicit_points=[cg_diagnostic_point()],
        )
        return 0
    if args.cg_cutoff_reference:
        reference_root = (
            args.output_root
            if args.output_root != DEFAULT_OUTPUT_ROOT
            else ROOT / "qe_inputs/diagnostics/pristine/cutoff_reference"
        )
        generate(
            args.config,
            reference_root,
            ("cutoff_reference",),
            explicit_points=[cg_cutoff_reference_point()],
        )
        return 0
    studies = tuple(args.study) if args.study else STUDY_ORDER
    generate(args.config, args.output_root, studies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
