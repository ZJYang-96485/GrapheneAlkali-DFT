#!/usr/bin/env python3
"""Run and validate a PWSCF wavefunction-cutoff convergence series."""

import argparse
import math
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Sequence

try:
    from .extract_total_energy import get_total_energy
except ImportError:  # Support direct execution: python3 scripts/run_cutoff_convergence.py
    from extract_total_energy import get_total_energy


_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_ECUTWFC = re.compile(
    rf"^([ \t]*ecutwfc[ \t]*=[ \t]*)({_FLOAT})",
    re.IGNORECASE | re.MULTILINE,
)
_ECUTRHO = re.compile(
    rf"^[ \t]*ecutrho[ \t]*=[ \t]*({_FLOAT})",
    re.IGNORECASE | re.MULTILINE,
)
_JOB_DONE = re.compile(r"^[ \t]*JOB DONE\.?[ \t]*$", re.IGNORECASE | re.MULTILINE)


def _as_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def _cutoff_text(cutoff: float) -> str:
    if cutoff.is_integer():
        return str(int(cutoff))
    return format(cutoff, ".15g")


def _cutoff_label(cutoff: float) -> str:
    return _cutoff_text(cutoff).replace("-", "m").replace("+", "p").replace(".", "p")


def _resolve_pw_executable(pw_executable: str | Path) -> Path:
    supplied_path = Path(pw_executable).expanduser()
    try:
        resolved_path = supplied_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"PWSCF executable does not exist: {supplied_path}") from exc

    if not resolved_path.is_file():
        raise ValueError(f"PWSCF executable is not a file: {resolved_path}")
    if not os.access(resolved_path, os.X_OK):
        raise ValueError(f"PWSCF executable is not executable: {resolved_path}")
    return resolved_path


def _normalize_cutoffs(cutoffs: Sequence[float]) -> list[float]:
    normalized = [float(cutoff) for cutoff in cutoffs]
    if not normalized:
        raise ValueError("At least one ecutwfc value is required.")
    if any(not math.isfinite(cutoff) or cutoff <= 0 for cutoff in normalized):
        raise ValueError("Every ecutwfc value must be a finite positive number.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate ecutwfc values are not allowed.")
    return sorted(normalized)


def _render_input(template: str, cutoff: float) -> str:
    rendered, replacements = _ECUTWFC.subn(
        lambda match: f"{match.group(1)}{_cutoff_text(cutoff)}",
        template,
    )
    if replacements != 1:
        raise ValueError(
            "The template must contain exactly one active ecutwfc assignment; "
            f"found {replacements}."
        )
    return rendered


def _print_results(results: Sequence[tuple[float, float]]) -> None:
    print("\nCutoff (Ry)  Total energy (Ry)")
    print("-----------  -----------------")
    for cutoff, energy in results:
        print(f"{_cutoff_text(cutoff):>11}  {energy:17.10f}")


def run_cutoff_convergence(
    cutoffs: Sequence[float],
    template_path: str | Path,
    pw_executable: str | Path,
    results_dir: str | Path,
) -> list[tuple[float, float]]:
    """Run PWSCF for each cutoff and return sorted ``(cutoff_Ry, energy_Ry)`` pairs."""
    sorted_cutoffs = _normalize_cutoffs(cutoffs)
    executable = _resolve_pw_executable(pw_executable)

    template_file = Path(template_path).expanduser().resolve()
    if not template_file.is_file():
        raise ValueError(f"PWSCF template does not exist: {template_file}")
    template = template_file.read_bytes().decode("utf-8")

    ecutrho_matches = _ECUTRHO.findall(template)
    if len(ecutrho_matches) > 1:
        raise ValueError(
            "The template must contain at most one active ecutrho assignment; "
            f"found {len(ecutrho_matches)}."
        )
    if ecutrho_matches:
        ecutrho = _as_float(ecutrho_matches[0])
        recommended_minimum = 8.0 * sorted_cutoffs[-1]
        if ecutrho < recommended_minimum:
            warnings.warn(
                f"Template ecutrho={ecutrho:g} Ry is less than eight times the "
                f"largest ecutwfc ({recommended_minimum:g} Ry).",
                RuntimeWarning,
                stacklevel=2,
            )

    output_directory = Path(results_dir).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    template_suffix = template_file.suffix or ".in"
    template_stem = (
        template_file.name[: -len(template_file.suffix)]
        if template_file.suffix
        else template_file.name
    )
    planned_runs: list[tuple[float, Path, Path, bytes]] = []

    for cutoff in sorted_cutoffs:
        label = _cutoff_label(cutoff)
        input_path = output_directory / f"{template_stem}.ecutwfc_{label}{template_suffix}"
        output_path = output_directory / f"{template_stem}.ecutwfc_{label}.out"
        if input_path.exists() or output_path.exists():
            raise FileExistsError(
                "Refusing to overwrite an existing cutoff result: "
                f"{input_path if input_path.exists() else output_path}"
            )
        rendered = _render_input(template, cutoff)
        planned_runs.append((cutoff, input_path, output_path, rendered.encode("utf-8")))

    for _, input_path, _, rendered in planned_runs:
        input_path.write_bytes(rendered)

    results: list[tuple[float, float]] = []
    for cutoff, input_path, output_path, _ in planned_runs:
        print(f"Running ecutwfc={_cutoff_text(cutoff)} Ry -> {output_path.name}")
        try:
            with output_path.open("wb") as output_file:
                completed = subprocess.run(
                    [str(executable), "-in", str(input_path)],
                    cwd=template_file.parent,
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
        except OSError as exc:
            raise RuntimeError(
                f"Could not start PWSCF for ecutwfc={_cutoff_text(cutoff)} Ry: {exc}"
            ) from exc

        if completed.returncode != 0:
            raise RuntimeError(
                f"PWSCF failed for ecutwfc={_cutoff_text(cutoff)} Ry with exit code "
                f"{completed.returncode}; see {output_path}."
            )

        output_text = output_path.read_text(encoding="utf-8", errors="replace")
        if not _JOB_DONE.search(output_text):
            raise RuntimeError(
                f"PWSCF did not report JOB DONE for ecutwfc={_cutoff_text(cutoff)} Ry; "
                f"see {output_path}."
            )

        try:
            energy = get_total_energy(output_path)
        except ValueError as exc:
            raise RuntimeError(
                f"No converged energy was found for ecutwfc={_cutoff_text(cutoff)} Ry; "
                f"see {output_path}."
            ) from exc

        if results and energy > results[-1][1]:
            previous_cutoff, previous_energy = results[-1]
            raise RuntimeError(
                "Total energy is not monotonically non-increasing: "
                f"{energy:.10f} Ry at {_cutoff_text(cutoff)} Ry is greater than "
                f"{previous_energy:.10f} Ry at {_cutoff_text(previous_cutoff)} Ry."
            )
        results.append((cutoff, energy))

    _print_results(results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path, help="PWSCF input template")
    parser.add_argument(
        "--pw-executable",
        required=True,
        type=Path,
        help="path to the pw.x executable",
    )
    parser.add_argument("--results-dir", required=True, type=Path, help="output directory")
    parser.add_argument(
        "--cutoffs",
        required=True,
        nargs="+",
        type=float,
        help="ecutwfc values in Ry",
    )
    args = parser.parse_args()

    try:
        run_cutoff_convergence(
            args.cutoffs,
            args.template,
            args.pw_executable,
            args.results_dir,
        )
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
