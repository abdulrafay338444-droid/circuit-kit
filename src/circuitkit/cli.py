"""Command-line interface: `circuitkit <command> ...`."""

from __future__ import annotations

import argparse
import sys

from . import basics, eseries, filters, impedance, opamp, rlc
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
