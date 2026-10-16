"""555 timer calculator for astable (oscillator) and monostable (one-shot) modes.

Uses the exact exponents ln(2) ≈ 0.693 and ln(3) ≈ 1.0986 rather than the
rounded 0.693 / 1.1 from datasheets, so results match simulation closely.
"""

from __future__ import annotations

import math

from .eseries import nearest

LN2 = math.log(2)
LN3 = math.log(3)


def _pos(**kw: float) -> None:
    for name, v in kw.items():
        if v <= 0:
            raise ValueError(f"{name} must be positive, got {v}")


# ---- astable ----------------------------------------------------------

def astable(r1: float, r2: float, c: float) -> dict[str, float]:
    """Timing of the standard astable circuit (R1 to Vcc, R2 between pins 7 and 6/2)."""
    _pos(r1=r1, r2=r2, c=c)
    t_high = LN2 * (r1 + r2) * c
    t_low = LN2 * r2 * c
    period = t_high + t_low
    return {
        "frequency": 1 / period,
        "period": period,
        "t_high": t_high,
        "t_low": t_low,
        "duty_cycle": t_high / period,
    }


def design_astable(frequency: float, duty_cycle: float, c: float,
                   series: str | None = "E12") -> dict[str, float]:
    """Find R1 and R2 for a target frequency and duty cycle.

    The standard circuit needs duty_cycle > 0.5 (high time is always longer than
    low time). Pass series=None for exact values, or "E12"/"E24" for real parts;
    the returned timing is recalculated for the parts chosen.
    """
    _pos(frequency=frequency, c=c)
    if not 0.5 < duty_cycle < 1:
        raise ValueError("standard 555 astable needs 0.5 < duty cycle < 1 "
                         "(add a diode across R2 for 50% or less)")
    period = 1 / frequency
    t_high, t_low = duty_cycle * period, (1 - duty_cycle) * period
    r2 = t_low / (LN2 * c)
    r1 = t_high / (LN2 * c) - r2
    if series:
        r1, r2 = nearest(r1, series), nearest(r2, series)
    return {"r1": r1, "r2": r2, **astable(r1, r2, c)}


# ---- monostable -------------------------------------------------------

def monostable(r: float, c: float) -> float:
    """Output pulse width of a one-shot: ln(3)·R·C ≈ 1.1·R·C."""
    _pos(r=r, c=c)
    return LN3 * r * c


def design_monostable(pulse_width: float, c: float,
                      series: str | None = "E12") -> dict[str, float]:
    """Find R for a target one-shot pulse width with a given capacitor."""
    _pos(pulse_width=pulse_width, c=c)
    r = pulse_width / (LN3 * c)
    if series:
        r = nearest(r, series)
    return {"r": r, "pulse_width": monostable(r, c)}
