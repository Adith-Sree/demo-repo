"""Loads the JSON databases (materials, ISO threads, bolt classes, standard sizes).

Everything is converted to the program's internal units on load:
    length  -> mm
    force   -> N
    stress  -> MPa (= N/mm^2)
    modulus -> MPa (the JSON stores GPa)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- materials
@dataclass(frozen=True)
class Material:
    id: str
    name: str
    is_equiv: str
    category: str
    brittle: bool
    Sut: float          # MPa, ultimate tensile strength
    Syt: float | None   # MPa, tensile yield strength (None for brittle cast iron)
    E: float            # MPa
    G: float            # MPa
    density: float      # kg/m^3
    elongation: float   # %
    BHN: float
    rel_cost: float
    uses: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{self.name} ({self.is_equiv})"

    @property
    def Sy_or_Sut(self) -> float:
        """Yield strength, or the ultimate strength for brittle materials with no yield point."""
        return self.Syt if self.Syt is not None else self.Sut


@dataclass(frozen=True)
class ThreadSize:
    d: float              # nominal (major) diameter, mm
    P: float              # pitch, mm
    series: str           # "coarse" | "fine"
    first_choice: bool
    nut_height: float     # ISO 4032 nut height m, mm
    across_flats: float   # width across flats s, mm
    washer_thickness: float

    # ISO 724 basic-profile relations
    @property
    def d2(self) -> float:
        """Pitch diameter."""
        return self.d - 0.649519 * self.P

    @property
    def d3(self) -> float:
        """Minor (root) diameter of the external (bolt) thread."""
        return self.d - 1.226869 * self.P

    @property
    def At(self) -> float:
        """Tensile-stress area, mm^2 (ISO 898-1)."""
        return math.pi / 4.0 * ((self.d2 + self.d3) / 2.0) ** 2

    @property
    def Ar(self) -> float:
        """Minor-diameter (root) area, mm^2."""
        return math.pi / 4.0 * self.d3 ** 2

    @property
    def Ad(self) -> float:
        """Nominal (shank) area, mm^2."""
        return math.pi / 4.0 * self.d ** 2

    @property
    def designation(self) -> str:
        d = f"{self.d:g}"
        return f"M{d}" if self.series == "coarse" else f"M{d}x{self.P:g}"

    @property
    def full_designation(self) -> str:
        return f"M{self.d:g} x {self.P:g}"


@dataclass(frozen=True)
class BoltClass:
    name: str
    d_min: float
    d_max: float
    Sp: float
    Sut: float
    Sy: float
    Se_table: float | None
    rel_cost: float


class Database:
    """In-memory view of all data files."""

    def __init__(self) -> None:
        mats = _load("materials.json")["materials"]
        self.materials: dict[str, Material] = {}
        for m in mats:
            self.materials[m["id"]] = Material(
                id=m["id"],
                name=m["name"],
                is_equiv=m["is_equiv"],
                category=m["category"],
                brittle=bool(m["brittle"]),
                Sut=float(m["Sut"]),
                Syt=None if m["Syt"] is None else float(m["Syt"]),
                E=float(m["E"]) * 1000.0,
                G=float(m["G"]) * 1000.0,
                density=float(m["density"]),
                elongation=float(m["elongation"]),
                BHN=float(m["BHN"]),
                rel_cost=float(m["rel_cost"]),
                uses=tuple(m["uses"]),
            )

        self.threads: list[ThreadSize] = []
        for t in _load("iso_metric_threads.json")["threads"]:
            common = dict(
                d=float(t["d"]),
                first_choice=bool(t["first_choice"]),
                nut_height=float(t["nut_height"]),
                across_flats=float(t["across_flats"]),
                washer_thickness=float(t["washer_thickness"]),
            )
            self.threads.append(ThreadSize(P=float(t["pitch_coarse"]), series="coarse", **common))
            if t.get("pitch_fine"):
                self.threads.append(ThreadSize(P=float(t["pitch_fine"]), series="fine", **common))

        self.bolt_classes: list[BoltClass] = [
            BoltClass(
                name=c["class"],
                d_min=float(c["d_min"]),
                d_max=float(c["d_max"]),
                Sp=float(c["Sp"]),
                Sut=float(c["Sut"]),
                Sy=float(c["Sy"]),
                Se_table=None if c["Se"] is None else float(c["Se"]),
                rel_cost=float(c["rel_cost"]),
            )
            for c in _load("bolt_classes.json")["classes"]
        ]

        std = _load("standards.json")
        self.shaft_diameters: list[float] = [float(v) for v in std["shaft_diameters"]["values"]]
        self.key_rows: list[dict] = std["parallel_keys"]["rows"]
        self.key_lengths: list[float] = [float(v) for v in std["key_lengths"]["values"]]
        self.bolt_lengths: list[float] = [float(v) for v in std["bolt_lengths"]["values"]]

    # ------------------------------------------------------------------ materials
    def material(self, mat_id: str) -> Material:
        try:
            return self.materials[mat_id]
        except KeyError:
            known = ", ".join(self.materials)
            raise KeyError(f"Unknown material id '{mat_id}'. Known ids: {known}") from None

    def materials_for(self, use: str) -> list[Material]:
        return [m for m in self.materials.values() if use in m.uses]

    # ------------------------------------------------------------------ threads
    def thread_sizes(self, series: str = "coarse", first_choice_only: bool = False) -> list[ThreadSize]:
        out = [t for t in self.threads if t.series == series]
        if first_choice_only:
            out = [t for t in out if t.first_choice]
        return sorted(out, key=lambda t: t.d)

    def thread(self, d: float, series: str = "coarse") -> ThreadSize:
        for t in self.threads:
            if t.series == series and abs(t.d - d) < 1e-9:
                return t
        raise KeyError(f"No ISO {series} thread with d = {d:g} mm in the database")

    def thread_by_name(self, name: str) -> ThreadSize:
        """Parse 'M12' (coarse) or 'M12x1.25' (fine) and return the thread."""
        txt = name.strip().upper().replace(" ", "").replace("×", "X")
        if not txt.startswith("M"):
            raise KeyError(f"Thread designation must look like M12 or M12x1.25, got '{name}'")
        body = txt[1:]
        if "X" in body:
            d_txt, p_txt = body.split("X", 1)
            d, p = float(d_txt), float(p_txt)
            for t in self.threads:
                if abs(t.d - d) < 1e-9 and abs(t.P - p) < 1e-9:
                    return t
            raise KeyError(f"No ISO thread M{d:g}x{p:g} in the database")
        return self.thread(float(body), "coarse")

    # ------------------------------------------------------------------ bolt classes
    def bolt_class_names(self) -> list[str]:
        seen: list[str] = []
        for c in self.bolt_classes:
            if c.name not in seen:
                seen.append(c.name)
        return seen

    def bolt_class(self, name: str, d: float) -> BoltClass | None:
        """Property-class row valid for nominal diameter d, or None if the class is not made in that size."""
        for c in self.bolt_classes:
            if c.name == name and c.d_min <= d <= c.d_max:
                return c
        return None

    # ------------------------------------------------------------------ standard sizes
    @staticmethod
    def round_up(value: float, series: list[float]) -> float | None:
        """Smallest value in `series` that is >= value (None if value exceeds the series)."""
        for s in series:
            if s >= value - 1e-9:
                return s
        return None

    def standard_shaft(self, d: float) -> float | None:
        return self.round_up(d, self.shaft_diameters)

    def key_for_shaft(self, d: float) -> tuple[float, float]:
        for row in self.key_rows:
            if row["d_over"] < d <= row["d_upto"]:
                return float(row["b"]), float(row["h"])
        raise ValueError(f"No standard parallel key for a {d:g} mm shaft (table covers 6-500 mm)")


_DB: Database | None = None


def get_db() -> Database:
    """Shared, lazily-created database instance."""
    global _DB
    if _DB is None:
        _DB = Database()
    return _DB
