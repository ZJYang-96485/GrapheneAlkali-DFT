#!/usr/bin/env python3
"""Extract basic completion data from a Quantum ESPRESSO pw.x output."""

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
    rf"^\s*([A-Za-z][A-Za-z0-9]*)\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})(?:\s|$)",
    re.MULTILINE,
)


class QEOutputParseError(ValueError):
    """Raised when a QE output is incomplete or cannot be interpreted."""


def as_float(value):
    return float(value.replace("D", "E").replace("d", "e"))


def parse_total_energy(text):
    matches = re.findall(
        rf"!\s+total energy\s*=\s*({FLOAT})\s+Ry",
        text,
        re.IGNORECASE,
    )
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


def parse_ionic_completion(text):
    if re.search(r"End of BFGS Geometry Optimization", text, re.IGNORECASE):
        return True
    if re.search(r"JOB DONE\.", text, re.IGNORECASE):
        return True
    if re.search(r"bfgs converged", text, re.IGNORECASE):
        return True
    return False if re.search(r"ATOMIC_POSITIONS", text) else None


def parse_final_forces(text):
    markers = list(
        re.finditer(r"Forces acting on atoms\s+\(cartesian axes", text, re.IGNORECASE)
    )
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
        re.finditer(
            r"ATOMIC_POSITIONS\s*(?:\(([^)]*)\))?\s*\n",
            search_text,
            re.IGNORECASE,
        )
    )
    if not positions:
        return None

    position = positions[-1]
    units = position.group(1)
    section = search_text[position.end() :]
    end_marker = re.search(r"\n\s*End final coordinates", section, re.IGNORECASE)
    if end_marker:
        section = section[: end_marker.start()]
    return parse_coordinate_block(section, units)


def parse_output(path):
    path = Path(path)
    if not path.is_file():
        raise QEOutputParseError(f"QE output not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    result = {
        "file": str(path),
        "final_total_energy_ry": parse_total_energy(text),
        "electronic_convergence_reached": parse_electronic_convergence(text),
        "ionic_relaxation_completed": parse_ionic_completion(text),
        "final_forces": parse_final_forces(text),
        "final_coordinates": parse_final_coordinates(text),
    }

    missing = [
        key
        for key in (
            "final_total_energy_ry",
            "electronic_convergence_reached",
            "final_forces",
            "final_coordinates",
        )
        if result[key] is None
    ]
    if result["ionic_relaxation_completed"] is not True:
        missing.append("ionic_relaxation_completed")
    if missing:
        raise QEOutputParseError(
            f"Incomplete QE output {path}; missing or unfinished: {', '.join(missing)}"
        )
    if result["electronic_convergence_reached"] is not True:
        raise QEOutputParseError(
            f"QE output {path} indicates that electronic convergence was not reached."
        )

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
        if args.allow_incomplete:
            path = args.output
            text = path.read_text(encoding="utf-8", errors="replace")
            result = {
                "file": str(path),
                "final_total_energy_ry": parse_total_energy(text),
                "electronic_convergence_reached": parse_electronic_convergence(text),
                "ionic_relaxation_completed": parse_ionic_completion(text),
                "final_forces": parse_final_forces(text),
                "final_coordinates": parse_final_coordinates(text),
            }
        else:
            result = parse_output(args.output)
    except (OSError, QEOutputParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
