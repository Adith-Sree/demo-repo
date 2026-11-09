"""CODING 2 - Design of a rigid (protected-type) flanged coupling under static torque.

Pipeline
    1. Design torque  Td = service factor x T   (T given, or from power and speed)
    2. Permissible stresses from the materials database and factor of safety
       (or user-specified permissible stresses, as in many textbook problems)
    3. Shaft diameter from strength and from the angle-of-twist limit, rounded up
       to a standard size, checked against the maximum-diameter constraint
    4. Hub (D = 2d, L = 1.5d), checked as a hollow shaft
    5. Parallel key from the IS 2048 table, checked for shear and crushing
    6. Flange (PCD = 3d, OD = 4d, t = 0.5d, rim = 0.25d), checked for shear at the hub
    7. Bolts: number by rule, diameter from shear, rounded to an ISO metric size,
       checked for crushing; bolt length from the joint stack-up
    8. Verification table and drawing dimensions

Proportions follow V.B. Bhandari, Design of Machine Elements (protective-type
rigid flange coupling). Internal units: N, mm, MPa, N.mm.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields

from .database import Database, Material, ThreadSize, get_db
from .report import Report, num


@dataclass
class CouplingInput:
    torque_mode: str = "torque"     # "torque" | "power"
    T: float = 0.0                  # N.m (torque mode)
    power_kW: float = 0.0           # kW (power mode)
    rpm: float = 0.0                # rev/min (power mode)
    service_factor: float = 1.0
    fos: float = 3.0                # factor of safety for steel parts (shaft, key, bolts)
    fos_flange: float = 6.0         # factor of safety for the flange (cast iron is brittle)
    shaft_material: str = "auto"
    key_material: str = "same"      # "same" = shaft material
    bolt_material: str = "same"
    flange_material: str = "FG200"
    # optional permissible stresses in MPa (None -> derived from material and FoS)
    tau_shaft: float | None = None
    tau_key: float | None = None
    sigc_key: float | None = None
    tau_bolt: float | None = None
    sigc_bolt: float | None = None
    tau_flange: float | None = None
    # constraints
    d_max: float = 100.0            # mm
    shaft_length: float = 1000.0    # mm, length over which twist is limited
    twist_allow_deg: float = 1.0    # deg over shaft_length
    n_bolts: int = 0                # 0 -> standard rule

    @classmethod
    def from_dict(cls, data: dict) -> "CouplingInput":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"_comment", "module"}
        if unknown:
            raise ValueError(f"Unknown coupling input field(s): {', '.join(sorted(unknown))}")
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["module"] = "coupling"
        return d

    def torque_Nmm(self) -> float:
        if self.torque_mode == "power":
            return 60e6 * self.power_kW / (2 * math.pi * self.rpm)
        return self.T * 1e3

    def validate(self, db: Database) -> None:
        errs = []
        if self.torque_mode not in ("torque", "power"):
            errs.append("torque_mode must be 'torque' or 'power'")
        if self.torque_mode == "torque" and self.T <= 0:
            errs.append("torque T must be > 0")
        if self.torque_mode == "power" and (self.power_kW <= 0 or self.rpm <= 0):
            errs.append("power and speed must be > 0")
        if self.service_factor < 1:
            errs.append("service factor must be >= 1")
        if self.fos <= 0 or self.fos_flange <= 0:
            errs.append("factors of safety must be > 0")
        for name, use in (("shaft_material", "shaft"), ("key_material", "key"),
                          ("bolt_material", "bolt"), ("flange_material", "flange")):
            val = getattr(self, name)
            if val in ("auto", "same"):
                if val == "auto" and name != "shaft_material":
                    errs.append(f"{name} cannot be 'auto' (use 'same' or a material id)")
                if val == "same" and name in ("shaft_material", "flange_material"):
                    errs.append(f"{name} cannot be 'same'")
                continue
            if val not in db.materials:
                errs.append(f"unknown {name} '{val}'")
            elif use not in db.material(val).uses:
                errs.append(f"material '{val}' is not suitable for the {use}")
        for name in ("tau_shaft", "tau_key", "sigc_key", "tau_bolt", "sigc_bolt", "tau_flange"):
            v = getattr(self, name)
            if v is not None and v <= 0:
                errs.append(f"{name} must be > 0")
        if self.d_max <= 0 or self.shaft_length <= 0 or self.twist_allow_deg <= 0:
            errs.append("d_max, shaft_length and twist_allow_deg must be > 0")
        if self.n_bolts < 0:
            errs.append("n_bolts must be >= 0")
        if errs:
            raise ValueError("Invalid coupling input:\n  - " + "\n  - ".join(errs))


# --------------------------------------------------------------------------- helpers
def permissible(mat: Material, fos: float) -> tuple[float, float]:
    """(shear, crushing) permissible stresses.

    Ductile: tau = 0.5 Syt / n (maximum shear stress theory), sigma_c = Syt / n.
    Brittle: tau = 0.5 Sut / n, sigma_c = Sut / n.
    """
    S = mat.Sy_or_Sut
    return 0.5 * S / fos, S / fos


def bolts_by_rule(d: float) -> int:
    """Number of bolts (Bhandari): 3 up to d = 40 mm, 4 up to 100 mm, 6 up to 180 mm, then 8."""
    if d <= 40:
        return 3
    if d <= 100:
        return 4
    if d <= 180:
        return 6
    return 8


def shaft_diameter(Td: float, tau: float, G: float, L: float, theta_deg: float) -> tuple[float, float]:
    d_strength = (16.0 * Td / (math.pi * tau)) ** (1 / 3)
    d_twist = (32.0 * Td * L / (math.pi * G * math.radians(theta_deg))) ** 0.25
    return d_strength, d_twist


@dataclass
class CouplingResult:
    feasible: bool
    dims: dict
    checks: list            # (ok, text)
    shaft_material: Material
    bolt: ThreadSize | None
    report: Report

    @property
    def summary(self) -> str:
        d = self.dims
        state = "" if self.feasible else "  (DOES NOT satisfy all constraints)"
        bolt = self.bolt.designation if self.bolt else "?"
        return (f"Shaft {num(d['d'])} mm ({self.shaft_material.id}), key {num(d['key_b'])}x{num(d['key_h'])}x"
                f"{num(d['key_l'])}, {d['n_bolts']} x {bolt} bolts on {num(d['D1'])} mm PCD, "
                f"flange OD {num(d['D2'])} mm{state}")


# --------------------------------------------------------------------------- pipeline
def design_coupling(inp: CouplingInput, db: Database | None = None) -> CouplingResult:
    db = db or get_db()
    inp.validate(db)
    rep = Report("CODING 2 - DESIGN OF A RIGID FLANGED COUPLING (STATIC TORQUE)")
    checks: list[tuple[bool, str]] = []

    def check(ok: bool, text: str) -> None:
        checks.append((ok, text))
        rep.check(ok, text)

    # ------------------------------------------------------------------ step 0: inputs
    rep.heading("Step 0 - Input data")
    if inp.torque_mode == "power":
        torque_txt = f"{num(inp.power_kW)} kW at {num(inp.rpm)} rpm"
    else:
        torque_txt = f"{num(inp.T)} N.m"
    rep.table(["Item", "Value"], [
        ["Torque to be transmitted", torque_txt],
        ["Service factor", num(inp.service_factor)],
        ["FoS steel parts / flange", f"{num(inp.fos)} / {num(inp.fos_flange)}"],
        ["Shaft material", "automatic selection" if inp.shaft_material == "auto" else inp.shaft_material],
        ["Key / bolt material", f"{inp.key_material} / {inp.bolt_material}"],
        ["Flange material", inp.flange_material],
        ["Constraint: max shaft diameter", f"{num(inp.d_max)} mm"],
        ["Constraint: max angle of twist", f"{num(inp.twist_allow_deg)} deg over {num(inp.shaft_length)} mm"],
    ])

    # ------------------------------------------------------------------ step 1: torque
    rep.heading("Step 1 - Design torque")
    T = inp.torque_Nmm()
    if inp.torque_mode == "power":
        rep.calc("Rated torque T", T / 1e3, "N.m", "60 x 10^6 P / (2 pi n) / 10^3")
    else:
        rep.calc("Rated torque T", T / 1e3, "N.m")
    Td = inp.service_factor * T
    rep.calc("Design torque Td", Td / 1e3, "N.m", f"{num(inp.service_factor)} x T")

    # ------------------------------------------------------------------ step 2: shaft + materials
    rep.heading("Step 2 - Shaft material and permissible stresses")
    flange_mat = db.material(inp.flange_material)

    def shaft_option(mat: Material) -> dict:
        tau = inp.tau_shaft if inp.tau_shaft is not None else permissible(mat, inp.fos)[0]
        d_s, d_t = shaft_diameter(Td, tau, mat.G, inp.shaft_length, inp.twist_allow_deg)
        d_req = max(d_s, d_t)
        d_std = db.standard_shaft(d_req)
        feasible = d_std is not None and d_std <= inp.d_max + 1e-9
        cost = mat.rel_cost * mat.density * math.pi / 4 * (d_std / 1000) ** 2 if d_std else math.inf
        return dict(mat=mat, tau=tau, d_s=d_s, d_t=d_t, d_req=d_req, d_std=d_std, feasible=feasible, cost=cost)

    if inp.shaft_material == "auto":
        options = [shaft_option(m) for m in db.materials_for("shaft")]
        rep.text("Each shaft material is sized for strength and twist; the cheapest feasible one is chosen.")
        rows = [[o["mat"].id, o["mat"].is_equiv, o["mat"].Syt, o["tau"], o["d_s"], o["d_t"],
                 num(o["d_std"]) if o["d_std"] else "> 500", "yes" if o["feasible"] else "no", o["cost"]]
                for o in sorted(options, key=lambda o: (not o["feasible"], o["cost"]))]
        rep.table(["Material", "IS", "Syt", "tau perm", "d strength", "d twist", "d std", "Feasible",
                   "Cost idx"], rows)
        feas = [o for o in options if o["feasible"]]
        opt = min(feas, key=lambda o: o["cost"]) if feas else min(options, key=lambda o: o["d_req"])
    else:
        opt = shaft_option(db.material(inp.shaft_material))
    smat: Material = opt["mat"]
    kmat = smat if inp.key_material == "same" else db.material(inp.key_material)
    bmat = smat if inp.bolt_material == "same" else db.material(inp.bolt_material)

    tau_s = opt["tau"]
    tau_k = inp.tau_key if inp.tau_key is not None else permissible(kmat, inp.fos)[0]
    sc_k = inp.sigc_key if inp.sigc_key is not None else permissible(kmat, inp.fos)[1]
    tau_b = inp.tau_bolt if inp.tau_bolt is not None else permissible(bmat, inp.fos)[0]
    sc_b = inp.sigc_bolt if inp.sigc_bolt is not None else permissible(bmat, inp.fos)[1]
    tau_f = inp.tau_flange if inp.tau_flange is not None else permissible(flange_mat, inp.fos_flange)[0]

    def src(user_value) -> str:
        return "user specified" if user_value is not None else "from material"

    rep.table(["Part", "Material", "Sut / Syt (MPa)", "Permissible stresses (MPa)", "Source"], [
        ["Shaft", smat.label, f"{num(smat.Sut)} / {num(smat.Syt)}", f"tau = {num(tau_s)}", src(inp.tau_shaft)],
        ["Key", kmat.label, f"{num(kmat.Sut)} / {num(kmat.Syt)}", f"tau = {num(tau_k)}, sigma_c = {num(sc_k)}",
         src(inp.tau_key)],
        ["Bolts", bmat.label, f"{num(bmat.Sut)} / {num(bmat.Syt)}", f"tau = {num(tau_b)}, sigma_c = {num(sc_b)}",
         src(inp.tau_bolt)],
        ["Flange", flange_mat.label, f"{num(flange_mat.Sut)} / {num(flange_mat.Syt)}", f"tau = {num(tau_f)}",
         src(inp.tau_flange)],
    ])
    rep.text("Ductile parts: tau = 0.5 Syt / n (max. shear stress theory), sigma_c = Syt / n.")
    rep.text("Cast-iron flange: tau = 0.5 Sut / n_flange (no yield point).")

    # ------------------------------------------------------------------ step 3: shaft
    rep.heading("Step 3 - Shaft diameter")
    rep.calc("Strength: d = (16 Td / (pi tau))^(1/3)", opt["d_s"], "mm")
    rep.calc("Rigidity: d = (32 Td L / (pi G theta))^(1/4)", opt["d_t"], "mm")
    rep.calc("Required diameter", opt["d_req"], "mm")
    d = opt["d_std"]
    if d is None:
        rep.text("Required diameter exceeds the largest standard shaft (500 mm). Design stopped.")
        return CouplingResult(False, {}, [(False, "shaft too large")], smat, None, rep)
    rep.calc("Standard shaft diameter d", d, "mm")
    check(d <= inp.d_max, f"d = {num(d)} mm <= d_max = {num(inp.d_max)} mm")
    tau_actual = 16 * Td / (math.pi * d ** 3)
    theta = math.degrees(32 * Td * inp.shaft_length / (math.pi * smat.G * d ** 4))
    rep.calc("Shear stress in shaft", tau_actual, "MPa", "16 Td/(pi d^3)")
    check(tau_actual <= tau_s + 1e-9, f"tau = {num(tau_actual)} MPa <= {num(tau_s)} MPa")
    rep.calc("Angle of twist", theta, "deg")
    check(theta <= inp.twist_allow_deg + 1e-9, f"theta = {num(theta)} deg <= {num(inp.twist_allow_deg)} deg")

    # ------------------------------------------------------------------ step 4: hub
    rep.heading("Step 4 - Hub (D = 2d, L = 1.5d)")
    D = 2 * d

    def hub_tau(Dh: float) -> float:
        return 16 * Td * Dh / (math.pi * (Dh ** 4 - d ** 4))

    while hub_tau(D) > tau_f and D < 6 * d:
        D += 1.0
    rep.calc("Hub outer diameter D", D, "mm", "2d" if D == 2 * d else "increased for strength")
    rep.calc("Hub as hollow shaft: tau", hub_tau(D), "MPa", "16 Td D / (pi (D^4 - d^4))")
    check(hub_tau(D) <= tau_f + 1e-9, f"hub tau = {num(hub_tau(D))} MPa <= {num(tau_f)} MPa")

    # ------------------------------------------------------------------ step 5: key
    rep.heading("Step 5 - Key (parallel key, IS 2048)")
    b, h = db.key_for_shaft(d)
    rep.calc("Key width x height (from table)", f"{num(b)} x {num(h)}", "mm")
    l_shear = 2 * Td / (d * b * tau_k)
    l_crush = 4 * Td / (d * h * sc_k)
    rep.calc("Length for shear  2Td/(d b tau)", l_shear, "mm")
    rep.calc("Length for crushing  4Td/(d h sigma_c)", l_crush, "mm")
    l_min = max(1.5 * d, l_shear, l_crush)
    lk = db.round_up(l_min, db.key_lengths) or math.ceil(l_min)
    rep.calc("Hub length = key length", lk, "mm",
             f"max(1.5d, {num(l_shear)}, {num(l_crush)}) -> standard")
    tk = 2 * Td / (d * b * lk)
    ck = 4 * Td / (d * h * lk)
    rep.calc("Key shear stress", tk, "MPa")
    rep.calc("Key crushing stress", ck, "MPa")
    check(tk <= tau_k + 1e-9, f"key tau = {num(tk)} MPa <= {num(tau_k)} MPa")
    check(ck <= sc_k + 1e-9, f"key sigma_c = {num(ck)} MPa <= {num(sc_k)} MPa")

    # ------------------------------------------------------------------ step 6: flange
    rep.heading("Step 6 - Flange")
    D1 = float(math.ceil(3 * d))
    D2 = float(math.ceil(4 * d))
    t = float(math.ceil(0.5 * d))
    t1 = float(math.ceil(0.25 * d))
    t_req = 2 * Td / (math.pi * D ** 2 * tau_f)
    if t < t_req:
        t = float(math.ceil(t_req))
    rep.calc("Pitch circle diameter of bolts D1", D1, "mm", "3d")
    rep.calc("Outer diameter of flange D2", D2, "mm", "4d")
    rep.calc("Flange thickness t", t, "mm", "0.5d")
    rep.calc("Protective rim thickness t1", t1, "mm", "0.25d")
    tf = 2 * Td / (math.pi * D ** 2 * t)
    rep.calc("Flange shear at hub  2Td/(pi D^2 t)", tf, "MPa")
    check(tf <= tau_f + 1e-9, f"flange tau = {num(tf)} MPa <= {num(tau_f)} MPa")

    # ------------------------------------------------------------------ step 7: bolts
    rep.heading("Step 7 - Bolts (fitted in reamed holes, shank in shear)")
    N = inp.n_bolts or bolts_by_rule(d)
    if inp.n_bolts:
        rep.calc("Number of bolts N (user)", N)
    else:
        rep.text("Rule: N = 3 for d <= 40 mm, 4 for d <= 100 mm, 6 for d <= 180 mm, else 8")
        rep.calc("Number of bolts N", N)
    d1_req = math.sqrt(8 * Td / (math.pi * tau_b * N * D1))
    rep.calc("Bolt diameter for shear", d1_req, "mm", "sqrt(8 Td / (pi tau N D1))")
    bolt = None
    for th in db.thread_sizes("coarse", first_choice_only=True):
        if th.d < max(d1_req, 6.0) - 1e-9:
            continue
        if 2 * Td / (N * th.d * t * D1) <= sc_b:
            bolt = th
            break
    if bolt is None:
        rep.text("No ISO bolt in the database is large enough. Design stopped.")
        return CouplingResult(False, {}, checks + [(False, "bolts too large")], smat, None, rep)
    rep.text("Smallest first-choice ISO coarse bolt >= required size (minimum M6), crushing checked:")
    rep.calc("Selected bolt", f"{bolt.designation} (pitch {num(bolt.P)} mm)")
    tb = 8 * Td / (math.pi * bolt.d ** 2 * N * D1)
    cb = 2 * Td / (N * bolt.d * t * D1)
    rep.calc("Bolt shear stress", tb, "MPa")
    rep.calc("Bolt crushing stress  2Td/(N d1 t D1)", cb, "MPa")
    check(tb <= tau_b + 1e-9, f"bolt tau = {num(tb)} MPa <= {num(tau_b)} MPa")
    check(cb <= sc_b + 1e-9, f"bolt sigma_c = {num(cb)} MPa <= {num(sc_b)} MPa")
    head_r = bolt.across_flats / math.sqrt(3)       # circumscribed radius of hex head / nut
    check((D1 - D) / 2 >= head_r, f"room for bolt head between hub and PCD: {num((D1 - D) / 2)} mm "
                                  f">= {num(head_r)} mm")
    check((D2 - D1) / 2 >= head_r, f"room for bolt head between PCD and flange OD: {num((D2 - D1) / 2)} mm "
                                   f">= {num(head_r)} mm")
    L_need = 2 * t + bolt.washer_thickness + bolt.nut_height + 2 * bolt.P
    L_bolt = db.round_up(L_need, db.bolt_lengths) or math.ceil(L_need)
    rep.calc("Bolt length  2t + washer + nut + 2P", L_need, "mm")
    rep.calc("Standard bolt length", L_bolt, "mm")

    # ------------------------------------------------------------------ output
    dims = dict(d=d, D=D, L_hub=lk, key_b=b, key_h=h, key_l=lk, D1=D1, D2=D2, t=t, t1=t1,
                n_bolts=N, bolt=bolt.designation, bolt_length=L_bolt, Td=Td)
    feasible = all(ok for ok, _ in checks)
    result = CouplingResult(feasible, dims, checks, smat, bolt, rep)
    rep.heading("FINAL OUTPUT - Dimensions of the coupling")
    rep.table(["Part", "Dimension", "Value"], [
        ["Shaft", "Diameter d", f"{num(d)} mm  ({smat.id} / {smat.is_equiv})"],
        ["Hub", "Outer diameter D", f"{num(D)} mm"],
        ["Hub", "Length L", f"{num(lk)} mm"],
        ["Key", "b x h x l", f"{num(b)} x {num(h)} x {num(lk)} mm  ({kmat.id})"],
        ["Flange", "Pitch circle diameter D1", f"{num(D1)} mm"],
        ["Flange", "Outer diameter D2", f"{num(D2)} mm"],
        ["Flange", "Thickness t", f"{num(t)} mm  ({flange_mat.id})"],
        ["Flange", "Protective rim thickness t1", f"{num(t1)} mm"],
        ["Bolts", "Number x size", f"{N} x {bolt.designation} x {num(L_bolt)} long  ({bmat.id})"],
        ["Torque", "Design torque Td", f"{num(Td / 1e3)} N.m"],
    ])
    rep.text(f"All checks passed: {'YES' if feasible else 'NO'}")
    if not feasible:
        rep.text("Suggestions: choose a stronger material, relax the twist limit, or allow a larger diameter.")
    return result
