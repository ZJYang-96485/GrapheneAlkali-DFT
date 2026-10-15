#!/usr/bin/env python3
"""Build a fixed-geometry 9x9x1 SCF input from an accepted QE relaxation.

The relaxation output is parsed strictly, so a final-SCF input is never made
from an incomplete ionic trajectory.  All physical settings are inherited
from the relaxation template; only the calculation type, restart metadata,
time limit, geometry, and k-point mesh are changed.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from parse_qe_output import parse_output


def replace_control(text: str, prefix: str, outdir: str, restart_mode: str) -> str:
    match = re.search(r"(?ms)^&CONTROL\s*$.*?^/\s*$", text)
    if not match:
        raise ValueError("missing &CONTROL namelist")
    block = match.group(0)
    replacements = {
        "calculation": "'scf'",
        "restart_mode": f"'{restart_mode}'",
        "prefix": f"'{prefix}'",
        "outdir": f"'{outdir}'",
    }
    for key, value in replacements.items():
        pattern = rf"(?mi)^(\s*{re.escape(key)}\s*=\s*).+?,\s*$"
        block, count = re.subn(pattern, rf"\g<1>{value},", block)
        if count == 0:
            block = block[:-1] + f"   {key} = {value},\n/"

    block = re.sub(
        r"(?mi)^\s*(?:etot_conv_thr|forc_conv_thr|nstep|max_seconds)\s*=.*\n?",
        "",
        block,
    )
    block = block[:-1] + "   max_seconds = 14400,\n/"
    return text[: match.start()] + block + text[match.end() :]


def build(template: Path, relaxation: Path, prefix: str, restart_mode: str) -> str:
    parsed = parse_output(relaxation, calculation="relax")
    coordinates = parsed["final_coordinates"]
    if not coordinates:
        raise ValueError("accepted relaxation has no final coordinates")
    if {entry["units"].lower() for entry in coordinates} != {"angstrom"}:
        raise ValueError("final coordinates are not in angstrom")

    text = template.read_text(encoding="utf-8")
    nat_match = re.search(r"(?mi)^\s*nat\s*=\s*(\d+)\s*,?", text)
    if not nat_match or int(nat_match.group(1)) != len(coordinates):
        raise ValueError("template nat does not match accepted final geometry")

    outdir = f"./qe_scratch/final_scf/{prefix}"
    text = replace_control(text, prefix, outdir, restart_mode)
    text = re.sub(r"(?ms)^&IONS\s*$.*?^/\s*\n?", "", text)

    card = re.search(
        r"(?ms)^ATOMIC_POSITIONS(?:\s+\w+|\s*\([^)]*\))?\s*$.*?(?=^K_POINTS\b)",
        text,
    )
    if not card:
        raise ValueError("template has no replaceable ATOMIC_POSITIONS card")
    rows = ["ATOMIC_POSITIONS angstrom"]
    for entry in coordinates:
        rows.append(
            f"{entry['symbol']:<3s} {entry['x']: .10f} {entry['y']: .10f} {entry['z']: .10f}"
        )
    text = text[: card.start()] + "\n".join(rows) + "\n\n" + text[card.end() :]

    kcard = re.search(r"(?m)^K_POINTS\s+automatic\s*\n\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*$", text)
    if not kcard:
        raise ValueError("template has no automatic K_POINTS card")
    text = text[: kcard.start()] + "K_POINTS automatic\n  9 9 1 0 0 0" + text[kcard.end() :]

    note = (
        "! Fixed-geometry final SCF built from a strictly accepted relaxation.\n"
        "! PBE, DFT-D3(BJ), 65/520 Ry, MV smearing 0.01 Ry, CG, and spin settings inherited.\n"
    )
    return note + text.lstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--relax-output", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--restart-mode", choices=("from_scratch", "restart"), default="from_scratch")
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    content = build(args.template, args.relax_output, args.prefix, args.restart_mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
