#!/usr/bin/env python3
"""Create report Figure 5: pristine-graphene numerical convergence.

The three panels show energy differences per carbon atom for the plane-wave
cutoff, k-point mesh, and smearing tests. Signed smearing differences are
preserved. All rows must pass the stored GPU, SCF-convergence, and JOB DONE
checks before they are plotted.
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
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "plot_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

LINE_COLOR = "#4D4D4D"
SELECTED_COLOR = "#0072B2"
CRITERION_COLOR = "#CC79A7"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require_valid_run(row: dict[str, str], identifier: str) -> None:
    for field in ("gpu_active", "scf_converged", "job_done"):
        if row[field].strip().lower() != "true":
            raise ValueError(f"{identifier} failed required validation flag {field}")


def load_cutoff(path: Path) -> tuple[np.ndarray, np.ndarray]:
    records: list[tuple[float, float]] = []
    for row in read_csv(path):
        identifier = f"ecutwfc={row['ecutwfc_ry']} Ry"
        require_valid_run(row, identifier)
        ecutwfc = float(row["ecutwfc_ry"])
        ecutrho = float(row["ecutrho_ry"])
        if not np.isclose(ecutrho, 8.0 * ecutwfc):
            raise ValueError(f"Unexpected ecutrho ratio for {identifier}")
        records.append((ecutwfc, float(row["delta_vs_70_560_mev_per_carbon"])))

    records.sort()
    x = np.asarray([item[0] for item in records])
    y = np.asarray([item[1] for item in records])
    if not np.array_equal(x, np.asarray([40, 45, 50, 55, 60, 65, 70], dtype=float)):
        raise ValueError(f"Unexpected cutoff grid: {x}")
    if not np.isclose(y[-1], 0.0, atol=5.0e-12):
        raise ValueError("70/560 Ry cutoff reference is not zero")
    if np.any(np.diff(y) > 5.0e-12):
        raise ValueError("Cutoff energy differences are not monotonically nonincreasing")
    return x, y


def load_kpoints(path: Path) -> tuple[np.ndarray, np.ndarray]:
    records: list[tuple[float, float]] = []
    for row in read_csv(path):
        identifier = row["k_mesh"]
        require_valid_run(row, identifier)
        n = float(row["k_grid_n"])
        if row["k_mesh"] != f"{int(n)}x{int(n)}x1":
            raise ValueError(f"Mesh label does not match k_grid_n for {identifier}")
        records.append((n, float(row["delta_vs_12x12x1_mev_per_carbon"])))

    records.sort()
    x = np.asarray([item[0] for item in records])
    y = np.asarray([item[1] for item in records])
    if not np.array_equal(x, np.asarray([3, 6, 9, 12], dtype=float)):
        raise ValueError(f"Unexpected k-point grid: {x}")
    if not np.isclose(y[-1], 0.0, atol=5.0e-12):
        raise ValueError("12x12x1 k-point reference is not zero")
    return x, y


def load_smearing(path: Path) -> tuple[np.ndarray, np.ndarray]:
    records: list[tuple[float, float]] = []
    for row in read_csv(path):
        identifier = f"degauss={row['degauss_ry']} Ry"
        require_valid_run(row, identifier)
        records.append((float(row["degauss_ry"]), float(row["delta_vs_0p01_mev_per_carbon"])))

    records.sort()
    x = np.asarray([item[0] for item in records])
    y = np.asarray([item[1] for item in records])
    if not np.allclose(x, np.asarray([0.005, 0.010, 0.020]), rtol=0.0, atol=5.0e-12):
        raise ValueError(f"Unexpected smearing grid: {x}")
    if not np.isclose(y[1], 0.0, atol=5.0e-12):
        raise ValueError("0.010 Ry smearing reference is not zero")
    if not (np.any(y < 0.0) and np.any(y > 0.0)):
        raise ValueError("Signed smearing differences were not preserved")
    return x, y


def base_style(ax: plt.Axes) -> None:
    ax.tick_params(axis="both", which="major", direction="out", length=6, width=1.0)
    ax.tick_params(axis="both", which="minor", direction="out", length=3, width=0.8)
    ax.set_axisbelow(True)
    ax.grid(axis="y", which="major", color="#D5D5D5", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_series(ax: plt.Axes, x: np.ndarray, y: np.ndarray) -> None:
    ax.plot(
        x,
        y,
        color=LINE_COLOR,
        linewidth=1.8,
        marker="o",
        markersize=6.5,
        markerfacecolor="white",
        markeredgecolor=LINE_COLOR,
        markeredgewidth=1.4,
        zorder=3,
    )


def mark_selected(ax: plt.Axes, x: float, y: float, label: str, xytext: tuple[float, float]) -> None:
    ax.scatter(
        [x],
        [y],
        marker="*",
        s=170,
        facecolor=SELECTED_COLOR,
        edgecolor="#202020",
        linewidth=0.8,
        zorder=5,
    )
    ax.annotate(
        label,
        xy=(x, y),
        xytext=xytext,
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=10.5,
        color="#202020",
    )


def add_positive_criterion(ax: plt.Axes) -> None:
    ax.axhline(
        1.0,
        color=CRITERION_COLOR,
        linestyle=(0, (5, 3)),
        linewidth=1.6,
        zorder=2,
    )


def make_figure(
    cutoff: tuple[np.ndarray, np.ndarray],
    kpoints: tuple[np.ndarray, np.ndarray],
    smearing: tuple[np.ndarray, np.ndarray],
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

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.8), constrained_layout=True)
    cutoff_x, cutoff_y = cutoff
    k_x, k_y = kpoints
    smear_x, smear_y = smearing

    # (a) Plane-wave cutoff convergence.
    ax = axes[0]
    plot_series(ax, cutoff_x, cutoff_y)
    add_positive_criterion(ax)
    mark_selected(ax, 65.0, cutoff_y[np.where(cutoff_x == 65.0)[0][0]], "65/520", (0, 10))
    ax.set_title("(a) Plane-wave cutoff", fontsize=13.5, fontweight="bold", pad=12)
    ax.set_xlabel("Wavefunction cutoff (Ry)")
    ax.set_ylabel("Energy difference (meV/C)")
    ax.set_xlim(38.5, 71.5)
    ax.set_ylim(-0.45, 10.55)
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_locator(MultipleLocator(2.0))
    ax.yaxis.set_minor_locator(AutoMinorLocator(4))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    base_style(ax)

    # (b) k-point convergence. Both the relaxation and final-SCF meshes are selected.
    ax = axes[1]
    plot_series(ax, k_x, k_y)
    add_positive_criterion(ax)
    y6 = k_y[np.where(k_x == 6.0)[0][0]]
    y9 = k_y[np.where(k_x == 9.0)[0][0]]
    mark_selected(ax, 6.0, y6, "relax.", (0, 10))
    mark_selected(ax, 9.0, y9, "final SCF", (0, 15))
    ax.set_title("(b) k-point mesh", fontsize=13.5, fontweight="bold", pad=12)
    ax.set_xlabel(r"Mesh density $N$ in $N\!\times\!N\!\times\!1$")
    ax.set_ylabel("Energy difference (meV/C)")
    ax.set_xlim(2.2, 12.8)
    ax.set_ylim(-0.10, 1.78)
    ax.xaxis.set_major_locator(MultipleLocator(3.0))
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    base_style(ax)

    # (c) Preserve the sign and zoom around zero; the ±1 criterion is outside this scale.
    ax = axes[2]
    plot_series(ax, smear_x, smear_y)
    ax.axhline(0.0, color="#202020", linewidth=1.0, zorder=2)
    y_selected = smear_y[np.where(np.isclose(smear_x, 0.010))[0][0]]
    mark_selected(ax, 0.010, y_selected, "selected", (0, 10))
    ax.text(
        0.5,
        0.965,
        r"$\pm$1 meV/C criterion is outside this zoom",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9.5,
        color="#404040",
    )
    ax.set_title("(c) Smearing", fontsize=13.5, fontweight="bold", pad=12)
    ax.set_xlabel("Smearing width (Ry)")
    ax.set_ylabel("Energy difference (meV/C)")
    ax.set_xlim(0.0038, 0.0212)
    ax.set_ylim(-0.075, 0.075)
    ax.xaxis.set_major_locator(MultipleLocator(0.005))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    base_style(ax)

    handles = [
        Line2D(
            [0],
            [0],
            color=LINE_COLOR,
            linewidth=1.8,
            marker="o",
            markersize=6,
            markerfacecolor="white",
            markeredgecolor=LINE_COLOR,
            label="Calculated point",
        ),
        Line2D(
            [0],
            [0],
            linestyle="none",
            marker="*",
            markersize=11,
            markerfacecolor=SELECTED_COLOR,
            markeredgecolor="#202020",
            label="Selected setting",
        ),
        Line2D(
            [0],
            [0],
            color=CRITERION_COLOR,
            linestyle=(0, (5, 3)),
            linewidth=1.6,
            label="1 meV/C criterion",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.075),
        ncol=3,
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
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the three convergence CSV files",
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
    cutoff = load_cutoff(args.data_dir / "cutoff_convergence.csv")
    kpoints = load_kpoints(args.data_dir / "kpoint_convergence.csv")
    smearing = load_smearing(args.data_dir / "smearing_sensitivity.csv")

    png_path = args.output_dir / "fig05_pristine_convergence.png"
    pdf_path = args.output_dir / "fig05_pristine_convergence.pdf"
    make_figure(cutoff, kpoints, smearing, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    print(f"65/520 cutoff delta: {cutoff[1][5]:.12f} meV/C")
    print(f"6x6x1 k-point delta: {kpoints[1][1]:.12f} meV/C")
    print(f"9x9x1 k-point delta: {kpoints[1][2]:.12f} meV/C")
    print(
        "Smearing deltas: "
        + ", ".join(f"{x:.3f} Ry={y:+.12f} meV/C" for x, y in zip(*smearing))
    )


if __name__ == "__main__":
    main()
