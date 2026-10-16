"""Ideal op-amp gain stages and a helper to design them with standard resistors."""

from __future__ import annotations

import math

from .eseries import best_ratio_pair


def _pos(**kw: float) -> None:
    for name, v in kw.items():
        if v <= 0:
            raise ValueError(f"{name} must be positive, got {v}")


def inverting_gain(rf: float, rin: float) -> float:
    """Gain of an inverting amplifier: -Rf / Rin."""
    _pos(rf=rf, rin=rin)
    return -rf / rin


def non_inverting_gain(rf: float, rg: float) -> float:
    """Gain of a non-inverting amplifier: 1 + Rf / Rg."""
    _pos(rf=rf, rg=rg)
    return 1 + rf / rg


def output_voltage(v_in: float, gain: float, v_supply: float | None = None) -> float:
    """Ideal output, clipped to ±v_supply if given (rail saturation)."""
    v = v_in * gain
    if v_supply is not None:
        v = max(-v_supply, min(v_supply, v))
    return v


def gain_db(gain: float) -> float:
    """Voltage gain in dB."""
    if gain == 0:
        return -math.inf
    return 20 * math.log10(abs(gain))


def design(target_gain: float, kind: str = "non-inverting", series: str = "E12",
           lo: float = 1e3, hi: float = 1e6) -> dict[str, float]:
    """Pick standard resistors that get as close as possible to a target gain.

    For 'inverting', target_gain is the magnitude (e.g. 10 for a gain of -10).
    Returns {'rf', 'r_other', 'gain', 'error_percent'}.
    """
    if kind == "inverting":
        if target_gain <= 0:
            raise ValueError("give the inverting gain as a positive magnitude")
        rf, rin = best_ratio_pair(target_gain, series, lo, hi)
        g = inverting_gain(rf, rin)
        err = (abs(g) - target_gain) / target_gain * 100
        return {"rf": rf, "r_other": rin, "gain": g, "error_percent": err}
    if kind == "non-inverting":
        if target_gain <= 1:
            raise ValueError("non-inverting gain must be greater than 1")
        rf, rg = best_ratio_pair(target_gain - 1, series, lo, hi)
        g = non_inverting_gain(rf, rg)
        err = (g - target_gain) / target_gain * 100
        return {"rf": rf, "r_other": rg, "gain": g, "error_percent": err}
    raise ValueError("kind must be 'inverting' or 'non-inverting'")
