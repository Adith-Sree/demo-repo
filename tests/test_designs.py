"""Validation tests. Run with:  python -m unittest discover -s tests -v

The textbook cross-checks use published worked examples:
  * Shigley, Mechanical Engineering Design, Example 7-1 (shaft fatigue FoS)
  * Shigley Table 8-1 (ISO thread stress areas)
  * Classic cast-iron flange coupling problem: 15 kW at 900 rpm, Ks = 1.35,
    tau = 40 MPa, sigma_c = 80 MPa, tau(CI) = 8 MPa  ->  d = 35 mm, 3 x M8 bolts
"""

import contextlib
import io
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mdesign import fatigue as fat                                   # noqa: E402
from mdesign.bolted_joint import (BoltInput, analyse, design_bolted_joint,  # noqa: E402
                                  member_stiffness)
from mdesign.cli import main as cli_main                             # noqa: E402
from mdesign.coupling import CouplingInput, design_coupling          # noqa: E402
from mdesign.database import get_db                                  # noqa: E402
from mdesign.shaft import ShaftInput, ShaftLoad, analyse_beam, design_shaft  # noqa: E402

KPSI = 6.894757      # MPa per kpsi
LBF_IN = 0.112985    # N.m per lbf.in


class TestFatigue(unittest.TestCase):
    def setUp(self):
        # Shigley Example 7-1: shoulder, d = 1.1 in, r = 0.11 in, Sut = 105 kpsi, Sy = 82 kpsi,
        # Ma = 1260 lbf.in (fully reversed), Tm = 1100 lbf.in, Kt = 1.68, Kts = 1.42, R = 0.99
        self.Sut, self.Sy = 105 * KPSI, 82 * KPSI
        d, r = 1.1 * 25.4, 0.11 * 25.4
        Kf = fat.fatigue_factor(1.68, fat.notch_sensitivity(self.Sut, r))
        Kfs = fat.fatigue_factor(1.42, fat.notch_sensitivity(self.Sut, r, torsion=True))
        self.Se = (0.5 * self.Sut * fat.surface_factor(self.Sut, "machined") * fat.size_factor(d)
                   * fat.reliability_factor(99))
        self.sa = Kf * 32 * 1260 * LBF_IN * 1e3 / (math.pi * d ** 3)
        self.sm = math.sqrt(3) * Kfs * 16 * 1100 * LBF_IN * 1e3 / (math.pi * d ** 3)
        self.Kf, self.Kfs = Kf, Kfs

    def test_marin_and_notch_factors(self):
        self.assertAlmostEqual(self.Kf, 1.58, delta=0.01)
        self.assertAlmostEqual(fat.surface_factor(self.Sut, "machined"), 0.787, delta=0.003)
        self.assertAlmostEqual(fat.size_factor(1.1 * 25.4), 0.870, delta=0.003)
        self.assertAlmostEqual(self.Se / KPSI, 29.3, delta=0.2)

    def test_shigley_example_7_1_factors_of_safety(self):
        published = {"goodman": 1.62, "gerber": 1.87, "asme": 1.88, "soderberg": 1.56}
        for crit, n_pub in published.items():
            n = fat.fos_fluctuating(self.sa, self.sm, self.Se, self.Sut, self.Sy, crit)
            self.assertAlmostEqual(n, n_pub, delta=0.02 * n_pub, msg=crit)

    def test_closed_form_diameter_matches_factor_of_safety(self):
        """Diameter from the DE equation must give back exactly the target FoS."""
        Kf, Kfs, Se, Sut, Sy = 1.6, 1.4, 180.0, 630.0, 530.0
        Ma, Mm, Ta, Tm = 300e3, 120e3, 80e3, 400e3
        for crit in fat.FAILURE_CRITERIA:
            d = fat.de_shaft_diameter(2.0, Kf, Kfs, Ma, Mm, Ta, Tm, Se, Sut, Sy, crit)
            k = 1 / (math.pi * d ** 3)
            sa = math.sqrt((Kf * 32 * Ma * k) ** 2 + 3 * (Kfs * 16 * Ta * k) ** 2)
            sm = math.sqrt((Kf * 32 * Mm * k) ** 2 + 3 * (Kfs * 16 * Tm * k) ** 2)
            self.assertAlmostEqual(fat.fos_fluctuating(sa, sm, Se, Sut, Sy, crit), 2.0, places=6, msg=crit)


class TestShaft(unittest.TestCase):
    def test_beam_central_load(self):
        beam = analyse_beam(1000, [ShaftLoad("P", 500, 1000, 1000, 0, 0)])
        self.assertAlmostEqual(beam.x_crit, 500)
        self.assertAlmostEqual(beam.M_max, 250e3)            # PL/4 = 250 N.m

    def test_beam_overhang_and_two_planes(self):
        beam = analyse_beam(1000, [ShaftLoad("P", 1200, 1000, 500, 0, 0)])
        self.assertAlmostEqual(beam.x_crit, 1000)
        self.assertAlmostEqual(beam.M_max, 200e3)            # F x overhang
        beam = analyse_beam(1000, [ShaftLoad("P", 500, 3000, 0, 4000, 0)])
        self.assertAlmostEqual(beam.M_max, 5000 * 250)       # resultant of 3-4-5 loads

    def test_example_design_meets_all_requirements(self):
        data = json.loads((ROOT / "examples" / "shaft_beam.json").read_text())
        res = design_shaft(ShaftInput.from_dict(data))
        self.assertTrue(res.feasible)
        self.assertIn(res.d, get_db().shaft_diameters)
        v = res.sizing.verify
        self.assertGreaterEqual(v["n_f"], 2.0)
        self.assertGreaterEqual(v["n_y"], 2.0)
        self.assertLessEqual(v["theta_deg"], 1.0)
        self.assertLessEqual(res.d, 60)

    def test_twist_constraint_governs_when_tight(self):
        inp = ShaftInput(M_max=100, M_min=-100, T_max=500, T_min=500, material="4340-QT540",
                         twist_allow_deg=0.25, d_max=200)
        res = design_shaft(inp)
        s = res.sizing
        self.assertEqual(max(s.d_fatigue, s.d_yield, s.d_twist), s.d_twist)
        self.assertLessEqual(s.verify["theta_deg"], 0.25 + 1e-9)

    def test_infeasible_when_max_diameter_too_small(self):
        res = design_shaft(ShaftInput(M_max=2000, M_min=0, T_max=2000, T_min=0, d_max=30))
        self.assertFalse(res.feasible)

    def test_round_trip_dict(self):
        data = json.loads((ROOT / "examples" / "shaft_beam.json").read_text())
        inp = ShaftInput.from_dict(data)
        self.assertEqual(ShaftInput.from_dict(inp.to_dict()), inp)

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            design_shaft(ShaftInput(M_max=100, M_min=200))
        with self.assertRaises(ValueError):
            ShaftInput.from_dict({"M_maxx": 1})


class TestCoupling(unittest.TestCase):
    def test_textbook_problem(self):
        data = json.loads((ROOT / "examples" / "coupling_textbook.json").read_text())
        res = design_coupling(CouplingInput.from_dict(data))
        d = res.dims
        self.assertTrue(res.feasible)
        self.assertAlmostEqual(d["Td"] / 1e3, 214.9, delta=0.1)
        self.assertEqual(d["d"], 35)
        self.assertEqual(d["n_bolts"], 3)
        self.assertEqual(res.bolt.designation, "M8")
        self.assertEqual((d["key_b"], d["key_h"]), (10, 8))
        self.assertEqual((d["D"], d["D1"], d["D2"]), (70, 105, 140))

    def test_material_based_design_passes_checks(self):
        data = json.loads((ROOT / "examples" / "coupling.json").read_text())
        res = design_coupling(CouplingInput.from_dict(data))
        self.assertTrue(res.feasible)
        self.assertTrue(all(ok for ok, _ in res.checks))
        self.assertLessEqual(res.dims["d"], 80)

    def test_too_small_d_max_is_flagged(self):
        res = design_coupling(CouplingInput(T=5000, d_max=40))
        self.assertFalse(res.feasible)


class TestBolts(unittest.TestCase):
    db = get_db()

    def test_thread_areas_match_iso_tables(self):
        # Shigley Table 8-1 (coarse): At / Ar in mm^2
        for size, At, Ar in [("M8", 36.6, 32.8), ("M12", 84.3, 76.3), ("M16", 157, 144), ("M24", 353, 324)]:
            th = self.db.thread_by_name(size)
            self.assertAlmostEqual(th.At, At, delta=0.01 * At, msg=size)
            self.assertAlmostEqual(th.Ar, Ar, delta=0.01 * Ar, msg=size)

    def test_member_stiffness_close_to_wileman(self):
        # The 30-deg frustum model and Wileman's FEA fit agree within ~10 % for usual
        # grips (0.5 d .. 3.5 d). For very long grips the frustum value is lower, i.e.
        # it gives a larger joint constant C, which is conservative for the bolt.
        E, d = 207000.0, 12.0
        for l in (6.0, 12.0, 24.0, 40.0):
            wileman = E * d * 0.78715 * math.exp(0.62873 * d / l)
            self.assertAlmostEqual(member_stiffness(E, d, l) / wileman, 1.0, delta=0.10)

    def test_selected_bolt_is_smallest_that_passes(self):
        inp = BoltInput(load_type="axial", P_max=120, P_min=30, n_bolts=8, grip=40, bolt_class="8.8")
        res = design_bolted_joint(inp)
        self.assertTrue(res.ok)
        chosen = res.chosen["th"]
        smaller = [t for t in self.db.thread_sizes("coarse", True) if t.d < chosen.d]
        for th in smaller:
            cls = self.db.bolt_class("8.8", th.d)
            self.assertFalse(analyse(inp, th, cls, self.db.material(inp.member_material), self.db)["ok"])

    def test_goodman_reduces_to_repeated_load_form(self):
        # with Pmin = 0, n_f = Se (Sut - si) / (sa (Sut + Se))   (Shigley Eq. 8-39)
        inp = BoltInput(load_type="axial", P_max=50, P_min=0, n_bolts=4, grip=30, bolt_class="8.8",
                        bolt_size="M12")
        r = design_bolted_joint(inp).chosen
        Se, Sut = r["Se"], r["cls"].Sut
        self.assertAlmostEqual(r["n_f"], Se * (Sut - r["s_i"]) / (r["s_a"] * (Sut + Se)), places=9)

    def test_shear_joints(self):
        data = json.loads((ROOT / "examples" / "bolt_shear.json").read_text())
        res = design_bolted_joint(BoltInput.from_dict(data))
        self.assertTrue(res.ok)
        fr = design_bolted_joint(BoltInput(load_type="shear", P_max=30, P_min=10, n_bolts=4,
                                           joint_type="friction", grip=24, bolt_class="8.8"))
        self.assertTrue(fr.ok)
        self.assertGreaterEqual(fr.chosen["n_slip"], 2.0)

    def test_specific_size_that_is_too_small_fails(self):
        res = design_bolted_joint(BoltInput(load_type="axial", P_max=120, P_min=30, n_bolts=8, grip=40,
                                            bolt_class="8.8", bolt_size="M6"))
        self.assertFalse(res.ok)


class TestCommandLine(unittest.TestCase):
    def test_all_examples_run(self):
        for path in sorted((ROOT / "examples").glob("*.json")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli_main(["--input", str(path)])
            self.assertEqual(code, 0, msg=path.name)
            self.assertIn("FINAL OUTPUT", buf.getvalue(), msg=path.name)

    def test_database_views(self):
        for view in ("materials", "threads", "classes"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cli_main([view]), 0)
            self.assertGreater(len(buf.getvalue()), 200)


if __name__ == "__main__":
    unittest.main()
