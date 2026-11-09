"""Fatigue relations shared by the shaft and bolt modules.

References: Shigley's Mechanical Engineering Design, Ch. 6-7 (Marin factors,
Neuber notch sensitivity, fatigue failure criteria, DE shaft equations).
Units: MPa, mm, N.mm.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------- Marin factors
# Surface factor ka = a * Sut^b  (Sut in MPa)
SURFACE_FINISH = {
    "ground": (1.58, -0.085),
    "machined": (4.51, -0.265),   # machined or cold-drawn
    "hot-rolled": (57.7, -0.718),
    "as-forged": (272.0, -0.995),
}

# Reliability factor ke (Shigley Table 6-5)
RELIABILITY = {
    50.0: 1.000,
    90.0: 0.897,
    95.0: 0.868,
    99.0: 0.814,
    99.9: 0.753,
    99.99: 0.702,
    99.999: 0.659,
    99.9999: 0.620,
}

FAILURE_CRITERIA = {
    "goodman": "DE-Goodman",
    "soderberg": "DE-Soderberg",
    "gerber": "DE-Gerber",
    "asme": "DE-ASME elliptic",
}


def endurance_limit_specimen(Sut: float) -> float:
    """Rotating-beam specimen endurance limit Se' (steels)."""
    return 0.5 * Sut if Sut <= 1400.0 else 700.0


def surface_factor(Sut: float, finish: str) -> float:
    a, b = SURFACE_FINISH[finish]
    return min(1.0, a * Sut ** b)


def size_factor(d: float, rotating: bool = True) -> float:
    """kb for bending/torsion of a round section. Non-rotating round bars use the
    equivalent diameter de = 0.370 d (Shigley Eq. 6-24)."""
    de = d if rotating else 0.370 * d
    if de <= 2.79:
        return 1.0
    if de <= 51.0:
        return 1.24 * de ** -0.107
    return max(0.60, 1.51 * de ** -0.157)


def temperature_factor(T_celsius: float) -> float:
    """kd from Shigley Eq. 6-27 (polynomial in deg F, valid 70-1000 F). Never above 1."""
    if T_celsius <= 21.0:
        return 1.0
    TF = T_celsius * 9.0 / 5.0 + 32.0
    TF = min(TF, 1000.0)
    kd = (0.975 + 0.432e-3 * TF - 0.115e-5 * TF ** 2
          + 0.104e-8 * TF ** 3 - 0.595e-12 * TF ** 4)
    return min(1.0, kd)


def reliability_factor(reliability_pct: float) -> float:
    """ke for the given reliability (%). Uses the nearest tabulated value at or above it."""
    for r in sorted(RELIABILITY):
        if reliability_pct <= r + 1e-9:
            return RELIABILITY[r]
    return RELIABILITY[max(RELIABILITY)]


# --------------------------------------------------------------------------- notches
# First-iteration stress-concentration factors (Shigley Table 7-1).
# r_over_d is the notch radius relative to the shaft diameter.
NOTCHES = {
    "none": {"label": "Plain shaft, no notch", "Kt": 1.0, "Kts": 1.0, "r_over_d": 0.0},
    "shoulder-rounded": {"label": "Shoulder fillet, well rounded (r/d = 0.1)", "Kt": 1.7, "Kts": 1.5, "r_over_d": 0.10},
    "shoulder-sharp": {"label": "Shoulder fillet, sharp (r/d = 0.02)", "Kt": 2.7, "Kts": 2.2, "r_over_d": 0.02},
    "keyseat": {"label": "End-mill keyseat (r/d = 0.02)", "Kt": 2.14, "Kts": 3.0, "r_over_d": 0.02},
}


def neuber_sqrt_a(Sut: float, torsion: bool = False) -> float:
    """Neuber constant sqrt(a) in sqrt(inch) for steels (Shigley Eqs. 6-35a/b).
    Sut in MPa; the fit is in kpsi and valid for 50-250 kpsi."""
    S = min(max(Sut / 6.894757, 50.0), 250.0)
    if torsion:
        return 0.190 - 2.51e-3 * S + 1.35e-5 * S ** 2 - 2.67e-8 * S ** 3
    return 0.246 - 3.08e-3 * S + 1.51e-5 * S ** 2 - 2.67e-8 * S ** 3


def notch_sensitivity(Sut: float, r_mm: float, torsion: bool = False) -> float:
    """q = 1 / (1 + sqrt(a)/sqrt(r)). A zero radius returns q = 1 (fully notch sensitive)."""
    if r_mm <= 0.0:
        return 1.0
    sa = neuber_sqrt_a(Sut, torsion)
    return 1.0 / (1.0 + sa / math.sqrt(r_mm / 25.4))


def fatigue_factor(Kt: float, q: float) -> float:
    """Kf = 1 + q (Kt - 1)."""
    return 1.0 + q * (Kt - 1.0)


# --------------------------------------------------------------------------- failure criteria
def fos_fluctuating(sig_a: float, sig_m: float, Se: float, Sut: float, Sy: float, criterion: str) -> float:
    """Fatigue factor of safety for von Mises alternating/mean stresses.

    sig_a, sig_m are the von Mises alternating and mean stresses (sig_m >= 0).
    """
    sig_m = abs(sig_m)
    if sig_a <= 0.0 and sig_m <= 0.0:
        return math.inf
    if criterion == "goodman":
        return 1.0 / (sig_a / Se + sig_m / Sut)
    if criterion == "soderberg":
        return 1.0 / (sig_a / Se + sig_m / Sy)
    if criterion == "asme":
        return 1.0 / math.sqrt((sig_a / Se) ** 2 + (sig_m / Sy) ** 2)
    if criterion == "gerber":
        if sig_m == 0.0:
            return Se / sig_a
        if sig_a == 0.0:
            return Sut / sig_m
        return 0.5 * (Sut / sig_m) ** 2 * (sig_a / Se) * (
            -1.0 + math.sqrt(1.0 + (2.0 * sig_m * Se / (Sut * sig_a)) ** 2))
    raise ValueError(f"Unknown fatigue criterion '{criterion}'")


def de_shaft_diameter(n: float, Kf: float, Kfs: float, Ma: float, Mm: float, Ta: float, Tm: float,
                      Se: float, Sut: float, Sy: float, criterion: str) -> float:
    """Closed-form distortion-energy shaft diameter (Shigley Eqs. 7-8, 7-10, 7-12, 7-14).

    Moments/torques in N.mm, strengths in MPa, returns d in mm.
    """
    A = math.sqrt(4.0 * (Kf * Ma) ** 2 + 3.0 * (Kfs * Ta) ** 2)
    B = math.sqrt(4.0 * (Kf * Mm) ** 2 + 3.0 * (Kfs * Tm) ** 2)
    if A == 0.0 and B == 0.0:
        return 0.0
    if criterion == "goodman":
        val = 16.0 * n / math.pi * (A / Se + B / Sut)
    elif criterion == "soderberg":
        val = 16.0 * n / math.pi * (A / Se + B / Sy)
    elif criterion == "asme":
        val = 16.0 * n / math.pi * math.sqrt(
            4.0 * (Kf * Ma / Se) ** 2 + 3.0 * (Kfs * Ta / Se) ** 2
            + 4.0 * (Kf * Mm / Sy) ** 2 + 3.0 * (Kfs * Tm / Sy) ** 2)
    elif criterion == "gerber":
        if A == 0.0:
            val = 16.0 * n * B / (math.pi * Sut)
        else:
            val = 8.0 * n * A / (math.pi * Se) * (1.0 + math.sqrt(1.0 + (2.0 * B * Se / (A * Sut)) ** 2))
    else:
        raise ValueError(f"Unknown fatigue criterion '{criterion}'")
    return val ** (1.0 / 3.0)


DE_EQUATION_TEXT = {
    "goodman": "d = [ 16n/pi * ( A/Se + B/Sut ) ]^(1/3)",
    "soderberg": "d = [ 16n/pi * ( A/Se + B/Syt ) ]^(1/3)",
    "gerber": "d = [ 8nA/(pi Se) * ( 1 + sqrt(1 + (2 B Se / (A Sut))^2) ) ]^(1/3)",
    "asme": "d = [ 16n/pi * sqrt( 4(Kf Ma/Se)^2 + 3(Kfs Ta/Se)^2 + 4(Kf Mm/Syt)^2 + 3(Kfs Tm/Syt)^2 ) ]^(1/3)",
}
