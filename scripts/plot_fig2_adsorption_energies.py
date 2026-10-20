#!/usr/bin/env python3
"""Create report Figure 2: adsorption energies with literature benchmarks.

The bars use only the common four-system 65/520 Ry dataset. Open diamonds are
published comparison values. The plot is exported as both a high-resolution
PNG and a vector PDF.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "plot_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

SYSTEMS = ("Li/C50", "Na/C50", "Li/C49", "Na/C49")
SUBSTRATES = ("C50", "C49")
METALS = ("Li", "Na")
COLORS = {"Li": "#0072B2", "Na": "#E69F00"}  # Okabe-Ito palette
HATCHES = {"Li": "///", "Na": "\\\\\\"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require_true(row: dict[str, str], fields: tuple[str, ...]) -> None:
    failed = [field for field in fields if row.get(field, "").strip().lower() != "true"]
    if failed:
        raise ValueError(
            f"Rejected {row.get('record_id', row.get('system', 'row'))}: "
            f"required validation flag(s) are not true: {', '.join(failed)}"
        )


def load_project_values(path: Path) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    for row in read_csv(path):
        if row["comparison_role"] != "common_four_system_dataset":
            continue
        if row["system"] not in SYSTEMS:
            continue
        require_true(row, ("gpu_active", "electronic_converged", "job_done"))
        if row["ecutwfc_ry"] != "65" or row["ecutrho_ry"] != "520":
            raise ValueError(f"Common-dataset row {row['record_id']} is not 65/520 Ry")
        key = (row["substrate"], row["metal"])
        if key in values:
            raise ValueError(f"Duplicate project value for {key}")
        values[key] = float(row["adsorption_energy_ev"])

    expected = {(substrate, metal) for substrate in SUBSTRATES for metal in METALS}
    if set(values) != expected:
        raise ValueError(f"Project data mismatch: expected {expected}, found {set(values)}")
    return values


def load_literature_values(path: Path) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    substrate_map = {"pristine": "C50", "monovacancy": "C49"}
    for row in read_csv(path):
        if row["quantity"] != "adsorption_energy":
            continue
        key = (substrate_map[row["substrate"]], row["metal"])
        if key in values:
            raise ValueError(f"Duplicate literature value for {key}")
        values[key] = float(row["literature_value"])

    expected = {(substrate, metal) for substrate in SUBSTRATES for metal in METALS}
    if set(values) != expected:
        raise ValueError(f"Literature data mismatch: expected {expected}, found {set(values)}")
    return values


def make_figure(
    project: dict[tuple[str, str], float],
    literature: dict[tuple[str, str], float],
    png_path: Path,
    pdf_path: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 11,
            "axes.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(7.4, 5.4), constrained_layout=True)
    centers = np.arange(len(SUBSTRATES), dtype=float)
    width = 0.30
    offsets = {"Li": -width / 1.8, "Na": width / 1.8}

    for metal in METALS:
        x_positions = centers + offsets[metal]
        y_values = [project[(substrate, metal)] for substrate in SUBSTRATES]
        bars = ax.bar(
            x_positions,
            y_values,
            width=width,
            color=COLORS[metal],
            edgecolor="#202020",
            linewidth=0.9,
            hatch=HATCHES[metal],
            zorder=2,
        )

        for x, y_project, substrate in zip(x_positions, y_values, SUBSTRATES):
            y_literature = literature[(substrate, metal)]
            ax.plot(
                [x, x],
                [y_project, y_literature],
                color="#555555",
                linestyle=(0, (2, 2)),
                linewidth=1.0,
                zorder=3,
            )
            ax.scatter(
                x,
                y_literature,
                marker="D",
                s=72,
                facecolor="white",
                edgecolor="#202020",
                linewidth=1.6,
                zorder=4,
            )

        for bar, value in zip(bars, y_values):
            ax.annotate(
                f"{value:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, value),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color="white",
                fontsize=11,
                fontweight="bold",
                zorder=5,
            )

    ax.set_xlabel("Graphene substrate")
    ax.set_ylabel("Adsorption energy (eV)")
    ax.set_xticks(centers, ("Pristine C50", "Monovacancy C49"))
    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(-3.55, 0.15)

    # One-decimal major tick labels and four evenly spaced subticks per interval.
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.tick_params(axis="both", which="major", direction="out", length=6, width=1.0)
    ax.tick_params(axis="y", which="minor", direction="out", length=3, width=0.8)
    ax.tick_params(axis="x", which="minor", bottom=False)

    ax.set_axisbelow(True)
    ax.grid(axis="y", which="major", color="#D5D5D5", linewidth=0.7)
    ax.axhline(0.0, color="#202020", linewidth=1.0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    handles = [
        Patch(
            facecolor=COLORS["Li"],
            edgecolor="#202020",
            hatch=HATCHES["Li"],
            label="Li (this work)",
        ),
        Patch(
            facecolor=COLORS["Na"],
            edgecolor="#202020",
            hatch=HATCHES["Na"],
            label="Na (this work)",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="none",
            markersize=7.5,
            markerfacecolor="white",
            markeredgecolor="#202020",
            markeredgewidth=1.5,
            label="Literature",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=3,
        frameon=False,
        handlelength=1.5,
        columnspacing=1.8,
    )
    ax.text(
        0.985,
        0.03,
        "More negative = stronger adsorption",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=10.5,
        color="#404040",
    )

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing adsorption_energies.csv and literature_comparison.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the PNG and PDF outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adsorption_csv = args.data_dir / "adsorption_energies.csv"
    literature_csv = args.data_dir / "literature_comparison.csv"
    png_path = args.output_dir / "fig02_adsorption_energies.png"
    pdf_path = args.output_dir / "fig02_adsorption_energies.pdf"

    project = load_project_values(adsorption_csv)
    literature = load_literature_values(literature_csv)
    make_figure(project, literature, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    for substrate in SUBSTRATES:
        for metal in METALS:
            print(
                f"{metal}/{substrate}: project={project[(substrate, metal)]:.6f} eV, "
                f"literature={literature[(substrate, metal)]:.6f} eV"
            )


if __name__ == "__main__":
    main()
