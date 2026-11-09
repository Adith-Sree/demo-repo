"""CODING 3 - Design of a bolted joint under fluctuating load (axial or shear).

Axial (tension) joint pipeline - Shigley Ch. 8 approach
    1. External load per bolt (Pmax, Pmin)
    2. For every ISO property class and every ISO metric size (smallest first):
         a. bolt length from the grip stack-up, threaded / unthreaded length in the grip
         b. bolt stiffness kb, member stiffness km (30 deg frustum), joint constant C
         c. preload Fi = 0.75 Fp (reusable) or 0.90 Fp (permanent), Fp = Sp At
         d. stresses sigma_i, sigma_a, sigma_m
         e. Goodman fatigue FoS, yield (proof) FoS, load factor, separation factor
       The first size that meets every requirement is that class's answer.
    3. Pick the cheapest class/size combination and report the standard bolt.

Shear joint pipeline
    * friction-grip (slip-critical): preload x friction must carry the load;
      bolts only see the steady preload, so they are not in fatigue.
    * bearing type: fluctuating shear in the bolt (Goodman on von Mises stresses),
      static shear, and bearing on the bolt and on the plates.

Internal units: N, mm, MPa. Loads are entered in kN.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields

from . import fatigue as fat
from .database import BoltClass, Database, Material, ThreadSize, get_db
from .report import Report, num

E_BOLT = 207_000.0   # MPa, steel bolts
PRELOAD_FRACTION = {"reusable": 0.75, "permanent": 0.90}


@dataclass
class BoltInput:
    load_type: str = "axial"        # axial | shear
    P_max: float = 0.0              # kN, total external load on the joint
    P_min: float = 0.0              # kN
    n_bolts: int = 4
    fos: float = 2.0
    bolt_class: str = "auto"        # "auto" or an ISO 898-1 class such as "8.8"
    bolt_size: str = "auto"         # "auto" or a designation such as "M12" / "M12x1.25"
    series: str = "coarse"          # coarse | fine
    first_choice_only: bool = True  # only ISO 261 first-choice sizes
    preload: str = "reusable"       # reusable | permanent
    nut_factor: float = 0.2         # torque coefficient K (T = K Fi d)
    member_material: str = "1020-HR"
    grip: float = 30.0              # mm, total thickness of the clamped plates
    washers: bool = True            # one plain washer under the nut
    # shear joints only
    joint_type: str = "bearing"     # bearing | friction
    shear_planes: int = 1
    plate_thickness: float = 0.0    # mm, thinnest plate in bearing (0 -> grip / (planes + 1))
    mu: float = 0.30                # friction coefficient at the faying surfaces
    threads_in_shear_plane: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "BoltInput":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known - {"_comment", "module"}
        if unknown:
            raise ValueError(f"Unknown bolt input field(s): {', '.join(sorted(unknown))}")
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["module"] = "bolt"
        return d

    def validate(self, db: Database) -> None:
        errs = []
        if self.load_type not in ("axial", "shear"):
            errs.append("load_type must be 'axial' or 'shear'")
        if self.P_max <= 0:
            errs.append("P_max must be > 0")
        if self.load_type == "axial" and not 0 <= self.P_min <= self.P_max:
            errs.append("axial joint: need 0 <= P_min <= P_max (tension joint)")
        if self.load_type == "shear" and not -self.P_max <= self.P_min <= self.P_max:
            errs.append("shear joint: need -P_max <= P_min <= P_max")
        if self.n_bolts < 1:
            errs.append("n_bolts must be >= 1")
        if self.fos <= 0:
            errs.append("factor of safety must be > 0")
        if self.bolt_class != "auto" and self.bolt_class not in db.bolt_class_names():
            errs.append(f"bolt_class must be 'auto' or one of {db.bolt_class_names()}")
        if self.series not in ("coarse", "fine"):
            errs.append("series must be 'coarse' or 'fine'")
        if self.bolt_size != "auto":
            try:
                db.thread_by_name(self.bolt_size)
            except KeyError as exc:
                errs.append(str(exc))
        if self.preload not in PRELOAD_FRACTION:
            errs.append("preload must be 'reusable' or 'permanent'")
        if self.member_material not in db.materials:
            errs.append(f"unknown member material '{self.member_material}'")
        if self.grip <= 0:
            errs.append("grip (total plate thickness) must be > 0")
        if self.joint_type not in ("bearing", "friction"):
            errs.append("joint_type must be 'bearing' or 'friction'")
        if self.shear_planes < 1:
            errs.append("shear_planes must be >= 1")
        if not 0 < self.mu < 1:
            errs.append("friction coefficient must be between 0 and 1")
        if errs:
            raise ValueError("Invalid bolt input:\n  - " + "\n  - ".join(errs))


# --------------------------------------------------------------------------- bolt data
def bolt_endurance(cls: BoltClass) -> tuple[float, str]:
    """Fully corrected endurance strength of a rolled-thread bolt.

    Uses Shigley Table 8-17 where available. Otherwise it is estimated as
    Se = 0.5 Sut * ka(machined) * kc(axial = 0.85) / Kf, with Kf = 2.2 for rolled
    threads of classes up to 5.8 (Shigley Table 8-16).
    """
    if cls.Se_table is not None:
        return cls.Se_table, "Shigley Table 8-17"
    ka = fat.surface_factor(cls.Sut, "machined")
    Se = 0.5 * cls.Sut * ka * 0.85 / 2.2
    return Se, "estimated: 0.5 Sut ka kc / Kf, Kf = 2.2"


def thread_length(d: float, L: float) -> float:
    """Thread length b of a partially threaded bolt (ISO 4014)."""
    if L <= 125:
        return 2 * d + 6
    if L <= 200:
        return 2 * d + 12
    return 2 * d + 25


def member_stiffness(E: float, d: float, l: float) -> float:
    """Two identical-material members, 30 deg pressure frustum (Shigley Eq. 8-23)."""
    return 0.5774 * math.pi * E * d / (2 * math.log(5 * (0.5774 * l + 0.5 * d) / (0.5774 * l + 2.5 * d)))


def standard_designation(th: ThreadSize, L: float, fully_threaded: bool, cls_name: str) -> str:
    if th.series == "coarse":
        std = "ISO 4017 hex screw (fully threaded)" if fully_threaded else "ISO 4014 hex bolt"
        nut = "ISO 4032"
    else:
        std = "ISO 8676 hex screw, fine pitch (fully threaded)" if fully_threaded else "ISO 8765 hex bolt, fine pitch"
        nut = "ISO 8673"
    return (f"{std} {th.full_designation} x {num(L)} - {cls_name}, "
            f"with {nut} hex nut and ISO 7089 washer")


# --------------------------------------------------------------------------- analysis
def analyse(inp: BoltInput, th: ThreadSize, cls: BoltClass, member: Material, db: Database) -> dict:
    """All quantities for one bolt size + property class."""
    N = inp.n_bolts
    f = PRELOAD_FRACTION[inp.preload]
    At, Ad = th.At, th.Ad
    Se, Se_src = bolt_endurance(cls)
    washer = th.washer_thickness if inp.washers else 0.0
    l = inp.grip + washer                           # grip length incl. washer
    L_need = l + th.nut_height + 2 * th.P           # at least two threads past the nut
    L = db.round_up(L_need, db.bolt_lengths) or float(math.ceil(L_need))
    LT = thread_length(th.d, L)
    ld = min(max(0.0, L - LT), l)                   # unthreaded shank in the grip
    lt = l - ld                                     # threaded part in the grip
    Fp = cls.Sp * At
    Fi = f * Fp
    r = dict(th=th, cls=cls, Se=Se, Se_src=Se_src, l=l, L_need=L_need, L=L, LT=LT, ld=ld, lt=lt,
             fully_threaded=L - LT < th.P, Fp=Fp, Fi=Fi, f=f, torque=inp.nut_factor * Fi * th.d)

    if inp.load_type == "axial":
        P1, P2 = inp.P_max * 1e3 / N, inp.P_min * 1e3 / N
        kb = Ad * At * E_BOLT / (Ad * lt + At * ld)
        km = member_stiffness(member.E, th.d, l)
        C = kb / (kb + km)
        s_i = Fi / At
        s_a = C * (P1 - P2) / (2 * At)
        s_m = s_i + C * (P1 + P2) / (2 * At)
        denom = cls.Sut * s_a + Se * (s_m - s_i)
        n_f = Se * (cls.Sut - s_i) / denom if denom > 0 else math.inf
        n_p = cls.Sp * At / (C * P1 + Fi)
        n_L = (cls.Sp * At - Fi) / (C * P1)
        n_0 = Fi / (P1 * (1 - C))
        reqs = {"Fatigue (Goodman) n_f": (n_f, inp.fos), "Load factor n_L": (n_L, inp.fos),
                "Separation n_0": (n_0, inp.fos), "Yield / proof n_p": (n_p, 1.0)}
        r.update(P1=P1, P2=P2, kb=kb, km=km, C=C, s_i=s_i, s_a=s_a, s_m=s_m,
                 n_f=n_f, n_p=n_p, n_L=n_L, n_0=n_0, reqs=reqs)
    else:
        m = inp.shear_planes
        t = inp.plate_thickness or inp.grip / (m + 1)
        r["t"] = t
        if inp.joint_type == "friction":
            slip = N * inp.mu * m * Fi
            n_slip = slip / (inp.P_max * 1e3)
            n_p = cls.Sp * At / Fi
            reqs = {"Slip resistance n_slip": (n_slip, inp.fos), "Yield / proof n_p": (n_p, 1.0)}
            r.update(slip=slip, n_slip=n_slip, n_p=n_p, reqs=reqs)
        else:
            A = th.Ar if inp.threads_in_shear_plane else Ad
            V1 = inp.P_max * 1e3 / (N * m)
            V2 = inp.P_min * 1e3 / (N * m)
            t1, t2 = V1 / A, V2 / A
            t_a, t_m = abs(t1 - t2) / 2, (t1 + t2) / 2
            s_a, s_m = math.sqrt(3) * t_a, math.sqrt(3) * abs(t_m)
            n_f = fat.fos_fluctuating(s_a, s_m, Se, cls.Sut, cls.Sy, "goodman")
            t_peak = max(abs(t1), abs(t2))
            n_s = 0.577 * cls.Sp / t_peak
            P_peak = max(abs(inp.P_max), abs(inp.P_min)) * 1e3
            s_b = P_peak / (N * th.d * t)
            n_bb = cls.Sp / s_b
            n_bm = member.Sy_or_Sut / s_b
            reqs = {"Fatigue (Goodman) n_f": (n_f, inp.fos), "Static shear n_s": (n_s, inp.fos),
                    "Bearing on bolt": (n_bb, inp.fos), "Bearing on plate": (n_bm, inp.fos)}
            r.update(A=A, V1=V1, V2=V2, tau_max=t1, tau_min=t2, tau_a=t_a, tau_m=t_m, s_a=s_a, s_m=s_m,
                     n_f=n_f, n_s=n_s, s_b=s_b, n_bb=n_bb, n_bm=n_bm, reqs=reqs)
    r["ok"] = all(val >= need - 1e-9 for val, need in r["reqs"].values())
    r["cost"] = cls.rel_cost * th.d ** 2 * L / 1000.0       # proportional to bolt volume x class cost
    return r


@dataclass
class BoltResult:
    ok: bool
    chosen: dict | None
    candidates: list[dict]
    designation: str
    report: Report

    @property
    def summary(self) -> str:
        return self.designation if self.ok else f"{self.designation}  (DOES NOT satisfy all requirements)"


# --------------------------------------------------------------------------- pipeline
def design_bolted_joint(inp: BoltInput, db: Database | None = None) -> BoltResult:
    db = db or get_db()
    inp.validate(db)
    member = db.material(inp.member_material)
    rep = Report(f"CODING 3 - DESIGN OF A BOLTED JOINT UNDER FLUCTUATING {inp.load_type.upper()} LOAD")

    # ------------------------------------------------------------------ step 0
    rep.heading("Step 0 - Input data")
    rows = [
        ["Load type", inp.load_type + (f" ({inp.joint_type} type)" if inp.load_type == "shear" else "")],
        ["Total external load, max / min", f"{num(inp.P_max)} / {num(inp.P_min)} kN"],
        ["Number of bolts", str(inp.n_bolts)],
        ["Required factor of safety", num(inp.fos)],
        ["Property class", inp.bolt_class],
        ["Bolt size", inp.bolt_size + f" ({inp.series} series"
         + (", first-choice sizes only)" if inp.first_choice_only else ")")],
        ["Preload", f"{inp.preload} joint: Fi = {PRELOAD_FRACTION[inp.preload]} x proof load"],
        ["Clamped plates (grip)", f"{num(inp.grip)} mm of {member.label}"],
        ["Washer under nut", "yes" if inp.washers else "no"],
    ]
    if inp.load_type == "shear":
        rows += [["Shear planes", str(inp.shear_planes)],
                 ["Friction coefficient", num(inp.mu)],
                 ["Threads in shear plane", "yes" if inp.threads_in_shear_plane else "no"]]
    rep.table(["Item", "Value"], rows)

    # ------------------------------------------------------------------ step 1
    rep.heading("Step 1 - Load shared by each bolt")
    rep.calc("Pmax per bolt", inp.P_max * 1e3 / inp.n_bolts, "N", "Pmax / N")
    rep.calc("Pmin per bolt", inp.P_min * 1e3 / inp.n_bolts, "N", "Pmin / N")
    if inp.load_type == "shear":
        rep.text(f"Shear per bolt per shear plane = P / (N x {inp.shear_planes})")

    # ------------------------------------------------------------------ step 2: search the database
    rep.heading("Step 2 - Bolt selection from the ISO metric thread database")
    class_names = db.bolt_class_names() if inp.bolt_class == "auto" else [inp.bolt_class]
    if inp.bolt_size == "auto":
        sizes = db.thread_sizes(inp.series, inp.first_choice_only)
    else:
        sizes = [db.thread_by_name(inp.bolt_size)]
    candidates = []
    for cname in class_names:
        best = None
        for th in sizes:
            cls = db.bolt_class(cname, th.d)
            if cls is None:
                continue
            res = analyse(inp, th, cls, member, db)
            best = res
            if res["ok"]:
                break
        if best is not None:
            candidates.append(best)
    if not candidates:
        rep.text("No property class is made in the requested size.")
        return BoltResult(False, None, [], "no bolt found", rep)

    rep.text("For each property class, sizes are tried from smallest up; the first that meets every")
    rep.text("requirement is listed. Cost index = class cost factor x d^2 x L (relative).")
    req_names = list(candidates[0]["reqs"])
    rows = []
    for c in candidates:
        rows.append([c["cls"].name, c["th"].designation, num(c["L"])]
                    + [num(c["reqs"][k][0]) for k in req_names]
                    + ["yes" if c["ok"] else "no", num(c["cost"])])
    rep.table(["Class", "Size", "L (mm)"] + req_names + ["Meets all", "Cost idx"], rows)
    passing = [c for c in candidates if c["ok"]]
    if passing:
        chosen = min(passing, key=lambda c: (c["cost"], c["cls"].Sp))
        rep.text(f"Selected: {chosen['th'].designation} class {chosen['cls'].name} (lowest cost index that passes).")
    else:
        chosen = max(candidates, key=lambda c: min(v / need for v, need in c["reqs"].values()))
        rep.text("No combination meets every requirement. The best attempt is shown below.")
        rep.text("Try more bolts, a higher property class, or allow second-choice / larger sizes.")

    th, cls = chosen["th"], chosen["cls"]

    # ------------------------------------------------------------------ step 3: thread data
    rep.heading(f"Step 3 - Thread and property-class data: {th.full_designation}, class {cls.name}")
    rep.calc("Nominal diameter d", th.d, "mm")
    rep.calc("Pitch P", th.P, "mm")
    rep.calc("Pitch diameter d2", th.d2, "mm", "d - 0.6495 P")
    rep.calc("Minor diameter d3", th.d3, "mm", "d - 1.2269 P")
    rep.calc("Tensile-stress area At", th.At, "mm^2", "(pi/4) ((d2 + d3)/2)^2")
    rep.calc("Root area Ar", th.Ar, "mm^2", "(pi/4) d3^2")
    rep.calc("Shank area Ad", th.Ad, "mm^2", "(pi/4) d^2")
    rep.calc("Proof strength Sp", cls.Sp, "MPa")
    rep.calc("Tensile strength Sut", cls.Sut, "MPa")
    rep.calc("Yield strength Sy", cls.Sy, "MPa")
    rep.calc("Endurance strength Se", chosen["Se"], "MPa", chosen["Se_src"])

    # ------------------------------------------------------------------ step 4: length
    rep.heading("Step 4 - Bolt length")
    rep.calc("Grip l = plates + washer", chosen["l"], "mm")
    rep.calc("Length needed  l + nut height + 2P", chosen["L_need"], "mm")
    rep.calc("Standard length L", chosen["L"], "mm")
    rep.calc("Thread length LT (ISO 4014)", chosen["LT"], "mm", "2d + 6 (L <= 125)" if chosen["L"] <= 125 else "")
    rep.calc("Unthreaded length in grip ld", chosen["ld"], "mm")
    rep.calc("Threaded length in grip lt", chosen["lt"], "mm")

    # ------------------------------------------------------------------ step 5: preload
    rep.heading("Step 5 - Preload and tightening torque")
    rep.calc("Proof load Fp", chosen["Fp"] / 1e3, "kN", "Sp At")
    rep.calc("Preload Fi", chosen["Fi"] / 1e3, "kN", f"{chosen['f']} Fp")
    rep.calc("Tightening torque", chosen["torque"] / 1e3, "N.m", f"K Fi d, K = {num(inp.nut_factor)}")

    # ------------------------------------------------------------------ step 6: stresses and FoS
    if inp.load_type == "axial":
        rep.heading("Step 6 - Joint stiffness")
        rep.calc("Bolt stiffness kb", chosen["kb"] / 1e3, "kN/mm", "Ad At E / (Ad lt + At ld)")
        rep.calc("Member stiffness km", chosen["km"] / 1e3, "kN/mm", "frustum, Em = " + num(member.E / 1e3) + " GPa")
        rep.calc("Joint constant C", chosen["C"], "", "kb / (kb + km)")
        rep.text("Only the fraction C of the external load reaches the bolt; the rest unloads the plates.")
        rep.heading("Step 7 - Stresses in the bolt")
        rep.calc("Preload stress sigma_i", chosen["s_i"], "MPa", "Fi / At")
        rep.calc("Alternating stress sigma_a", chosen["s_a"], "MPa", "C (Pmax - Pmin) / (2 At)")
        rep.calc("Mean stress sigma_m", chosen["s_m"], "MPa", "sigma_i + C (Pmax + Pmin) / (2 At)")
        rep.heading("Step 8 - Factors of safety")
        rep.calc("Fatigue, Goodman n_f", chosen["n_f"], "", "Se (Sut - si) / (Sut sa + Se (sm - si))")
        rep.calc("Yield (proof) n_p", chosen["n_p"], "", "Sp At / (C Pmax + Fi)")
        rep.calc("Load factor n_L", chosen["n_L"], "", "(Sp At - Fi) / (C Pmax)")
        rep.calc("Joint separation n_0", chosen["n_0"], "", "Fi / (Pmax (1 - C))")
    elif inp.joint_type == "friction":
        rep.heading("Step 6 - Friction-grip (slip-critical) joint")
        rep.calc("Slip resistance", chosen["slip"] / 1e3, "kN", f"N mu m Fi = {inp.n_bolts} x {num(inp.mu)} x "
                 f"{inp.shear_planes} x Fi")
        rep.calc("Slip factor of safety n_slip", chosen["n_slip"], "", "slip resistance / Pmax")
        rep.calc("Yield (proof) n_p", chosen["n_p"], "", "Sp At / Fi")
        rep.text("The load is carried by friction, so the bolt stress stays at the preload value:")
        rep.text("there is no fluctuating stress in the bolt and no fatigue check is needed.")
    else:
        rep.heading("Step 6 - Bearing-type joint: shear stresses in the bolt")
        rep.calc("Shear area", chosen["A"], "mm^2", "Ar (threads in plane)" if inp.threads_in_shear_plane else "Ad")
        rep.calc("tau_max / tau_min", f"{num(chosen['tau_max'])} / {num(chosen['tau_min'])}", "MPa")
        rep.calc("tau_a, tau_m", f"{num(chosen['tau_a'])}, {num(chosen['tau_m'])}", "MPa")
        rep.calc("von Mises sigma'_a, sigma'_m", f"{num(chosen['s_a'])}, {num(chosen['s_m'])}", "MPa",
                 "sqrt(3) tau")
        rep.heading("Step 7 - Factors of safety")
        rep.calc("Fatigue, Goodman n_f", chosen["n_f"], "", "1 / (s'a/Se + s'm/Sut)")
        rep.calc("Static shear n_s", chosen["n_s"], "", "0.577 Sp / tau_max")
        rep.calc("Bearing stress on bolt / plate", chosen["s_b"], "MPa", f"Pmax / (N d t), t = {num(chosen['t'])} mm")
        rep.calc("Bearing FoS, bolt", chosen["n_bb"], "", "Sp / sigma_b")
        rep.calc("Bearing FoS, plate", chosen["n_bm"], "", f"Sy(plate) / sigma_b, Sy = {num(member.Sy_or_Sut)}")
        rep.text("Se from the bolt table includes the thread notch effect, so it is conservative for a plain shank.")
    for name, (val, need) in chosen["reqs"].items():
        rep.check(val >= need - 1e-9, f"{name} = {num(val)} >= {num(need)}")

    # ------------------------------------------------------------------ output
    designation = standard_designation(th, chosen["L"], chosen["fully_threaded"], cls.name)
    result = BoltResult(chosen["ok"], chosen, candidates, designation, rep)
    rep.heading("FINAL OUTPUT - Standard bolt")
    rep.text(f"{inp.n_bolts} x {designation}")
    out_rows = [
        ["Thread", f"{th.full_designation} ({th.series})"],
        ["Property class", f"{cls.name}  (Sp {num(cls.Sp)}, Sut {num(cls.Sut)} MPa)"],
        ["Length", f"{num(chosen['L'])} mm"],
        ["Tensile-stress area", f"{num(th.At)} mm^2"],
        ["Nut height / across flats", f"{num(th.nut_height)} / {num(th.across_flats)} mm"],
        ["Preload / tightening torque", f"{num(chosen['Fi'] / 1e3)} kN / {num(chosen['torque'] / 1e3)} N.m"],
    ]
    out_rows += [[name, num(val)] for name, (val, _) in chosen["reqs"].items()]
    out_rows.append(["Meets all requirements", "YES" if chosen["ok"] else "NO"])
    rep.table(["Output", "Value"], out_rows)
    return result
