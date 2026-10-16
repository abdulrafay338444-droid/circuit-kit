"""Standard E-series resistor values (IEC 60063) and helpers to pick real parts."""

from __future__ import annotations

import math

E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
E24 = (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1)
SERIES = {"E12": E12, "E24": E24}


def _base(series: str) -> tuple[float, ...]:
    try:
        return SERIES[series.upper()]
    except KeyError:
        raise ValueError(f"series must be one of {sorted(SERIES)}") from None


def standard_values(series: str = "E12", lo: float = 1.0, hi: float = 10e6) -> list[float]:
    """All standard values of a series between lo and hi ohms (inclusive)."""
    base = _base(series)
    values = []
    for decade in range(math.floor(math.log10(lo)) - 1, math.ceil(math.log10(hi)) + 1):
        for b in base:
            v = round(b * 10 ** decade, 10)
            if lo <= v <= hi:
                values.append(v)
    return sorted(set(values))


def nearest(value: float, series: str = "E12") -> float:
    """Closest standard value (compared on a log scale, as tolerances are relative)."""
    if value <= 0:
        raise ValueError("value must be positive")
    decade = math.floor(math.log10(value))
    candidates = [b * 10 ** d for d in (decade - 1, decade, decade + 1) for b in _base(series)]
    best = min(candidates, key=lambda c: abs(math.log(c / value)))
    return round(best, 10)


def error_percent(actual: float, target: float) -> float:
    """Percentage error of actual relative to target."""
    return (actual - target) / target * 100


def best_ratio_pair(ratio: float, series: str = "E12",
                    lo: float = 1e3, hi: float = 1e6) -> tuple[float, float]:
    """Find standard values (a, b) with a / b as close as possible to ratio.

    Useful for op-amp gains (Rf / Rin) and voltage dividers.
    """
    if ratio <= 0:
        raise ValueError("ratio must be positive")
    values = standard_values(series, lo, hi)
    best = None
    for b in values:
        a = nearest(ratio * b, series)
        if not lo <= a <= hi:
            continue
        err = abs(math.log((a / b) / ratio))
        if best is None or err < best[0]:
            best = (err, a, b)
    if best is None:
        raise ValueError("no pair found in that range")
    return best[1], best[2]
