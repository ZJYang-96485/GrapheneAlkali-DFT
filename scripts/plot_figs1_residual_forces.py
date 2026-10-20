#!/usr/bin/env python3
"""Create Supplementary Figure S1: residual-force convergence check.

The accepted 65/520 Ry, 6x6x1 relaxation results are compared with the
4.0e-4 Ry/Bohr force-component threshold.  A logarithmic vertical axis keeps
the much smaller pristine-C50 residual visible.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "plot_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

FORCE_THRESHOLD = 4.0e-4
SYSTEM_ORDER = ("C50", "C49", "Li/C50", "Na/C50", "Li/C49", "Na/C49")
DISPLAY_LABELS = {
    "C50": "Bare\nC50",
    "C49": "Bare\nC49",
    "Li/C50": "Li/C50",
    "Na/C50": "Na/C50",
    "Li/C49": "Li/C49",
    "Na/C49": "Na/C49",
}
COLORS = {
    "C50": "#8A8A8A",
    "C49": "#4D4D4D",
    "Li/C50": "#56B4E9",
    "Li/C49": "#0072B2",
    "Na/C50": "#F0C24B",
    "Na/C49": "#E69F00",
}
HATCHES = {
    "C50": "",
    "C49": "...",
    "Li/C50": "//",
    "Li/C49": "///",
    "Na/C50": "\\\\",
    "Na/C49": "\\\\\\",
}
EXPECTED_FORCES = {
    "C50": 0.00000207,
    "C49": 0.000328405665,
    "Li/C50": 0.000316472047,
    "Na/C50": 0.00036846,
    "Li/C49": 0.00036398,
    "Na/C49": 0.00039186,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_forces(path: Path) -> dict[str, float]:
    forces: dict[str, float] = {}
    for row in read_csv(path):
        system = row["system"]
        if system not in SYSTEM_ORDER:
            continue
        if row["ecutwfc_ry"] != "65" or row["ecutrho_ry"] != "520":
            raise ValueError(f"{system} is not the accepted 65/520 Ry relaxation")
        if row["k_mesh"] != "6x6x1":
            raise ValueError(f"{system} is not from the 6x6x1 relaxation mesh")
        for flag in ("ionic_converged", "job_done"):
            if row[flag].strip().lower() != "true":
                raise ValueError(f"{system} failed required status {flag}")
        if system in forces:
            raise ValueError(f"Duplicate relaxed-force row for {system}")
        if row["max_force_component_ry_bohr"] == "":
            raise ValueError(f"Maximum force component is missing for {system}")

        value = float(row["max_force_component_ry_bohr"])
        if value <= 0.0:
            raise ValueError(f"Non-positive maximum force component for {system}: {value}")
        if value >= FORCE_THRESHOLD:
            raise ValueError(
                f"{system} exceeds the {FORCE_THRESHOLD:.1e} Ry/Bohr threshold"
            )
        if not np.isclose(
            value, EXPECTED_FORCES[system], rtol=0.0, atol=5.0e-13
        ):
            raise ValueError(f"Unexpected prepared force for {system}: {value:.12e}")
        forces[system] = value

    if set(forces) != set(SYSTEM_ORDER):
        raise ValueError(f"Expected systems {SYSTEM_ORDER}, found {tuple(forces)}")
    return forces


def scientific_label(value: float) -> str:
    exponent = int(np.floor(np.log10(value)))
    coefficient = value / (10.0**exponent)
    return rf"${coefficient:.2f}\times10^{{{exponent}}}$"


def make_figure(forces: dict[str, float], png_path: Path, pdf_path: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.labelsize": 14,
            "axes.titlesize": 14,
            "xtick.labelsize": 11.5,
            "ytick.labelsize": 12,
            "axes.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    systems = list(SYSTEM_ORDER)
    values = np.array([forces[system] for system in systems])
    x = np.arange(len(systems), dtype=float)
    lower_bound = 1.0e-6

    fig, ax = plt.subplots(figsize=(9.4, 5.6), constrained_layout=True)
    bars = ax.bar(
        x,
        values - lower_bound,
        bottom=lower_bound,
        width=0.62,
        color=[COLORS[system] for system in systems],
        edgecolor="#202020",
        linewidth=1.0,
        hatch=[HATCHES[system] for system in systems],
        zorder=3,
    )

    for bar, value, system in zip(bars, values, systems):
        x_center = bar.get_x() + bar.get_width() / 2.0
        if system == "C50":
            ax.annotate(
                scientific_label(value),
                xy=(x_center, value),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10.5,
                fontweight="bold",
                color="#202020",
                zorder=5,
            )
        else:
            ax.text(
                x_center,
                value / 1.22,
                scientific_label(value),
                ha="center",
                va="top",
                fontsize=10.0,
                fontweight="bold",
                color="#202020",
                bbox={
                    "facecolor": "white",
                    "edgecolor": "none",
                    "pad": 1.2,
                    "alpha": 0.88,
                },
                zorder=5,
            )

    ax.axhline(
        FORCE_THRESHOLD,
        color="#CC79A7",
        linestyle=(0, (5, 3)),
        linewidth=2.0,
        zorder=4,
    )
    ax.text(
        0.015,
        0.965,
        r"Force threshold $=4.0\times10^{-4}$ Ry/Bohr",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        color="#8F3E72",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5, "alpha": 0.9},
        zorder=6,
    )

    ax.set_title("Residual force check", fontweight="bold", pad=13)
    ax.set_xlabel("Relaxed system")
    ax.set_ylabel("Maximum force component (Ry/Bohr)")
    ax.set_xticks(x, [DISPLAY_LABELS[system] for system in systems])
    ax.set_xlim(-0.60, len(systems) - 0.40)
    ax.set_yscale("log")
    ax.set_ylim(lower_bound, 7.0e-4)
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=4))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10.0))
    ax.yaxis.set_minor_locator(
        LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1, numticks=30)
    )
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="both", which="major", direction="out", length=6, width=1.0)
    ax.tick_params(axis="y", which="minor", direction="out", length=3, width=0.8)
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", which="major", color="#D5D5D5", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

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
    forces = load_forces(args.data_dir / "relaxed_geometry_properties.csv")
    png_path = args.output_dir / "figS1_residual_forces.png"
    pdf_path = args.output_dir / "figS1_residual_forces.pdf"
    make_figure(forces, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    for system in SYSTEM_ORDER:
        fraction = forces[system] / FORCE_THRESHOLD
        print(
            f"{system}: {forces[system]:.12e} Ry/Bohr "
            f"({fraction * 100.0:.3f}% of threshold)"
        )


if __name__ == "__main__":
    main()
