"""Command-line interface: `circuitkit <command> ...`."""

from __future__ import annotations

import argparse
import sys

from . import basics, filters
from .units import format_si, parse


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
