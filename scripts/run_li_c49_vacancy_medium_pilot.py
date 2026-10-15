#!/usr/bin/env python3
"""Run the fresh, post-restart Li/C49 disk_io=medium pilot only."""

import run_li_c49_vacancy_pilot as pilot


pilot.RUN_ID = "20260921a"
pilot.STEM = "li_c49_vacancy_20260921a_medium_pilot"
pilot.MANIFEST = pilot.ROOT / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260921a_medium_manifest.json"
pilot.INPUT = pilot.ROOT / "qe_inputs/adsorption/li_monovacancy/li_c49_vacancy_20260921a_medium_pilot.in"
pilot.DIAG = pilot.ROOT / "results/phase5/diagnostics" / pilot.STEM
pilot.STATUS = pilot.DIAG / "status.json"
pilot.OUTPUT = pilot.DIAG / f"{pilot.STEM}.out"
pilot.SCRATCH = pilot.ROOT / "qe_scratch/adsorption" / pilot.STEM


if __name__ == "__main__":
    pilot.main()
