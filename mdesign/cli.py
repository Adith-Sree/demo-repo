"""Command-line front end: interactive menus, JSON input files and report saving.

    python main.py                         interactive menu
    python main.py shaft                   interactive shaft design
    python main.py --input examples/shaft_beam.json --report reports/shaft.md
    python main.py materials | threads | classes     show the databases
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import fatigue as fat
from . import ui
from .bolted_joint import PRELOAD_FRACTION, BoltInput, design_bolted_joint
from .coupling import CouplingInput, design_coupling
from .database import Database, get_db
from .report import Report, num
from .shaft import ShaftInput, ShaftLoad, design_shaft

MODULES = {
    "shaft": "Coding 1 - Power transmission shaft (fluctuating torque and bending)",
    "coupling": "Coding 2 - Rigid flanged coupling (static torque)",
    "bolt": "Coding 3 - Bolted joint (fluctuating axial / shear load)",
}


# =========================================================================== database views
def materials_table(db: Database, use: str | None = None) -> str:
    rep = Report("MATERIALS DATABASE" + (f" - suitable for {use}" if use else ""))
    mats = db.materials_for(use) if use else list(db.materials.values())
    rep.table(["id", "Material", "IS equivalent", "Sut", "Syt", "E (GPa)", "G (GPa)", "rho", "Elong %", "BHN",
               "Rel. cost"],
              [[m.id, m.name, m.is_equiv, m.Sut, num(m.Syt), m.E / 1000, m.G / 1000, m.density, m.elongation,
                m.BHN, m.rel_cost] for m in mats])
    rep.text("Strengths in MPa, density in kg/m^3. Syt '-' = brittle (no yield point).")
    return rep.to_text()


def threads_table(db: Database, series: str = "coarse") -> str:
    rep = Report(f"ISO METRIC THREAD DATABASE - {series} series (ISO 261 / 724, nuts ISO 4032)")
    rep.table(["Size", "Pitch", "d2", "d3", "At (mm^2)", "Ar (mm^2)", "Nut m", "Across flats", "Washer h",
               "1st choice"],
              [[t.designation, t.P, t.d2, t.d3, t.At, t.Ar, t.nut_height, t.across_flats, t.washer_thickness,
                "yes" if t.first_choice else "no"] for t in db.thread_sizes(series)])
    return rep.to_text()


def classes_table(db: Database) -> str:
    from .bolted_joint import bolt_endurance
    rep = Report("BOLT PROPERTY CLASSES (ISO 898-1)")
    rows = []
    for c in db.bolt_classes:
        Se, src = bolt_endurance(c)
        rows.append([c.name, f"M{c.d_min:g}-M{c.d_max:g}", c.Sp, c.Sut, c.Sy, Se, src])
    rep.table(["Class", "Sizes", "Sp", "Sut", "Sy", "Se", "Se source"], rows)
    rep.text("All strengths in MPa. Sp = proof strength, Se = endurance strength of rolled threads.")
    return rep.to_text()


def choose_material(db: Database, use: str, default: str, allow_auto: bool = True,
                    allow_same: bool = False) -> str:
    print(materials_table(db, use))
    extra = []
    if allow_auto:
        extra.append("auto")
    if allow_same:
        extra.append("same")
    ids = [m.id for m in db.materials_for(use)]
    hint = " / ".join(extra + ["a material id from the table"])
    return ui.ask_text(f"Material for the {use} ({hint})", default, allowed=extra + ids)


# =========================================================================== interactive input
def collect_shaft(db: Database) -> ShaftInput:
    inp = ShaftInput()
    print("\nDesign of a power transmission shaft. Press Enter to accept the value in [brackets].")

    ui.section("1. Shaft configuration and bending moment")
    inp.bm_mode = ui.ask_choice("How is the bending moment given?", [
        ("beam", "From the shaft configuration (two bearings + gear/pulley loads)"),
        ("direct", "I already know Mmax and Mmin at the critical section"),
    ], "beam")
    if inp.bm_mode == "direct":
        inp.M_max = ui.ask_float("Maximum bending moment Mmax", 600, "N.m")
        inp.M_min = ui.ask_float("Minimum bending moment Mmin", 200, "N.m", maximum=inp.M_max)
        default_cycle = "given"
    else:
        print("  Bearing A is at x = 0 and bearing B at x = span. Loads outside 0..span are overhung.")
        print("  Give each load's vertical (Fv) and horizontal (Fh) components; each fluctuates min..max.")
        inp.span = ui.ask_float("Distance between bearings (span)", 600, "mm", strictly_positive=True)
        n = ui.ask_int("Number of loads (gears/pulleys)", 2, minimum=1, maximum=10)
        defaults = [ShaftLoad("Gear", 150, 1456, 485, 4000, 1333), ShaftLoad("Pulley", 450, 4500, 1500, 0, 0)]
        for i in range(n):
            dl = defaults[i] if i < len(defaults) else ShaftLoad(f"Load {i + 1}", inp.span / 2)
            print(f"  -- load {i + 1}")
            name = ui.ask_text("Name", dl.name)
            x = ui.ask_float("Position x from bearing A", dl.x, "mm")
            fv_max = ui.ask_float("Vertical force, max Fv_max", dl.Fv_max, "N")
            fv_min = ui.ask_float("Vertical force, min Fv_min", dl.Fv_min, "N", maximum=fv_max)
            fh_max = ui.ask_float("Horizontal force, max Fh_max", dl.Fh_max, "N")
            fh_min = ui.ask_float("Horizontal force, min Fh_min", dl.Fh_min, "N", maximum=fh_max)
            inp.loads.append(ShaftLoad(name, x, fv_max, fv_min, fh_max, fh_min))
        default_cycle = "rotating"
    cycle = ui.ask_choice("Bending stress cycle", [
        ("rotating", "Rotating shaft, stationary loads -> fully reversed bending (Mm = 0, Ma = Mmax)"),
        ("given", "Use Mmax / Mmin as the fluctuating cycle (Mm and Ma from Mmax, Mmin)"),
    ], default_cycle)
    inp.rotating = cycle == "rotating"

    ui.section("2. Fluctuating torque")
    tmode = ui.ask_choice("How is the torque given?", [
        ("torque", "Tmax and Tmin directly"),
        ("power", "Power, speed and +/- fluctuation"),
    ], "torque")
    if tmode == "torque":
        inp.T_max = ui.ask_float("Maximum torque Tmax", 600, "N.m")
        inp.T_min = ui.ask_float("Minimum torque Tmin", 200, "N.m", maximum=inp.T_max)
    else:
        P = ui.ask_float("Power", 25, "kW", strictly_positive=True)
        rpm = ui.ask_float("Speed", 600, "rpm", strictly_positive=True)
        fl = ui.ask_float("Torque fluctuation about the mean", 50, "%", minimum=0, maximum=100)
        Tm = 9549.3 * P / rpm
        inp.T_max, inp.T_min = Tm * (1 + fl / 100), Tm * (1 - fl / 100)
        print(f"    -> mean torque {Tm:.1f} N.m, Tmax {inp.T_max:.1f} N.m, Tmin {inp.T_min:.1f} N.m")

    ui.section("3. Design factors")
    inp.fos = ui.ask_float("Factor of safety", 2.0, strictly_positive=True)
    inp.criterion = ui.ask_choice("Fatigue failure criterion", [(k, v) for k, v in fat.FAILURE_CRITERIA.items()],
                                  "goodman")
    inp.surface = ui.ask_choice("Surface finish of the shaft", [
        ("machined", "Machined or cold-drawn"), ("ground", "Ground"),
        ("hot-rolled", "Hot-rolled"), ("as-forged", "As forged")], "machined")
    inp.reliability = ui.ask_choice("Reliability", [(f"{r:g}", f"{r:g} %") for r in fat.RELIABILITY], "90")
    inp.reliability = float(inp.reliability)
    inp.temperature = ui.ask_float("Operating temperature", 25, "C")
    notch_opts = [(k, v["label"]) for k, v in fat.NOTCHES.items()] + [("custom", "Custom Kt, Kts and r/d")]
    inp.notch = ui.ask_choice("Stress raiser at the critical section", notch_opts, "shoulder-rounded")
    if inp.notch == "custom":
        inp.Kt = ui.ask_float("Kt (bending)", 2.0, minimum=1)
        inp.Kts = ui.ask_float("Kts (torsion)", 1.6, minimum=1)
        inp.r_over_d = ui.ask_float("Notch radius / diameter r/d (0 -> q = 1)", 0.05, minimum=0)

    ui.section("4. Constraints")
    inp.d_max = ui.ask_float("Maximum shaft diameter", 60, "mm", strictly_positive=True)
    inp.twist_length = ui.ask_float("Shaft length subjected to torque", 1000, "mm", strictly_positive=True)
    inp.twist_allow_deg = ui.ask_float("Maximum allowable angle of twist over that length", 1.0, "deg",
                                       strictly_positive=True)

    ui.section("5. Material")
    inp.material = choose_material(db, "shaft", "auto")
    return inp


def collect_coupling(db: Database) -> CouplingInput:
    inp = CouplingInput()
    print("\nDesign of a rigid flanged coupling. Press Enter to accept the value in [brackets].")

    ui.section("1. Torque to be transmitted")
    inp.torque_mode = ui.ask_choice("How is the torque given?", [
        ("torque", "Torque directly"), ("power", "Power and speed")], "torque")
    if inp.torque_mode == "torque":
        inp.T = ui.ask_float("Torque", 1000, "N.m", strictly_positive=True)
    else:
        inp.power_kW = ui.ask_float("Power", 37.5, "kW", strictly_positive=True)
        inp.rpm = ui.ask_float("Speed", 360, "rpm", strictly_positive=True)
    inp.service_factor = ui.ask_float("Service factor", 1.25, minimum=1)

    ui.section("2. Materials and factors of safety")
    inp.shaft_material = choose_material(db, "shaft", "auto")
    inp.key_material = ui.ask_text("Key material ('same' as shaft or an id)", "same",
                                   allowed=["same"] + [m.id for m in db.materials_for("key")])
    inp.bolt_material = ui.ask_text("Bolt material ('same' as shaft or an id)", "same",
                                    allowed=["same"] + [m.id for m in db.materials_for("bolt")])
    inp.flange_material = ui.ask_text("Flange material id (e.g. FG200, SG400, 1030-HR)", "FG200",
                                      allowed=[m.id for m in db.materials_for("flange")])
    inp.fos = ui.ask_float("Factor of safety for shaft, key and bolts", 3.0, strictly_positive=True)
    inp.fos_flange = ui.ask_float("Factor of safety for the flange", 6.0 if db.material(inp.flange_material).brittle
                                  else 3.0, strictly_positive=True)
    if ui.ask_yes_no("Use your own permissible stresses instead (textbook-style problem)?", False):
        inp.tau_shaft = ui.ask_float("Permissible shear stress, shaft", 40, "MPa", strictly_positive=True)
        inp.tau_key = ui.ask_float("Permissible shear stress, key", inp.tau_shaft, "MPa", strictly_positive=True)
        inp.sigc_key = ui.ask_float("Permissible crushing stress, key", 2 * inp.tau_key, "MPa",
                                    strictly_positive=True)
        inp.tau_bolt = ui.ask_float("Permissible shear stress, bolts", inp.tau_shaft, "MPa", strictly_positive=True)
        inp.sigc_bolt = ui.ask_float("Permissible crushing stress, bolts", 2 * inp.tau_bolt, "MPa",
                                     strictly_positive=True)
        inp.tau_flange = ui.ask_float("Permissible shear stress, flange", 8, "MPa", strictly_positive=True)

    ui.section("3. Constraints")
    inp.d_max = ui.ask_float("Maximum shaft diameter", 80, "mm", strictly_positive=True)
    inp.shaft_length = ui.ask_float("Shaft length subjected to torque", 1000, "mm", strictly_positive=True)
    inp.twist_allow_deg = ui.ask_float("Maximum allowable angle of twist over that length", 1.0, "deg",
                                       strictly_positive=True)
    inp.n_bolts = ui.ask_int("Number of bolts (0 = standard rule)", 0, minimum=0, maximum=24)
    return inp


def collect_bolt(db: Database) -> BoltInput:
    inp = BoltInput()
    print("\nDesign of a bolted joint under fluctuating load. Press Enter to accept the value in [brackets].")

    ui.section("1. Load")
    inp.load_type = ui.ask_choice("Load on the joint", [
        ("axial", "Axial (tension) load - e.g. cylinder cover, bearing cap"),
        ("shear", "Shear (transverse) load - e.g. lap / butt joint, bracket")], "axial")
    if inp.load_type == "axial":
        inp.P_max = ui.ask_float("Total external load, maximum Pmax", 120, "kN", strictly_positive=True)
        inp.P_min = ui.ask_float("Total external load, minimum Pmin", 30, "kN", minimum=0, maximum=inp.P_max)
    else:
        inp.P_max = ui.ask_float("Total shear load, maximum Pmax", 30, "kN", strictly_positive=True)
        inp.P_min = ui.ask_float("Total shear load, minimum Pmin (negative = reversed)", 10, "kN",
                                 minimum=-inp.P_max, maximum=inp.P_max)
    inp.n_bolts = ui.ask_int("Number of bolts", 8 if inp.load_type == "axial" else 4, minimum=1, maximum=64)
    inp.fos = ui.ask_float("Required factor of safety", 2.0, strictly_positive=True)

    ui.section("2. Joint geometry")
    inp.grip = ui.ask_float("Total thickness of the clamped plates (grip)", 40 if inp.load_type == "axial" else 24,
                            "mm", strictly_positive=True)
    print(materials_table(db, "member"))
    inp.member_material = ui.ask_text("Plate (member) material id", "1020-HR",
                                      allowed=[m.id for m in db.materials_for("member")])
    inp.washers = ui.ask_yes_no("Plain washer under the nut?", True)
    if inp.load_type == "shear":
        inp.joint_type = ui.ask_choice("Joint type", [
            ("bearing", "Bearing type - bolt shank carries the shear"),
            ("friction", "Friction grip (slip-critical) - preload x friction carries the shear")], "bearing")
        inp.shear_planes = ui.ask_int("Number of shear planes (1 = lap joint, 2 = double-cover butt)", 1,
                                      minimum=1, maximum=4)
        if inp.joint_type == "bearing":
            inp.plate_thickness = ui.ask_float("Thickness of the thinnest plate in bearing",
                                               inp.grip / (inp.shear_planes + 1), "mm", strictly_positive=True)
            inp.threads_in_shear_plane = ui.ask_yes_no("Are threads in the shear plane?", False)
        else:
            inp.mu = ui.ask_float("Friction coefficient of the faying surfaces", 0.30, minimum=0.01, maximum=0.99)

    ui.section("3. Bolt selection from the ISO metric thread database")
    inp.series = ui.ask_choice("Thread series", [("coarse", "Coarse (standard)"), ("fine", "Fine pitch")], "coarse")
    if ui.ask_yes_no("Show the ISO metric thread database?", True):
        print(threads_table(db, inp.series))
    inp.first_choice_only = ui.ask_yes_no("Use first-choice sizes only (M6, M8, M10, M12, M16, M20...)?", True)
    sizes = [t.designation for t in db.thread_sizes(inp.series)]
    inp.bolt_size = ui.ask_text("Bolt size ('auto' = smallest that works, or e.g. " + sizes[6] + ")", "auto",
                                allowed=["auto"] + sizes)
    if ui.ask_yes_no("Show the bolt property classes (ISO 898-1)?", False):
        print(classes_table(db))
    inp.bolt_class = ui.ask_text("Property class ('auto' or e.g. 8.8)", "auto",
                                 allowed=["auto"] + db.bolt_class_names())
    inp.preload = ui.ask_choice("Preload", [
        ("reusable", f"Reusable connection: Fi = {PRELOAD_FRACTION['reusable']} x proof load"),
        ("permanent", f"Permanent connection: Fi = {PRELOAD_FRACTION['permanent']} x proof load")], "reusable")
    inp.nut_factor = ui.ask_float("Torque coefficient K (0.2 dry, 0.18 lubricated)", 0.2, strictly_positive=True)
    return inp


COLLECTORS = {"shaft": collect_shaft, "coupling": collect_coupling, "bolt": collect_bolt}
INPUT_CLASSES = {"shaft": ShaftInput, "coupling": CouplingInput, "bolt": BoltInput}


def run_design(module: str, inp, db: Database):
    if module == "shaft":
        return design_shaft(inp, db)
    if module == "coupling":
        return design_coupling(inp, db)
    if module == "bolt":
        return design_bolted_joint(inp, db)
    raise ValueError(module)


# =========================================================================== flows
def run_interactive(module: str, db: Database, report_path: str | None, save_inputs: str | None) -> int:
    inp = COLLECTORS[module](db)
    try:
        result = run_design(module, inp, db)
    except ValueError as exc:
        print(f"\nERROR: {exc}")
        return 2
    print()
    print(result.report.to_text())
    print(f">>> {result.summary}\n")
    if report_path is None and ui.ask_yes_no("Save the calculation report as Markdown?", True):
        report_path = ui.ask_text("Report file", f"reports/{module}_report.md")
    if report_path:
        print(f"Report saved to {result.report.save(report_path)}")
    if save_inputs is None and ui.ask_yes_no("Save these inputs as JSON (to re-run later)?", False):
        save_inputs = ui.ask_text("Input file", f"reports/{module}_inputs.json")
    if save_inputs:
        Path(save_inputs).parent.mkdir(parents=True, exist_ok=True)
        Path(save_inputs).write_text(json.dumps(inp.to_dict(), indent=2), encoding="utf-8")
        print(f"Inputs saved to {save_inputs}")
    return 0


def run_from_file(path: str, module: str | None, db: Database, report_path: str | None) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    module = module or data.get("module")
    if module not in INPUT_CLASSES:
        print(f"ERROR: say which design to run (shaft / coupling / bolt) or add \"module\" to {path}")
        return 2
    try:
        inp = INPUT_CLASSES[module].from_dict(data)
        result = run_design(module, inp, db)
    except (ValueError, TypeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(result.report.to_text())
    print(f">>> {result.summary}")
    if report_path:
        print(f"Report saved to {result.report.save(report_path)}")
    return 0


def menu(db: Database) -> int:
    while True:
        print()
        print("=" * 64)
        print("  DESIGN OF MACHINE ELEMENTS - CODING ASSIGNMENT")
        print("=" * 64)
        print("  1) " + MODULES["shaft"])
        print("  2) " + MODULES["coupling"])
        print("  3) " + MODULES["bolt"])
        print("  4) Show the materials database")
        print("  5) Show the ISO metric thread database")
        print("  6) Show the bolt property classes")
        print("  0) Exit")
        choice = ui.ask_text("Select", "1", allowed=["0", "1", "2", "3", "4", "5", "6"])
        if choice == "0":
            return 0
        if choice in ("1", "2", "3"):
            module = {"1": "shaft", "2": "coupling", "3": "bolt"}[choice]
            run_interactive(module, db, None, None)
            ui.ask_text("Press Enter to return to the menu", "")
        elif choice == "4":
            print(materials_table(db))
        elif choice == "5":
            print(threads_table(db, "coarse"))
            print(threads_table(db, "fine"))
        elif choice == "6":
            print(classes_table(db))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Design of machine elements: shaft, rigid flanged coupling and bolted joint.")
    parser.add_argument("module", nargs="?",
                        choices=["shaft", "coupling", "bolt", "materials", "threads", "classes"],
                        help="design to run, or a database to display (omit for the menu)")
    parser.add_argument("-i", "--input", help="JSON input file (non-interactive run)")
    parser.add_argument("-r", "--report", help="save the calculation report to this Markdown file")
    parser.add_argument("--save-inputs", help="save the inputs typed in an interactive run to this JSON file")
    args = parser.parse_args(argv)
    db = get_db()

    try:
        if args.module == "materials":
            print(materials_table(db))
            return 0
        if args.module == "threads":
            print(threads_table(db, "coarse"))
            print(threads_table(db, "fine"))
            return 0
        if args.module == "classes":
            print(classes_table(db))
            return 0
        if args.input:
            return run_from_file(args.input, args.module, db, args.report)
        if args.module:
            return run_interactive(args.module, db, args.report, args.save_inputs)
        return menu(db)
    except (ui.InputAborted, KeyboardInterrupt):
        print("\nStopped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
