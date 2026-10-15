#!/usr/bin/env python3
"""Prepare one auditable neutral-Li/C50 hollow-site pilot and relaxation."""

import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path

import numpy as np
from ase import Atom
from ase.geometry import find_mic
from ase.io import read, write

from generate_qe_inputs import cell_lines, format_coordinate, load_config, qe_scientific
from parse_qe_output import parse_output


ROOT = Path(__file__).resolve().parents[1]
LI_MD5 = "e912e257baa3777c20ea3d68f190483c"
SOURCE = ROOT / "structures/relaxed/pristine/graphene_5x5_pristine_relaxed.traj"
SOURCE_OUTPUT = ROOT / "results/relaxation/pristine/relax_pristine_65_520_cg_20260916.out"


def digest(path, algorithm="sha256"):
    result = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def hollow_site(carbon):
    """Find the central C6-ring centre and verify its sixfold C shell."""
    positions = carbon.positions
    candidates = []
    target = 0.5 * (carbon.cell.array[0] + carbon.cell.array[1])
    for index, origin in enumerate(positions):
        vectors, distances = find_mic(positions - origin, carbon.cell, pbc=carbon.pbc)
        neighbors = [j for j in range(len(carbon)) if j != index and 1.35 < distances[j] < 1.49]
        if len(neighbors) != 3:
            raise ValueError(f"C atom {index + 1} has {len(neighbors)} nearest neighbors, not three")
        for first, second in itertools.combinations(neighbors, 2):
            center = origin + vectors[first] + vectors[second]
            fractional = carbon.cell.scaled_positions(center[np.newaxis, :])[0]
            fractional[:2] %= 1.0
            center = fractional @ carbon.cell.array
            _, shell = find_mic(positions - center, carbon.cell, pbc=carbon.pbc)
            shell.sort()
            if np.max(np.abs(shell[:6] - 1.42)) < 0.03 and shell[6] > 2.3:
                candidates.append((float(np.linalg.norm(center[:2] - target[:2])), center))
    if not candidates:
        raise ValueError("No verified C6 hollow site found")
    center = min(candidates, key=lambda item: item[0])[1]
    return center


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
    ):
        raise ValueError("Locked Li pilot methodology differs from approved settings")

    lines = [
        "! Neutral Li on relaxed C50, central hollow-site starting geometry.",
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
        lines.append(f"   forc_conv_thr = {qe_scientific(relax['forc_conv_thr'])},")
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
        "   starting_magnetization(2) = 0.33,",
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
        f"C  12.011  {files['C']}",
        f"Li 6.94    {files['Li']}",
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
    li_upf = ROOT / "pseudopotentials" / config["pseudopotentials"]["files"]["Li"]
    if not li_upf.is_file() or digest(li_upf, "md5") != LI_MD5:
        raise ValueError("Li UPF is absent or does not match the published SSSP MD5")
    if parse_output(SOURCE_OUTPUT, calculation="relax")["ionic_convergence_reached"] is not True:
        raise ValueError("Accepted pristine reference did not pass the raw-output audit")
    carbon = read(SOURCE)
    if len(carbon) != 50 or set(carbon.get_chemical_symbols()) != {"C"}:
        raise ValueError("Expected accepted pristine C50 structure")
    if not np.isclose(carbon.cell.lengths()[2], 18.0):
        raise ValueError("Expected the approved 18-angstrom z cell")
    center = hollow_site(carbon)
    li_position = center.copy()
    li_position[2] = float(np.mean(carbon.positions[:, 2])) + 2.0
    atoms = carbon.copy()
    atoms.append(Atom("Li", position=li_position))

    stem = f"li_c50_hollow_{args.run_id}"
    input_dir = ROOT / "qe_inputs/adsorption/li_pristine_hollow"
    structure_path = ROOT / "structures/adsorption/li_pristine_hollow" / f"{stem}_start.traj"
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
        text = render_input(
            atoms, config, calculation, f"{stem}_{stage}",
            f"qe_scratch/adsorption/{stem}_{stage}",
        )
        path.write_text(text, encoding="utf-8")

    manifest = {
        "run_id": args.run_id,
        "system": "neutral Li/C50 above central pristine hollow site",
        "source_structure": str(SOURCE.relative_to(ROOT)),
        "source_structure_sha256": digest(SOURCE),
        "source_qe_output": str(SOURCE_OUTPUT.relative_to(ROOT)),
        "li_upf": li_upf.name,
        "li_upf_md5": digest(li_upf, "md5"),
        "initial_li_position_angstrom": [float(value) for value in li_position],
        "initial_height_above_mean_carbon_plane_angstrom": 2.0,
        "starting_structure": str(structure_path.relative_to(ROOT)),
        "starting_structure_sha256": digest(structure_path),
        "pilot_input": str(pilot_path.relative_to(ROOT)),
        "pilot_input_sha256": digest(pilot_path),
        "relax_input": str(relax_path.relative_to(ROOT)),
        "relax_input_sha256": digest(relax_path),
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "scope": "single pilot, then one gated relaxation; not adsorption-energy convergence data",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
