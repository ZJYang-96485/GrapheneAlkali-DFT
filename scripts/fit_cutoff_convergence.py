#!/usr/bin/env python3
"""Fit and plot the supplied H2 plane-wave cutoff convergence data."""

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


CUTOFFS_RY = np.array([20.0, 30.0, 40.0, 50.0, 60.0])
ENERGIES_RY = np.array(
    [-2.30738561, -2.31131605, -2.31147421, -2.31151522, -2.31155612]
)
TOLERANCE_RY = 0.004


def exponential_model(ecut_ry: np.ndarray | float, a: float, b: float, c: float):
    """Return A exp(-B Ecut) + C."""
    return a * np.exp(-b * ecut_ry) + c


def fit_convergence(
    cutoffs_ry: np.ndarray, energies_ry: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit the exponential convergence model and return parameters and covariance."""
    initial_c = float(energies_ry[-1])
    initial_a = float(energies_ry[0] - initial_c) * math.exp(2.0)
    initial_guess = (initial_a, 0.1, initial_c)
    parameters, covariance = curve_fit(
        exponential_model,
        cutoffs_ry,
        energies_ry,
        p0=initial_guess,
        bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
        maxfev=100_000,
    )
    return parameters, covariance


def minimum_cutoff(a: float, b: float, tolerance_ry: float) -> float:
    """Return the smallest nonnegative cutoff where |E(Ecut) - C| <= tolerance."""
    if tolerance_ry <= 0.0:
        raise ValueError("The energy tolerance must be positive.")
    if b <= 0.0:
        raise ValueError("The fitted decay constant B must be positive.")
    if abs(a) <= tolerance_ry:
        return 0.0
    return max(0.0, math.log(abs(a) / tolerance_ry) / b)


def save_plot(
    output_path: Path,
    parameters: np.ndarray,
    threshold_ry: float,
    first_sampled_cutoff_ry: float | None,
) -> None:
    """Save a publication-quality plot of the data and fitted model."""
    a, b, c = parameters
    x_min = max(0.0, min(float(CUTOFFS_RY.min()), threshold_ry) - 5.0)
    x_max = float(CUTOFFS_RY.max()) + 5.0
    fit_cutoffs = np.linspace(x_min, x_max, 600)

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 13,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )
    figure, axis = plt.subplots(figsize=(7.2, 5.4), constrained_layout=False)
    axis.scatter(
        CUTOFFS_RY,
        ENERGIES_RY,
        s=55,
        color="#1f77b4",
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
        label="PWSCF data",
    )
    axis.plot(
        fit_cutoffs,
        exponential_model(fit_cutoffs, a, b, c),
        color="#d62728",
        linewidth=2.0,
        label=r"Fit: $A\exp(-B E_{\mathrm{cut}})+C$",
    )
    axis.axhline(c, color="#444444", linestyle="--", linewidth=1.2, label="Asymptote C")
    axis.fill_between(
        fit_cutoffs,
        c - TOLERANCE_RY,
        c + TOLERANCE_RY,
        color="#2ca02c",
        alpha=0.12,
        label=r"$|E-C|\leq 0.004$ Ry",
    )
    axis.axvline(
        threshold_ry,
        color="#2ca02c",
        linestyle=":",
        linewidth=1.6,
        label=f"Model threshold: {threshold_ry:.2f} Ry",
    )
    axis.set_xlabel(r"Wavefunction cutoff, $E_{\mathrm{cut}}$ (Ry)")
    axis.set_ylabel("Total energy (Ry)")
    axis.set_title(r"H$_2$ plane-wave cutoff convergence")
    axis.grid(True, linestyle=":", linewidth=0.7, alpha=0.55)
    axis.ticklabel_format(axis="y", style="plain", useOffset=False)
    axis.legend(frameon=True, loc="best")

    sampled_text = (
        f"{first_sampled_cutoff_ry:g} Ry is the first sampled cutoff meeting the criterion"
        if first_sampled_cutoff_ry is not None
        else "none of the sampled cutoffs meets the criterion"
    )
    caption = (
        f"Conclusion: the fitted curve reaches |E-C| <= {TOLERANCE_RY:g} Ry at "
        f"{threshold_ry:.2f} Ry; {sampled_text}."
    )
    figure.subplots_adjust(bottom=0.21, left=0.14, right=0.97, top=0.91)
    figure.text(0.5, 0.04, caption, ha="center", va="bottom", fontsize=9, wrap=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight", metadata={"Creator": __file__})
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("cutoff_convergence_fit.png"),
        help="plot filename (default: cutoff_convergence_fit.png)",
    )
    args = parser.parse_args()

    parameters, covariance = fit_convergence(CUTOFFS_RY, ENERGIES_RY)
    uncertainties = np.sqrt(np.diag(covariance))
    if not np.all(np.isfinite(uncertainties)):
        raise RuntimeError("The fit covariance did not yield finite uncertainties.")

    a, b, c = (float(value) for value in parameters)
    sigma_a, sigma_b, sigma_c = (float(value) for value in uncertainties)
    threshold_ry = minimum_cutoff(a, b, TOLERANCE_RY)
    sampled_candidates = CUTOFFS_RY[
        np.abs(exponential_model(CUTOFFS_RY, a, b, c) - c) <= TOLERANCE_RY
    ]
    first_sampled_cutoff = (
        float(sampled_candidates[0]) if sampled_candidates.size else None
    )

    energy_60_ry = float(ENERGIES_RY[CUTOFFS_RY == 60.0][0])
    asymptote_difference_ry = c - energy_60_ry
    output_path = args.output.expanduser().resolve()
    save_plot(output_path, parameters, threshold_ry, first_sampled_cutoff)

    print("Fit: E(Ecut) = A exp(-B Ecut) + C")
    print(f"A = {a:.10g} +/- {sigma_a:.3g} Ry")
    print(f"B = {b:.10g} +/- {sigma_b:.3g} Ry^-1")
    print(f"C = {c:.10f} +/- {sigma_c:.3g} Ry")
    print(f"E(60 Ry) = {energy_60_ry:.8f} Ry")
    print(f"C - E(60 Ry) = {asymptote_difference_ry:+.10f} Ry")
    print(f"|C - E(60 Ry)| = {abs(asymptote_difference_ry):.10f} Ry")
    print(f"Minimum fitted cutoff for |E-C| <= {TOLERANCE_RY:g} Ry: {threshold_ry:.4f} Ry")
    if first_sampled_cutoff is None:
        print("No sampled cutoff satisfies the fitted tolerance criterion.")
    else:
        print(f"First sampled cutoff satisfying the criterion: {first_sampled_cutoff:g} Ry")
    print(f"Plot saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
