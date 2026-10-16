"""RL circuits and second-order series/parallel RLC circuits."""

from __future__ import annotations

import math


def _pos(**kw: float) -> None:
    for name, v in kw.items():
        if v <= 0:
            raise ValueError(f"{name} must be positive, got {v}")


# ---- RL ---------------------------------------------------------------

def rl_time_constant(r: float, l: float) -> float:
    """RL time constant tau = L / R (seconds)."""
    _pos(r=r, l=l)
    return l / r


def rl_cutoff_frequency(r: float, l: float) -> float:
    """-3 dB cutoff of a first-order RL filter: R / (2πL)."""
    _pos(r=r, l=l)
    return r / (2 * math.pi * l)


def inductor_current(t: float, v_source: float, r: float, l: float) -> float:
    """Inductor current at time t after a DC step, starting from 0 A."""
    if t < 0:
        raise ValueError("time cannot be negative")
    return (v_source / r) * (1 - math.exp(-t / rl_time_constant(r, l)))


# ---- RLC --------------------------------------------------------------

def resonant_frequency(l: float, c: float) -> float:
    """Resonant frequency f0 = 1 / (2π√(LC)) in Hz."""
    _pos(l=l, c=c)
    return 1 / (2 * math.pi * math.sqrt(l * c))


def quality_factor(r: float, l: float, c: float, topology: str = "series") -> float:
    """Q factor. Series: (1/R)√(L/C). Parallel: R√(C/L)."""
    _pos(r=r, l=l, c=c)
    if topology == "series":
        return math.sqrt(l / c) / r
    if topology == "parallel":
        return r * math.sqrt(c / l)
    raise ValueError("topology must be 'series' or 'parallel'")


def bandwidth(r: float, l: float, c: float, topology: str = "series") -> float:
    """-3 dB bandwidth in Hz: f0 / Q."""
    return resonant_frequency(l, c) / quality_factor(r, l, c, topology)


def damping_ratio(r: float, l: float, c: float, topology: str = "series") -> float:
    """Damping ratio ζ = 1 / (2Q)."""
    return 1 / (2 * quality_factor(r, l, c, topology))


def damping_type(r: float, l: float, c: float, topology: str = "series",
                 tol: float = 1e-9) -> str:
    """Classify the step response: 'underdamped', 'critically damped' or 'overdamped'."""
    z = damping_ratio(r, l, c, topology)
    if abs(z - 1) <= tol:
        return "critically damped"
    return "underdamped" if z < 1 else "overdamped"


def critical_resistance(l: float, c: float, topology: str = "series") -> float:
    """Resistance that makes the circuit exactly critically damped."""
    _pos(l=l, c=c)
    if topology == "series":
        return 2 * math.sqrt(l / c)
    if topology == "parallel":
        return 0.5 * math.sqrt(l / c)
    raise ValueError("topology must be 'series' or 'parallel'")


def series_step_response(t: float, v_source: float, r: float, l: float, c: float) -> float:
    """Capacitor voltage in a series RLC after a DC step (starting at rest).

    Handles the underdamped, critically damped and overdamped cases analytically.
    """
    _pos(r=r, l=l, c=c)
    if t < 0:
        raise ValueError("time cannot be negative")
    w0 = 1 / math.sqrt(l * c)
    alpha = r / (2 * l)
    if math.isclose(alpha, w0, rel_tol=1e-9):          # critically damped
        return v_source * (1 - (1 + w0 * t) * math.exp(-w0 * t))
    if alpha < w0:                                      # underdamped
        wd = math.sqrt(w0 ** 2 - alpha ** 2)
        return v_source * (1 - math.exp(-alpha * t)
                           * (math.cos(wd * t) + alpha / wd * math.sin(wd * t)))
    s = math.sqrt(alpha ** 2 - w0 ** 2)                 # overdamped
    s1, s2 = -alpha + s, -alpha - s
    return v_source * (1 + (s2 * math.exp(s1 * t) - s1 * math.exp(s2 * t)) / (s1 - s2))
