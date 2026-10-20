#!/usr/bin/env python3
"""Create report Figure 3: defect enhancement and metal selectivity.

Panel (a) plots the positive magnitude by which a monovacancy strengthens
adsorption. Panel (b) plots the positive magnitude by which Li binds more
strongly than Na. Values are read from the prepared comparison table and
cross-checked against the common 65/520 Ry adsorption-energy dataset.
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

COLORS = {
    "Li": "#0072B2",
    "Na": "#E69F00",
    "pristine": "#7A7A7A",
    "monovacancy": "#CC79A7",
}
HATCHES = {
    "Li": "///",
    "Na": "\\\\\\",
    "pristine": "...",
    "monovacancy": "xxx",
}

EXPECTED_ROWS = {
    "li_vacancy_strengthening": ("defect_strengthening", 1.551834880855),
    "na_vacancy_strengthening": ("defect_strengthening", 1.454187093426),
    "li_minus_na_pristine": ("metal_selectivity", 0.603951819681),
    "li_minus_na_vacancy": ("metal_selectivity", 0.701599607110),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_comparisons(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in read_csv(path):
        comparison_id = row["comparison_id"]
        if comparison_id not in EXPECTED_ROWS:
            continue
        expected_type, expected_value = EXPECTED_ROWS[comparison_id]
        if row["comparison_type"] != expected_type:
            raise ValueError(
                f"{comparison_id} has type {row['comparison_type']!r}; "
                f"expected {expected_type!r}"
            )
        if row["input_dataset"] != "65/520 Ry 9x9x1 common four-system data":
            raise ValueError(f"{comparison_id} is not from the common 65/520 Ry dataset")
        value = float(row["value_ev"])
        if value <= 0.0:
            raise ValueError(f"{comparison_id} must be a positive magnitude, found {value}")
        if not np.isclose(value, expected_value, rtol=0.0, atol=5.0e-12):
            raise ValueError(
                f"Unexpected prepared value for {comparison_id}: {value:.12f} eV"
            )
        values[comparison_id] = value

    missing = set(EXPECTED_ROWS) - set(values)
    if missing:
        raise ValueError(f"Missing required comparison row(s): {sorted(missing)}")
    return values


def load_common_adsorption_energies(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in read_csv(path):
        if row["comparison_role"] != "common_four_system_dataset":
            continue
        if row["ecutwfc_ry"] != "65" or row["ecutrho_ry"] != "520":
            raise ValueError(f"Common row {row['record_id']} is not 65/520 Ry")
        for flag in ("gpu_active", "electronic_converged", "job_done"):
            if row[flag].strip().lower() != "true":
                raise ValueError(f"Common row {row['record_id']} failed validation flag {flag}")
        if row["system"] in values:
            raise ValueError(f"Duplicate adsorption-energy row for {row['system']}")
        values[row["system"]] = float(row["adsorption_energy_ev"])

    expected = {"Li/C50", "Na/C50", "Li/C49", "Na/C49"}
    if set(values) != expected:
        raise ValueError(f"Expected adsorption systems {expected}, found {set(values)}")
    return values


def cross_check(comparisons: dict[str, float], energies: dict[str, float]) -> None:
    independently_derived = {
        # Positive if adsorption is more exothermic at the vacancy.
        "li_vacancy_strengthening": energies["Li/C50"] - energies["Li/C49"],
        "na_vacancy_strengthening": energies["Na/C50"] - energies["Na/C49"],
        # Positive if Li adsorption is more exothermic than Na adsorption.
        "li_minus_na_pristine": energies["Na/C50"] - energies["Li/C50"],
        "li_minus_na_vacancy": energies["Na/C49"] - energies["Li/C49"],
    }
    for comparison_id, calculated in independently_derived.items():
        prepared = comparisons[comparison_id]
        if not np.isclose(prepared, calculated, rtol=0.0, atol=5.0e-12):
            raise ValueError(
                f"Cross-check failed for {comparison_id}: prepared={prepared:.12f}, "
                f"calculated={calculated:.12f} eV"
            )


def draw_panel(
    ax: plt.Axes,
    labels: tuple[str, str],
    values: tuple[float, float],
    colors: tuple[str, str],
    hatches: tuple[str, str],
    title: str,
    interpretation: str,
) -> None:
    x = np.arange(2, dtype=float)
    bars = ax.bar(
        x,
        values,
        width=0.56,
        color=colors,
        edgecolor="#202020",
        linewidth=1.0,
        hatch=hatches,
        zorder=3,
    )

    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2.0, value),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color="#202020",
        )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=13)
    ax.set_xticks(x, labels)
    ax.set_xlim(-0.62, 1.62)
    ax.set_ylim(0.0, 1.80)
    ax.text(
        0.5,
        0.965,
        interpretation,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10.5,
        color="#404040",
    )

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


def make_figure(
    values: dict[str, float], png_path: Path, pdf_path: Path
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

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(9.0, 5.2),
        sharey=True,
        constrained_layout=True,
    )

    draw_panel(
        axes[0],
        labels=("Li", "Na"),
        values=(
            values["li_vacancy_strengthening"],
            values["na_vacancy_strengthening"],
        ),
        colors=(COLORS["Li"], COLORS["Na"]),
        hatches=(HATCHES["Li"], HATCHES["Na"]),
        title="(a) Vacancy strengthening",
        interpretation="Positive = stronger at the vacancy",
    )
    draw_panel(
        axes[1],
        labels=("Pristine C50", "Monovacancy C49"),
        values=(
            values["li_minus_na_pristine"],
            values["li_minus_na_vacancy"],
        ),
        colors=(COLORS["pristine"], COLORS["monovacancy"]),
        hatches=(HATCHES["pristine"], HATCHES["monovacancy"]),
        title="(b) Li–Na selectivity",
        interpretation="Positive = Li binds more strongly",
    )

    axes[0].set_ylabel("Energy difference (eV)")
    axes[0].set_xlabel("Adsorbate")
    axes[1].set_xlabel("Graphene substrate")

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
        help="Directory containing derived_comparisons.csv and adsorption_energies.csv",
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
    comparisons = load_comparisons(args.data_dir / "derived_comparisons.csv")
    energies = load_common_adsorption_energies(args.data_dir / "adsorption_energies.csv")
    cross_check(comparisons, energies)

    png_path = args.output_dir / "fig03_defect_selectivity.png"
    pdf_path = args.output_dir / "fig03_defect_selectivity.pdf"
    make_figure(comparisons, png_path, pdf_path)

    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    for comparison_id in EXPECTED_ROWS:
        print(f"{comparison_id}: {comparisons[comparison_id]:.12f} eV")


if __name__ == "__main__":
    main()
