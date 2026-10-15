#!/usr/bin/env python3
"""Regression tests for Quantum ESPRESSO output parsing."""

import unittest

from scripts.parse_qe_output import maximum_force_component, parse_ionic_convergence


class IonicConvergenceTests(unittest.TestCase):
    def test_recoverable_curvature_warning_does_not_mask_convergence(self):
        text = """\
WARNING: bfgs curvature condition failed, Theta= 0.857
bfgs converged in 51 scf cycles and 48 bfgs steps
End of BFGS Geometry Optimization
"""
        self.assertIs(parse_ionic_convergence(text), True)

    def test_last_terminal_outcome_wins(self):
        stopped_then_converged = """\
The maximum number of bfgs steps has been reached
bfgs converged in 51 scf cycles and 48 bfgs steps
"""
        converged_then_stopped = """\
bfgs converged in 51 scf cycles and 48 bfgs steps
The maximum number of bfgs steps has been reached
"""
        self.assertIs(parse_ionic_convergence(stopped_then_converged), True)
        self.assertIs(parse_ionic_convergence(converged_then_stopped), False)

    def test_explicit_bfgs_failure_is_terminal(self):
        self.assertIs(parse_ionic_convergence("bfgs failed"), False)


class ForceMetricTests(unittest.TestCase):
    def test_maximum_cartesian_component_is_reported_separately(self):
        forces = [
            {"fx_ry_bohr": -0.3, "fy_ry_bohr": 0.4, "fz_ry_bohr": 0.0},
            {"fx_ry_bohr": 0.1, "fy_ry_bohr": -0.2, "fz_ry_bohr": 0.25},
        ]
        self.assertEqual(maximum_force_component(forces), 0.4)


if __name__ == "__main__":
    unittest.main()
