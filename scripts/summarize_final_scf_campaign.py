#!/usr/bin/env python3
"""Summarize the six strictly accepted 9x9x1 final SCFs.

The script fails closed unless every case is accepted and strictly parseable.
It writes report-ready CSV, JSON, Markdown, and OVITO-compatible extended XYZ
structures without modifying any raw QE output.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

try:
    from .parse_qe_output import parse_output
except ImportError:  # Direct execution as ``python3 scripts/...``.
    from parse_qe_output import parse_output


RY_TO_EV = 13.605693122994
ATOM_ENERGIES_RY = {"Li": -14.35806979, "Na": -95.26886282}
CASES = ("na_c49", "c49", "li_c49", "c50", "li_c50", "na_c50")
ADSORPTION_PAIRS = {
    "li_c50": ("c50", "Li"),
    "na_c50": ("c50", "Na"),
    "li_c49": ("c49", "Li"),
    "na_c49": ("c49", "Na"),
}


def read_accepted_output(root: Path, case_name: str) -> Path:
    case_root = root / case_name
    state = (case_root / "state.txt").read_text(encoding="utf-8").strip()
    if state != "accepted":
        raise ValueError(f"{case_name} is not accepted (state={state!r})")
    output = Path(
        (case_root / "accepted_output.txt").read_text(encoding="utf-8").strip()
    )
    if not output.is_absolute():
        output = Path.cwd() / output
    if not output.is_file():
        raise FileNotFoundError(f"accepted output for {case_name} not found: {output}")
    return output


def adsorption_energy_ry(combined_ry: float, substrate_ry: float, metal: str) -> float:
    return combined_ry - substrate_ry - ATOM_ENERGIES_RY[metal]


def parse_card(
    text: str, header: str, count: int, fields_per_row: int
) -> list[list[str]]:
    match = re.search(rf"(?mi)^{re.escape(header)}[^\n]*\n", text)
    if not match:
        raise ValueError(f"missing {header} card")
    rows = []
    for line in text[match.end() :].splitlines():
        fields = line.split()
        if len(fields) < fields_per_row:
            if rows:
                break
            continue
        rows.append(fields[:fields_per_row])
        if len(rows) == count:
            break
    if len(rows) != count:
        raise ValueError(f"{header} has {len(rows)} rows; expected {count}")
    return rows


def export_extxyz(input_path: Path, output_path: Path, case_name: str) -> None:
    text = input_path.read_text(encoding="utf-8")
    nat_match = re.search(r"(?mi)^\s*nat\s*=\s*(\d+)", text)
    if not nat_match:
        raise ValueError(f"missing nat in {input_path}")
    nat = int(nat_match.group(1))
    cell = parse_card(text, "CELL_PARAMETERS", 3, 3)
    atoms = parse_card(text, "ATOMIC_POSITIONS", nat, 4)
    lattice = " ".join(value for row in cell for value in row)
    lines = [
        str(nat),
        (
            f'Lattice="{lattice}" Properties=species:S:1:pos:R:3 '
            f'pbc="T T F" case="{case_name}" source="{input_path}"'
        ),
    ]
    for label, x, y, z in atoms:
        symbol_match = re.match(r"[A-Z][a-z]?", label)
        if not symbol_match:
            raise ValueError(f"cannot infer element from label {label!r}")
        lines.append(f"{symbol_match.group(0)} {x} {y} {z}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(root: Path, input_root: Path, output_dir: Path) -> dict:
    records = {}
    for case_name in CASES:
        output = read_accepted_output(root, case_name)
        parsed = parse_output(output, calculation="scf")
        records[case_name] = {
            "case": case_name,
            "accepted_output": str(output.relative_to(Path.cwd())),
            "final_total_energy_ry": parsed["final_total_energy_ry"],
            "internal_energy_ry": parsed["internal_energy_ry"],
            "smearing_contribution_ry": parsed["smearing_contribution_ry"],
            "fermi_energy_ev": parsed["fermi_energy_ev"],
            "total_magnetization_mu_b": parsed[
                "total_magnetization_bohr_magneton_per_cell"
            ],
            "absolute_magnetization_mu_b": parsed[
                "absolute_magnetization_bohr_magneton_per_cell"
            ],
            "scf_iterations": parsed["scf_iterations"],
            "wall_time_seconds": parsed["wall_time_seconds"],
            "gpu_acceleration_active": parsed["gpu_acceleration_active"],
            "job_completed": parsed["job_completed"],
            "all_electronic_cycles_converged": parsed[
                "all_electronic_cycles_converged"
            ],
        }

    adsorption = []
    for combined, (substrate, metal) in ADSORPTION_PAIRS.items():
        energy_ry = adsorption_energy_ry(
            records[combined]["final_total_energy_ry"],
            records[substrate]["final_total_energy_ry"],
            metal,
        )
        adsorption.append(
            {
                "system": combined,
                "metal": metal,
                "substrate": substrate,
                "combined_energy_ry": records[combined]["final_total_energy_ry"],
                "substrate_energy_ry": records[substrate]["final_total_energy_ry"],
                "atom_reference_energy_ry": ATOM_ENERGIES_RY[metal],
                "adsorption_energy_ry": energy_ry,
                "adsorption_energy_ev": energy_ry * RY_TO_EV,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    structures = output_dir / "structures_extxyz"
    structures.mkdir(exist_ok=True)
    for case_name in CASES:
        export_extxyz(
            input_root / f"{case_name}_9x9x1.in",
            structures / f"{case_name}_final.extxyz",
            case_name,
        )

    payload = {
        "method": {
            "code": "Quantum ESPRESSO pw.x 7.6",
            "k_points": "9x9x1, unshifted",
            "functional": "PBE + DFT-D3(BJ)",
            "cutoffs_ry": "65/520",
            "smearing": "Marzari-Vanderbilt, 0.01 Ry",
            "adsorption_energy_equation": "E(M/Cn) - E(Cn) - E(M_atom)",
            "ry_to_ev": RY_TO_EV,
        },
        "scf_results": [records[name] for name in CASES],
        "adsorption_results": adsorption,
    }
    (output_dir / "final_scf_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    with (output_dir / "final_scf_energies.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[CASES[0]].keys()))
        writer.writeheader()
        writer.writerows(records[name] for name in CASES)
    with (output_dir / "final_adsorption_energies.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(adsorption[0].keys()))
        writer.writeheader()
        writer.writerows(adsorption)

    md = [
        "# Standardized 9x9x1 final-SCF results",
        "",
        "All six entries passed strict parsing: GPU acceleration, electronic convergence,",
        "a final energy, clean completion, and `JOB DONE`. Adsorption energies use",
        "`E_ads = E(M/Cn) - E(Cn) - E(M_atom)`; negative values are exothermic.",
        "",
        "| System | Total energy (Ry) | SCF iterations | Magnetization (mu_B) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in CASES:
        row = records[name]
        mag = row["total_magnetization_mu_b"]
        md.append(
            f"| {name} | {row['final_total_energy_ry']:.8f} | "
            f"{row['scf_iterations']} | {mag if mag is not None else 'n/a'} |"
        )
    md.extend(
        [
            "",
            "| Adsorption system | E_ads (eV) |",
            "| --- | ---: |",
        ]
    )
    for row in adsorption:
        md.append(f"| {row['system']} | {row['adsorption_energy_ev']:.6f} |")
    md.extend(
        [
            "",
            "The `structures_extxyz` directory contains the exact fixed geometries used",
            "for the final SCFs and can be opened directly in OVITO.",
            "",
        ]
    )
    (output_dir / "final_scf_summary.md").write_text("\n".join(md), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("results/cloud/20261014_final_scf")
    )
    parser.add_argument(
        "--input-root", type=Path, default=Path("qe_inputs/final_scf/20261014")
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/final_project/20261015_final_scf"),
    )
    args = parser.parse_args()
    summarize(args.root, args.input_root, args.output_dir)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
