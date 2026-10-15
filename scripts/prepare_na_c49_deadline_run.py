#!/usr/bin/env python3
"""Prepare the approved October 12 Na/C49 pilot and relaxation inputs."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20261012a"
SOURCE = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261001a_cloud_pilot.in"
SOURCE_MANIFEST = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261001a_cloud_pilot_manifest.json"
OUTPUT_DIR = SOURCE.parent
PILOT = OUTPUT_DIR / f"na_c49_vacancy_{RUN_ID}_pilot.in"
RELAX = OUTPUT_DIR / f"na_c49_vacancy_{RUN_ID}_relax.in"
MANIFEST = OUTPUT_DIR / f"na_c49_vacancy_{RUN_ID}_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def validate_locked_settings(text: str) -> None:
    required = (
        "nat = 50",
        "ntyp = 3",
        "tot_charge = 0.0",
        "input_dft = 'PBE'",
        "vdw_corr = 'dft-d3'",
        "dftd3_version = 4",
        "dftd3_threebody = .true.",
        "assume_isolated = '2D'",
        "ecutwfc = 65",
        "ecutrho = 520",
        "nspin = 2",
        "smearing = 'mv'",
        "degauss = 0.01",
        "conv_thr = 1.0d-8",
        "mixing_beta = 0.3",
        "diagonalization = 'cg'",
        "na_pbe_v1.5.uspp.F.UPF",
        "6 6 1 0 0 0",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise ValueError(f"Locked settings missing from source: {missing}")
    positions = text.split("ATOMIC_POSITIONS angstrom\n", 1)[1].split("\nK_POINTS", 1)[0]
    rows = [line for line in positions.splitlines() if line.strip()]
    if len(rows) != 50 or sum(line.startswith("Na ") for line in rows) != 1:
        raise ValueError("Expected one Na atom and 49 carbon atoms")


def main() -> None:
    targets = (PILOT, RELAX, MANIFEST)
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to overwrite an existing deadline input set")

    source = SOURCE.read_text(encoding="utf-8")
    validate_locked_settings(source)

    pilot = source.replace("20261001a", RUN_ID)
    pilot = pilot.replace(
        "! Conditional fixed-geometry pilot: neutral Na above the reconstructed C49 vacancy.",
        "! Approved deadline pilot: neutral Na above the reconstructed C49 vacancy.",
        1,
    )

    relax = pilot
    relax = replace_once(relax, "calculation = 'scf',", "calculation = 'relax',\n   restart_mode = 'from_scratch',")
    relax = replace_once(relax, f"prefix = 'na_c49_vacancy_{RUN_ID}_pilot',", f"prefix = 'na_c49_vacancy_{RUN_ID}_relax',")
    relax = replace_once(
        relax,
        f"outdir = './qe_scratch/adsorption/na_c49_vacancy_{RUN_ID}_pilot',",
        f"outdir = './qe_scratch/adsorption/na_c49_vacancy_{RUN_ID}_relax',",
    )
    relax = replace_once(
        relax,
        "   max_seconds = 14400,",
        "   etot_conv_thr = 1.0d-4,\n   forc_conv_thr = 4.0d-4,\n   max_seconds = 82800,\n   nstep = 80,",
    )
    relax = replace_once(
        relax,
        "ATOMIC_SPECIES\n",
        "&IONS\n   ion_dynamics = 'bfgs',\n/\n\nATOMIC_SPECIES\n",
    )
    relax = relax.replace("! Approved deadline pilot:", "! Approved deadline relaxation:", 1)

    validate_locked_settings(pilot)
    validate_locked_settings(relax)
    PILOT.write_text(pilot, encoding="utf-8")
    RELAX.write_text(relax, encoding="utf-8")

    manifest = {
        "status": "approved for the October 12-13, 2026 guarded 24-hour RunPod window",
        "system": "neutral Na/C49 at the reconstructed-vacancy-centred starting site",
        "run_id": RUN_ID,
        "source_pilot": str(SOURCE.relative_to(ROOT)),
        "source_pilot_sha256": sha256(SOURCE),
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "pilot_input": str(PILOT.relative_to(ROOT)),
        "pilot_input_sha256": sha256(PILOT),
        "relax_input": str(RELAX.relative_to(ROOT)),
        "relax_input_sha256": sha256(RELAX),
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "site_literature": [
            "https://doi.org/10.3390/molecules24040754",
            "https://doi.org/10.1039/C8NR10383F",
        ],
        "method": {
            "functional": "PBE+D3(BJ)",
            "ecutwfc_ry": 65,
            "ecutrho_ry": 520,
            "k_points": [6, 6, 1, 0, 0, 0],
            "smearing": "Marzari-Vanderbilt",
            "degauss_ry": 0.01,
            "assume_isolated": "2D",
            "nspin": 2,
            "diagonalization": "cg",
            "forc_conv_thr_ry_bohr": 0.0004,
        },
        "limitations": "One vacancy-centred starting site and one spin seed; no exhaustive ground-state claim.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(PILOT.relative_to(ROOT))
    print(RELAX.relative_to(ROOT))
    print(MANIFEST.relative_to(ROOT))


if __name__ == "__main__":
    main()
