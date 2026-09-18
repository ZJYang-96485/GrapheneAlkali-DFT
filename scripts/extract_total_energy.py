#!/usr/bin/env python3
"""Extract the last converged total energy from a PWSCF output file."""

import argparse
import re
import sys
from pathlib import Path


_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_CONVERGED_ENERGY = re.compile(
    rf"^[ \t]*![ \t]+total[ \t]+energy[ \t]*=[ \t]*({_FLOAT})[ \t]+Ry(?:[ \t]|$)",
    re.IGNORECASE | re.MULTILINE,
)


def get_total_energy(output_path: str | Path) -> float:
    """Return the last converged PWSCF total energy, in Ry."""
    path = Path(output_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = _CONVERGED_ENERGY.findall(text)

    if not matches:
        raise ValueError(f"No converged total energy found in {path}.")

    return float(matches[-1].replace("D", "E").replace("d", "e"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="PWSCF output file to parse")
    args = parser.parse_args()

    try:
        energy = get_total_energy(args.output)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(energy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
