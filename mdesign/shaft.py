"""CODING 1 - Design of a power-transmission shaft under fluctuating bending and torsion.

Pipeline
    1. Bending moment at the critical section (given directly, or computed from a
       simply supported shaft carrying point loads in two planes)
    2. Mean / alternating components of bending moment and torque
    3. Material selection from the materials database (manual or automatic)
    4. Endurance limit Se = ka kb kc kd ke Se'  (Marin equation)
    5. Fatigue stress-concentration factors Kf, Kfs (Neuber notch sensitivity)
    6. Fatigue diameter from the distortion-energy (DE) criterion, iterated because
       kb and Kf depend on d
    7. First-cycle yield diameter
    8. Torsional rigidity diameter from the allowable angle of twist
    9. Round up to a standard shaft size and check the maximum-diameter constraint
   10. Verify the standard shaft (factors of safety and twist)

Internal units: N, mm, MPa, N.mm. Torques/moments are entered in N.m.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields

from . import fatigue as fat
from .database import Database, Material, get_db
from .report import Report, num


# =========================================================================== inputs
@dataclass
class ShaftLoad:
    """A point load (gear, pulley, sprocket...) on the shaft.

    x is measured from bearing A (x = 0); bearing B is at x = span. Loads outside
    0..span are overhung. Forces are in N, positive downward (vertical plane) or
    positive in the chosen horizontal direction. Each component fluctuates between
    its _min and _max value.
    """
    name: str = "Load"
    x: float = 0.0
    Fv_max: float = 0.0
    Fv_min: float = 0.0
    Fh_max: float = 0.0
    Fh_min: float = 0.0


@dataclass
class ShaftInput:
    # ---- bending
    bm_mode: str = "direct"        # "direct": Mmax/Mmin given; "beam": compute from loads
    M_max: float = 0.0             # N.m (direct mode)
    M_min: float = 0.0             # N.m (direct mode)
    span: float = 0.0              # mm, distance between bearings (beam mode)
    loads: list[ShaftLoad] = field(default_factory=list)
    rotating: bool = False         # True: rotating shaft, stationary loads -> fully reversed bending
    # ---- torsion
    T_max: float = 0.0             # N.m
    T_min: float = 0.0             # N.m
    # ---- design data
    fos: float = 2.0
    criterion: str = "goodman"     # goodman | soderberg | gerber | asme
    surface: str = "machined"      # ground | machined | hot-rolled | as-forged
    reliability: float = 90.0      # %
    temperature: float = 25.0      # deg C
    notch: str = "shoulder-rounded"  # none | shoulder-rounded | shoulder-sharp | keyseat | custom
    Kt: float | None = None        # custom notch only
    Kts: float | None = None
    r_over_d: float | None = None
    # ---- constraints
    d_max: float = 100.0           # mm, maximum allowed shaft diameter
    twist_length: float = 1000.0   # mm, length of shaft carrying the torque
    twist_allow_deg: float = 1.0   # deg, allowable twist over twist_length
    # ---- material
    material: str = "auto"         # material id or "auto"

    # ------------------------------------------------------------------ (de)serialise
    @classmethod
    def from_dict(cls, data: dict) -> "ShaftInput":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"_comment", "module"}
        if unknown:
            raise ValueError(f"Unknown shaft input field(s): {', '.join(sorted(unknown))}")
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs["loads"] = [ShaftLoad(**ld) for ld in data.get("loads", [])]
        return cls(**kwargs)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["module"] = "shaft"
        return d

    def validate(self, db: Database) -> None:
        errs = []
        if self.bm_mode not in ("direct", "beam"):
            errs.append("bm_mode must be 'direct' or 'beam'")
        if self.bm_mode == "direct" and self.M_min > self.M_max:
            errs.append("M_min must not exceed M_max")
        if self.bm_mode == "beam":
            if self.span <= 0:
                errs.append("span between bearings must be > 0")
            if not self.loads:
                errs.append("beam mode needs at least one load")
            for ld in self.loads:
                if ld.Fv_min > ld.Fv_max or ld.Fh_min > ld.Fh_max:
                    errs.append(f"load '{ld.name}': min value must not exceed max value")
        if self.T_min > self.T_max:
            errs.append("T_min must not exceed T_max")
        if self.fos <= 0:
            errs.append("factor of safety must be > 0")
        if self.criterion not in fat.FAILURE_CRITERIA:
            errs.append(f"criterion must be one of {list(fat.FAILURE_CRITERIA)}")
        if self.surface not in fat.SURFACE_FINISH:
            errs.append(f"surface must be one of {list(fat.SURFACE_FINISH)}")
        if not 50 <= self.reliability < 100:
            errs.append("reliability must be between 50 and 99.9999 %")
        if self.notch != "custom" and self.notch not in fat.NOTCHES:
            errs.append(f"notch must be one of {list(fat.NOTCHES) + ['custom']}")
        if self.notch == "custom":
            if self.Kt is None or self.Kts is None or self.Kt < 1 or self.Kts < 1:
                errs.append("custom notch needs Kt >= 1 and Kts >= 1")
            if self.r_over_d is None or self.r_over_d < 0:
                errs.append("custom notch needs r_over_d >= 0 (0 means q = 1)")
        if self.d_max <= 0 or self.twist_length <= 0 or self.twist_allow_deg <= 0:
            errs.append("d_max, twist_length and twist_allow_deg must be > 0")
        if self.material != "auto":
            if self.material not in db.materials:
                errs.append(f"unknown material '{self.material}'")
            elif "shaft" not in db.material(self.material).uses:
                errs.append(f"material '{self.material}' is not suitable for shafts")
        if errs:
            raise ValueError("Invalid shaft input:\n  - " + "\n  - ".join(errs))

    def notch_data(self) -> tuple[str, float, float, float]:
        if self.notch == "custom":
            return "Custom notch", float(self.Kt), float(self.Kts), float(self.r_over_d)
        n = fat.NOTCHES[self.notch]
        return n["label"], n["Kt"], n["Kts"], n["r_over_d"]


# =========================================================================== beam analysis
@dataclass
class BeamResult:
    x_crit: float
    M_max: float          # N.mm, resultant at critical section, max load case
    M_min: float          # N.mm, signed (projected on the max-case direction), min load case
    reactions: dict       # {"max": (RAv, RBv, RAh, RBh), "min": (...)}
    rows: list            # [x, Mv_max, Mh_max, M_max, M_min] in N.m for the report


def _reactions(span: float, forces: list[tuple[float, float]]) -> tuple[float, float]:
    """Simply supported at x=0 (A) and x=span (B); forces positive downward."""
    RB = sum(F * x for x, F in forces) / span
    RA = sum(F for _, F in forces) - RB
    return RA, RB


def _moment(x: float, span: float, forces: list[tuple[float, float]], RA: float, RB: float) -> float:
    """Bending moment at section x from the forces to its left (sagging positive)."""
    M = 0.0
    if x > 0.0:
        M += RA * x
    if x > span:
        M += RB * (x - span)
    for xi, F in forces:
        if xi < x:
            M -= F * (x - xi)
    return M


def analyse_beam(span: float, loads: list[ShaftLoad]) -> BeamResult:
    cases = {
        "max": ([(ld.x, ld.Fv_max) for ld in loads], [(ld.x, ld.Fh_max) for ld in loads]),
        "min": ([(ld.x, ld.Fv_min) for ld in loads], [(ld.x, ld.Fh_min) for ld in loads]),
    }
    reac = {}
    for case, (fv, fh) in cases.items():
        RAv, RBv = _reactions(span, fv)
        RAh, RBh = _reactions(span, fh)
        reac[case] = (RAv, RBv, RAh, RBh)

    def moments(case: str, x: float) -> tuple[float, float]:
        fv, fh = cases[case]
        RAv, RBv, RAh, RBh = reac[case]
        return _moment(x, span, fv, RAv, RBv), _moment(x, span, fh, RAh, RBh)

    x_lo = min([0.0] + [ld.x for ld in loads])
    x_hi = max([span] + [ld.x for ld in loads])
    key_points = sorted({0.0, span, *[ld.x for ld in loads]})
    grid = [x_lo + (x_hi - x_lo) * i / 400 for i in range(401)]
    best_x, best_M = key_points[0], -1.0
    for x in key_points + grid:
        mv, mh = moments("max", x)
        m = math.hypot(mv, mh)
        if m > best_M + 1e-9:
            best_x, best_M = x, m

    def signed_min(x: float) -> float:
        mv1, mh1 = moments("max", x)
        mv2, mh2 = moments("min", x)
        m1 = math.hypot(mv1, mh1)
        if m1 == 0.0:
            return math.hypot(mv2, mh2)
        return (mv2 * mv1 + mh2 * mh1) / m1   # component of the min-case moment along the max-case direction

    rows = []
    for x in sorted(set(key_points) | {best_x}):
        mv, mh = moments("max", x)
        rows.append([x, mv / 1e3, mh / 1e3, math.hypot(mv, mh) / 1e3, signed_min(x) / 1e3])
    return BeamResult(x_crit=best_x, M_max=best_M, M_min=signed_min(best_x), reactions=reac, rows=rows)


# =========================================================================== sizing
@dataclass
class ShaftSizing:
    material: Material
    Se_prime: float
    ka: float
    kc: float
    kd: float
    ke: float
    iterations: list
    Kf: float
    Kfs: float
    d_fatigue: float
    d_yield: float
    d_twist: float
    d_required: float
    d_std: float | None
    feasible: bool
    verify: dict | None
    mass_per_m: float | None
    cost_index: float | None


@dataclass
class Loads:
    Mm: float   # N.mm (>= 0 after abs, sign irrelevant for DE)
    Ma: float
    Tm: float
    Ta: float

    @property
    def M_peak(self) -> float:
        return abs(self.Mm) + self.Ma

    @property
    def T_peak(self) -> float:
        return abs(self.Tm) + self.Ta


def _notch_factors(inp: ShaftInput, Sut: float, d: float) -> tuple[float, float, float, float]:
    _, Kt, Kts, r_over_d = inp.notch_data()
    r = r_over_d * d
    q = fat.notch_sensitivity(Sut, r) if Kt > 1.0 else 1.0
    qs = fat.notch_sensitivity(Sut, r, torsion=True) if Kts > 1.0 else 1.0
    return q, qs, fat.fatigue_factor(Kt, q), fat.fatigue_factor(Kts, qs)


def verify_diameter(inp: ShaftInput, mat: Material, L: Loads, d: float, base_Se: float) -> dict:
    """Stresses, factors of safety and twist for a given diameter."""
    kb = fat.size_factor(d, inp.rotating)
    q, qs, Kf, Kfs = _notch_factors(inp, mat.Sut, d)
    Se = base_Se * kb
    c_b = 32.0 / (math.pi * d ** 3)
    c_t = 16.0 / (math.pi * d ** 3)
    sa, sm = Kf * c_b * L.Ma, Kf * c_b * abs(L.Mm)
    ta, tm = Kfs * c_t * L.Ta, Kfs * c_t * abs(L.Tm)
    sa_vm = math.sqrt(sa ** 2 + 3 * ta ** 2)
    sm_vm = math.sqrt(sm ** 2 + 3 * tm ** 2)
    n_f = fat.fos_fluctuating(sa_vm, sm_vm, Se, mat.Sut, mat.Syt, inp.criterion)
    s_max = math.sqrt((sa + sm) ** 2 + 3 * (ta + tm) ** 2)
    n_y = mat.Syt / s_max if s_max > 0 else math.inf
    J = math.pi * d ** 4 / 32.0
    theta = L.T_peak * inp.twist_length / (mat.G * J)
    return dict(d=d, kb=kb, q=q, qs=qs, Kf=Kf, Kfs=Kfs, Se=Se, sigma_a=sa, sigma_m=sm, tau_a=ta, tau_m=tm,
                sigma_a_vm=sa_vm, sigma_m_vm=sm_vm, sigma_max_vm=s_max, n_f=n_f, n_y=n_y,
                theta_deg=math.degrees(theta))


def size_for_material(inp: ShaftInput, mat: Material, L: Loads, db: Database) -> ShaftSizing:
    n = inp.fos
    _, Kt, Kts, _ = inp.notch_data()
    Se_prime = fat.endurance_limit_specimen(mat.Sut)
    ka = fat.surface_factor(mat.Sut, inp.surface)
    kc = 1.0   # combined loading is handled through von Mises stresses
    kd = fat.temperature_factor(inp.temperature)
    ke = fat.reliability_factor(inp.reliability)
    base_Se = Se_prime * ka * kc * kd * ke          # Se without kb

    # --- fatigue diameter: start with kb = 1 and q = 1 (Kf = Kt), then iterate
    iterations = []
    d = fat.de_shaft_diameter(n, Kt, Kts, L.Ma, abs(L.Mm), L.Ta, abs(L.Tm), base_Se,
                              mat.Sut, mat.Syt, inp.criterion)
    Kf, Kfs = Kt, Kts
    if d > 0:
        for i in range(1, 51):
            kb = fat.size_factor(d, inp.rotating)
            q, qs, Kf, Kfs = _notch_factors(inp, mat.Sut, d)
            Se = base_Se * kb
            d_new = fat.de_shaft_diameter(n, Kf, Kfs, L.Ma, abs(L.Mm), L.Ta, abs(L.Tm), Se,
                                          mat.Sut, mat.Syt, inp.criterion)
            iterations.append([i, d, kb, q, qs, Kf, Kfs, Se, d_new])
            converged = abs(d_new - d) < 1e-3
            d = d_new
            if converged:
                break
    d_fatigue = d

    # --- first-cycle yield (peak von Mises stress, Kf applied conservatively)
    peak = math.sqrt(4 * (Kf * L.M_peak) ** 2 + 3 * (Kfs * L.T_peak) ** 2)
    d_yield = (16.0 * n * peak / (math.pi * mat.Syt)) ** (1 / 3) if peak > 0 else 0.0

    # --- torsional rigidity
    theta_allow = math.radians(inp.twist_allow_deg)
    d_twist = ((32.0 * L.T_peak * inp.twist_length) / (math.pi * mat.G * theta_allow)) ** 0.25 \
        if L.T_peak > 0 else 0.0

    d_req = max(d_fatigue, d_yield, d_twist)
    d_std = db.standard_shaft(d_req)
    feasible = d_std is not None and d_std <= inp.d_max + 1e-9
    verify = verify_diameter(inp, mat, L, d_std, base_Se) if d_std else None
    if d_std:
        mass = mat.density * math.pi / 4 * (d_std / 1000.0) ** 2   # kg per metre of shaft
        cost = mass * mat.rel_cost
    else:
        mass = cost = None
    return ShaftSizing(material=mat, Se_prime=Se_prime, ka=ka, kc=kc, kd=kd, ke=ke, iterations=iterations,
                       Kf=Kf, Kfs=Kfs, d_fatigue=d_fatigue, d_yield=d_yield, d_twist=d_twist,
                       d_required=d_req, d_std=d_std, feasible=feasible, verify=verify,
                       mass_per_m=mass, cost_index=cost)


# =========================================================================== main pipeline
@dataclass
class ShaftResult:
    feasible: bool
    d: float | None
    material: Material
    sizing: ShaftSizing
    candidates: list[ShaftSizing]
    loads: Loads
    report: Report

    @property
    def summary(self) -> str:
        if self.d is None:
            return "No standard shaft found"
        state = "" if self.feasible else "  (DOES NOT satisfy all constraints)"
        return f"Standard shaft: diameter {self.d:g} mm, {self.material.label}{state}"


def design_shaft(inp: ShaftInput, db: Database | None = None) -> ShaftResult:
    db = db or get_db()
    inp.validate(db)
    rep = Report("CODING 1 - DESIGN OF A POWER TRANSMISSION SHAFT (FLUCTUATING LOADS)")
    crit_name = fat.FAILURE_CRITERIA[inp.criterion]
    notch_label, Kt, Kts, r_over_d = inp.notch_data()

    # ------------------------------------------------------------------ step 0: inputs
    rep.heading("Step 0 - Input data")
    rows = []
    if inp.bm_mode == "direct":
        rows += [["Bending moment, max / min", f"{num(inp.M_max)} / {num(inp.M_min)} N.m"]]
    else:
        rows += [["Shaft configuration", f"simply supported, bearings at x = 0 and x = {num(inp.span)} mm"]]
        for ld in inp.loads:
            rows.append([f"  {ld.name} at x = {num(ld.x)} mm",
                         f"Fv {num(ld.Fv_min)}..{num(ld.Fv_max)} N, Fh {num(ld.Fh_min)}..{num(ld.Fh_max)} N"])
    rows += [
        ["Bending stress cycle", "fully reversed (rotating shaft)" if inp.rotating else "as given by Mmax / Mmin"],
        ["Torque, max / min", f"{num(inp.T_max)} / {num(inp.T_min)} N.m"],
        ["Factor of safety n", num(inp.fos)],
        ["Fatigue criterion", crit_name],
        ["Surface finish", inp.surface],
        ["Reliability", f"{inp.reliability:g} %"],
        ["Operating temperature", f"{inp.temperature:g} C"],
        ["Stress raiser at critical section", notch_label],
        ["Constraint: max shaft diameter", f"{num(inp.d_max)} mm"],
        ["Constraint: max angle of twist", f"{num(inp.twist_allow_deg)} deg over {num(inp.twist_length)} mm"],
        ["Material", "automatic selection" if inp.material == "auto" else db.material(inp.material).label],
    ]
    rep.table(["Item", "Value"], rows)

    # ------------------------------------------------------------------ step 1: bending moment
    rep.heading("Step 1 - Bending moment at the critical section")
    if inp.bm_mode == "beam":
        beam = analyse_beam(inp.span, inp.loads)
        for case in ("max", "min"):
            RAv, RBv, RAh, RBh = beam.reactions[case]
            rep.text(f"{case.upper()} load case reactions: vertical RA = {num(RAv)} N, RB = {num(RBv)} N; "
                     f"horizontal RA = {num(RAh)} N, RB = {num(RBh)} N")
        rep.text("Resultant moment M = sqrt(Mv^2 + Mh^2). Bending-moment values (N.m):")
        rep.table(["x (mm)", "Mv (max case)", "Mh (max case)", "M resultant (max case)", "M (min case)"],
                  beam.rows)
        rep.calc("Critical section x (largest M)", beam.x_crit, "mm from bearing A")
        M_max, M_min = beam.M_max, beam.M_min
        rep.text("The stress raiser is assumed to sit at this section (conservative).")
    else:
        M_max, M_min = inp.M_max * 1e3, inp.M_min * 1e3
    rep.calc("Mmax", M_max / 1e3, "N.m")
    rep.calc("Mmin", M_min / 1e3, "N.m")

    # ------------------------------------------------------------------ step 2: components
    rep.heading("Step 2 - Mean and alternating components")
    if inp.rotating:
        Ma = max(abs(M_max), abs(M_min))
        Mm = 0.0
        rep.text("Rotating shaft with stationary loads: every fibre sees +M and -M each revolution,")
        rep.text("so bending is completely reversed: Mm = 0, Ma = max|M|.")
    else:
        Mm = (M_max + M_min) / 2.0
        Ma = abs(M_max - M_min) / 2.0
    T_max, T_min = inp.T_max * 1e3, inp.T_min * 1e3
    Tm, Ta = (T_max + T_min) / 2.0, abs(T_max - T_min) / 2.0
    L = Loads(Mm=Mm, Ma=Ma, Tm=Tm, Ta=Ta)
    rep.calc("Mean bending moment Mm", Mm / 1e3, "N.m", "(Mmax + Mmin)/2" if not inp.rotating else "")
    rep.calc("Alternating bending moment Ma", Ma / 1e3, "N.m", "(Mmax - Mmin)/2" if not inp.rotating else "")
    rep.calc("Mean torque Tm", Tm / 1e3, "N.m", "(Tmax + Tmin)/2")
    rep.calc("Alternating torque Ta", Ta / 1e3, "N.m", "(Tmax - Tmin)/2")

    # ------------------------------------------------------------------ step 3: material
    rep.heading("Step 3 - Material selection (materials database)")
    if inp.material == "auto":
        candidates = [size_for_material(inp, m, L, db) for m in db.materials_for("shaft")]
        rep.text("Every shaft material in the database is sized with the same procedure (steps 4-9).")
        rep.text("Feasible = standard diameter <= d_max. Cost index = relative cost x kg per metre.")
        table = []
        for c in sorted(candidates, key=lambda c: (not c.feasible, c.cost_index or math.inf)):
            m = c.material
            table.append([m.id, m.is_equiv, m.Sut, m.Syt, c.d_fatigue, c.d_yield, c.d_twist,
                          num(c.d_std) if c.d_std else "> 500", "yes" if c.feasible else "no",
                          num(c.cost_index) if c.cost_index else "-"])
        rep.table(["Material", "IS", "Sut", "Syt", "d fatigue", "d yield", "d twist", "d std", "Feasible",
                   "Cost idx"], table)
        feasible = [c for c in candidates if c.feasible]
        if feasible:
            # cheapest first; on a tie prefer the larger factor of safety
            chosen = min(feasible, key=lambda c: (round(c.cost_index, 6),
                                                  -min(c.verify["n_f"], c.verify["n_y"])))
            rep.text(f"Selected: {chosen.material.label} - cheapest feasible option.")
        else:
            chosen = min(candidates, key=lambda c: c.d_required)
            rep.text("No material meets every constraint. Showing the material that gives the smallest shaft.")
    else:
        chosen = size_for_material(inp, db.material(inp.material), L, db)
        candidates = [chosen]
    mat = chosen.material
    rep.table(["Property", "Value"], [
        ["Material", mat.label],
        ["Ultimate tensile strength Sut", f"{num(mat.Sut)} MPa"],
        ["Yield strength Syt", f"{num(mat.Syt)} MPa"],
        ["Modulus of elasticity E", f"{num(mat.E / 1000)} GPa"],
        ["Modulus of rigidity G", f"{num(mat.G / 1000)} GPa"],
        ["Density", f"{num(mat.density)} kg/m^3"],
        ["Elongation / hardness", f"{num(mat.elongation)} % / {num(mat.BHN)} BHN"],
    ])

    # ------------------------------------------------------------------ step 4: endurance limit
    s = chosen
    rep.heading("Step 4 - Endurance limit (Marin equation  Se = ka kb kc kd ke Se')")
    rep.calc("Specimen endurance limit Se'", s.Se_prime, "MPa", "0.5 x Sut" if mat.Sut <= 1400 else "700 (Sut > 1400)")
    a, b = fat.SURFACE_FINISH[inp.surface]
    rep.calc(f"Surface factor ka ({inp.surface})", s.ka, "", f"{a} x Sut^({b})")
    rep.calc("Size factor kb", "depends on d - see iteration in step 6", "")
    rep.calc("Load factor kc (combined, von Mises)", s.kc)
    rep.calc(f"Temperature factor kd ({inp.temperature:g} C)", s.kd)
    rep.calc(f"Reliability factor ke ({inp.reliability:g} %)", s.ke)
    rep.calc("Se without kb", s.Se_prime * s.ka * s.kc * s.kd * s.ke, "MPa", "ka kc kd ke Se'")

    # ------------------------------------------------------------------ step 5: notch
    rep.heading("Step 5 - Stress concentration at the critical section")
    rep.text(notch_label)
    rep.calc("Theoretical factor, bending Kt", Kt)
    rep.calc("Theoretical factor, torsion Kts", Kts)
    rep.calc("Notch radius ratio r/d", r_over_d)
    rep.text("Notch sensitivity (Neuber): q = 1/(1 + sqrt(a)/sqrt(r)),  Kf = 1 + q(Kt - 1)")
    rep.text("q depends on r = (r/d) x d, so Kf and Kfs are updated in the iteration below.")

    # ------------------------------------------------------------------ step 6: fatigue diameter
    rep.heading(f"Step 6 - Fatigue diameter ({crit_name})")
    rep.text("A = sqrt(4(Kf Ma)^2 + 3(Kfs Ta)^2),  B = sqrt(4(Kf Mm)^2 + 3(Kfs Tm)^2)")
    rep.text(fat.DE_EQUATION_TEXT[inp.criterion])
    rep.text("Start with kb = 1 and Kf = Kt, then repeat until d stops changing:")
    if s.iterations:
        rep.table(["Iter", "d assumed (mm)", "kb", "q", "qs", "Kf", "Kfs", "Se (MPa)", "d new (mm)"],
                  s.iterations)
    rep.calc("Fatigue diameter d_f", s.d_fatigue, "mm")

    # ------------------------------------------------------------------ step 7: yield
    rep.heading("Step 7 - First-cycle yield check (static, peak load)")
    rep.text("sigma'_max = (16/(pi d^3)) sqrt(4(Kf Mmax)^2 + 3(Kfs Tmax)^2) <= Syt / n")
    rep.calc("Peak bending moment |Mm| + Ma", L.M_peak / 1e3, "N.m")
    rep.calc("Peak torque |Tm| + Ta", L.T_peak / 1e3, "N.m")
    rep.calc("Yield diameter d_y", s.d_yield, "mm")

    # ------------------------------------------------------------------ step 8: twist
    rep.heading("Step 8 - Torsional rigidity (angle of twist constraint)")
    rep.text("theta = T L / (G J),  J = pi d^4 / 32   =>   d = [32 T L / (pi G theta)]^(1/4)")
    rep.calc("Allowable twist theta", math.radians(inp.twist_allow_deg), "rad", f"{inp.twist_allow_deg:g} deg")
    rep.calc("Rigidity diameter d_t", s.d_twist, "mm")

    # ------------------------------------------------------------------ step 9: standard size
    rep.heading("Step 9 - Required diameter, standard size and diameter constraint")
    rep.calc("Required d = max(d_f, d_y, d_t)", s.d_required, "mm")
    governing = max([("fatigue", s.d_fatigue), ("yield", s.d_yield), ("twist", s.d_twist)], key=lambda t: t[1])[0]
    rep.text(f"Governing requirement: {governing}")
    if s.d_std:
        rep.calc("Next standard shaft diameter", s.d_std, "mm")
    rep.check(bool(s.d_std) and s.d_std <= inp.d_max, f"d = {num(s.d_std)} mm <= d_max = {num(inp.d_max)} mm")

    # ------------------------------------------------------------------ step 10: verification
    rep.heading("Step 10 - Verification of the standard shaft")
    v = s.verify
    if v:
        rep.calc("kb, Kf, Kfs at final d", f"{num(v['kb'])}, {num(v['Kf'])}, {num(v['Kfs'])}")
        rep.calc("Endurance limit Se", v["Se"], "MPa")
        rep.calc("Alternating bending stress sigma_a", v["sigma_a"], "MPa", "Kf 32 Ma/(pi d^3)")
        rep.calc("Mean bending stress sigma_m", v["sigma_m"], "MPa", "Kf 32 Mm/(pi d^3)")
        rep.calc("Alternating shear stress tau_a", v["tau_a"], "MPa", "Kfs 16 Ta/(pi d^3)")
        rep.calc("Mean shear stress tau_m", v["tau_m"], "MPa", "Kfs 16 Tm/(pi d^3)")
        rep.calc("von Mises alternating sigma'_a", v["sigma_a_vm"], "MPa", "sqrt(sa^2 + 3 ta^2)")
        rep.calc("von Mises mean sigma'_m", v["sigma_m_vm"], "MPa", "sqrt(sm^2 + 3 tm^2)")
        rep.calc(f"Fatigue factor of safety ({crit_name})", v["n_f"])
        rep.calc("Yield factor of safety Syt/sigma'_max", v["n_y"])
        rep.calc("Angle of twist", v["theta_deg"], "deg")
        rep.check(v["n_f"] >= inp.fos - 1e-9, f"Fatigue FoS {num(v['n_f'])} >= required {num(inp.fos)}")
        rep.check(v["n_y"] >= inp.fos - 1e-9, f"Yield FoS {num(v['n_y'])} >= required {num(inp.fos)}")
        rep.check(v["theta_deg"] <= inp.twist_allow_deg + 1e-9,
                  f"Twist {num(v['theta_deg'])} deg <= allowed {num(inp.twist_allow_deg)} deg")
        rep.check(v["d"] <= inp.d_max, f"Diameter {num(v['d'])} mm <= d_max {num(inp.d_max)} mm")

    # ------------------------------------------------------------------ output
    result = ShaftResult(feasible=s.feasible, d=s.d_std, material=mat, sizing=s, candidates=candidates,
                         loads=L, report=rep)
    rep.heading("FINAL OUTPUT")
    rep.text(result.summary)
    if s.d_std:
        rep.table(["Output", "Value"], [
            ["Shaft diameter (standard)", f"{num(s.d_std)} mm"],
            ["Material", mat.label],
            ["Sut / Syt", f"{num(mat.Sut)} / {num(mat.Syt)} MPa"],
            ["Fatigue factor of safety", num(v["n_f"])],
            ["Yield factor of safety", num(v["n_y"])],
            ["Angle of twist", f"{num(v['theta_deg'])} deg over {num(inp.twist_length)} mm"],
            ["Mass per metre", f"{num(s.mass_per_m)} kg/m"],
            ["Governing requirement", governing],
        ])
    if not s.feasible:
        rep.text("Suggestions: choose a stronger material, relax the twist limit, or allow a larger diameter.")
    return result
