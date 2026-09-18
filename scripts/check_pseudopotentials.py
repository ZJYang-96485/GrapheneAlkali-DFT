#!/usr/bin/env python3
"""Check the configured SSSP pseudopotential files for the current phase."""

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CURRENTLY_REQUIRED = {"C"}
APPROVED_CURRENT = {
    "C": {
        "filename": "C.pbe-n-kjpaw_psl.1.0.0.UPF",
        "md5": "8e281b34a927efac7e739263a90d7aed",
        "element": "C",
        "pseudo_type": "PAW",
        "input_dft": "PBE",
    }
}


def md5sum(path):
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_required_upf(element, path, filename):
    approved = APPROVED_CURRENT[element]
    if filename != approved["filename"]:
        raise ValueError(
            f"{element}: configured filename {filename!r} is not the approved "
            f"{approved['filename']!r}"
        )

    digest = md5sum(path)
    if digest.lower() != approved["md5"]:
        raise ValueError(
            f"{element}: MD5 mismatch for {filename}: {digest}; "
            f"expected {approved['md5']}"
        )

    text = path.read_text(encoding="utf-8", errors="replace")
    header_match = re.search(r"<PP_HEADER\b(.*?)/>", text, re.IGNORECASE | re.DOTALL)
    if not header_match or "<PP_INFO>" not in text:
        raise ValueError(f"{element}: UPF is missing PP_HEADER or PP_INFO")
    attributes = {
        match.group(1): match.group(3)
        for match in re.finditer(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(['\"])(.*?)\2",
            header_match.group(1),
            re.DOTALL,
        )
    }

    actual_element = attributes.get("element", "").strip()
    pseudo_type = attributes.get("pseudo_type", "").strip().upper()
    if actual_element != approved["element"]:
        raise ValueError(
            f"{element}: UPF header element is {actual_element!r}, "
            f"expected {approved['element']!r}"
        )
    if pseudo_type != approved["pseudo_type"]:
        raise ValueError(
            f"{element}: UPF pseudo_type is {pseudo_type!r}, "
            f"expected {approved['pseudo_type']!r}"
        )

    input_match = re.search(r"<PP_INPUTFILE>(.*?)</PP_INPUTFILE>", text, re.IGNORECASE | re.DOTALL)
    input_text = input_match.group(1) if input_match else ""
    dft_match = re.search(r"\bdft\s*=\s*['\"]([^'\"]+)['\"]", input_text, re.IGNORECASE)
    generated_dft = dft_match.group(1).strip().upper() if dft_match else None
    if generated_dft != approved["input_dft"]:
        raise ValueError(
            f"{element}: UPF generation input_dft is {generated_dft!r}, "
            f"expected {approved['input_dft']!r}"
        )

    try:
        wfc_cutoff = float(attributes["wfc_cutoff"])
        rho_cutoff = float(attributes["rho_cutoff"])
        z_valence = float(attributes["z_valence"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"{element}: invalid cutoff or valence metadata in PP_HEADER") from exc

    return {
        "md5": digest,
        "element": actual_element,
        "pseudo_type": pseudo_type,
        "functional": attributes.get("functional", "").strip(),
        "input_dft": generated_dft,
        "z_valence": z_valence,
        "wfc_cutoff": wfc_cutoff,
        "rho_cutoff": rho_cutoff,
    }


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
            if element in CURRENTLY_REQUIRED:
                try:
                    metadata = audit_required_upf(element, path, filename)
                except (OSError, ValueError) as exc:
                    print(f"{element}: INVALID (required now) - {exc}")
                    failed = True
                    continue
                print(f"{element}: VERIFIED ({phase_note}) - {filename}")
                print(
                    "  "
                    f"MD5={metadata['md5']}; element={metadata['element']}; "
                    f"type={metadata['pseudo_type']}; generated_dft={metadata['input_dft']}; "
                    f"header_functional={metadata['functional']}; "
                    f"z_valence={metadata['z_valence']:.1f}"
                )
                print(
                    "  header recommendations: "
                    f"ecutwfc={metadata['wfc_cutoff']:.6f} Ry; "
                    f"ecutrho={metadata['rho_cutoff']:.6f} Ry"
                )
            else:
                print(f"{element}: present ({phase_note}) - {filename}")
        elif element in CURRENTLY_REQUIRED:
            print(f"{element}: MISSING (required for current bare-substrate runs) - {filename}")
            failed = True
        else:
            print(f"{element}: missing (not required for current phase) - {filename}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
