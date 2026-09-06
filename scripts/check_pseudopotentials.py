#!/usr/bin/env python3
"""Check the configured SSSP pseudopotential files for the current phase."""

import argparse
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CURRENTLY_REQUIRED = {"C"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/qe.yaml", help="QE YAML config."
    )
    args = parser.parse_args()

    try:
        with args.config.open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        pseudo_dir = Path(config["paths"]["pseudo_dir"])
        if not pseudo_dir.is_absolute():
            pseudo_dir = ROOT / pseudo_dir
        expected = config["pseudopotentials"]["files"]
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"error: cannot read pseudopotential configuration: {exc}", file=sys.stderr)
        return 2

    failed = False
    print(f"Pseudopotential directory: {pseudo_dir}")
    for element in ("C", "Li", "Na"):
        filename = expected.get(element)
        if not filename:
            print(f"{element}: no expected filename configured")
            if element in CURRENTLY_REQUIRED:
                failed = True
            continue

        path = pseudo_dir / filename
        present = path.is_file() and path.stat().st_size > 0
        if present:
            phase_note = "required now" if element in CURRENTLY_REQUIRED else "not required for current phase"
            print(f"{element}: present ({phase_note}) - {filename}")
        elif element in CURRENTLY_REQUIRED:
            print(f"{element}: MISSING (required for current bare-substrate runs) - {filename}")
            failed = True
        else:
            print(f"{element}: missing (not required for current phase) - {filename}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
