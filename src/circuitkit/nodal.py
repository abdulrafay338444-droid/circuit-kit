"""Nodal analysis (modified nodal analysis, MNA) for small DC networks.

Build a circuit from resistors, independent current sources and independent
voltage sources, then solve for every node voltage. Node 0 is ground.

>>> ckt = Circuit()
>>> ckt.voltage_source(1, 0, 10)
>>> ckt.resistor(1, 2, 1000)
>>> ckt.resistor(2, 0, 1000)
>>> round(ckt.solve().voltages[2], 6)
5.0

Pure Python (no NumPy needed) — fine for the tens of nodes you meet in coursework.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Union

Node = Union[int, str]  # Union keeps Python 3.9 support


@dataclass
class Solution:
    voltages: dict[Node, float]
    """Voltage of every node relative to ground (node 0)."""
    source_currents: list[float]
    """Current through each voltage source, in the order added, flowing
    from its + terminal through the external circuit back to its − terminal
    (i.e. the current the source delivers)."""

    def voltage(self, a: Node, b: Node = 0) -> float:
        """Voltage between two nodes, V(a) − V(b)."""
        return self.voltages[a] - self.voltages[b]


@dataclass
class Circuit:
    resistors: list[tuple[Node, Node, float]] = field(default_factory=list)
    current_sources: list[tuple[Node, Node, float]] = field(default_factory=list)
    voltage_sources: list[tuple[Node, Node, float]] = field(default_factory=list)

    # ---- building ------------------------------------------------------
    def resistor(self, a: Node, b: Node, ohms: float) -> None:
        if ohms <= 0:
            raise ValueError("resistance must be positive (use a voltage source of 0 V for a wire)")
        self.resistors.append((a, b, ohms))

    def current_source(self, from_node: Node, to_node: Node, amps: float) -> None:
        """Current source pushing `amps` out of from_node and into to_node."""
        self.current_sources.append((from_node, to_node, amps))

    def voltage_source(self, plus: Node, minus: Node, volts: float) -> None:
        """Ideal voltage source with V(plus) − V(minus) = volts."""
        self.voltage_sources.append((plus, minus, volts))

    # ---- solving -------------------------------------------------------
    def nodes(self) -> list[Node]:
        seen: dict[Node, None] = {}
        for a, b, _ in self.resistors + self.current_sources + self.voltage_sources:
            seen.setdefault(a); seen.setdefault(b)
        return [n for n in seen if n != 0]

    def solve(self) -> Solution:
        nodes = self.nodes()
        idx = {n: i for i, n in enumerate(nodes)}
        n, m = len(nodes), len(self.voltage_sources)
        size = n + m
        if size == 0:
            raise ValueError("circuit is empty")
        A = [[0.0] * size for _ in range(size)]
        z = [0.0] * size

        for a, b, r in self.resistors:
            g = 1 / r
            for p, q in ((a, b), (b, a)):
                if p != 0:
                    A[idx[p]][idx[p]] += g
                    if q != 0:
                        A[idx[p]][idx[q]] -= g

        for a, b, i in self.current_sources:
            if a != 0: z[idx[a]] -= i
            if b != 0: z[idx[b]] += i

        for k, (p, q, v) in enumerate(self.voltage_sources):
            row = n + k
            if p != 0:
                A[idx[p]][row] += 1; A[row][idx[p]] += 1
            if q != 0:
                A[idx[q]][row] -= 1; A[row][idx[q]] -= 1
            z[row] = v

        x = _gauss_solve(A, z)
        voltages: dict[Node, float] = {0: 0.0}
        voltages.update({node: x[idx[node]] for node in nodes})
        # MNA's unknown is the current flowing into the + terminal; the
        # current the source delivers to the circuit is its negative.
        currents = [-x[n + k] for k in range(m)]
        return Solution(voltages, currents)

    def thevenin(self, a: Node, b: Node = 0) -> tuple[float, float]:
        """Thevenin equivalent (Vth, Rth) seen between nodes a and b."""
        v_th = self.solve().voltage(a, b)
        dead = copy.deepcopy(self)  # turn off independent sources
        dead.voltage_sources = [(p, q, 0.0) for p, q, _ in dead.voltage_sources]
        dead.current_sources = [(p, q, 0.0) for p, q, _ in dead.current_sources]
        dead.current_source(b, a, 1.0)  # inject a 1 A test current
        r_th = dead.solve().voltage(a, b)
        return v_th, r_th


def _gauss_solve(A: list[list[float]], z: list[float]) -> list[float]:
    """Solve A x = z by Gaussian elimination with partial pivoting."""
    n = len(z)
    M = [row[:] + [z[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-15:
            raise ValueError("circuit can't be solved: check for floating nodes "
                             "or loops of voltage sources")
        M[col], M[pivot] = M[pivot], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            if f:
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


def parse_netlist(text: str) -> Circuit:
    """Build a Circuit from a SPICE-style netlist.

    One element per line, ``name node node value``; ``*`` or ``#`` starts a comment::

        V1 in 0 12      * 12 V source, + at "in"
        R1 in out 4.7k
        R2 out 0 10k
        I1 0 out 1m     * 1 mA pushed into "out"

    The first letter picks the element: R (resistor), V (voltage source),
    I (current source). Node ``0`` (or ``gnd``) is ground; other node names can
    be numbers or words. Values accept SI prefixes like 4.7k or 100m.
    """
    from .units import parse  # local import avoids a cycle at package import

    def node(token: str) -> Node:
        if token.lower() in ("0", "gnd", "ground"):
            return 0
        return int(token) if token.isdigit() else token

    ckt = Circuit()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("*")[0].split("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"line {lineno}: expected 'name node node value', got {raw!r}")
        name, a, b, value = parts
        kind = name[0].upper()
        v = parse(value)
        if kind == "R":
            ckt.resistor(node(a), node(b), v)
        elif kind == "V":
            ckt.voltage_source(node(a), node(b), v)
        elif kind == "I":
            ckt.current_source(node(a), node(b), v)
        else:
            raise ValueError(f"line {lineno}: unknown element {name!r} (use R, V or I)")
    return ckt
