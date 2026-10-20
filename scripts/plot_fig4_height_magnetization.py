#!/usr/bin/env python3
"""Create report Figure 4: relaxed height and magnetic response.

The two panels use the accepted 65/520 Ry, 6x6x1 relaxation results. Panel (a)
compares relaxed adsorbate heights. Panel (b) compares total magnetization and
shows the accepted bare-C49 moment as a reference over the vacancy group only.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "plot_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

SUBSTRATES = ("C50", "C49")
METALS = ("Li", "Na")
SYSTEMS = {f"{metal}/{substrate}" for substrate in SUBSTRATES for metal in METALS}
COLORS = {"Li": "#0072B2", "Na": "#E69F00"}
HATCHES = {"Li": "///", "Na": "\\\\\\"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require_accepted_relaxation(row: dict[str, str]) -> None:
    if row["ecutwfc_ry"] != "65" or row["ecutrho_ry"] != "520":
        raise ValueError(f"{row['system']} is not the accepted 65/520 Ry result")
    if row["k_mesh"] != "6x6x1":
        raise ValueError(f"{row['system']} is not from the 6x6x1 relaxation")
    for field in ("ionic_converged", "job_done"):
        if row[field].strip().lower() != "true":
            raise ValueError(f"{row['system']} failed required status {field}")


def load_properties(
    path: Path,
) -> tuple[dict[tuple[str, str], dict[str, float]], float]:
    properties: dict[tuple[str, str], dict[str, float]] = {}
    bare_c49_moment: float | None = None

    for row in read_csv(path):
        if row["system"] == "C49":
            require_accepted_relaxation(row)
            if row["total_magnetization_muB"] == "":
                raise ValueError("Bare C49 magnetization is missing")
            bare_c49_moment = float(row["total_magnetization_muB"])
            continue

        if row["system"] not in SYSTEMS:
            continue
        require_accepted_relaxation(row)
        key = (row["substrate"], row["metal"])
        if key in properties:
            raise ValueError(f"Duplicate relaxed-property row for {key}")
        if row["adsorbate_height_ang"] == "" or row["total_magnetization_muB"] == "":
            raise ValueError(f"Height or magnetization is missing for {row['system']}")

        height = float(row["adsorbate_height_ang"])
        moment = float(row["total_magnetization_muB"])
        if height <= 0.0:
            raise ValueError(f"Non-positive adsorbate height for {row['system']}: {height}")
        if moment < 0.0:
            raise ValueError(f"Negative total-magnetization magnitude for {row['system']}")
        properties[key] = {"height": height, "moment": moment}

    expected = {(substrate, metal) for substrate in SUBSTRATES for metal in METALS}
    if set(properties) != expected:
        raise ValueError(f"Expected relaxed systems {expected}, found {set(properties)}")
    if bare_c49_moment is None:
        raise ValueError("Bare C49 reference row was not found")
    if not np.isclose(bare_c49_moment, 1.60, rtol=0.0, atol=5.0e-12):
        raise ValueError(f"Unexpected bare C49 moment: {bare_c49_moment:.12f} muB/cell")
    return properties, bare_c49_moment


def style_axis(ax: plt.Axes, major_step: float) -> None:
    ax.yaxis.set_major_locator(MultipleLocator(major_step))
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


def add_grouped_bars(
    ax: plt.Axes,
    properties: dict[tuple[str, str], dict[str, float]],
    field: str,
    value_decimals: int,
) -> None:
    centers = np.arange(len(SUBSTRATES), dtype=float)
    width = 0.30
    offsets = {"Li": -width / 1.8, "Na": width / 1.8}

    for metal in METALS:
        x_positions = centers + offsets[metal]
        values = [properties[(substrate, metal)][field] for substrate in SUBSTRATES]
        bars = ax.bar(
            x_positions,
            values,
            width=width,
            color=COLORS[metal],
            edgecolor="#202020",
            linewidth=0.9,
            hatch=HATCHES[metal],
            zorder=3,
        )
        for bar, value in zip(bars, values):
            ax.annotate(
                f"{value:.{value_decimals}f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, value),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=11.5,
                fontweight="bold",
                color="#202020",
                zorder=5,
            )

    ax.set_xticks(centers, ("Pristine\nC50", "Monovacancy\nC49"))
    ax.set_xlim(-0.55, 1.55)


def make_figure(
    properties: dict[tuple[str, str], dict[str, float]],
    bare_c49_moment: float,
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

    fig, axes = plt.subplots(1, 2, figsize=(9.1, 5.3), constrained_layout=True)
    add_grouped_bars(axes[0], properties, "height", value_decimals=3)
    add_grouped_bars(axes[1], properties, "moment", value_decimals=2)

    axes[0].set_title("(a) Adsorbate height", fontsize=14, fontweight="bold", pad=13)
    axes[0].set_ylabel("Adsorbate height (Å)")
    axes[0].set_xlabel("Graphene substrate")
    axes[0].set_ylim(0.0, 2.65)
    style_axis(axes[0], major_step=0.5)

    axes[1].set_title("(b) Magnetic response", fontsize=14, fontweight="bold", pad=13)
    axes[1].set_ylabel(r"Total magnetization ($\mu_B$/cell)")
    axes[1].set_xlabel("Graphene substrate")
    axes[1].set_ylim(0.0, 1.82)
    style_axis(axes[1], major_step=0.5)

    # Bare C49 is a vacancy-only reference, so the guide spans only that group.
    axes[1].hlines(
        bare_c49_moment,
        xmin=0.68,
        xmax=1.32,
        color="#404040",
        linestyle=(0, (5, 3)),
        linewidth=1.8,
        zorder=4,
    )
    axes[1].text(
        1.0,
        bare_c49_moment + 0.035,
        f"Bare C49: {bare_c49_moment:.2f}",
        ha="center",
        va="bottom",
        fontsize=10.5,
        color="#404040",
    )

    handles = [
        Patch(
            facecolor=COLORS["Li"],
            edgecolor="#202020",
            hatch=HATCHES["Li"],
            label="Li",
        ),
        Patch(
            facecolor=COLORS["Na"],
            edgecolor="#202020",
            hatch=HATCHES["Na"],
            label="Na",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.035),
        ncol=2,
        frameon=False,
        handlelength=1.6,
        columnspacing=2.0,
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
        help="Directory containing relaxed_geometry_properties.csv",
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
    properties, bare_c49_moment = load_properties(
        args.data_dir / "relaxed_geometry_properties.csv"
    )
    png_path = args.output_dir / "fig04_height_magnetization.png"
    pdf_path = args.output_dir / "fig04_height_magnetization.pdf"
    make_figure(properties, bare_c49_moment, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    for substrate in SUBSTRATES:
        for metal in METALS:
            values = properties[(substrate, metal)]
            print(
                f"{metal}/{substrate}: height={values['height']:.10f} A, "
                f"moment={values['moment']:.10f} muB/cell"
            )
    print(f"Bare C49 moment={bare_c49_moment:.10f} muB/cell")


if __name__ == "__main__":
    main()
