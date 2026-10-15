#!/usr/bin/env python3
"""Run the conditional neutral-Na 16 Angstrom reference box point."""

import run_isolated_li_reference as pilot


pilot.RUN_ID = "20260923c_box16"
pilot.STEM = "na_atom_20260923c_box16"
pilot.STAGE = "isolated_na_box16_final_comparison_only"
pilot.INPUT = (
    pilot.ROOT
    / "qe_inputs/references/isolated_atoms/na_atom_20260923c_box16.in"
)
pilot.MANIFEST = (
    pilot.ROOT
    / "qe_inputs/references/isolated_atoms/na_atom_20260923c_box16_manifest.json"
)
pilot.DIAG = pilot.ROOT / "results/phase5/diagnostics" / pilot.STEM
pilot.STATUS = pilot.DIAG / "status.json"
pilot.OUTPUT = (
    pilot.ROOT / "results/references/isolated_atoms" / f"{pilot.STEM}.out"
)
pilot.SCRATCH = pilot.ROOT / "qe_scratch/references" / pilot.STEM
pilot.ELEMENT = "Na"
pilot.PSEUDOPOTENTIAL = "na_pbe_v1.5.uspp.F.UPF"
pilot.PSEUDOPOTENTIAL_MD5 = "44600605ef58000f06b90626533354dc"
pilot.FORBIDDEN_PSEUDOPOTENTIAL_TOKENS = ("C.pbe", "li_pbe")
pilot.EXPECTED_MAGNETIZATION = 1.0
pilot.WALL_EXIT_SECONDS = 2100
pilot.HIGH_VRAM_STOP_FRACTION = 0.80


if __name__ == "__main__":
    pilot.main()
