"""Core DC circuit relationships: Ohm's law, power, resistor networks, dividers."""

from __future__ import annotations

from typing import Iterable


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def ohms_law(*, voltage: float | None = None, current: float | None = None,
             resistance: float | None = None) -> dict[str, float]:
    """Solve V = I * R given any two of the three quantities.

    Returns a dict with all three values filled in.

    >>> ohms_law(voltage=12, resistance=4)
    {'voltage': 12, 'current': 3.0, 'resistance': 4}
    """
    known = {k: v for k, v in
             {"voltage": voltage, "current": current, "resistance": resistance}.items()
             if v is not None}
    if len(known) != 2:
        raise ValueError("Provide exactly two of voltage, current, resistance")

    if voltage is None:
        voltage = current * resistance
    elif current is None:
        _require_positive("resistance", resistance)
        current = voltage / resistance
    else:
        if current == 0:
            raise ValueError("current must be non-zero to solve for resistance")
        resistance = voltage / current
    return {"voltage": voltage, "current": current, "resistance": resistance}


def power(*, voltage: float | None = None, current: float | None = None,
          resistance: float | None = None) -> float:
    """Power dissipated (W) from any two of V, I, R."""
    v = ohms_law(voltage=voltage, current=current, resistance=resistance)
    return v["voltage"] * v["current"]


def series(resistors: Iterable[float]) -> float:
    """Equivalent resistance of resistors in series."""
    values = list(resistors)
    if not values:
        raise ValueError("Need at least one resistor")
    for r in values:
        if r < 0:
            raise ValueError("Resistances cannot be negative")
    return float(sum(values))


def parallel(resistors: Iterable[float]) -> float:
    """Equivalent resistance of resistors in parallel."""
    values = list(resistors)
    if not values:
        raise ValueError("Need at least one resistor")
    for r in values:
        _require_positive("resistance", r)
    return 1.0 / sum(1.0 / r for r in values)


def voltage_divider(v_in: float, r1: float, r2: float) -> float:
    """Output voltage across R2 in a two-resistor divider (R1 on top)."""
    _require_positive("r1 + r2", r1 + r2)
    return v_in * r2 / (r1 + r2)
