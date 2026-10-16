"""Thevenin and Norton equivalents, loading and maximum power transfer.

For an arbitrary network, build it with :class:`circuitkit.nodal.Circuit` and
call ``Circuit.thevenin(a, b)``. The helpers here cover the common hand cases.
"""

from __future__ import annotations


def _pos(**kw: float) -> None:
    for name, v in kw.items():
        if v <= 0:
            raise ValueError(f"{name} must be positive, got {v}")


def from_measurements(v_oc: float, i_sc: float) -> tuple[float, float]:
    """Thevenin (Vth, Rth) from open-circuit voltage and short-circuit current."""
    if i_sc == 0:
        raise ValueError("short-circuit current can't be zero")
    return v_oc, v_oc / i_sc


def to_norton(v_th: float, r_th: float) -> tuple[float, float]:
    """Convert Thevenin (Vth, Rth) to Norton (In, Rn)."""
    _pos(r_th=r_th)
    return v_th / r_th, r_th


def to_thevenin(i_n: float, r_n: float) -> tuple[float, float]:
    """Convert Norton (In, Rn) to Thevenin (Vth, Rth)."""
    _pos(r_n=r_n)
    return i_n * r_n, r_n


def of_divider(v_source: float, r1: float, r2: float) -> tuple[float, float]:
    """Thevenin equivalent at the midpoint of a voltage divider (R1 on top)."""
    _pos(r1=r1, r2=r2)
    return v_source * r2 / (r1 + r2), r1 * r2 / (r1 + r2)


def load_voltage(v_th: float, r_th: float, r_load: float) -> float:
    """Voltage across a load connected to a Thevenin source."""
    if r_load < 0 or r_th < 0:
        raise ValueError("resistances cannot be negative")
    if r_th + r_load == 0:
        raise ValueError("Rth + Rload can't be zero")
    return v_th * r_load / (r_th + r_load)


def load_power(v_th: float, r_th: float, r_load: float) -> float:
    """Power delivered to a load connected to a Thevenin source."""
    v = load_voltage(v_th, r_th, r_load)
    return 0.0 if r_load == 0 else v ** 2 / r_load


def max_power(v_th: float, r_th: float) -> tuple[float, float]:
    """Maximum power transfer: returns (best Rload = Rth, Pmax = Vth²/4Rth)."""
    _pos(r_th=r_th)
    return r_th, v_th ** 2 / (4 * r_th)


def efficiency(r_th: float, r_load: float) -> float:
    """Fraction of total power that reaches the load (0..1)."""
    if r_th + r_load <= 0:
        raise ValueError("Rth + Rload must be positive")
    return r_load / (r_th + r_load)

