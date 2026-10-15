#!/usr/bin/env python3
"""Prepare, but never launch, neutral Li/C49 vacancy-centred QE inputs."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from ase import Atom
from ase.geometry import find_mic
from ase.io import read, write

from parse_qe_output import parse_output
from check_pseudopotentials import audit_required_upf


ROOT = Path(__file__).resolve().parents[1]
SOURCE_INPUT = ROOT / "qe_inputs/relaxation/monovacancy/relax_monovacancy.in"
SOURCE_OUTPUT = ROOT / "results/relaxation/monovacancy/relax_monovacancy_65_520_cg_seed001_c1_20260917.out"
SOURCE_ANALYSIS = ROOT / "results/relaxation/monovacancy/final_structure_analysis.json"
SOURCE_STRUCTURE = ROOT / "structures/relaxed/monovacancy/graphene_5x5_monovacancy_relaxed.traj"
LI_UPF = ROOT / "pseudopotentials/li_pbe_v1.4.uspp.F.UPF"
INITIAL_HEIGHT_ANGSTROM = 2.0
MAX_SECONDS_CPU = 36000


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text, pattern, replacement):
    changed, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one source field matching {pattern!r}; got {count}")
    return changed


def source_labels():
    raw = SOURCE_INPUT.read_text(encoding="utf-8")
    if "ATOMIC_POSITIONS angstrom\n" not in raw or "\nK_POINTS automatic" not in raw:
        raise ValueError("Unexpected source input card layout")
    card = raw.split("ATOMIC_POSITIONS angstrom\n", 1)[1].split("\nK_POINTS automatic", 1)[0]
    labels = [line.split()[0] for line in card.splitlines() if line.strip()]
    if len(labels) != 49 or labels.count("C1") != 3 or labels.count("C") != 46:
        raise ValueError("Source does not contain the accepted C/C1 vacancy labeling")
    return labels


def accepted_substrate():
    analysis = json.loads(SOURCE_ANALYSIS.read_text(encoding="utf-8"))
    if sha256(SOURCE_OUTPUT) != analysis["qe_output_sha256"]:
        raise ValueError("C49 QE output differs from the accepted analysis hash")
    result = parse_output(SOURCE_OUTPUT, calculation="relax")
    if not result["ionic_convergence_reached"] or result["electronic_failed_cycles"] != 0:
        raise ValueError("C49 source relaxation is not fully converged")
    if abs(result["final_total_energy_ry"] + 903.50175873) > 1e-8:
        raise ValueError("C49 source energy differs from the accepted result")
    carbon = read(SOURCE_STRUCTURE)
    labels = source_labels()
    if len(carbon) != 49 or set(carbon.get_chemical_symbols()) != {"C"}:
        raise ValueError("Expected the accepted C49 structure")
    if not np.allclose(carbon.cell.array,
                       [[12.3, 0, 0], [-6.15, 10.65211247, 0], [0, 0, 18]], atol=1e-7):
        raise ValueError("C49 cell differs from the locked fixed 18-angstrom cell")
    if not np.allclose(carbon.positions[:, 2], 9.0, atol=0.02):
        raise ValueError("Unexpected C49 out-of-plane geometry")
    return carbon, labels


def vacancy_site(carbon, labels):
    neighbors = carbon.positions[[i for i, label in enumerate(labels) if label == "C1"]]
    center = np.mean(neighbors, axis=0)
    original_missing = np.array([3.69, 4.97098582, 9.0])
    _, offset = find_mic(center - original_missing, carbon.cell, pbc=carbon.pbc)
    if offset > 0.2:
        raise ValueError("Reconstructed vacancy-neighbor centroid moved unexpectedly")
    pair_distances = [float(np.linalg.norm(neighbors[i] - neighbors[j]))
                      for i, j in ((0, 1), (0, 2), (1, 2))]
    if not 2.0 < min(pair_distances) < 2.2 or max(pair_distances) >= 2.8:
        raise ValueError("Expected the accepted asymmetric reconstructed vacancy")
    position = center.copy()
    position[2] = float(np.mean(carbon.positions[:, 2])) + INITIAL_HEIGHT_ANGSTROM
    return position, pair_distances, center


def render_input(carbon, labels, li_position, stage, stem):
    raw = SOURCE_INPUT.read_text(encoding="utf-8")
    before, after = raw.split("ATOMIC_POSITIONS angstrom\n", 1)
    _, k_card = after.split("\nK_POINTS automatic\n", 1)
    if [int(value) for value in k_card.split()] != [6, 6, 1, 0, 0, 0]:
        raise ValueError("Source k-point mesh is not 6x6x1 unshifted")
    if not all(fragment in before for fragment in (
        "vdw_corr = 'dft-d3'", "dftd3_version = 4", "assume_isolated = '2D'",
        "ecutwfc = 65", "ecutrho = 520", "nspin = 2", "smearing = 'mv'",
        "degauss = 0.01", "mixing_beta = 0.3", "diagonalization = 'cg'",
        "C1  12.011  C.pbe-n-kjpaw_psl.1.0.0.UPF",
    )):
        raise ValueError("Locked C49 scientific settings changed")
    before = re.sub(r"\A(?:!.*\n)+\s*", "", before)
    before = replace_once(before, r"^\s*calculation = 'relax',", f"   calculation = '{'scf' if stage == 'pilot' else 'relax'}',")
    before = replace_once(before, r"^\s*prefix = '[^']+',", f"   prefix = '{stem}_{stage}',")
    before = replace_once(before, r"^\s*outdir = '[^']+',",
                          f"   outdir = './qe_scratch/adsorption/{stem}_{stage}',")
    before = replace_once(before, r"^\s*nat = 49,", "   nat = 50,")
    before = replace_once(before, r"^\s*ntyp = 2,", "   ntyp = 3,\n   tot_charge = 0.0,")
    before = replace_once(before, r"^\s*starting_magnetization\(2\) = 0.1,",
                          "   starting_magnetization(2) = 0.1,\n   starting_magnetization(3) = 0.33,")
    before = replace_once(before,
                          r"^C1  12\.011  C\.pbe-n-kjpaw_psl\.1\.0\.0\.UPF$",
                          "C1  12.011  C.pbe-n-kjpaw_psl.1.0.0.UPF\nLi  6.94    li_pbe_v1.4.uspp.F.UPF")
    before = replace_once(before, r"^\s*forc_conv_thr = 4.0d-4,",
                          "   forc_conv_thr = 4.0d-4,\n   max_seconds = 36000,")
    if stage == "pilot":
        before = replace_once(before, r"^\s*forc_conv_thr = 4.0d-4,\n", "\n")
        before = replace_once(before, r"^&IONS\n\s*ion_dynamics = 'bfgs',\n/\n", "")
    positions = "\n".join(
        f"{label:<2} {xyz[0]:16.10f} {xyz[1]:16.10f} {xyz[2]:16.10f}"
        for label, xyz in zip(labels, carbon.positions)
    )
    positions += f"\nLi {li_position[0]:16.10f} {li_position[1]:16.10f} {li_position[2]:16.10f}"
    return (
        "! PROPOSAL ONLY: neutral Li above reconstructed C49 vacancy-neighbor centroid.\n"
        "! Starting site is a hypothesis, not an established adsorption minimum.\n"
        "! Source/method/literature: docs/codex_prompts/oct16_2026_final_project_scope.md\n"
        + before + "ATOMIC_POSITIONS angstrom\n" + positions
        + "\n\nK_POINTS automatic\n  6 6 1 0 0 0\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Unique alphanumeric/underscore preparation ID")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.run_id):
        parser.error("run_id must contain only letters, numbers, and underscores")
    audit_required_upf("Li", LI_UPF, LI_UPF.name)
    carbon, labels = accepted_substrate()
    li_position, pair_distances, center = vacancy_site(carbon, labels)
    combined = carbon.copy()
    combined.append(Atom("Li", position=li_position))
    stem = f"li_c49_vacancy_{args.run_id}"
    input_dir = ROOT / "qe_inputs/adsorption/li_monovacancy"
    structure_path = ROOT / "structures/adsorption/li_monovacancy" / f"{stem}_start.traj"
    manifest_path = input_dir / f"{stem}_manifest.json"
    inputs = {stage: input_dir / f"{stem}_{stage}.in" for stage in ("pilot", "relax")}
    targets = [structure_path, manifest_path, *inputs.values()]
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to overwrite an existing proposal")
    input_dir.mkdir(parents=True, exist_ok=True)
    structure_path.parent.mkdir(parents=True, exist_ok=True)
    write(structure_path, combined)
    for stage, path in inputs.items():
        path.write_text(render_input(carbon, labels, li_position, stage, stem), encoding="utf-8")
    manifest = {
        "status": "prepared_only; GPU queue paused; not authorized to launch",
        "system": "neutral Li/C49 at reconstructed monovacancy-centred starting site",
        "run_id": args.run_id,
        "source_structure": str(SOURCE_STRUCTURE.relative_to(ROOT)),
        "source_structure_sha256": sha256(SOURCE_STRUCTURE),
        "source_input": str(SOURCE_INPUT.relative_to(ROOT)),
        "source_input_sha256": sha256(SOURCE_INPUT),
        "source_output": str(SOURCE_OUTPUT.relative_to(ROOT)),
        "source_output_sha256": sha256(SOURCE_OUTPUT),
        "carbon_species_labels": labels,
        "vacancy_neighbor_centroid_angstrom": [float(value) for value in center],
        "vacancy_neighbor_pair_distances_angstrom": pair_distances,
        "initial_li_position_angstrom": [float(value) for value in li_position],
        "initial_height_above_mean_carbon_plane_angstrom": INITIAL_HEIGHT_ANGSTROM,
        "starting_structure": str(structure_path.relative_to(ROOT)),
        "starting_structure_sha256": sha256(structure_path),
        "pilot_input": str(inputs["pilot"].relative_to(ROOT)),
        "pilot_input_sha256": sha256(inputs["pilot"]),
        "relax_input": str(inputs["relax"].relative_to(ROOT)),
        "relax_input_sha256": sha256(inputs["relax"]),
        "li_upf_md5": "e912e257baa3777c20ea3d68f190483c",
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "site_literature": "https://doi.org/10.3390/molecules24040754",
        "max_seconds_cpu": MAX_SECONDS_CPU,
        "limitations": "One central starting site and one spin seed; no ground-state or cutoff claim",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared proposal: {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
