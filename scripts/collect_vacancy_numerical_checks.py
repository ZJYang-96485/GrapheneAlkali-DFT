#!/usr/bin/env python3
"""Collect and validate the available vacancy-system numerical checks.

This script intentionally does not describe the data as a full convergence
study.  The repository contains a two-point, fixed-geometry Li/C49 cutoff
check and post-relaxation 6x6x1-to-9x9x1 total-energy refinements for C49,
Li/C49, and Na/C49.  It verifies completion flags, input settings, and the
identity of the geometries before writing report-ready CSV files.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parse_qe_output import parse_output  # noqa: E402


RY_TO_EV = 13.605693122994
CARBON_COUNT = 49
OUTPUT_DIR = ROOT / "results" / "final_project" / "convergence_collection"

CUTOFF_CASES = (
    {
        "label": "55/440",
        "status": ROOT
        / "results/phase5/diagnostics/li_c49_vacancy_20260923a_e55_pilot/status.json",
        "input": ROOT
        / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260923a_e55_pilot.in",
        "ecutwfc_ry": 55,
        "ecutrho_ry": 440,
    },
    {
        "label": "65/520",
        "status": ROOT
        / "results/phase5/diagnostics/li_c49_vacancy_20260921a_medium_pilot/status.json",
        "input": ROOT
        / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260921a_medium_pilot.in",
        "ecutwfc_ry": 65,
        "ecutrho_ry": 520,
    },
)

KPOINT_CASES = (
    {
        "system": "C49",
        "relax_output": ROOT
        / "results/relaxation/monovacancy/relax_monovacancy_65_520_cg_seed001_c1_20260917.out",
        "final_input": ROOT / "qe_inputs/final_scf/20261014/c49_9x9x1.in",
        "final_output": ROOT
        / "results/cloud/20261014_final_scf/c49/c49_9x9x1_attempt01.out",
    },
    {
        "system": "Li/C49",
        "relax_output": ROOT
        / "results/cloud/20261008_li_c49_vacancy_18h_cont2/li_c49_vacancy_20261008a_segment03.out",
        "final_input": ROOT / "qe_inputs/final_scf/20261014/li_c49_9x9x1.in",
        "final_output": ROOT
        / "results/cloud/20261014_final_scf/li_c49/li_c49_9x9x1_attempt01.out",
    },
    {
        "system": "Na/C49",
        "relax_output": ROOT
        / "results/cloud/20261014_na_c49_resilient/na_c49_segment001.out",
        "final_input": ROOT / "qe_inputs/final_scf/20261014/na_c49_9x9x1.in",
        "final_output": ROOT
        / "results/cloud/20261014_final_scf/na_c49/na_c49_9x9x1_attempt04.out",
    },
)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_input(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    cutoff_values = {}
    for key in ("ecutwfc", "ecutrho", "degauss"):
        match = re.search(
            rf"\b{key}\s*=\s*([-+0-9.eEdD]+)", text, re.IGNORECASE
        )
        cutoff_values[key] = (
            float(match.group(1).replace("D", "E").replace("d", "e"))
            if match
            else None
        )

    k_match = re.search(
        r"K_POINTS\s+automatic\s*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+[-+0-9]+\s+[-+0-9]+\s+[-+0-9]+",
        text,
        re.IGNORECASE,
    )
    if not k_match:
        raise ValueError(f"Automatic k-point mesh not found in {path}")
    k_mesh = tuple(int(value) for value in k_match.groups())

    nat_match = re.search(r"\bnat\s*=\s*(\d+)", text, re.IGNORECASE)
    if not nat_match:
        raise ValueError(f"nat not found in {path}")
    nat = int(nat_match.group(1))

    position_match = re.search(
        r"ATOMIC_POSITIONS\s+(?:\(([^)]*)\)|([^\s]+))\s*\n",
        text,
        re.IGNORECASE,
    )
    if not position_match:
        raise ValueError(f"ATOMIC_POSITIONS not found in {path}")
    units = (position_match.group(1) or position_match.group(2)).lower()
    lines = text[position_match.end() :].splitlines()[:nat]
    positions = []
    for line in lines:
        fields = line.split()
        if len(fields) < 4:
            raise ValueError(f"Incomplete coordinate line in {path}: {line!r}")
        positions.append(
            {
                "symbol": fields[0],
                "x": float(fields[1]),
                "y": float(fields[2]),
                "z": float(fields[3]),
                "units": units,
            }
        )
    if len(positions) != nat:
        raise ValueError(f"Expected {nat} coordinates in {path}; found {len(positions)}")

    return {**cutoff_values, "k_mesh": k_mesh, "positions": positions}


def maximum_coordinate_difference(first: list[dict], second: list[dict]) -> float:
    if len(first) != len(second):
        raise ValueError(f"Geometry atom counts differ: {len(first)} versus {len(second)}")
    maximum = 0.0
    for index, (left, right) in enumerate(zip(first, second), start=1):
        if left["symbol"] != right["symbol"]:
            raise ValueError(
                f"Geometry species differ at atom {index}: "
                f"{left['symbol']} versus {right['symbol']}"
            )
        if left["units"].lower() != "angstrom" or right["units"].lower() != "angstrom":
            raise ValueError("Only angstrom coordinates are supported for geometry checks")
        for component in ("x", "y", "z"):
            maximum = max(maximum, abs(float(left[component]) - float(right[component])))
    return maximum


def require_valid_result(result: dict, label: str, ionic: bool = False) -> None:
    required = {
        "job_completed": True,
        "gpu_acceleration_active": True,
        "all_electronic_cycles_converged": True,
    }
    if ionic:
        required["ionic_convergence_reached"] = True
    for field, expected in required.items():
        if result.get(field) is not expected:
            raise ValueError(f"{label} failed validation field {field}")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def collect_cutoff() -> list[dict]:
    prepared = []
    inputs = []
    statuses = []
    for case in CUTOFF_CASES:
        input_data = parse_input(case["input"])
        status = load_json(case["status"])
        result = status["strict_result"]
        require_valid_result(result, f"Li/C49 {case['label']} pilot")
        if input_data["ecutwfc"] != case["ecutwfc_ry"]:
            raise ValueError(f"Wrong ecutwfc in {case['input']}")
        if input_data["ecutrho"] != case["ecutrho_ry"]:
            raise ValueError(f"Wrong ecutrho in {case['input']}")
        if input_data["k_mesh"] != (6, 6, 1):
            raise ValueError(f"Wrong k-point mesh in {case['input']}")
        if input_data["degauss"] != 0.01:
            raise ValueError(f"Wrong smearing width in {case['input']}")
        inputs.append(input_data)
        statuses.append(status)

    geometry_delta = maximum_coordinate_difference(
        inputs[0]["positions"], inputs[1]["positions"]
    )
    if geometry_delta > 1.0e-10:
        raise ValueError(
            f"Li/C49 cutoff pilot geometries differ by {geometry_delta:.3e} angstrom"
        )

    energy_65 = statuses[1]["strict_result"]["final_total_energy_ry"]
    for case, input_data, status in zip(CUTOFF_CASES, inputs, statuses):
        result = status["strict_result"]
        resource_gate = status.get("acceptance_gates", {}).get(
            "gpu_memory_below_90_percent"
        )
        if resource_gate is None:
            host_gate = status.get("host_review", {}).get("relaxation_gate_passed")
            resource_gate = (
                "pass" if host_gate is True else "fail" if host_gate is False else "not_recorded"
            )
        delta_ry = result["final_total_energy_ry"] - energy_65
        prepared.append(
            {
                "system": "Li/C49",
                "check_type": "two_point_fixed_geometry_cutoff",
                "ecutwfc_ry": case["ecutwfc_ry"],
                "ecutrho_ry": case["ecutrho_ry"],
                "k_mesh": "6x6x1",
                "degauss_ry": f"{input_data['degauss']:.3f}",
                "total_energy_ry": f"{result['final_total_energy_ry']:.8f}",
                "delta_vs_65_520_mev_per_carbon": f"{delta_ry * RY_TO_EV * 1000.0 / CARBON_COUNT:.9f}",
                "total_force_ry_bohr": f"{result['final_total_force_ry_bohr']:.6f}",
                "maximum_force_ry_bohr": f"{result['maximum_force_ry_bohr']:.12f}",
                "total_magnetization_muB": f"{result['total_magnetization_bohr_magneton_per_cell']:.6f}",
                "gpu_active": str(result["gpu_acceleration_active"]).lower(),
                "scf_converged": str(result["all_electronic_cycles_converged"]).lower(),
                "job_done": str(result["job_completed"]).lower(),
                "same_geometry_max_coordinate_difference_ang": f"{geometry_delta:.3e}",
                "resource_gate": resource_gate,
                "source_input": relative(case["input"]),
                "source_output": status["output"],
            }
        )

    recorded_delta = statuses[0]["cutoff_comparison"]["energy_delta_ry"]
    calculated_delta = float(prepared[0]["total_energy_ry"]) - float(
        prepared[1]["total_energy_ry"]
    )
    if abs(recorded_delta - calculated_delta) > 5.0e-10:
        raise ValueError("Stored and independently calculated cutoff shifts disagree")
    return prepared


def collect_kpoints() -> list[dict]:
    prepared = []
    for case in KPOINT_CASES:
        relax = parse_output(case["relax_output"], calculation="relax")
        final_scf = parse_output(case["final_output"], calculation="scf")
        final_input = parse_input(case["final_input"])
        require_valid_result(relax, f"{case['system']} 6x6x1 relaxation", ionic=True)
        require_valid_result(final_scf, f"{case['system']} 9x9x1 final SCF")
        if final_input["ecutwfc"] != 65 or final_input["ecutrho"] != 520:
            raise ValueError(f"Wrong cutoff pair in {case['final_input']}")
        if final_input["k_mesh"] != (9, 9, 1):
            raise ValueError(f"Wrong k-point mesh in {case['final_input']}")
        if final_input["degauss"] != 0.01:
            raise ValueError(f"Wrong smearing width in {case['final_input']}")

        geometry_delta = maximum_coordinate_difference(
            relax["final_coordinates"], final_input["positions"]
        )
        if geometry_delta > 5.0e-9:
            raise ValueError(
                f"{case['system']} final-SCF geometry differs from the relaxed geometry "
                f"by {geometry_delta:.3e} angstrom"
            )

        delta_ry = final_scf["final_total_energy_ry"] - relax["final_total_energy_ry"]
        shared = {
            "system": case["system"],
            "check_type": "two_point_post_relaxation_kpoint_refinement",
            "ecutwfc_ry": 65,
            "ecutrho_ry": 520,
            "degauss_ry": "0.010",
            "delta_9x9_minus_6x6_mev_per_carbon": f"{delta_ry * RY_TO_EV * 1000.0 / CARBON_COUNT:.9f}",
            "geometry_match_max_coordinate_difference_ang": f"{geometry_delta:.3e}",
        }
        prepared.extend(
            (
                {
                    **shared,
                    "k_mesh": "6x6x1",
                    "calculation": "final_ionic_step_of_relaxation",
                    "total_energy_ry": f"{relax['final_total_energy_ry']:.8f}",
                    "gpu_active": str(relax["gpu_acceleration_active"]).lower(),
                    "scf_converged": str(relax["all_electronic_cycles_converged"]).lower(),
                    "job_done": str(relax["job_completed"]).lower(),
                    "source_input": "relaxation input/restart chain",
                    "source_output": relative(case["relax_output"]),
                },
                {
                    **shared,
                    "k_mesh": "9x9x1",
                    "calculation": "fixed_geometry_final_scf",
                    "total_energy_ry": f"{final_scf['final_total_energy_ry']:.8f}",
                    "gpu_active": str(final_scf["gpu_acceleration_active"]).lower(),
                    "scf_converged": str(final_scf["all_electronic_cycles_converged"]).lower(),
                    "job_done": str(final_scf["job_completed"]).lower(),
                    "source_input": relative(case["final_input"]),
                    "source_output": relative(case["final_output"]),
                },
            )
        )
    return prepared


def main() -> None:
    cutoff_rows = collect_cutoff()
    kpoint_rows = collect_kpoints()

    cutoff_status = load_json(CUTOFF_CASES[0]["status"])
    comparison = cutoff_status["cutoff_comparison"]
    acceptance = cutoff_status["acceptance_gates"]
    cutoff_comparison_rows = [
        {
            "system": "Li/C49",
            "comparison": "55/440_minus_65/520_fixed_geometry",
            "energy_difference_ry": f"{comparison['energy_delta_ry']:.14f}",
            "energy_difference_mev_per_carbon": cutoff_rows[0][
                "delta_vs_65_520_mev_per_carbon"
            ],
            "largest_force_component_delta_ry_bohr": f"{comparison['largest_force_component_delta_ry_bohr']:.8f}",
            "force_component_limit_ry_bohr": f"{comparison['force_component_limit_ry_bohr']:.8f}",
            "rms_force_component_delta_ry_bohr": f"{comparison['rms_force_component_delta_ry_bohr']:.12f}",
            "largest_force_vector_delta_ry_bohr": f"{comparison['largest_force_vector_delta_ry_bohr']:.12f}",
            "total_magnetization_delta_muB": f"{comparison['total_magnetization_delta_bohr_magneton_per_cell']:.6f}",
            "magnetization_limit_muB": f"{comparison['magnetization_limit_bohr_magneton_per_cell']:.6f}",
            "scientific_completion_gate": acceptance["scientific_completion"],
            "force_field_gate": acceptance["force_field"],
            "magnetization_gate": acceptance["magnetization"],
            "gpu_memory_gate": acceptance["gpu_memory_below_90_percent"],
        }
    ]

    write_csv(
        OUTPUT_DIR / "vacancy_cutoff_check.csv",
        cutoff_rows,
        list(cutoff_rows[0]),
    )
    write_csv(
        OUTPUT_DIR / "vacancy_kpoint_refinement.csv",
        kpoint_rows,
        list(kpoint_rows[0]),
    )
    write_csv(
        OUTPUT_DIR / "vacancy_cutoff_comparison.csv",
        cutoff_comparison_rows,
        list(cutoff_comparison_rows[0]),
    )

    coverage_rows = [
        {
            "system": "C49",
            "cutoff_evidence": "not_calculated",
            "kpoint_evidence": "two_point_6x6x1_to_9x9x1_final_energy",
            "smearing_evidence": "not_calculated",
        },
        {
            "system": "Li/C49",
            "cutoff_evidence": "two_point_55_440_to_65_520_fixed_geometry",
            "kpoint_evidence": "two_point_6x6x1_to_9x9x1_final_energy",
            "smearing_evidence": "not_calculated",
        },
        {
            "system": "Na/C49",
            "cutoff_evidence": "not_calculated",
            "kpoint_evidence": "two_point_6x6x1_to_9x9x1_final_energy",
            "smearing_evidence": "not_calculated",
        },
    ]
    write_csv(
        OUTPUT_DIR / "vacancy_validation_coverage.csv",
        coverage_rows,
        list(coverage_rows[0]),
    )

    print(f"Wrote {OUTPUT_DIR / 'vacancy_cutoff_check.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'vacancy_cutoff_comparison.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'vacancy_kpoint_refinement.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'vacancy_validation_coverage.csv'}")
    print(
        "Li/C49 55/440 minus 65/520: "
        f"{cutoff_rows[0]['delta_vs_65_520_mev_per_carbon']} meV/C"
    )
    for row in kpoint_rows[::2]:
        print(
            f"{row['system']} 9x9x1 minus 6x6x1: "
            f"{row['delta_9x9_minus_6x6_mev_per_carbon']} meV/C"
        )


if __name__ == "__main__":
    main()
