"""Parse and format engineering notation like '4.7k', '10u', '2.2M'."""

from __future__ import annotations

import re

PREFIXES = {
    "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3,
    "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9,
}

_PATTERN = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([pnuµmkKMG]?)\s*[A-Za-zΩ]*\s*$")


def parse(text: str | float | int) -> float:
    """Convert '4.7k', '100n', '10uF', '2.2MΩ' or a plain number to a float."""
    if isinstance(text, (int, float)):
        return float(text)
    match = _PATTERN.match(text)
    if not match:
        raise ValueError(f"Can't understand value: {text!r}")
    number, prefix = match.groups()
    return float(number) * PREFIXES[prefix]


def format_si(value: float, unit: str = "", digits: int = 3) -> str:
    """Format a float with an SI prefix, e.g. 0.0047 -> '4.7 m'."""
    if value == 0:
        return f"0 {unit}".strip()
    for prefix, scale in [("G", 1e9), ("M", 1e6), ("k", 1e3), ("", 1.0),
                          ("m", 1e-3), ("µ", 1e-6), ("n", 1e-9), ("p", 1e-12)]:
        if abs(value) >= scale:
            return f"{value / scale:.{digits}g} {prefix}{unit}".strip()
    return f"{value:.{digits}g} {unit}".strip()
