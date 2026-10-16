"""First-order RC low-pass and high-pass filters."""

from __future__ import annotations

import math


def _check(r: float, c: float) -> None:
    if r <= 0 or c <= 0:
        raise ValueError("R and C must both be positive")


def time_constant(r: float, c: float) -> float:
    """RC time constant tau (seconds)."""
    _check(r, c)
    return r * c


def cutoff_frequency(r: float, c: float) -> float:
    """-3 dB cutoff frequency (Hz): f_c = 1 / (2*pi*R*C)."""
    _check(r, c)
    return 1.0 / (2 * math.pi * r * c)


def gain(f: float, r: float, c: float, kind: str = "lowpass") -> float:
    """Magnitude of the transfer function |H(f)| (linear, 0..1)."""
    _check(r, c)
    if f < 0:
        raise ValueError("frequency cannot be negative")
    ratio = f / cutoff_frequency(r, c)
    if kind == "lowpass":
        return 1.0 / math.sqrt(1 + ratio ** 2)
    if kind == "highpass":
        return ratio / math.sqrt(1 + ratio ** 2)
    raise ValueError("kind must be 'lowpass' or 'highpass'")


def gain_db(f: float, r: float, c: float, kind: str = "lowpass") -> float:
    """Gain in decibels: 20*log10(|H(f)|)."""
    g = gain(f, r, c, kind)
    return -math.inf if g == 0 else 20 * math.log10(g)


def phase_deg(f: float, r: float, c: float, kind: str = "lowpass") -> float:
    """Phase shift of the output relative to the input, in degrees."""
    ratio = f / cutoff_frequency(r, c)
    lp = -math.degrees(math.atan(ratio))
    if kind == "lowpass":
        return lp
    if kind == "highpass":
        return 90.0 + lp
    raise ValueError("kind must be 'lowpass' or 'highpass'")


def capacitor_charge(t: float, v_source: float, r: float, c: float) -> float:
    """Capacitor voltage at time t when charging from 0 V through R."""
    if t < 0:
        raise ValueError("time cannot be negative")
    return v_source * (1 - math.exp(-t / time_constant(r, c)))
