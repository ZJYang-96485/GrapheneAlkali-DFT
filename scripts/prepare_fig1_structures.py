#!/usr/bin/env python3
"""Validate accepted QE relaxations and prepare Figure 1 structure files.

This script never modifies the raw QE outputs. It requires a strictly
completed relaxation for each case and verifies that the periodic EXTXYZ
coordinates recovered from the final-SCF bundle reproduce the QE final
coordinate block atom-for-atom before writing report copies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from parse_qe_output import QEOutputParseError, parse_output

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Case:
    panel: str
    key: str
    system: str
    metal: str
    carbon_count: int
    source_output: str
    periodic_source: str
    expected_height: float

    @property
    def atom_count(self) -> int:
        return self.carbon_count + 1

CASES = (
    Case("a", "li_c50", "Li/C50", "Li", 50,
         "results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.out",
         "results/final_project/20261015_final_scf/structures_extxyz/li_c50_final.extxyz", 1.691),
    Case("b", "na_c50", "Na/C50", "Na", 50,
         "results/cloud/20260930_blackwell48_restart2/na_c50_hollow_20260924a_relax_restart2.out",
         "results/final_project/20261015_final_scf/structures_extxyz/na_c50_final.extxyz", 2.249),
    Case("c", "li_c49", "Li/C49", "Li", 49,
         "results/cloud/20261008_li_c49_vacancy_18h_cont2/li_c49_vacancy_20261008a_segment03.out",
         "results/final_project/20261015_final_scf/structures_extxyz/li_c49_final.extxyz", 1.795),
    Case("d", "na_c49", "Na/C49", "Na", 49,
         "results/cloud/20261014_na_c49_resilient/na_c49_segment001.out",
         "results/final_project/20261015_final_scf/structures_extxyz/na_c49_final.extxyz",
         2.2695104401),
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def normalize_symbol(label: str) -> str:
    """Map QE labels such as C1 to chemical symbols used by visualization."""
    match = re.match(r"[A-Za-z]+", label)
    if not match:
        raise ValueError(f"Cannot identify a chemical symbol in {label!r}.")
    letters = match.group(0)
    return letters[0].upper() + letters[1:].lower()

def read_extxyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Invalid EXTXYZ file: {path}")
    atom_count = int(lines[0])
    if len(lines) < atom_count + 2:
        raise ValueError(f"Truncated EXTXYZ file: {path}")
    lattice_match = re.search(r'Lattice="([^"]+)"', lines[1])
    pbc_match = re.search(r'pbc="([^"]+)"', lines[1], re.IGNORECASE)
    if not lattice_match or not pbc_match:
        raise ValueError(f"Periodic cell metadata is missing from {path}")
    lattice = [float(value) for value in lattice_match.group(1).split()]
    if len(lattice) != 9:
        raise ValueError(f"Expected nine lattice components in {path}")
    atoms = []
    for line_number, line in enumerate(lines[2 : atom_count + 2], start=3):
        fields = line.split()
        if len(fields) < 4:
            raise ValueError(f"Malformed atom line {line_number} in {path}")
        atoms.append((normalize_symbol(fields[0]), *(float(value) for value in fields[1:4])))
    return atoms, lattice, pbc_match.group(1)

def fmt_bool(value: bool) -> str:
    return "True" if value else "False"

def quote_extxyz(value: str) -> str:
    return value.replace("\\", "/").replace('"', "'")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "structures" / "report" / "fig1")
    parser.add_argument("--force", action="store_true",
                        help="Replace generated report copies, never raw outputs.")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [output_dir / "provenance.csv"]
    for case in CASES:
        targets += [output_dir / f"{case.key}_relaxed.xyz",
                    output_dir / f"{case.key}_relaxed.extxyz"]
    existing = [path for path in targets if path.exists()]
    if existing and not args.force:
        print("error: refusing to overwrite generated file(s): "
              + ", ".join(str(path) for path in existing), file=sys.stderr)
        return 2

    rows, summaries = [], []
    try:
        for case in CASES:
            raw_path = ROOT / case.source_output
            periodic_path = ROOT / case.periodic_source
            raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
            if "begin final coordinates" not in raw_text.lower():
                raise ValueError(f"Begin final coordinates missing: {raw_path}")
            if "end final coordinates" not in raw_text.lower():
                raise ValueError(f"End final coordinates missing: {raw_path}")
            parsed = parse_output(raw_path, calculation="relax")
            raw_coordinates = parsed["final_coordinates"] or []
            atoms, lattice, pbc = read_extxyz(periodic_path)
            if len(raw_coordinates) != case.atom_count or len(atoms) != case.atom_count:
                raise ValueError(f"{case.system}: expected {case.atom_count} atoms, found "
                                 f"{len(raw_coordinates)} in QE and {len(atoms)} in EXTXYZ.")
            raw_atoms = [(normalize_symbol(entry["symbol"]), float(entry["x"]),
                          float(entry["y"]), float(entry["z"]))
                         for entry in raw_coordinates]
            if [row[0] for row in raw_atoms] != [row[0] for row in atoms]:
                raise ValueError(f"{case.system}: QE and EXTXYZ species order differs.")
            max_coordinate_delta = max(
                abs(qe_atom[index] - ext_atom[index])
                for qe_atom, ext_atom in zip(raw_atoms, atoms)
                for index in (1, 2, 3))
            if max_coordinate_delta > 5.0e-8:
                raise ValueError(f"{case.system}: periodic structure differs from QE final "
                                 f"coordinates by {max_coordinate_delta:.3e} angstrom.")
            symbols = [row[0] for row in atoms]
            if symbols.count("C") != case.carbon_count or symbols.count(case.metal) != 1:
                counts = {symbol: symbols.count(symbol) for symbol in set(symbols)}
                raise ValueError(f"{case.system}: expected C{case.carbon_count}+"
                                 f"{case.metal}, found {counts}.")
            carbon_z = [row[3] for row in atoms if row[0] == "C"]
            metal_z = next(row[3] for row in atoms if row[0] == case.metal)
            height = metal_z - sum(carbon_z) / len(carbon_z)
            height_delta = abs(height - case.expected_height)
            if height_delta > 0.02:
                raise ValueError(f"{case.system}: height {height:.6f} A disagrees with "
                                 f"accepted value {case.expected_height:.6f} A by "
                                 f"{height_delta:.6f} A.")
            raw_hash = sha256(raw_path)
            xyz_path = output_dir / f"{case.key}_relaxed.xyz"
            extxyz_path = output_dir / f"{case.key}_relaxed.extxyz"
            xyz_lines = [str(len(atoms)),
                         f"Accepted relaxed {case.system}; source={case.source_output}; "
                         f"sha256={raw_hash}"]
            xyz_lines += [f"{symbol:<2s} {x: .10f} {y: .10f} {z: .10f}"
                          for symbol, x, y, z in atoms]
            xyz_path.write_text("\n".join(xyz_lines) + "\n", encoding="utf-8")
            lattice_text = " ".join(f"{value:.8f}" for value in lattice)
            extxyz_lines = [
                str(len(atoms)),
                f'Lattice="{lattice_text}" Properties=species:S:1:pos:R:3 '
                f'pbc="{pbc}" panel="{case.panel}" system="{case.system}" '
                f'source_output="{quote_extxyz(case.source_output)}" '
                f'source_sha256="{raw_hash}" adsorbate_height_angstrom={height:.10f}',
            ]
            extxyz_lines += [f"{symbol:<2s} {x: .10f} {y: .10f} {z: .10f}"
                             for symbol, x, y, z in atoms]
            extxyz_path.write_text("\n".join(extxyz_lines) + "\n", encoding="utf-8")
            rows.append({
                "panel": case.panel, "system": case.system,
                "source_output": case.source_output, "source_sha256": raw_hash,
                "atom_count": case.atom_count,
                "job_done": fmt_bool(parsed["job_completed"]),
                "electronic_converged": fmt_bool(parsed["all_electronic_cycles_converged"]),
                "ionic_converged": fmt_bool(parsed["ionic_convergence_reached"]),
                "adsorbate_height_angstrom": f"{height:.10f}",
            })
            summaries.append({
                "panel": case.panel, "system": case.system,
                "atom_count": case.atom_count, "source_output": case.source_output,
                "source_sha256": raw_hash, "periodic_source": case.periodic_source,
                "coordinate_max_abs_difference_angstrom": max_coordinate_delta,
                "adsorbate_height_angstrom": height,
                "accepted_height_angstrom": case.expected_height,
                "height_difference_angstrom": height_delta,
                "final_total_energy_ry": parsed["final_total_energy_ry"],
            })
    except (OSError, ValueError, QEOutputParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    with (output_dir / "provenance.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "panel", "system", "source_output", "source_sha256", "atom_count",
            "job_done", "electronic_converged", "ionic_converged",
            "adsorbate_height_angstrom"))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summaries, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
