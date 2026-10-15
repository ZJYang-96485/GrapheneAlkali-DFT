#!/usr/bin/env python3
"""Prepare one auditable neutral-Na/C50 hollow-site pilot and relaxation."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from ase import Atom
from ase.io import read, write

from generate_qe_inputs import cell_lines, format_coordinate, load_config, qe_scientific
from parse_qe_output import parse_output
from prepare_li_pristine_hollow import digest, hollow_site


ROOT = Path(__file__).resolve().parents[1]
NA_MD5 = "44600605ef58000f06b90626533354dc"
SOURCE = ROOT / "structures/relaxed/pristine/graphene_5x5_pristine_relaxed.traj"
SOURCE_OUTPUT = ROOT / "results/relaxation/pristine/relax_pristine_65_520_cg_20260916.out"
INITIAL_HEIGHT_ANGSTROM = 2.5


def render_input(atoms, config, calculation, prefix, outdir):
    dft = config["dft"]
    relax = config["relaxation"]
    files = config["pseudopotentials"]["files"]
    dispersion = dft["dispersion"]
    if (
        dft["xc_functional"] != "PBE"
        or dispersion["qe_vdw_corr"] != "dft-d3"
        or dispersion["qe_dftd3_version"] != 4
        or dft["assume_isolated"] != "2D"
        or dft["diagonalization"] != "cg"
        or float(dft["ecutwfc_ry"]) != 65
        or float(dft["ecutrho_ry"]) != 520
        or relax["k_points"] != {"mesh": [6, 6, 1], "shift": [0, 0, 0]}
        or float(relax["degauss_ry"]) != 0.01
        or float(dft["conv_thr"]) != 1.0e-8
        or float(dft["mixing_beta"]) != 0.3
    ):
        raise ValueError("Locked Na/C50 methodology differs from the approved settings")

    lines = [
        "! Neutral Na on relaxed C50, central hollow-site starting geometry.",
        "! Literature and pseudopotential references: docs/codex_prompts/oct16_2026_final_project_scope.md",
        "&CONTROL",
        f"   calculation = '{calculation}',",
        f"   prefix = '{prefix}',",
        "   pseudo_dir = './pseudopotentials',",
        f"   outdir = './{outdir}',",
        "   tstress = .true.,",
        "   tprnfor = .true.,",
    ]
    if calculation == "relax":
        lines += [
            f"   forc_conv_thr = {qe_scientific(relax['forc_conv_thr'])},",
            "   max_seconds = 36000,",
        ]
    lines += [
        "/",
        "&SYSTEM",
        "   ibrav = 0,",
        "   nat = 51,",
        "   ntyp = 2,",
        "   tot_charge = 0.0,",
        "   input_dft = 'PBE',",
        "   vdw_corr = 'dft-d3',",
        "   dftd3_version = 4,",
        "   dftd3_threebody = .true.,",
        "   assume_isolated = '2D',",
        "   ecutwfc = 65,",
        "   ecutrho = 520,",
        "   nspin = 2,",
        "   occupations = 'smearing',",
        "   smearing = 'mv',",
        "   degauss = 0.01,",
        "   starting_magnetization(1) = 0.0,",
        "   starting_magnetization(2) = 0.11,",
        "/",
        "&ELECTRONS",
        f"   conv_thr = {qe_scientific(dft['conv_thr'])},",
        f"   mixing_beta = {dft['mixing_beta']},",
        "   diagonalization = 'cg',",
        "/",
    ]
    if calculation == "relax":
        lines += ["&IONS", "   ion_dynamics = 'bfgs',", "/"]
    lines += [
        "ATOMIC_SPECIES",
        f"C  12.011       {files['C']}",
        f"Na 22.98976928  {files['Na']}",
        "",
        *cell_lines(atoms),
        "",
        "ATOMIC_POSITIONS angstrom",
    ]
    for atom in atoms:
        lines.append(
            f"{atom.symbol:<2} "
            + " ".join(format_coordinate(value) for value in atom.position)
        )
    lines += ["", "K_POINTS automatic", "  6 6 1 0 0 0", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Unique alphanumeric/underscore run identifier")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.run_id):
        parser.error("run_id must contain only letters, numbers, and underscores")

    config = load_config(ROOT / "config/qe.yaml")
    na_upf = ROOT / "pseudopotentials" / config["pseudopotentials"]["files"]["Na"]
    if not na_upf.is_file() or digest(na_upf, "md5") != NA_MD5:
        raise ValueError("Na UPF is absent or does not match the published SSSP MD5")
    source_result = parse_output(SOURCE_OUTPUT, calculation="relax")
    if not all(
        source_result[key] is True
        for key in (
            "job_completed",
            "gpu_acceleration_active",
            "all_electronic_cycles_converged",
            "ionic_convergence_reached",
        )
    ):
        raise ValueError("Accepted pristine reference did not pass the raw-output audit")
    carbon = read(SOURCE)
    if len(carbon) != 50 or set(carbon.get_chemical_symbols()) != {"C"}:
        raise ValueError("Expected accepted pristine C50 structure")
    if not np.isclose(carbon.cell.lengths()[2], 18.0):
        raise ValueError("Expected the approved 18-angstrom z cell")

    center = hollow_site(carbon)
    na_position = center.copy()
    na_position[2] = float(np.mean(carbon.positions[:, 2])) + INITIAL_HEIGHT_ANGSTROM
    atoms = carbon.copy()
    atoms.append(Atom("Na", position=na_position))

    stem = f"na_c50_hollow_{args.run_id}"
    input_dir = ROOT / "qe_inputs/adsorption/na_pristine_hollow"
    structure_path = ROOT / "structures/adsorption/na_pristine_hollow" / f"{stem}_start.traj"
    manifest_path = input_dir / f"{stem}_manifest.json"
    pilot_path = input_dir / f"{stem}_pilot.in"
    relax_path = input_dir / f"{stem}_relax.in"
    targets = [structure_path, manifest_path, pilot_path, relax_path]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing files: " + ", ".join(existing))

    input_dir.mkdir(parents=True, exist_ok=True)
    structure_path.parent.mkdir(parents=True, exist_ok=True)
    write(structure_path, atoms)
    for calculation, path in (("scf", pilot_path), ("relax", relax_path)):
        stage = "pilot" if calculation == "scf" else "relax"
        path.write_text(
            render_input(
                atoms,
                config,
                calculation,
                f"{stem}_{stage}",
                f"qe_scratch/adsorption/{stem}_{stage}",
            ),
            encoding="utf-8",
        )

    manifest = {
        "run_id": args.run_id,
        "system": "neutral Na/C50 above central pristine hollow site",
        "source_structure": str(SOURCE.relative_to(ROOT)),
        "source_structure_sha256": digest(SOURCE),
        "source_qe_output": str(SOURCE_OUTPUT.relative_to(ROOT)),
        "source_qe_output_sha256": digest(SOURCE_OUTPUT),
        "na_upf": na_upf.name,
        "na_upf_md5": digest(na_upf, "md5"),
        "initial_na_position_angstrom": [float(value) for value in na_position],
        "initial_height_above_mean_carbon_plane_angstrom": INITIAL_HEIGHT_ANGSTROM,
        "starting_structure": str(structure_path.relative_to(ROOT)),
        "starting_structure_sha256": digest(structure_path),
        "pilot_input": str(pilot_path.relative_to(ROOT)),
        "pilot_input_sha256": digest(pilot_path),
        "relax_input": str(relax_path.relative_to(ROOT)),
        "relax_input_sha256": digest(relax_path),
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "scope": "single 65/520 Ry resource-gated pilot, then one 12-hour relaxation only if every pilot gate passes",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
