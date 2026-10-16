"""AC impedance with complex numbers.

Impedances are Python ``complex`` values in ohms:
    Z_R = R,  Z_L = jωL,  Z_C = 1 / (jωC),  where ω = 2πf.
"""

from __future__ import annotations

import cmath
import math
from typing import Iterable


def _omega(f: float) -> float:
    if f <= 0:
        raise ValueError("frequency must be positive for AC impedance")
    return 2 * math.pi * f


def z_resistor(r: float) -> complex:
    """Impedance of a resistor (frequency independent)."""
    if r < 0:
        raise ValueError("resistance cannot be negative")
    return complex(r, 0)


def z_inductor(l: float, f: float) -> complex:
    """Impedance of an inductor: jωL."""
    if l <= 0:
        raise ValueError("inductance must be positive")
    return complex(0, _omega(f) * l)


def z_capacitor(c: float, f: float) -> complex:
    """Impedance of a capacitor: 1/(jωC) = -j/(ωC)."""
    if c <= 0:
        raise ValueError("capacitance must be positive")
    return complex(0, -1 / (_omega(f) * c))


def z_series(impedances: Iterable[complex]) -> complex:
    """Total impedance of elements in series."""
    values = list(impedances)
    if not values:
        raise ValueError("Need at least one impedance")
    return sum(values, complex(0, 0))


def z_parallel(impedances: Iterable[complex]) -> complex:
    """Total impedance of elements in parallel."""
    values = list(impedances)
    if not values:
        raise ValueError("Need at least one impedance")
    if any(z == 0 for z in values):
        return complex(0, 0)  # a short circuit dominates
    return 1 / sum(1 / z for z in values)


def polar(z: complex) -> tuple[float, float]:
    """Return (magnitude in ohms, phase in degrees)."""
    mag, ang = cmath.polar(z)
    return mag, math.degrees(ang)


def ac_current(v: float, z: complex) -> complex:
    """Phasor current I = V / Z for a source of amplitude v at 0°."""
    if z == 0:
        raise ValueError("zero impedance (short circuit)")
    return v / z
