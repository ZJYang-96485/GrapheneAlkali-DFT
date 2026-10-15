#!/usr/bin/env python3
"""Run the approved Li/C49 55/440 Ry force/resource pilot only."""

import run_li_c49_vacancy_pilot as pilot


pilot.RUN_ID = "20260923a_e55"
pilot.STEM = "li_c49_vacancy_20260923a_e55_pilot"
pilot.MANIFEST = pilot.ROOT / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260923a_e55_manifest.json"
pilot.INPUT = pilot.ROOT / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260923a_e55_pilot.in"
pilot.DIAG = pilot.ROOT / "results/phase5/diagnostics" / pilot.STEM
pilot.STATUS = pilot.DIAG / "status.json"
pilot.OUTPUT = pilot.DIAG / f"{pilot.STEM}.out"
pilot.SCRATCH = pilot.ROOT / "qe_scratch/adsorption" / pilot.STEM
pilot.WALL_EXIT_SECONDS = 2.5 * 3600
pilot.HIGH_VRAM_STOP_FRACTION = 0.95


if __name__ == "__main__":
    pilot.main()
