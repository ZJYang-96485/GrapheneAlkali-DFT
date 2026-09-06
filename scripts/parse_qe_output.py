#!/usr/bin/env python3
"""Extract completion, convergence, energy, force, structure, and spin from pw.x."""

import argparse
import json
import re
import sys
from pathlib import Path


FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
FORCE_LINE = re.compile(
    rf"^\s*atom\s+(\d+)\s+type\s+(\d+)\s+force\s*=\s*"
    rf"({FLOAT})\s+({FLOAT})\s+({FLOAT})",
    re.IGNORECASE | re.MULTILINE,
)
COORDINATE_LINE = re.compile(
    rf"^\s*([A-Za-z][A-Za-z0-9_-]*)\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})(?:\s|$)",
    re.MULTILINE,
)


class QEOutputParseError(ValueError):
    """Raised when a QE output is incomplete or cannot be interpreted."""


def as_float(value):
    return float(value.replace("D", "E").replace("d", "e"))


def parse_job_completion(text):
    return bool(re.search(r"\bJOB DONE\.\s*$", text, re.IGNORECASE | re.MULTILINE))


def parse_total_energy(text):
    matches = re.findall(rf"!\s+total energy\s*=\s*({FLOAT})\s+Ry", text, re.IGNORECASE)
    return as_float(matches[-1]) if matches else None


def parse_electronic_convergence(text):
    events = []
    pattern = re.compile(
        r"convergence\s+(has been achieved|NOT achieved|was not achieved)"
        r"|End of self-consistent calculation",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        phrase = match.group(0).lower()
        events.append("not achieved" not in phrase and "not" not in phrase)
    return events[-1] if events else None


def parse_ionic_convergence(text):
    if re.search(
        r"maximum number of (?:bfgs |ionic )?steps has been reached|"
        r"bfgs.*(?:not converged|failed)",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"bfgs converged|End of BFGS Geometry Optimization|"
        r"ionic convergence has been achieved",
        text,
        re.IGNORECASE,
    ):
        return True
    return None


def parse_final_forces(text):
    markers = list(re.finditer(r"Forces acting on atoms\s+\(cartesian axes", text, re.IGNORECASE))
    if not markers:
        return None

    section = text[markers[-1].end() :]
    section = re.split(r"\n\s*Total force\s*=", section, maxsplit=1, flags=re.IGNORECASE)[0]
    matches = list(FORCE_LINE.finditer(section))
    if not matches:
        return None

    return [
        {
            "atom": int(match.group(1)),
            "type": int(match.group(2)),
            "fx_ry_bohr": as_float(match.group(3)),
            "fy_ry_bohr": as_float(match.group(4)),
            "fz_ry_bohr": as_float(match.group(5)),
        }
        for match in matches
    ]


def maximum_force(forces):
    if not forces:
        return None
    return max(
        (entry["fx_ry_bohr"] ** 2 + entry["fy_ry_bohr"] ** 2 + entry["fz_ry_bohr"] ** 2)
        ** 0.5
        for entry in forces
    )


def parse_coordinate_block(section, units):
    coordinates = []
    for line in section.splitlines():
        match = COORDINATE_LINE.match(line)
        if match:
            coordinates.append(
                {
                    "symbol": match.group(1),
                    "x": as_float(match.group(2)),
                    "y": as_float(match.group(3)),
                    "z": as_float(match.group(4)),
                    "units": units or "unknown",
                }
            )
        elif coordinates:
            break
    return coordinates or None


def parse_final_coordinates(text):
    final_start = text.lower().rfind("begin final coordinates")
    search_text = text[final_start:] if final_start >= 0 else text
    positions = list(
        re.finditer(r"ATOMIC_POSITIONS\s*(?:\(([^)]*)\))?\s*\n", search_text, re.IGNORECASE)
    )
    if not positions:
        return None

    position = positions[-1]
    section = search_text[position.end() :]
    end_marker = re.search(r"\n\s*End final coordinates", section, re.IGNORECASE)
    if end_marker:
        section = section[: end_marker.start()]
    return parse_coordinate_block(section, position.group(1))


def parse_total_magnetization(text):
    matches = re.findall(
        rf"^\s*total magnetization\s*=\s*({FLOAT})\s+Bohr mag/cell",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    return as_float(matches[-1]) if matches else None


def parse_text(text, path):
    forces = parse_final_forces(text)
    ionic_convergence = parse_ionic_convergence(text)
    return {
        "file": str(path),
        "job_completed": parse_job_completion(text),
        "electronic_convergence_reached": parse_electronic_convergence(text),
        "ionic_convergence_reached": ionic_convergence,
        "ionic_relaxation_completed": ionic_convergence,
        "final_total_energy_ry": parse_total_energy(text),
        "maximum_force_ry_bohr": maximum_force(forces),
        "final_forces": forces,
        "final_coordinates": parse_final_coordinates(text),
        "total_magnetization_bohr_magneton_per_cell": parse_total_magnetization(text),
    }


def parse_output(path, allow_incomplete=False):
    path = Path(path)
    if not path.is_file():
        raise QEOutputParseError(f"QE output not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    result = parse_text(text, path)
    if allow_incomplete:
        return result

    missing = [
        key
        for key in (
            "final_total_energy_ry",
            "electronic_convergence_reached",
            "ionic_convergence_reached",
            "maximum_force_ry_bohr",
            "final_coordinates",
        )
        if result[key] is None
    ]
    if not result["job_completed"]:
        missing.append("job_completed")
    if missing:
        raise QEOutputParseError(
            f"Incomplete QE output {path}; missing or unfinished: {', '.join(missing)}"
        )
    if result["electronic_convergence_reached"] is not True:
        raise QEOutputParseError(f"QE output {path} indicates SCF convergence failure.")
    if result["ionic_convergence_reached"] is not True:
        raise QEOutputParseError(f"QE output {path} indicates ionic convergence failure.")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="pw.x output file to parse.")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Print partial fields instead of failing on incomplete output.",
    )
    args = parser.parse_args()

    try:
        result = parse_output(args.output, allow_incomplete=args.allow_incomplete)
    except (OSError, QEOutputParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
