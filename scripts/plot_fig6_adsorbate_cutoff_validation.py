#!/usr/bin/env python3
"""Create report Figure 6: adsorption energies and cutoff-validation coverage.

The top panels compare pristine Li/C50 and Na/C50 adsorption energies at
65/520 and 70/560 Ry.  The bottom panels retain the validated 65/520 Ry
vacancy-adsorption results and explicitly show that 70/560 Ry vacancy values
were not calculated.  Prepared pristine cutoff shifts are independently
checked against the adsorption-energy table before plotting.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "results" / "final_project" / "plot_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures" / "report"

METALS = ("Li", "Na")
CUTOFFS = ((65, 520), (70, 560))
COLORS = {"Li": "#0072B2", "Na": "#E69F00"}

EXPECTED_ENERGIES_EV = {
    ("Li", "C50", 65, 520): -1.165573742974,
    ("Li", "C50", 70, 560): -1.167671604795187,
    ("Na", "C50", 65, 520): -0.561621923293,
    ("Na", "C50", 70, 560): -0.572213139047872,
    ("Li", "C49", 65, 520): -2.717408623829,
    ("Na", "C49", 65, 520): -2.015809016719,
}
EXPECTED_SHIFTS_EV = {
    "Li": -0.002097861821,
    "Na": -0.010591215755,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_adsorption_energies(
    path: Path,
) -> dict[tuple[str, str, int, int], float]:
    energies: dict[tuple[str, str, int, int], float] = {}
    for row in read_csv(path):
        if row["substrate"] not in ("C50", "C49"):
            continue
        if row["metal"] not in METALS:
            continue

        ecutwfc = int(row["ecutwfc_ry"])
        ecutrho = int(row["ecutrho_ry"])
        if (ecutwfc, ecutrho) not in CUTOFFS:
            continue
        key = (row["metal"], row["substrate"], ecutwfc, ecutrho)
        if key not in EXPECTED_ENERGIES_EV:
            continue
        if ecutrho != 8 * ecutwfc:
            raise ValueError(f"{row['record_id']} does not use the 8x cutoff ratio")
        if row["k_mesh"] != "9x9x1" or not np.isclose(
            float(row["degauss_ry"]), 0.01, rtol=0.0, atol=1.0e-12
        ):
            raise ValueError(f"{row['record_id']} does not use the final-SCF sampling")
        for flag in ("gpu_active", "electronic_converged", "job_done"):
            if row[flag].strip().lower() != "true":
                raise ValueError(f"{row['record_id']} failed validation flag {flag}")

        expected_role = (
            "common_four_system_dataset"
            if ecutwfc == 65
            else "pristine_cutoff_validation"
        )
        if row["comparison_role"] != expected_role:
            raise ValueError(
                f"{row['record_id']} has role {row['comparison_role']!r}; "
                f"expected {expected_role!r}"
            )

        if key in energies:
            raise ValueError(f"Duplicate adsorption-energy row for {key}")
        value = float(row["adsorption_energy_ev"])
        expected = EXPECTED_ENERGIES_EV[key]
        if not np.isclose(value, expected, rtol=0.0, atol=5.0e-12):
            raise ValueError(
                f"Unexpected adsorption energy for {key}: {value:.15f} eV"
            )
        energies[key] = value

    if set(energies) != set(EXPECTED_ENERGIES_EV):
        missing = set(EXPECTED_ENERGIES_EV) - set(energies)
        extra = set(energies) - set(EXPECTED_ENERGIES_EV)
        raise ValueError(f"Cutoff-validation rows mismatch; missing={missing}, extra={extra}")
    return energies


def load_prepared_shifts(path: Path) -> dict[str, float]:
    shifts: dict[str, float] = {}
    expected_ids = {
        "li_cutoff_shift_70_minus_65": "Li",
        "na_cutoff_shift_70_minus_65": "Na",
    }
    for row in read_csv(path):
        if row["comparison_id"] not in expected_ids:
            continue
        metal = expected_ids[row["comparison_id"]]
        if row["comparison_type"] != "cutoff_shift":
            raise ValueError(f"Prepared shift for {metal} has the wrong comparison type")
        if row["input_dataset"] != "65/520 versus 70/560 Ry fixed geometry":
            raise ValueError(f"Prepared shift for {metal} is not fixed-geometry data")
        value = float(row["value_ev"])
        if not np.isclose(
            value, EXPECTED_SHIFTS_EV[metal], rtol=0.0, atol=5.0e-12
        ):
            raise ValueError(f"Unexpected prepared cutoff shift for {metal}: {value}")
        shifts[metal] = value

    if set(shifts) != set(METALS):
        raise ValueError(f"Expected prepared shifts for {METALS}, found {set(shifts)}")
    return shifts


def cross_check(
    energies: dict[tuple[str, str, int, int], float], shifts: dict[str, float]
) -> None:
    for metal in METALS:
        calculated = (
            energies[(metal, "C50", 70, 560)]
            - energies[(metal, "C50", 65, 520)]
        )
        if not np.isclose(calculated, shifts[metal], rtol=0.0, atol=5.0e-12):
            raise ValueError(
                f"Cutoff-shift cross-check failed for {metal}: "
                f"calculated={calculated:.12f}, prepared={shifts[metal]:.12f} eV"
            )


def style_axis(
    ax: plt.Axes,
    major_step: float,
    minor_divisions: int,
    y_limits: tuple[float, float],
) -> None:
    ax.set_xlim(-0.28, 1.28)
    ax.set_ylim(*y_limits)
    ax.set_xticks((0.0, 1.0), ("65/520", "70/560"))
    ax.set_xlabel("Cutoff pair (Ry)")
    ax.set_ylabel("Adsorption energy (eV)")
    ax.yaxis.set_major_locator(MultipleLocator(major_step))
    ax.yaxis.set_minor_locator(AutoMinorLocator(minor_divisions))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    ax.tick_params(axis="both", which="major", direction="out", length=6, width=1.0)
    ax.tick_params(axis="y", which="minor", direction="out", length=3, width=0.8)
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", which="major", color="#D5D5D5", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def draw_system(
    ax: plt.Axes,
    metal: str,
    substrate: str,
    energy_65_ev: float,
    energy_70_ev: float | None,
    shift_ev: float | None,
    panel_label: str,
    major_step: float,
    minor_divisions: int,
    y_limits: tuple[float, float],
) -> None:
    color = COLORS[metal]

    ax.scatter(
        0.0,
        energy_65_ev,
        s=105,
        facecolor="white",
        edgecolor=color,
        linewidth=2.0,
        zorder=4,
    )
    ax.annotate(
        f"{energy_65_ev:.5f}",
        xy=(0.0, energy_65_ev),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color="#202020",
        zorder=5,
    )

    if energy_70_ev is not None and shift_ev is not None:
        ax.plot(
            np.array((0.0, 1.0)),
            np.array((energy_65_ev, energy_70_ev)),
            color=color,
            linewidth=2.2,
            zorder=3,
        )
        ax.scatter(
            1.0,
            energy_70_ev,
            s=105,
            facecolor=color,
            edgecolor="#202020",
            linewidth=1.0,
            zorder=4,
        )
        ax.annotate(
            f"{energy_70_ev:.5f}",
            xy=(1.0, energy_70_ev),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="#202020",
            zorder=5,
        )
        ax.text(
            0.5,
            0.965,
            rf"$\Delta E_{{\mathrm{{ads}}}}$ (70−65) = {shift_ev * 1000.0:+.2f} meV",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=10.5,
            color="#404040",
        )
    else:
        ax.axvspan(0.76, 1.24, color="#F0F0F0", zorder=0)
        ax.text(
            1.0,
            0.50,
            "70/560\nnot calculated",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="center",
            fontsize=10.5,
            color="#505050",
            fontstyle="italic",
        )
        ax.text(
            0.5,
            0.965,
            "Vacancy result available at 65/520 Ry only",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=10.5,
            color="#404040",
        )

    ax.set_title(
        f"({panel_label}) {metal}/{substrate}",
        fontsize=14,
        fontweight="bold",
        pad=13,
    )
    style_axis(ax, major_step, minor_divisions, y_limits)


def make_figure(
    energies: dict[tuple[str, str, int, int], float],
    shifts: dict[str, float],
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
            "axes.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(9.4, 8.5), constrained_layout=True)
    draw_system(
        axes[0, 0],
        "Li",
        "C50",
        energies[("Li", "C50", 65, 520)],
        energies[("Li", "C50", 70, 560)],
        shifts["Li"],
        "a",
        major_step=0.001,
        minor_divisions=4,
        y_limits=(-1.1690, -1.1645),
    )
    draw_system(
        axes[0, 1],
        "Na",
        "C50",
        energies[("Na", "C50", 65, 520)],
        energies[("Na", "C50", 70, 560)],
        shifts["Na"],
        "b",
        major_step=0.005,
        minor_divisions=5,
        y_limits=(-0.5780, -0.5575),
    )
    draw_system(
        axes[1, 0],
        "Li",
        "C49",
        energies[("Li", "C49", 65, 520)],
        None,
        None,
        "c",
        major_step=0.02,
        minor_divisions=4,
        y_limits=(-2.755, -2.675),
    )
    draw_system(
        axes[1, 1],
        "Na",
        "C49",
        energies[("Na", "C49", 65, 520)],
        None,
        None,
        "d",
        major_step=0.02,
        minor_divisions=4,
        y_limits=(-2.055, -1.975),
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
        help="Directory containing adsorption_energies.csv and derived_comparisons.csv",
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
    energies = load_adsorption_energies(args.data_dir / "adsorption_energies.csv")
    shifts = load_prepared_shifts(args.data_dir / "derived_comparisons.csv")
    cross_check(energies, shifts)

    png_path = args.output_dir / "fig06_adsorbate_cutoff_validation.png"
    pdf_path = args.output_dir / "fig06_adsorbate_cutoff_validation.pdf"
    make_figure(energies, shifts, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    for metal in METALS:
        print(
            f"{metal}/C50: 65/520={energies[(metal, 'C50', 65, 520)]:.12f} eV, "
            f"70/560={energies[(metal, 'C50', 70, 560)]:.12f} eV, "
            f"shift={shifts[metal] * 1000.0:+.6f} meV"
        )
        print(
            f"{metal}/C49: 65/520={energies[(metal, 'C49', 65, 520)]:.12f} eV, "
            "70/560=not calculated"
        )


if __name__ == "__main__":
    main()
