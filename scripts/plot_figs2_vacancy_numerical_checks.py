#!/usr/bin/env python3
"""Plot the available two-point numerical checks for vacancy systems."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "convergence_collection"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

LINE_COLOR = "#4D4D4D"
SELECTED_COLOR = "#0072B2"
CRITERION_COLOR = "#CC79A7"
BAR_COLORS = ("#0072B2", "#E69F00", "#6F4C9B")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require_flags(row: dict[str, str], label: str) -> None:
    for field in ("gpu_active", "scf_converged", "job_done"):
        if row[field].strip().lower() != "true":
            raise ValueError(f"{label} failed required flag {field}")


def load_cutoff(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = read_csv(path)
    if len(rows) != 2:
        raise ValueError(f"Expected two Li/C49 cutoff rows; found {len(rows)}")
    points = []
    for row in rows:
        require_flags(row, f"Li/C49 {row['ecutwfc_ry']} Ry")
        if row["system"] != "Li/C49":
            raise ValueError("Vacancy cutoff check contains an unexpected system")
        if row["check_type"] != "two_point_fixed_geometry_cutoff":
            raise ValueError("Vacancy cutoff rows have the wrong check type")
        if row["k_mesh"] != "6x6x1" or not np.isclose(
            float(row["degauss_ry"]), 0.01, rtol=0.0, atol=1.0e-12
        ):
            raise ValueError("Vacancy cutoff inputs do not share the expected sampling")
        if float(row["same_geometry_max_coordinate_difference_ang"]) > 1.0e-10:
            raise ValueError("Vacancy cutoff inputs do not use the same geometry")
        ecutwfc = float(row["ecutwfc_ry"])
        ecutrho = float(row["ecutrho_ry"])
        if not np.isclose(ecutrho, 8.0 * ecutwfc):
            raise ValueError("Unexpected charge-density cutoff ratio")
        points.append(
            (ecutwfc, float(row["delta_vs_65_520_mev_per_carbon"]))
        )
    points.sort()
    x = np.asarray([point[0] for point in points])
    y = np.asarray([point[1] for point in points])
    if not np.array_equal(x, np.asarray((55.0, 65.0))):
        raise ValueError(f"Unexpected cutoff points: {x}")
    if not np.isclose(y[1], 0.0, rtol=0.0, atol=5.0e-12):
        raise ValueError("65/520 Ry cutoff reference is not zero")
    return x, y


def load_kpoints(path: Path) -> tuple[list[str], np.ndarray]:
    rows = read_csv(path)
    systems = ("C49", "Li/C49", "Na/C49")
    values = []
    for system in systems:
        system_rows = [row for row in rows if row["system"] == system]
        if len(system_rows) != 2:
            raise ValueError(f"Expected two k-point rows for {system}")
        meshes = {row["k_mesh"] for row in system_rows}
        if meshes != {"6x6x1", "9x9x1"}:
            raise ValueError(f"Unexpected k-point meshes for {system}: {meshes}")
        for row in system_rows:
            require_flags(row, f"{system} {row['k_mesh']}")
            if row["check_type"] != "two_point_post_relaxation_kpoint_refinement":
                raise ValueError(f"Wrong k-point check type for {system}")
            if float(row["geometry_match_max_coordinate_difference_ang"]) > 5.0e-9:
                raise ValueError(f"Geometry mismatch in {system} k-point check")
        deltas = {
            float(row["delta_9x9_minus_6x6_mev_per_carbon"])
            for row in system_rows
        }
        if len(deltas) != 1:
            raise ValueError(f"Inconsistent stored k-point shift for {system}")
        values.append(deltas.pop())
    return list(systems), np.asarray(values)


def style_axis(ax: plt.Axes) -> None:
    ax.tick_params(axis="both", which="major", direction="out", length=6, width=1.0)
    ax.tick_params(axis="y", which="minor", direction="out", length=3, width=0.8)
    ax.set_axisbelow(True)
    ax.grid(axis="y", which="major", color="#D5D5D5", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def make_figure(
    cutoff: tuple[np.ndarray, np.ndarray],
    kpoints: tuple[list[str], np.ndarray],
    png_path: Path,
    pdf_path: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11.5,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 10.5,
            "axes.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), constrained_layout=True)

    # (a) Li/C49 fixed-geometry cutoff check.
    cutoff_x, cutoff_y = cutoff
    ax = axes[0]
    ax.plot(
        cutoff_x,
        cutoff_y,
        color=LINE_COLOR,
        linewidth=1.8,
        marker="o",
        markersize=7,
        markerfacecolor="white",
        markeredgecolor=LINE_COLOR,
        markeredgewidth=1.4,
        zorder=3,
    )
    ax.scatter(
        [65.0],
        [0.0],
        marker="*",
        s=180,
        facecolor=SELECTED_COLOR,
        edgecolor="#202020",
        linewidth=0.8,
        zorder=5,
    )
    ax.axhline(
        1.0,
        color=CRITERION_COLOR,
        linestyle=(0, (5, 3)),
        linewidth=1.6,
        zorder=2,
    )
    for x, y in zip(cutoff_x, cutoff_y):
        ax.annotate(
            f"{y:+.3f}",
            xy=(x, y),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10.5,
            color="#202020",
        )
    ax.text(
        0.5,
        0.965,
        r"Same geometry; $6\!\times\!6\!\times\!1$ mesh",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10,
        color="#404040",
    )
    ax.set_title("(a) Li/C49 cutoff check", fontsize=13.5, fontweight="bold", pad=12)
    ax.set_xlabel("Wavefunction cutoff (Ry)")
    ax.set_ylabel("Energy difference from 65/520 (meV/C)")
    ax.set_xlim(52.5, 67.5)
    ax.set_ylim(-0.25, 3.20)
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    style_axis(ax)

    # (b) Fixed-geometry final-SCF refinement after the 6x6x1 relaxations.
    systems, shifts = kpoints
    ax = axes[1]
    positions = np.arange(len(systems))
    bars = ax.bar(
        positions,
        shifts,
        width=0.62,
        color=BAR_COLORS,
        edgecolor="#202020",
        linewidth=0.8,
        zorder=3,
    )
    ax.axhline(0.0, color="#202020", linewidth=1.0, zorder=2)
    for bar, value in zip(bars, shifts):
        offset = 7 if value >= 0.0 else -8
        va = "bottom" if value >= 0.0 else "top"
        ax.annotate(
            f"{value:+.3f}",
            xy=(bar.get_x() + bar.get_width() / 2.0, value),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=10.5,
            color="#202020",
        )
    ax.text(
        0.5,
        0.965,
        r"All $|\Delta E| < 0.026$ meV/C",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10,
        color="#404040",
    )
    ax.text(
        0.5,
        0.065,
        r"$\pm 1$ meV/C guide lies outside this zoom",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9.5,
        color="#505050",
    )
    ax.set_title("(b) k-point refinement", fontsize=13.5, fontweight="bold", pad=12)
    ax.set_xlabel("Vacancy-containing system")
    ax.set_ylabel(r"$E_{9\times9\times1}-E_{6\times6\times1}$ (meV/C)")
    ax.set_xticks(positions, systems)
    ax.set_ylim(-0.037, 0.042)
    ax.yaxis.set_major_locator(MultipleLocator(0.01))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    style_axis(ax)

    handles = [
        Line2D(
            [0],
            [0],
            color=CRITERION_COLOR,
            linestyle=(0, (5, 3)),
            linewidth=1.6,
            label="1 meV/C criterion",
        ),
        Line2D(
            [0],
            [0],
            linestyle="none",
            marker="*",
            markersize=11,
            markerfacecolor=SELECTED_COLOR,
            markeredgecolor="#202020",
            label="Selected cutoff",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.07),
        ncol=2,
        frameon=False,
        handlelength=2.2,
        columnspacing=1.8,
    )

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cutoff = load_cutoff(args.data_dir / "vacancy_cutoff_check.csv")
    kpoints = load_kpoints(args.data_dir / "vacancy_kpoint_refinement.csv")
    png_path = args.output_dir / "figS2_vacancy_numerical_checks.png"
    pdf_path = args.output_dir / "figS2_vacancy_numerical_checks.pdf"
    make_figure(cutoff, kpoints, png_path, pdf_path)
    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
