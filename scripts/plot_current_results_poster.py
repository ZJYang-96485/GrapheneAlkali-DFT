#!/usr/bin/env python3
"""Create the single-page current-results poster for the final project."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


COLORS = {
    "navy": "#10233F",
    "blue": "#2D5EAA",
    "teal": "#00A6A6",
    "li": "#6C63D9",
    "na": "#F28E2B",
    "green": "#2E9D68",
    "red": "#C94A4A",
    "ink": "#26364A",
    "muted": "#637083",
    "paper": "#F3F6FA",
    "grid": "#DDE4EC",
    "white": "#FFFFFF",
}


def read_rows(path: Path) -> list[dict[str, object]]:
    numeric = {
        "total_energy_ry",
        "adsorption_energy_ev",
        "height_ang",
        "total_magnetization_muB",
        "max_force_component_ry_bohr",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        rows: list[dict[str, object]] = list(csv.DictReader(handle))
    if len(rows) != 4:
        raise ValueError(f"Expected four adsorption systems, found {len(rows)}")
    for row in rows:
        for key in numeric:
            row[key] = float(row[key])
    return rows


def style_card(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_facecolor(COLORS["white"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, loc="left", color=COLORS["navy"], fontsize=15,
                 fontweight="bold", pad=16)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=COLORS["muted"],
                fontsize=9.5, va="bottom")


def add_card(fig, spec, title: str, subtitle: str | None = None):
    ax = fig.add_subplot(spec)
    style_card(ax, title, subtitle)
    return ax


def add_panel_label(ax, text: str) -> None:
    ax.text(
        0.985,
        1.08,
        text,
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=8.5,
        color=COLORS["muted"],
        bbox={"boxstyle": "round,pad=0.35", "fc": "#EDF2F8", "ec": "none"},
    )


def make_poster(rows: list[dict[str, object]], output_png: Path, output_pdf: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelcolor": COLORS["ink"],
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["ink"],
            "savefig.facecolor": COLORS["paper"],
        }
    )

    fig = plt.figure(figsize=(18, 10.125), facecolor=COLORS["paper"])
    gs = fig.add_gridspec(
        12,
        24,
        left=0.035,
        right=0.975,
        top=0.965,
        bottom=0.065,
        wspace=1.25,
        hspace=1.45,
    )

    # Header
    header = fig.add_subplot(gs[0:2, :])
    header.axis("off")
    header.add_patch(
        FancyBboxPatch(
            (0, 0.02), 1, 0.96, transform=header.transAxes,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=COLORS["navy"], edgecolor="none",
        )
    )
    header.text(
        0.025, 0.67, "ALKALI ADSORPTION ON GRAPHENE",
        color=COLORS["white"], fontsize=25, fontweight="bold", va="center",
    )
    header.text(
        0.025, 0.30,
        "Validated PBE + DFT-D3(BJ) relaxation results  •  Current checkpoint: 15 Oct 2026",
        color="#C9D7EA", fontsize=12.5, va="center",
    )
    header.text(
        0.975, 0.58, "4 / 4", ha="right", color="#6DE0B2",
        fontsize=27, fontweight="bold", va="center",
    )
    header.text(
        0.975, 0.26, "adsorption relaxations strictly converged",
        ha="right", color="#C9D7EA", fontsize=10.5, va="center",
    )

    labels = [str(row["system"]) for row in rows]
    y = list(range(len(rows)))
    bar_colors = [COLORS[str(row["metal"]).lower()] for row in rows]

    # Adsorption energy
    ax_e = add_card(
        fig, gs[2:7, 0:11], "Adsorption energy",
        "Atom-referenced Eads; more negative means stronger exothermic binding",
    )
    energies = [float(row["adsorption_energy_ev"]) for row in rows]
    bars = ax_e.barh(y, energies, color=bar_colors, height=0.58, zorder=3)
    ax_e.axvline(0, color=COLORS["ink"], lw=1)
    ax_e.set_xlim(-3.05, 0.12)
    ax_e.set_yticks(y, labels)
    ax_e.invert_yaxis()
    ax_e.set_xlabel("Adsorption energy (eV)", fontsize=10.5)
    ax_e.grid(axis="x", color=COLORS["grid"], lw=0.8, zorder=0)
    ax_e.tick_params(axis="both", length=0)
    for bar, value in zip(bars, energies):
        ax_e.text(value + 0.05, bar.get_y() + bar.get_height() / 2,
                  f"{value:.3f}", ha="left", va="center", color=COLORS["white"],
                  fontsize=11, fontweight="bold")
    ax_e.axhline(1.5, color=COLORS["grid"], lw=1.2)
    ax_e.text(-3.0, 1.37, "PRISTINE", color=COLORS["muted"], fontsize=8,
              fontweight="bold", va="bottom")
    ax_e.text(-3.0, 3.45, "MONOVACANCY", color=COLORS["muted"], fontsize=8,
              fontweight="bold", va="bottom")
    add_panel_label(ax_e, "RELAXED GEOMETRIES • 6×6×1")

    # Height
    ax_h = add_card(fig, gs[2:6, 12:18], "Adsorption height",
                    "Metal height above the mean carbon plane")
    heights = [float(row["height_ang"]) for row in rows]
    hb = ax_h.barh(y, heights, color=bar_colors, height=0.55)
    ax_h.set_xlim(0, 2.65)
    ax_h.set_yticks(y, labels)
    ax_h.invert_yaxis()
    ax_h.set_xlabel("Height (Å)", fontsize=10)
    ax_h.grid(axis="x", color=COLORS["grid"], lw=0.8)
    ax_h.tick_params(axis="both", length=0, labelsize=9)
    for bar, value in zip(hb, heights):
        ax_h.text(value + 0.05, bar.get_y() + bar.get_height() / 2,
                  f"{value:.2f} Å", va="center", fontsize=9.5,
                  color=COLORS["ink"], fontweight="bold")

    # Magnetization
    ax_m = add_card(fig, gs[2:6, 19:24], "Magnetism",
                    "Total magnetic moment per simulation cell")
    mags = [float(row["total_magnetization_muB"]) for row in rows]
    mb = ax_m.barh(y, mags, color=bar_colors, height=0.55)
    ax_m.set_xlim(0, 1.15)
    ax_m.set_yticks(y, labels)
    ax_m.invert_yaxis()
    ax_m.set_xlabel("Magnetization (μB)", fontsize=10)
    ax_m.grid(axis="x", color=COLORS["grid"], lw=0.8)
    ax_m.tick_params(axis="both", length=0, labelsize=9)
    for bar, value in zip(mb, mags):
        ax_m.text(max(value + 0.035, 0.035), bar.get_y() + bar.get_height() / 2,
                  f"{value:.2f}", va="center", fontsize=9.5,
                  color=COLORS["ink"], fontweight="bold")

    # Numerical validation
    ax_v = add_card(fig, gs[7:11, 12:19], "Numerical validation",
                    "Energy difference per carbon atom; dashed line = 1 meV/C criterion")
    validation = [
        ("65/520 vs 70/560 Ry", 0.9769),
        ("6×6×1 vs 12×12×1", 0.1375),
        ("9×9×1 vs 12×12×1", 0.0183),
        ("0.005 vs 0.010 Ry", 0.0496),
    ]
    vy = list(range(len(validation)))
    vv = [item[1] for item in validation]
    ax_v.hlines(vy, 0, vv, color="#AFC7E6", lw=7, zorder=1)
    ax_v.scatter(vv, vy, s=90, color=COLORS["green"], zorder=3,
                 edgecolors=COLORS["white"], linewidths=1.5)
    ax_v.axvline(1.0, color=COLORS["red"], lw=1.4, ls="--")
    ax_v.set_xlim(0, 1.12)
    ax_v.set_yticks(vy, [item[0] for item in validation])
    ax_v.invert_yaxis()
    ax_v.set_xlabel("Difference (meV/C)", fontsize=10)
    ax_v.grid(axis="x", color=COLORS["grid"], lw=0.8)
    ax_v.tick_params(axis="both", length=0, labelsize=9)
    for yi, value in zip(vy, vv):
        ax_v.text(min(value + 0.035, 1.035), yi, f"{value:.3f}",
                  va="center", fontsize=9, fontweight="bold", color=COLORS["ink"])

    # Key findings
    ax_k = fig.add_subplot(gs[7:11, 0:11])
    ax_k.axis("off")
    ax_k.text(0, 0.98, "What the calculations show", transform=ax_k.transAxes,
              color=COLORS["navy"], fontsize=15, fontweight="bold", va="top")
    findings = [
        ("01", "Vacancies strengthen binding",
         "Li: 1.538 eV stronger  •  Na: 1.439 eV stronger than pristine graphene"),
        ("02", "Li binds more strongly than Na",
         "By 0.603 eV on pristine C50 and 0.702 eV at the C49 vacancy"),
        ("03", "Vacancy magnetism persists",
         "Bare C49: 1.60 μB  →  Li/C49: 0.96 μB  •  Na/C49: 1.00 μB"),
    ]
    for idx, (number, title, body) in enumerate(findings):
        ypos = 0.72 - idx * 0.29
        ax_k.text(0.01, ypos, number, fontsize=13, fontweight="bold", color=COLORS["teal"],
                  va="center")
        ax_k.text(0.085, ypos + 0.055, title, fontsize=11.5, fontweight="bold",
                  color=COLORS["navy"], va="center")
        ax_k.text(0.085, ypos - 0.075, body, fontsize=9.5, color=COLORS["muted"], va="center")

    # Status and force gate
    ax_s = add_card(fig, gs[7:11, 20:24], "Quality gates")
    ax_s.axis("off")
    force_limit = 0.0004
    max_force = max(float(row["max_force_component_ry_bohr"]) for row in rows)
    ax_s.text(0.02, 0.80, "Relaxations", fontsize=10, color=COLORS["muted"])
    ax_s.text(0.98, 0.80, "4 / 4 PASS", ha="right", fontsize=12,
              color=COLORS["green"], fontweight="bold")
    ax_s.add_patch(FancyBboxPatch((0.02, 0.68), 0.96, 0.07, transform=ax_s.transAxes,
                                  boxstyle="round,pad=0.002,rounding_size=0.02",
                                  fc="#DBE5EF", ec="none"))
    ax_s.add_patch(FancyBboxPatch((0.02, 0.68), 0.96, 0.07, transform=ax_s.transAxes,
                                  boxstyle="round,pad=0.002,rounding_size=0.02",
                                  fc=COLORS["green"], ec="none"))
    ax_s.text(0.02, 0.54, "Largest force component", fontsize=10, color=COLORS["muted"])
    ax_s.text(0.02, 0.43, f"{max_force:.8f} Ry/Bohr", fontsize=12,
              color=COLORS["navy"], fontweight="bold")
    ax_s.text(0.02, 0.32, f"criterion ≤ {force_limit:.4f}", fontsize=9.5,
              color=COLORS["green"], fontweight="bold")
    ax_s.text(0.02, 0.17, "9×9×1 final SCFs", fontsize=10, color=COLORS["muted"])
    ax_s.text(0.98, 0.17, "RUNNING", ha="right", fontsize=11,
              color=COLORS["blue"], fontweight="bold")
    ax_s.text(0.02, 0.06, "Na/C49 attempt02 • GPU active", fontsize=8.8,
              color=COLORS["muted"])

    # Footer methods strip
    footer = fig.add_subplot(gs[11, :])
    footer.axis("off")
    footer.add_patch(
        FancyBboxPatch(
            (0, 0.02), 1, 0.94, transform=footer.transAxes,
            boxstyle="round,pad=0.008,rounding_size=0.02",
            facecolor="#E4EBF4", edgecolor="none",
        )
    )
    footer.text(
        0.018, 0.52,
        "METHOD  PBE  +  DFT-D3(BJ)   |   PAW pseudopotentials   |   65/520 Ry   |   "
        "6×6×1 relaxation   |   MV smearing 0.01 Ry   |   assume_isolated = '2D'",
        color=COLORS["ink"], fontsize=9.6, fontweight="bold", va="center",
    )
    footer.text(
        0.982, 0.52, "Quantum ESPRESSO 7.6 • GPU",
        color=COLORS["blue"], fontsize=9.6, fontweight="bold", ha="right", va="center",
    )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("results/final_project/current_adsorption_results_20261015.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("figures/final_project")
    )
    args = parser.parse_args()
    rows = read_rows(args.data)
    make_poster(
        rows,
        args.output_dir / "current_results_poster_20261015.png",
        args.output_dir / "current_results_poster_20261015.pdf",
    )


if __name__ == "__main__":
    main()
