#!/usr/bin/env python3
"""Parse, tabulate, evaluate, and plot Phase 4 pristine convergence results."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from parse_qe_output import parse_output


ROOT = Path(__file__).resolve().parents[1]
RY_TO_EV = 13.605693122994
NAT = 50
THRESHOLD_MEV_PER_ATOM = 1.0
STUDY_ORDER = ("cutoff", "kpoints", "smearing")
REFERENCE_TAG = {
    "cutoff": "ecutwfc_70_ecutrho_560",
    "kpoints": "k_12x12x1",
    "smearing": "degauss_0p010",
}
FIELDS = (
    "study",
    "tag",
    "ecutwfc_ry",
    "ecutrho_ry",
    "k_mesh",
    "k_shift",
    "degauss_ry",
    "total_energy_ry",
    "total_energy_ev",
    "energy_per_atom_ev",
    "delta_vs_reference_mev_per_atom",
    "smearing_contribution_ry",
    "internal_energy_ry",
    "fermi_energy_ev",
    "scf_iterations",
    "wall_time_seconds",
    "gpu_active",
    "scf_converged",
    "job_done",
    "output",
)


def load_results(manifest_path, studies):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    selected = [record for record in manifest if record["study"] in studies]
    parsed = []
    for record in selected:
        output_path = ROOT / record["output"]
        result = parse_output(output_path, calculation="scf")
        row = dict(record)
        row.update(
            {
                "total_energy_ry": result["final_total_energy_ry"],
                "total_energy_ev": result["final_total_energy_ry"] * RY_TO_EV,
                "energy_per_atom_ev": result["final_total_energy_ry"] * RY_TO_EV / NAT,
                "smearing_contribution_ry": result["smearing_contribution_ry"],
                "internal_energy_ry": result["internal_energy_ry"],
                "fermi_energy_ev": result["fermi_energy_ev"],
                "scf_iterations": result["scf_iterations"],
                "wall_time_seconds": result["wall_time_seconds"],
                "gpu_active": result["gpu_acceleration_active"],
                "scf_converged": result["electronic_convergence_reached"],
                "job_done": result["job_completed"],
            }
        )
        parsed.append(row)

    for study in studies:
        rows = [row for row in parsed if row["study"] == study]
        if not rows:
            continue
        reference = next(
            (row for row in rows if row["tag"] == REFERENCE_TAG[study]),
            None,
        )
        if reference is None:
            raise ValueError(f"missing {study} reference point {REFERENCE_TAG[study]}")
        reference_energy = reference["energy_per_atom_ev"]
        for row in rows:
            row["delta_vs_reference_mev_per_atom"] = (
                row["energy_per_atom_ev"] - reference_energy
            ) * 1000.0
    return parsed


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            rendered = dict(row)
            rendered["k_mesh"] = "x".join(str(value) for value in row["k_mesh"])
            rendered["k_shift"] = " ".join(str(value) for value in row["k_shift"])
            writer.writerow(rendered)


def markdown_table(rows):
    lines = [
        "| Point | Ecutwfc/rho (Ry) | k mesh | degauss (Ry) | Final F (Ry) | Delta (meV/C) | -TS (Ry) | Internal E=F+TS (Ry) | Fermi (eV) | SCF iterations | Wall (s) | GPU/JOB |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        smearing_contribution = row["smearing_contribution_ry"]
        internal_energy = row["internal_energy_ry"]
        fermi_energy = row["fermi_energy_ev"]
        lines.append(
            "| "
            f"{row['tag']} | {row['ecutwfc_ry']}/{row['ecutrho_ry']} | "
            f"{'x'.join(str(value) for value in row['k_mesh'])} | {row['degauss_ry']:.3f} | "
            f"{row['total_energy_ry']:.10f} | {row['delta_vs_reference_mev_per_atom']:+.4f} | "
            f"{smearing_contribution:.8f} | {internal_energy:.8f} | {fermi_energy:.4f} | "
            f"{row['scf_iterations']} | {row['wall_time_seconds']:.2f} | "
            f"{'yes' if row['gpu_active'] and row['job_done'] else 'NO'} |"
        )
    return lines


def evaluate(rows):
    by_tag = {row["tag"]: row for row in rows}
    evaluation = {}
    if "ecutwfc_65_ecutrho_520" in by_tag:
        delta = abs(by_tag["ecutwfc_65_ecutrho_520"]["delta_vs_reference_mev_per_atom"])
        evaluation["cutoff_supported"] = delta <= THRESHOLD_MEV_PER_ATOM
        evaluation["cutoff_delta"] = delta
        cutoff_rows = sorted(
            (row for row in rows if row["study"] == "cutoff"),
            key=lambda row: row["ecutwfc_ry"],
        )
        evaluation["cutoff_monotonic_nonincreasing"] = all(
            later["total_energy_ry"] <= earlier["total_energy_ry"] + 1.0e-8
            for earlier, later in zip(cutoff_rows, cutoff_rows[1:])
        )
    if "k_6x6x1" in by_tag:
        delta = abs(by_tag["k_6x6x1"]["delta_vs_reference_mev_per_atom"])
        evaluation["k6_supported"] = delta <= THRESHOLD_MEV_PER_ATOM
        evaluation["k6_delta"] = delta
    if "k_9x9x1" in by_tag:
        delta = abs(by_tag["k_9x9x1"]["delta_vs_reference_mev_per_atom"])
        evaluation["k9_supported"] = delta <= THRESHOLD_MEV_PER_ATOM
        evaluation["k9_delta"] = delta
    if "degauss_0p005" in by_tag:
        delta = abs(by_tag["degauss_0p005"]["delta_vs_reference_mev_per_atom"])
        evaluation["smearing_001_reasonable"] = delta <= THRESHOLD_MEV_PER_ATOM
        evaluation["smearing_0005_delta"] = delta
    return evaluation


def plot_study(study, rows, figures_root):
    if study == "cutoff":
        rows = sorted(rows, key=lambda row: row["ecutwfc_ry"])
        x = [row["ecutwfc_ry"] for row in rows]
        xlabel = "Wavefunction cutoff (Ry)"
        filename = "cutoff_convergence.png"
        title = "Pristine C50 cutoff convergence"
    elif study == "kpoints":
        rows = sorted(rows, key=lambda row: row["k_mesh"][0])
        x = [row["k_mesh"][0] for row in rows]
        xlabel = "In-plane k-mesh dimension (N for N x N x 1)"
        filename = "kpoint_convergence.png"
        title = "Pristine C50 k-point convergence"
    else:
        rows = sorted(rows, key=lambda row: row["degauss_ry"])
        x = [row["degauss_ry"] for row in rows]
        xlabel = "Marzari-Vanderbilt degauss (Ry)"
        filename = "smearing_sensitivity.png"
        title = "Pristine C50 smearing sensitivity"

    y = [row["delta_vs_reference_mev_per_atom"] for row in rows]
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    ax.plot(x, y, marker="o", linewidth=1.6, color="#2457A6")
    ax.margins(y=0.15)
    ax.axhline(0.0, color="black", linewidth=0.8)
    if study != "smearing":
        ax.axhline(THRESHOLD_MEV_PER_ATOM, color="#B33A3A", linestyle="--", linewidth=1.0, label="+/-1 meV/C criterion")
        ax.axhline(-THRESHOLD_MEV_PER_ATOM, color="#B33A3A", linestyle="--", linewidth=1.0)
        ax.legend(frameon=False)
    for x_value, y_value in zip(x, y):
        ax.annotate(f"{y_value:+.3f}", (x_value, y_value), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Energy difference from reference (meV per C atom)")
    ax.set_title(title)
    ax.grid(alpha=0.22)
    fig.tight_layout()
    figures_root.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_root / filename, dpi=180)
    plt.close(fig)


def write_report(path, rows, evaluation):
    lines = [
        "# Pristine C50 convergence summary",
        "",
        f"Working energy-convergence criterion: {THRESHOLD_MEV_PER_ATOM:.1f} meV per carbon atom.",
        "All reported energies are the final converged QE total energies marked with `!`.",
    ]
    for study, heading in (
        ("cutoff", "Cutoff convergence"),
        ("kpoints", "K-point convergence"),
        ("smearing", "Smearing sensitivity"),
    ):
        study_rows = [row for row in rows if row["study"] == study]
        if study_rows:
            lines.extend(["", f"## {heading}", "", *markdown_table(study_rows)])

    lines.extend(["", "## Decisions", ""])
    if "cutoff_supported" in evaluation:
        lines.append(
            f"- 65/520 Ry supported: **{'yes' if evaluation['cutoff_supported'] else 'no'}** "
            f"(absolute difference from 70/560: {evaluation['cutoff_delta']:.4f} meV/C)."
        )
        lines.append(
            f"- Cutoff energies monotonic within 1e-8 Ry: **{'yes' if evaluation['cutoff_monotonic_nonincreasing'] else 'no'}**."
        )
    if "k6_supported" in evaluation:
        lines.append(
            f"- 6x6x1 supported for relaxation: **{'yes' if evaluation['k6_supported'] else 'no'}** "
            f"(absolute difference from 12x12x1: {evaluation['k6_delta']:.4f} meV/C)."
        )
    if "k9_supported" in evaluation:
        lines.append(
            f"- 9x9x1 supported for final SCF: **{'yes' if evaluation['k9_supported'] else 'no'}** "
            f"(absolute difference from 12x12x1: {evaluation['k9_delta']:.4f} meV/C)."
        )
    if "smearing_001_reasonable" in evaluation:
        lines.append(
            f"- 0.01 Ry smearing reasonable for pristine relaxation: **{'yes' if evaluation['smearing_001_reasonable'] else 'no'}** "
            f"(absolute difference from 0.005 Ry: {evaluation['smearing_0005_delta']:.4f} meV/C)."
        )
    lines.extend(
        [
            "",
            "Smearing contributions, internal energies E=F+TS, and Fermi energies are transcribed from QE when present; no undocumented internal-energy quantity is introduced.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "qe_inputs/convergence/pristine/manifest.json",
    )
    parser.add_argument("--study", choices=(*STUDY_ORDER, "all"), default="all")
    args = parser.parse_args()
    studies = STUDY_ORDER if args.study == "all" else (args.study,)
    rows = load_results(args.manifest, studies)
    evaluation = evaluate(rows)

    results_root = ROOT / "results/convergence/pristine"
    if args.study == "all":
        write_csv(results_root / "summary.csv", rows)
        write_report(results_root / "summary.md", rows, evaluation)
        for study in STUDY_ORDER:
            plot_study(
                study,
                [row for row in rows if row["study"] == study],
                ROOT / "figures/convergence",
            )
    else:
        write_csv(results_root / args.study / "summary.csv", rows)
        write_report(results_root / args.study / "summary.md", rows, evaluation)
        plot_study(
            args.study,
            rows,
            ROOT / "figures/convergence",
        )

    print(json.dumps(evaluation, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
