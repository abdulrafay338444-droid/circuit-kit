"""LED current-limiting resistor calculator."""

from __future__ import annotations

import math

from .eseries import standard_values

# Typical forward voltages at ~20 mA. Always check your LED's datasheet.
TYPICAL_VF = {
    "red": 2.0, "orange": 2.1, "yellow": 2.1, "green": 2.2,
    "blue": 3.2, "white": 3.2, "infrared": 1.3,
}

POWER_RATINGS = (0.125, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0)  # watts


def forward_voltage(color_or_volts: str | float) -> float:
    """Return a forward voltage from a number or a colour name like 'red'."""
    if isinstance(color_or_volts, (int, float)):
        return float(color_or_volts)
    try:
        return TYPICAL_VF[color_or_volts.lower()]
    except KeyError:
        raise ValueError(f"unknown LED colour {color_or_volts!r}; "
                         f"use one of {sorted(TYPICAL_VF)} or give volts") from None


def exact_resistor(v_supply: float, v_forward: float, i_forward: float,
                   n_series: int = 1) -> float:
    """Exact resistance for `n_series` identical LEDs in a string."""
    if i_forward <= 0:
        raise ValueError("LED current must be positive")
    if n_series < 1:
        raise ValueError("need at least one LED")
    headroom = v_supply - n_series * v_forward
    if headroom <= 0:
        raise ValueError(f"supply {v_supply} V is too low for {n_series} LED(s) "
                         f"at {v_forward} V each")
    return headroom / i_forward


def design(v_supply: float, led: str | float = "red", i_forward: float = 0.02,
           n_series: int = 1, series: str = "E12") -> dict[str, float]:
    """Pick a real resistor for an LED string.

    Rounds *up* to the next standard value so the LED never gets more current
    than asked for, and picks a power rating with a 2x safety margin.
    """
    vf = forward_voltage(led)
    r_exact = exact_resistor(v_supply, vf, i_forward, n_series)
    candidates = [r for r in standard_values(series, 1, 10e6) if r >= r_exact * (1 - 1e-9)]
    if not candidates:
        raise ValueError("required resistance is beyond the standard range")
    r = candidates[0]
    i_actual = (v_supply - n_series * vf) / r
    p_resistor = i_actual ** 2 * r
    rating = next((w for w in POWER_RATINGS if w >= 2 * p_resistor), math.inf)
    return {
        "r_exact": r_exact,
        "r_standard": r,
        "current": i_actual,
        "resistor_power": p_resistor,
        "power_rating": rating,
        "led_power": i_actual * vf * n_series,
    }
