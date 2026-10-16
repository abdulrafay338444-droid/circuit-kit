"""Command-line interface: `circuitkit <command> ...`."""

from __future__ import annotations

import argparse
import sys

from pathlib import Path

from . import basics, eseries, filters, impedance, led, nodal, opamp, rlc, thevenin, timer555
from .units import format_si, parse


def _rlc(args: argparse.Namespace) -> None:
    r, l, c = parse(args.r), parse(args.l), parse(args.c)
    t = args.topology
    print(f"f0   = {format_si(rlc.resonant_frequency(l, c), 'Hz')}")
    print(f"Q    = {rlc.quality_factor(r, l, c, t):.3g}")
    print(f"BW   = {format_si(rlc.bandwidth(r, l, c, t), 'Hz')}")
    print(f"zeta = {rlc.damping_ratio(r, l, c, t):.3g} ({rlc.damping_type(r, l, c, t)})")
    print(f"R for critical damping = {format_si(rlc.critical_resistance(l, c, t), 'Ω')}")


def _rl(args: argparse.Namespace) -> None:
    r, l = parse(args.r), parse(args.l)
    print(f"tau = {format_si(rlc.rl_time_constant(r, l), 's')}")
    print(f"f_c = {format_si(rlc.rl_cutoff_frequency(r, l), 'Hz')}")


def _impedance(args: argparse.Namespace) -> None:
    f = parse(args.f)
    parts = []
    if args.r: parts.append(impedance.z_resistor(parse(args.r)))
    if args.l: parts.append(impedance.z_inductor(parse(args.l), f))
    if args.c: parts.append(impedance.z_capacitor(parse(args.c), f))
    if not parts:
        raise ValueError("give at least one of -r, -l, -c")
    z = impedance.z_parallel(parts) if args.parallel else impedance.z_series(parts)
    mag, ang = impedance.polar(z)
    print(f"Z = {z.real:.4g} {'+' if z.imag >= 0 else '-'} j{abs(z.imag):.4g} Ω")
    print(f"|Z| = {format_si(mag, 'Ω')} at {ang:.1f}°")


def _nearest(args: argparse.Namespace) -> None:
    target = parse(args.value)
    v = eseries.nearest(target, args.series)
    print(f"{format_si(v, 'Ω')} ({eseries.error_percent(v, target):+.1f}% from target)")


def _opamp(args: argparse.Namespace) -> None:
    d = opamp.design(float(args.gain), args.kind, args.series)
    other = "Rin" if args.kind == "inverting" else "Rg"
    print(f"Rf = {format_si(d['rf'], 'Ω')}, {other} = {format_si(d['r_other'], 'Ω')}")
    print(f"gain = {d['gain']:.4g} ({opamp.gain_db(d['gain']):.2f} dB), "
          f"error {d['error_percent']:+.2f}%")
    if args.series == "E12" and abs(d["error_percent"]) > 2:
        print("tip: E12 can't get closer; try --series E24")


def _ohm(args: argparse.Namespace) -> None:
    vals = {k: parse(v) for k, v in
            {"voltage": args.v, "current": args.i, "resistance": args.r}.items()
            if v is not None}
    res = basics.ohms_law(**vals)
    print(f"V = {format_si(res['voltage'], 'V')}")
    print(f"I = {format_si(res['current'], 'A')}")
    print(f"R = {format_si(res['resistance'], 'Ω')}")
    print(f"P = {format_si(res['voltage'] * res['current'], 'W')}")


def _series(args: argparse.Namespace) -> None:
    print(format_si(basics.series(parse(r) for r in args.resistors), "Ω"))


def _parallel(args: argparse.Namespace) -> None:
    print(format_si(basics.parallel(parse(r) for r in args.resistors), "Ω"))


def _divider(args: argparse.Namespace) -> None:
    out = basics.voltage_divider(parse(args.vin), parse(args.r1), parse(args.r2))
    print(f"Vout = {format_si(out, 'V')}")


def _rc(args: argparse.Namespace) -> None:
    r, c = parse(args.r), parse(args.c)
    print(f"tau = {format_si(filters.time_constant(r, c), 's')}")
    print(f"f_c = {format_si(filters.cutoff_frequency(r, c), 'Hz')}")
    if args.f is not None:
        f = parse(args.f)
        print(f"At {format_si(f, 'Hz')} ({args.kind}): "
              f"gain {filters.gain_db(f, r, c, args.kind):.2f} dB, "
              f"phase {filters.phase_deg(f, r, c, args.kind):.1f}°")


def _solve(args: argparse.Namespace) -> None:
    ckt = nodal.parse_netlist(Path(args.netlist).read_text())
    sol = ckt.solve()
    print("Node voltages:")
    for node, v in sol.voltages.items():
        if node != 0:
            print(f"  V({node}) = {format_si(v, 'V', 5)}")
    for k, i in enumerate(sol.source_currents, 1):
        print(f"Voltage source #{k} delivers {format_si(i, 'A', 4)}")
    if args.thevenin:
        a, b = (nodal_node(x) for x in args.thevenin)
        vth, rth = ckt.thevenin(a, b)
        print(f"Thevenin between {a} and {b}: Vth = {format_si(vth, 'V', 5)}, "
              f"Rth = {format_si(rth, 'Ω', 5)}")


def nodal_node(token: str):
    if token.lower() in ("0", "gnd", "ground"):
        return 0
    return int(token) if token.isdigit() else token


def _thevenin(args: argparse.Namespace) -> None:
    vth, rth = thevenin.of_divider(parse(args.vs), parse(args.r1), parse(args.r2))
    i_n, _ = thevenin.to_norton(vth, rth)
    print(f"Thevenin: Vth = {format_si(vth, 'V')}, Rth = {format_si(rth, 'Ω')}")
    print(f"Norton:   In  = {format_si(i_n, 'A')}, Rn  = {format_si(rth, 'Ω')}")
    rl, pmax = thevenin.max_power(vth, rth)
    print(f"Max power: {format_si(pmax, 'W')} into a {format_si(rl, 'Ω')} load")
    if args.load:
        r_load = parse(args.load)
        print(f"With {format_si(r_load, 'Ω')} load: "
              f"{format_si(thevenin.load_voltage(vth, rth, r_load), 'V')}, "
              f"{format_si(thevenin.load_power(vth, rth, r_load), 'W')}")


def _led(args: argparse.Namespace) -> None:
    color = args.color
    try:
        color = parse(color)
    except ValueError:
        pass
    d = led.design(parse(args.supply), color, parse(args.current), args.count, args.series)
    print(f"Exact R = {format_si(d['r_exact'], 'Ω')}  ->  use {format_si(d['r_standard'], 'Ω')}")
    print(f"LED current = {format_si(d['current'], 'A')}")
    print(f"Resistor dissipates {format_si(d['resistor_power'], 'W')}; "
          f"use a {d['power_rating']:g} W resistor or bigger")


def _timer(args: argparse.Namespace) -> None:
    c = parse(args.c)
    series = None if args.exact else args.series
    if args.mode == "astable":
        if args.r1 and args.r2:
            res = {"r1": parse(args.r1), "r2": parse(args.r2),
                   **timer555.astable(parse(args.r1), parse(args.r2), c)}
        elif args.f and args.duty:
            res = timer555.design_astable(parse(args.f), float(args.duty), c, series)
        else:
            raise ValueError("astable needs either --r1 and --r2, or -f and --duty")
        print(f"R1 = {format_si(res['r1'], 'Ω')}, R2 = {format_si(res['r2'], 'Ω')}, "
              f"C = {format_si(c, 'F')}")
        print(f"f = {format_si(res['frequency'], 'Hz', 4)}, "
              f"duty = {res['duty_cycle'] * 100:.1f}%, "
              f"high {format_si(res['t_high'], 's')}, low {format_si(res['t_low'], 's')}")
    else:
        if args.r:
            r = parse(args.r); width = timer555.monostable(r, c)
        elif args.width:
            d = timer555.design_monostable(parse(args.width), c, series)
            r, width = d["r"], d["pulse_width"]
        else:
            raise ValueError("monostable needs either -r or --width")
        print(f"R = {format_si(r, 'Ω')}, C = {format_si(c, 'F')} -> "
              f"pulse width {format_si(width, 's', 4)}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="circuitkit",
        description="Quick circuit calculations. Values accept SI prefixes: 4.7k, 100n, 10u, 2.2M.")
    sub = p.add_subparsers(dest="command", required=True)

    o = sub.add_parser("ohm", help="Solve Ohm's law from any two of V, I, R")
    o.add_argument("-v"); o.add_argument("-i"); o.add_argument("-r")
    o.set_defaults(func=_ohm)

    s = sub.add_parser("series", help="Equivalent series resistance")
    s.add_argument("resistors", nargs="+"); s.set_defaults(func=_series)

    pa = sub.add_parser("parallel", help="Equivalent parallel resistance")
    pa.add_argument("resistors", nargs="+"); pa.set_defaults(func=_parallel)

    d = sub.add_parser("divider", help="Voltage divider output")
    d.add_argument("vin"); d.add_argument("r1"); d.add_argument("r2")
    d.set_defaults(func=_divider)

    rc = sub.add_parser("rc", help="RC filter cutoff, time constant, and response")
    rc.add_argument("r"); rc.add_argument("c")
    rc.add_argument("-f", help="Evaluate gain/phase at this frequency")
    rc.add_argument("--kind", choices=["lowpass", "highpass"], default="lowpass")
    rc.set_defaults(func=_rc)

    rl_ = sub.add_parser("rl", help="RL time constant and cutoff")
    rl_.add_argument("r"); rl_.add_argument("l"); rl_.set_defaults(func=_rl)

    x = sub.add_parser("rlc", help="RLC resonance, Q, bandwidth and damping")
    x.add_argument("r"); x.add_argument("l"); x.add_argument("c")
    x.add_argument("--topology", choices=["series", "parallel"], default="series")
    x.set_defaults(func=_rlc)

    z = sub.add_parser("impedance", help="Complex impedance of R, L, C at a frequency")
    z.add_argument("-f", required=True, help="Frequency, e.g. 1k")
    z.add_argument("-r"); z.add_argument("-l"); z.add_argument("-c")
    z.add_argument("--parallel", action="store_true", help="Combine in parallel (default series)")
    z.set_defaults(func=_impedance)

    n = sub.add_parser("nearest", help="Closest standard E12/E24 resistor")
    n.add_argument("value"); n.add_argument("--series", choices=["E12", "E24"], default="E12")
    n.set_defaults(func=_nearest)

    op = sub.add_parser("opamp", help="Design an op-amp gain stage with standard resistors")
    op.add_argument("gain", help="Target gain (magnitude for inverting)")
    op.add_argument("--kind", choices=["non-inverting", "inverting"], default="non-inverting")
    op.add_argument("--series", choices=["E12", "E24"], default="E12")
    op.set_defaults(func=_opamp)

    so = sub.add_parser("solve", help="Nodal analysis of a SPICE-style netlist file")
    so.add_argument("netlist", help="Path to a netlist, e.g. examples/wheatstone.cir")
    so.add_argument("--thevenin", nargs=2, metavar=("A", "B"),
                    help="Also give the Thevenin equivalent between two nodes")
    so.set_defaults(func=_solve)

    th = sub.add_parser("thevenin", help="Thevenin/Norton of a voltage divider + max power")
    th.add_argument("vs"); th.add_argument("r1"); th.add_argument("r2")
    th.add_argument("--load", help="Also evaluate a specific load resistance")
    th.set_defaults(func=_thevenin)

    le = sub.add_parser("led", help="LED current-limiting resistor")
    le.add_argument("supply", help="Supply voltage, e.g. 5")
    le.add_argument("--color", default="red",
                    help="LED colour (red, green, blue, white...) or forward voltage")
    le.add_argument("-i", "--current", default="20m", help="LED current (default 20m)")
    le.add_argument("-n", "--count", type=int, default=1, help="LEDs in series")
    le.add_argument("--series", choices=["E12", "E24"], default="E12")
    le.set_defaults(func=_led)

    tm = sub.add_parser("555", help="555 timer: astable or monostable")
    tm.add_argument("mode", choices=["astable", "monostable"])
    tm.add_argument("-c", required=True, help="Timing capacitor, e.g. 10u")
    tm.add_argument("--r1"); tm.add_argument("--r2")
    tm.add_argument("-f", help="Target frequency (astable design)")
    tm.add_argument("--duty", help="Target duty cycle 0.5-1 (astable design)")
    tm.add_argument("-r", help="Timing resistor (monostable)")
    tm.add_argument("--width", help="Target pulse width (monostable design)")
    tm.add_argument("--series", choices=["E12", "E24"], default="E12")
    tm.add_argument("--exact", action="store_true", help="Exact values, don't round to E-series")
    tm.set_defaults(func=_timer)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
