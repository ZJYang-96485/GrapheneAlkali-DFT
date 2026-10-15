#!/usr/bin/env python3
"""Prepare the audited Na/C49 checkpoint-continuation input and manifest."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261012a_relax.in"
SOURCE_MANIFEST = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261012a_manifest.json"
TARGET = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_relax_restart.in"
MANIFEST = ROOT / "qe_inputs/adsorption/na_monovacancy/na_c49_vacancy_20261013a_restart_manifest.json"


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


def validate(text: str) -> None:
    required = (
        "calculation = 'relax'",
        "prefix = 'na_c49_vacancy_20261012a_relax'",
        "outdir = './qe_scratch/adsorption/na_c49_vacancy_20261012a_relax'",
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
        "forc_conv_thr = 4.0d-4",
        "ion_dynamics = 'bfgs'",
        "na_pbe_v1.5.uspp.F.UPF",
        "6 6 1 0 0 0",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise ValueError(f"Locked settings missing: {missing}")


def main() -> None:
    if TARGET.exists() or MANIFEST.exists():
        raise FileExistsError("Refusing to overwrite an existing continuation input set")

    source = SOURCE.read_text(encoding="utf-8")
    validate(source)
    restart = replace_once(source, "restart_mode = 'from_scratch'", "restart_mode = 'restart'")
    restart = replace_once(restart, "max_seconds = 82800", "max_seconds = 14400")
    restart = replace_once(
        restart,
        "! Approved deadline relaxation: neutral Na above the reconstructed C49 vacancy.",
        "! Approved checkpoint continuation: neutral Na above the reconstructed C49 vacancy.\n"
        "! Restarting the verified October 12 BFGS/electronic state without changing methodology.",
    )
    validate(restart)
    if "restart_mode = 'restart'" not in restart or "max_seconds = 14400" not in restart:
        raise ValueError("Restart controls were not applied")
    TARGET.write_text(restart, encoding="utf-8")

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest = {
        "status": "approved checkpoint continuation for the October 13, 2026 RunPod window",
        "system": source_manifest["system"],
        "run_id": "20261013a",
        "source_input": str(SOURCE.relative_to(ROOT)),
        "source_input_sha256": sha256(SOURCE),
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "restart_input": str(TARGET.relative_to(ROOT)),
        "restart_input_sha256": sha256(TARGET),
        "source_result_root": "results/cloud/20261012_na_c49_deadline_24h",
        "source_bundle_sha256": "d1e97200926832802c9033cc7b286e4e82a543baa56335bfb747d39c1e525a72f",
        "checkpoint_identity": {
            "prefix": "na_c49_vacancy_20261012a_relax",
            "outdir": "qe_scratch/adsorption/na_c49_vacancy_20261012a_relax",
            "restart_mode": "restart",
        },
        "segment_max_seconds": 14400,
        "scientific_settings_changed": False,
        "reference_list": source_manifest["reference_list"],
        "site_literature": source_manifest["site_literature"],
        "method": source_manifest["method"],
        "limitations": source_manifest["limitations"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(TARGET.relative_to(ROOT))
    print(MANIFEST.relative_to(ROOT))


if __name__ == "__main__":
    main()
