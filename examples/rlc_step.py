"""Plot the step response of a series RLC circuit for three damping cases.

Run:  python examples/rlc_step.py              -> L = 10 mH, C = 100 nF
      python examples/rlc_step.py 1m 1u        -> your own L and C
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from circuitkit import format_si, parse
from circuitkit.rlc import (critical_resistance, damping_ratio, resonant_frequency,
                            series_step_response)

l = parse(sys.argv[1]) if len(sys.argv) > 1 else 10e-3
c = parse(sys.argv[2]) if len(sys.argv) > 2 else 100e-9
rc = critical_resistance(l, c)
t = np.linspace(0, 6 / resonant_frequency(l, c), 600)

fig, ax = plt.subplots(figsize=(8, 4.5))
for scale, color in [(0.15, "#2563eb"), (1.0, "#16a34a"), (4.0, "#d97706")]:
    r = rc * scale
    label = f"R = {format_si(r, 'Ω')}  (ζ = {damping_ratio(r, l, c):.2f})"
    ax.plot(t * 1e3, [series_step_response(x, 1, r, l, c) for x in t], color=color, label=label)

ax.axhline(1, color="gray", linestyle="--", linewidth=1)
ax.set_xlabel("Time (ms)")
ax.set_ylabel("Capacitor voltage (V)")
ax.set_title(f"Series RLC step response: L = {format_si(l, 'H')}, C = {format_si(c, 'F')}")
ax.grid(True, alpha=0.3)
ax.legend(title="underdamped / critical / overdamped")
fig.tight_layout()

out = Path(__file__).with_name("rlc_step.png")
fig.savefig(out, dpi=150)
print(f"Saved {out}")
