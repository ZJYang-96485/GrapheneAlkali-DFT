#!/usr/bin/env python3
"""Run the reviewed neutral-Li 14 Angstrom reference box point."""

import run_isolated_li_reference as pilot


pilot.RUN_ID = "20260923c_box14"
pilot.STEM = "li_atom_20260923c_box14"
pilot.STAGE = "isolated_li_box14_comparison_only"
pilot.INPUT = (
    pilot.ROOT
    / "qe_inputs/references/isolated_atoms/li_atom_20260923c_box14.in"
)
pilot.MANIFEST = (
    pilot.ROOT
    / "qe_inputs/references/isolated_atoms/li_atom_20260923c_box14_manifest.json"
)
pilot.DIAG = pilot.ROOT / "results/phase5/diagnostics" / pilot.STEM
pilot.STATUS = pilot.DIAG / "status.json"
pilot.OUTPUT = (
    pilot.ROOT / "results/references/isolated_atoms" / f"{pilot.STEM}.out"
)
pilot.SCRATCH = pilot.ROOT / "qe_scratch/references" / pilot.STEM
pilot.WALL_EXIT_SECONDS = 2100
pilot.HIGH_VRAM_STOP_FRACTION = 0.80


if __name__ == "__main__":
    pilot.main()
