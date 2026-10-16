"""Draw a Bode plot (gain + phase) for an RC low-pass and high-pass filter.

Run:  python examples/bode_plot.py            -> saves examples/bode_plot.png
      python examples/bode_plot.py 4.7k 33n   -> your own R and C
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from circuitkit import cutoff_frequency, format_si, gain_db, parse, phase_deg

r = parse(sys.argv[1]) if len(sys.argv) > 1 else 1_000
c = parse(sys.argv[2]) if len(sys.argv) > 2 else 1e-6
fc = cutoff_frequency(r, c)
freqs = np.logspace(np.log10(fc / 1000), np.log10(fc * 1000), 400)

fig, (ax_g, ax_p) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
for kind, color in [("lowpass", "#2563eb"), ("highpass", "#d97706")]:
    ax_g.semilogx(freqs, [gain_db(f, r, c, kind) for f in freqs], color=color, label=kind)
    ax_p.semilogx(freqs, [phase_deg(f, r, c, kind) for f in freqs], color=color, label=kind)

for ax in (ax_g, ax_p):
    ax.axvline(fc, color="gray", linestyle="--", linewidth=1)
    ax.grid(True, which="both", alpha=0.3)
ax_g.axhline(-3, color="gray", linestyle=":", linewidth=1)
ax_g.set_ylabel("Gain (dB)")
ax_g.set_ylim(-60, 5)
ax_g.legend()
ax_p.set_ylabel("Phase (°)")
ax_p.set_xlabel("Frequency (Hz)")
fig.suptitle(f"RC filter: R = {format_si(r, 'Ω')}, C = {format_si(c, 'F')}, "
             f"f_c = {format_si(fc, 'Hz')}")
fig.tight_layout()

out = Path(__file__).with_name("bode_plot.png")
fig.savefig(out, dpi=150)
print(f"Saved {out}")
