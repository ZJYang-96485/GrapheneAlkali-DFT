#!/usr/bin/env python3
"""Regression tests for cutoff-input generation and CONTROL normalization."""

import unittest

from scripts.build_adsorbate_cutoff_validation_20261017 import replace_control
from scripts.build_final_scf_from_relax import replace_control as replace_final_control


class CutoffControlTests(unittest.TestCase):
    def test_historical_malformed_control_tail_is_removed(self):
        source = """\
&CONTROL
  calculation = 'scf',
  prefix = 'old',
  pseudo_dir = './pseudopotentials',
  outdir = './old',
  tprnfor = .true.,
/   restart_mode = 'from_scratch',
   disk_io = 'nowf',
   max_seconds = 14400,
/
&SYSTEM
  ecutwfc = 65,
  ecutrho = 520,
/
"""
        result = replace_control(source, "c50", 10800)
        control = result.split("&SYSTEM", 1)[0]
        self.assertNotIn("/   restart_mode", control)
        self.assertEqual(control.count("\n/"), 1)
        self.assertIn("pseudo_dir = './pseudopotentials'", control)
        self.assertIn("max_seconds = 10800", control)
        self.assertIn("prefix = 'cut70_c50_20261017'", control)


class FinalScfControlRegressionTests(unittest.TestCase):
    def test_missing_entries_are_inserted_before_slash(self):
        source = """\
&CONTROL
  calculation = 'relax',
  prefix = 'old',
  outdir = './old',
  tprnfor = .true.,
/
&SYSTEM
/
"""
        result = replace_final_control(source, "new", "./scratch/new", "from_scratch")
        control = result.split("&SYSTEM", 1)[0]
        self.assertEqual(control.count("\n/"), 1)
        self.assertNotIn("/   restart_mode", control)
        self.assertIn("restart_mode = 'from_scratch'", control)
        self.assertIn("disk_io = 'nowf'", control)
        self.assertIn("max_seconds = 14400", control)


if __name__ == "__main__":
    unittest.main()
