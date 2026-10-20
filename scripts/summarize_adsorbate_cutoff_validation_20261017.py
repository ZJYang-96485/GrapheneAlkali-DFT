#!/usr/bin/env python3
"""Strictly summarize the 70/560 Ry adsorption-cutoff validation campaign."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


RY_TO_EV = 13.605693122994
CASES = ("c50", "li_atom", "na_atom", "li_c50", "na_c50")
BASELINE_65_RY = {
    "c50": -922.52210437,
    "li_atom": -14.35806979,
    "na_atom": -95.26886282,
    "li_c50": -936.96584225,
    "na_c50": -1017.83224564,
}
BASELINE_ADSORPTION_EV = {
    "li_c50": -1.165573742974,
    "na_c50": -0.561621923293,
}


def strict_result(root: Path, case: str) -> dict:
    case_root = root / case
    if (case_root / "state.txt").read_text(encoding="utf-8").strip() != "accepted":
        raise ValueError(f"{case} is not accepted")
    accepted = Path(
        (case_root / "accepted_output.txt").read_text(encoding="utf-8").strip()
    )
    match = re.search(r"_attempt(\d\d)\.out$", accepted.name)
    if not match:
        raise ValueError(f"{case}: cannot identify accepted attempt from {accepted}")
    result_path = case_root / f"attempt{match.group(1)}_diagnostics" / "strict_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    required = {
        "job_completed": True,
        "gpu_acceleration_active": True,
        "all_electronic_cycles_converged": True,
    }
    for key, expected in required.items():
        if result.get(key) is not expected:
            raise ValueError(f"{case}: strict gate failed for {key}")
    if result.get("final_total_energy_ry") is None:
        raise ValueError(f"{case}: final total energy is missing")
    return result


def summarize(root: Path, output_dir: Path) -> dict:
    results = {case: strict_result(root, case) for case in CASES}
    energies_70 = {
        case: float(results[case]["final_total_energy_ry"]) for case in CASES
    }

    adsorption = []
    for combined, atom, metal in (
        ("li_c50", "li_atom", "Li"),
        ("na_c50", "na_atom", "Na"),
    ):
        energy_ry = energies_70[combined] - energies_70["c50"] - energies_70[atom]
        energy_ev = energy_ry * RY_TO_EV
        baseline_ev = BASELINE_ADSORPTION_EV[combined]
        adsorption.append(
            {
                "system": combined,
                "metal": metal,
                "ecutwfc_ry": 70,
                "ecutrho_ry": 560,
                "adsorption_energy_70_560_ev": energy_ev,
                "adsorption_energy_65_520_ev": baseline_ev,
                "delta_70_minus_65_ev": energy_ev - baseline_ev,
                "absolute_delta_mev": abs(energy_ev - baseline_ev) * 1000.0,
            }
        )

    scf_rows = []
    for case in CASES:
        scf_rows.append(
            {
                "case": case,
                "energy_65_520_ry": BASELINE_65_RY[case],
                "energy_70_560_ry": energies_70[case],
                "delta_ry": energies_70[case] - BASELINE_65_RY[case],
                "scf_iterations": results[case].get("scf_iterations"),
                "wall_time_seconds": results[case].get("wall_time_seconds"),
                "gpu_acceleration_active": results[case]["gpu_acceleration_active"],
                "job_completed": results[case]["job_completed"],
            }
        )

    payload = {
        "campaign": "adsorbate_cutoff_validation_20261017",
        "method": {
            "comparison": "70/560 Ry minus accepted 65/520 Ry",
            "geometry": "fixed accepted C50, Li/C50, and Na/C50 geometries",
            "adsorption_energy_equation": "E(M/C50) - E(C50) - E(M_atom)",
            "ry_to_ev": RY_TO_EV,
            "interpretation": (
                "Raw adsorption-energy shifts are reported without inventing a new "
                "acceptance threshold; scientific acceptance remains a review decision."
            ),
        },
        "scf_results": scf_rows,
        "adsorption_comparison": adsorption,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cutoff_validation_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "cutoff_validation_scf.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scf_rows[0]))
        writer.writeheader()
        writer.writerows(scf_rows)
    with (output_dir / "cutoff_validation_adsorption.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(adsorption[0]))
        writer.writeheader()
        writer.writerows(adsorption)

    lines = [
        "# Adsorbate-specific cutoff validation (70/560 Ry)",
        "",
        "All five fixed-geometry SCFs passed GPU, electronic-convergence, final-energy,",
        "and `JOB DONE` gates. The isolated references are neutral spin-polarized atoms",
        "using the same 70/560 Ry cutoffs as their corresponding combined systems.",
        "",
        "| System | Eads 65/520 (eV) | Eads 70/560 (eV) | absolute shift (meV) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in adsorption:
        lines.append(
            f"| {row['system']} | {row['adsorption_energy_65_520_ev']:.9f} | "
            f"{row['adsorption_energy_70_560_ev']:.9f} | "
            f"{row['absolute_delta_mev']:.3f} |"
        )
    lines.extend(
        [
            "",
            "No new cutoff threshold is imposed by this script; it reports the numerical",
            "shift for scientific review.",
            "",
        ]
    )
    (output_dir / "cutoff_validation_summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("results/cloud/20261017_adsorbate_cutoff_70_560"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/final_project/20261017_adsorbate_cutoff_validation"),
    )
    args = parser.parse_args()
    summarize(args.root, args.output_dir)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
