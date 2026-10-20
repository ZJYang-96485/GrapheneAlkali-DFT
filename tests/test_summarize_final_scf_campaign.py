#!/usr/bin/env python3
"""Unit tests for final-SCF adsorption-energy and structure helpers."""

import tempfile
import unittest
from pathlib import Path

from scripts.summarize_final_scf_campaign import adsorption_energy_ry, export_extxyz


class AdsorptionEnergyTests(unittest.TestCase):
    def test_li_reference_is_subtracted(self):
        self.assertAlmostEqual(
            adsorption_energy_ry(-936.0, -922.0, "Li"), 0.35806979
        )


class ExtxyzTests(unittest.TestCase):
    def test_qe_input_exports_periodic_xy_nonperiodic_z(self):
        text = """\
&SYSTEM
  nat = 2,
/
CELL_PARAMETERS angstrom
  2.0 0.0 0.0
  0.0 3.0 0.0
  0.0 0.0 9.0
ATOMIC_POSITIONS angstrom
C1 0.0 0.0 4.5
Li 1.0 1.0 6.0
K_POINTS gamma
"""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "case.in"
            output_path = Path(directory) / "case.extxyz"
            input_path.write_text(text, encoding="utf-8")
            export_extxyz(input_path, output_path, "test_case")
            result = output_path.read_text(encoding="utf-8")
        self.assertIn('pbc="T T F"', result)
        self.assertIn("C 0.0 0.0 4.5", result)
        self.assertIn("Li 1.0 1.0 6.0", result)


if __name__ == "__main__":
    unittest.main()
