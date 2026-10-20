#!/usr/bin/env python3
"""Build the fixed-geometry 70/560 Ry adsorption-cutoff validation inputs.

Only the wavefunction and charge-density cutoffs, isolated run identifiers,
scratch paths, and nonphysical runtime/I/O controls are changed.  The source
geometries and every other physical/numerical setting are retained verbatim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PERIODIC_SOURCES = {
    "c50": "qe_inputs/final_scf/20261014/c50_9x9x1.in",
    "li_c50": "qe_inputs/final_scf/20261014/li_c50_9x9x1.in",
    "na_c50": "qe_inputs/final_scf/20261014/na_c50_9x9x1.in",
}
ATOM_SOURCES = {
    "li_atom": "qe_inputs/references/isolated_atoms/li_atom_20260923d_box16.in",
    "na_atom": "qe_inputs/references/isolated_atoms/na_atom_20260923c_box16.in",
}
CASES = {**PERIODIC_SOURCES, **ATOM_SOURCES}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(pattern: str, text: str, description: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
        raise ValueError(f"source input failed audit: {description}")


def audit_source(case: str, text: str) -> None:
    common = {
        r"^\s*calculation\s*=\s*'scf'": "SCF calculation",
        r"^\s*input_dft\s*=\s*'PBE'": "PBE",
        r"^\s*vdw_corr\s*=\s*'dft-d3'": "DFT-D3",
        r"^\s*dftd3_version\s*=\s*4": "D3(BJ)",
        r"^\s*dftd3_threebody\s*=\s*\.true\.": "D3 three-body term",
        r"^\s*ecutwfc\s*=\s*65(?:\.0)?\s*,?\s*$": "65 Ry source ecutwfc",
        r"^\s*ecutrho\s*=\s*520(?:\.0)?\s*,?\s*$": "520 Ry source ecutrho",
        r"^\s*conv_thr\s*=\s*1\.0d-8": "1e-8 Ry convergence threshold",
        r"^\s*mixing_beta\s*=\s*0\.3": "mixing_beta 0.3",
        r"^\s*diagonalization\s*=\s*'cg'": "CG diagonalization",
    }
    for pattern, description in common.items():
        require(pattern, text, description)
    # Pristine C50 uses QE's documented default tot_charge=0; all other source
    # inputs state the neutral charge explicitly.
    if case != "c50":
        require(
            r"^\s*tot_charge\s*=\s*0(?:\.0)?\s*,?\s*$",
            text,
            "neutral charge",
        )

    if case in PERIODIC_SOURCES:
        periodic = {
            r"^\s*assume_isolated\s*=\s*'2D'": "2D isolation",
            r"^\s*occupations\s*=\s*'smearing'": "smearing occupations",
            r"^\s*smearing\s*=\s*'mv'": "Marzari-Vanderbilt smearing",
            r"^\s*degauss\s*=\s*0\.01": "0.01 Ry degauss",
            r"^K_POINTS\s+automatic\s*$\s*^\s*9\s+9\s+1\s+0\s+0\s+0\s*$":
                "9x9x1 unshifted k mesh",
        }
        for pattern, description in periodic.items():
            require(pattern, text, description)
    else:
        atom = {
            r"^\s*assume_isolated\s*=\s*'mt'": "Martyna-Tuckerman isolation",
            r"^\s*nspin\s*=\s*2": "spin polarization",
            r"^\s*tot_magnetization\s*=\s*1(?:\.0)?": "one unpaired electron",
            r"^\s*occupations\s*=\s*'fixed'": "fixed occupations",
            r"^K_POINTS\s+gamma\s*$": "Gamma-only atom",
        }
        for pattern, description in atom.items():
            require(pattern, text, description)


def replace_control(text: str, case: str, max_seconds: int) -> str:
    """Normalize CONTROL, including the historical ``/ restart_mode`` defect."""
    match = re.search(r"(?ms)^&CONTROL\s*$.*?(?=^&SYSTEM\s*$)", text)
    if not match:
        raise ValueError("missing CONTROL-to-SYSTEM span")

    managed = {
        "calculation",
        "prefix",
        "outdir",
        "restart_mode",
        "disk_io",
        "max_seconds",
    }
    kept = ["&CONTROL"]
    for original in match.group(0).splitlines()[1:]:
        stripped = original.strip()
        if not stripped or stripped == "/":
            continue
        candidate = stripped.lstrip("/").strip()
        assignment = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", candidate)
        if assignment and assignment.group(1).lower() in managed:
            continue
        if stripped.startswith("/"):
            raise ValueError(f"unrecognized malformed CONTROL line: {original!r}")
        kept.append(original.rstrip())

    prefix = f"cut70_{case}_20261017"
    kept.extend(
        [
            "   calculation = 'scf',",
            f"   prefix = '{prefix}',",
            f"   outdir = './qe_scratch/cutoff_validation_20261017/{prefix}',",
            "   restart_mode = 'from_scratch',",
            "   disk_io = 'nowf',",
            f"   max_seconds = {max_seconds},",
            "/",
            "",
        ]
    )
    return text[: match.start()] + "\n".join(kept) + text[match.end() :]


def build_case(case: str, source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    audit_source(case, text)
    text = replace_control(text, case, 10800 if case in PERIODIC_SOURCES else 1800)

    text, wfc_count = re.subn(
        r"(?mi)^(\s*ecutwfc\s*=\s*)65(?:\.0)?(\s*,?\s*)$",
        r"\g<1>70\g<2>",
        text,
    )
    text, rho_count = re.subn(
        r"(?mi)^(\s*ecutrho\s*=\s*)520(?:\.0)?(\s*,?\s*)$",
        r"\g<1>560\g<2>",
        text,
    )
    if (wfc_count, rho_count) != (1, 1):
        raise ValueError(
            f"{case}: expected one cutoff replacement each, got "
            f"ecutwfc={wfc_count}, ecutrho={rho_count}"
        )

    text = text.replace("65/520 Ry", "70/560 Ry")
    note = (
        "! Adsorbate-specific cutoff validation at 70/560 Ry.\n"
        "! Fixed accepted geometry; all physical/numerical settings except cutoffs are inherited.\n"
    )
    result = note + text.lstrip()
    require(r"^\s*ecutwfc\s*=\s*70", result, "70 Ry generated ecutwfc")
    require(r"^\s*ecutrho\s*=\s*560", result, "560 Ry generated ecutrho")
    return result


def write_idempotent(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"refusing to overwrite differing input: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("qe_inputs/convergence/adsorbate_cutoff/20261017"),
    )
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = repo / output_root

    records = []
    for case, relative_source in CASES.items():
        source = repo / relative_source
        if not source.is_file():
            raise FileNotFoundError(f"missing source for {case}: {source}")
        output = output_root / f"{case}_ecut70_560.in"
        content = build_case(case, source)
        write_idempotent(output, content)
        records.append(
            {
                "case": case,
                "source": str(source.relative_to(repo)),
                "source_sha256": sha256(source),
                "output": str(output.relative_to(repo)),
                "output_sha256": sha256(output),
            }
        )

    manifest = {
        "campaign": "adsorbate_cutoff_validation_20261017",
        "cutoffs_ry": {"ecutwfc": 70, "ecutrho": 560},
        "cases": records,
        "invariants": {
            "periodic_geometry": "fixed accepted 9x9x1 final-SCF geometries",
            "periodic_k_points": "9x9x1 unshifted",
            "atom_cell": "16 Angstrom cube, Gamma-only, neutral spin-polarized",
            "functional": "PBE + DFT-D3(BJ), including three-body term",
            "electronic": "conv_thr=1e-8 Ry; mixing_beta=0.3; diagonalization=cg",
        },
    }
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    write_idempotent(output_root / "manifest.json", manifest_text)
    print(output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
