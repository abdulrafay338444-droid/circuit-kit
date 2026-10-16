import math
from pathlib import Path

import pytest

from circuitkit import led, nodal, thevenin, timer555
from circuitkit.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


# ---- nodal analysis -----------------------------------------------------

def test_divider_via_nodal():
    ckt = nodal.Circuit()
    ckt.voltage_source(1, 0, 12)
    ckt.resistor(1, 2, 2000)
    ckt.resistor(2, 0, 1000)
    sol = ckt.solve()
    assert sol.voltages[2] == pytest.approx(4)
    assert sol.source_currents[0] == pytest.approx(12 / 3000)  # current delivered


def test_current_source_into_resistor():
    ckt = nodal.Circuit()
    ckt.current_source(0, "x", 2e-3)
    ckt.resistor("x", 0, 1000)
    assert ckt.solve().voltages["x"] == pytest.approx(2)


def test_superposition_two_sources():
    # 10 V source through 1k to node m, 1 mA injected at m, 1k from m to ground.
    ckt = nodal.Circuit()
    ckt.voltage_source("s", 0, 10)
    ckt.resistor("s", "m", 1000)
    ckt.resistor("m", 0, 1000)
    ckt.current_source(0, "m", 1e-3)
    # V-only: 5 V. I-only: 1 mA into 1k||1k = 0.5 V. Total 5.5 V.
    assert ckt.solve().voltage("m") == pytest.approx(5.5)


def test_series_voltage_sources_stack():
    ckt = nodal.Circuit()
    ckt.voltage_source(1, 0, 5)
    ckt.voltage_source(2, 1, 3)
    ckt.resistor(2, 0, 100)
    sol = ckt.solve()
    assert sol.voltages[2] == pytest.approx(8)
    assert sol.source_currents[1] == pytest.approx(0.08)


def test_floating_node_is_reported():
    ckt = nodal.Circuit()
    ckt.voltage_source(1, 0, 5)
    ckt.resistor(2, 3, 100)  # not connected to anything else
    with pytest.raises(ValueError, match="floating"):
        ckt.solve()


def test_thevenin_from_network_matches_hand_formula():
    ckt = nodal.Circuit()
    ckt.voltage_source("vs", 0, 12)
    ckt.resistor("vs", "out", 4700)
    ckt.resistor("out", 0, 10_000)
    assert ckt.thevenin("out") == pytest.approx(thevenin.of_divider(12, 4700, 10_000))


def test_netlist_wheatstone_bridge():
    ckt = nodal.parse_netlist((EXAMPLES / "wheatstone.cir").read_text())
    sol = ckt.solve()
    vth, rth = ckt.thevenin("a", "b")
    # Bridge without R5: Va = 5, Vb = 10*1.2/2.2; R5 then loads it.
    r_open = 500 + 1200 * 1000 / 2200
    assert rth == pytest.approx(r_open * 10_000 / (r_open + 10_000))
    assert vth == pytest.approx((5 - 10 * 1.2 / 2.2) * 10_000 / (r_open + 10_000))
    assert sol.voltage("top") == pytest.approx(10)


def test_netlist_errors():
    with pytest.raises(ValueError, match="unknown element"):
        nodal.parse_netlist("C1 1 0 1u")
    with pytest.raises(ValueError, match="expected"):
        nodal.parse_netlist("R1 1 0")


# ---- Thevenin / Norton ----------------------------------------------------

def test_conversions_round_trip():
    i_n, r_n = thevenin.to_norton(10, 2000)
    assert (i_n, r_n) == pytest.approx((5e-3, 2000))
    assert thevenin.to_thevenin(i_n, r_n) == pytest.approx((10, 2000))
    assert thevenin.from_measurements(10, 5e-3) == pytest.approx((10, 2000))


def test_max_power_transfer():
    rl, pmax = thevenin.max_power(10, 50)
    assert rl == 50 and pmax == pytest.approx(0.5)
    assert thevenin.load_power(10, 50, 50) == pytest.approx(pmax)
    for other in (10, 25, 100, 200):  # every other load gets less
        assert thevenin.load_power(10, 50, other) < pmax
    assert thevenin.efficiency(50, 50) == pytest.approx(0.5)


# ---- LED ---------------------------------------------------------------

def test_led_exact_and_standard():
    assert led.exact_resistor(5, 2.0, 0.02) == pytest.approx(150)
    d = led.design(12, "blue", 0.015, n_series=3)
    assert d["r_exact"] == pytest.approx(160)
    assert d["r_standard"] == 180           # rounded up, never down
    assert d["current"] <= 0.015
    assert d["power_rating"] >= 2 * d["resistor_power"]


def test_led_supply_too_low():
    with pytest.raises(ValueError, match="too low"):
        led.exact_resistor(5, 3.2, 0.02, n_series=2)
    with pytest.raises(ValueError, match="unknown LED colour"):
        led.forward_voltage("ultraviolet-ish")


# ---- 555 -----------------------------------------------------------------

def test_astable_textbook_values():
    t = timer555.astable(1000, 10_000, 10e-6)
    assert t["t_high"] == pytest.approx(math.log(2) * 11_000 * 10e-6)
    assert t["frequency"] == pytest.approx(1 / (math.log(2) * 21_000 * 10e-6))
    # the datasheet shortcut 1.44/((R1+2R2)C) rounds 1/ln2 = 1.4427, so ~0.2% off
    assert t["frequency"] == pytest.approx(1.44 / (21_000 * 10e-6), rel=5e-3)
    assert 0.5 < t["duty_cycle"] < 0.53


def test_astable_design_exact_hits_target():
    d = timer555.design_astable(1000, 0.6, 10e-9, series=None)
    assert d["frequency"] == pytest.approx(1000)
    assert d["duty_cycle"] == pytest.approx(0.6)


def test_astable_design_with_real_parts_is_close():
    d = timer555.design_astable(1000, 0.6, 10e-9, series="E24")
    assert d["frequency"] == pytest.approx(1000, rel=0.08)
    assert d["duty_cycle"] == pytest.approx(0.6, abs=0.03)


def test_astable_rejects_low_duty():
    with pytest.raises(ValueError, match="duty"):
        timer555.design_astable(1000, 0.4, 10e-9)


def test_monostable():
    assert timer555.monostable(100_000, 10e-6) == pytest.approx(1.0986, rel=1e-4)
    d = timer555.design_monostable(1.0, 10e-6, series=None)
    assert d["pulse_width"] == pytest.approx(1.0)


# ---- CLI ---------------------------------------------------------------

def test_cli_analysis_commands(capsys):
    assert main(["solve", str(EXAMPLES / "wheatstone.cir"), "--thevenin", "a", "b"]) == 0
    out = capsys.readouterr().out
    assert "V(a)" in out and "Thevenin" in out
    assert main(["thevenin", "12", "4.7k", "10k", "--load", "2.2k"]) == 0
    assert "Norton" in capsys.readouterr().out
    assert main(["led", "5"]) == 0
    assert "150 Ω" in capsys.readouterr().out
    assert main(["555", "astable", "-c", "10n", "-f", "1k", "--duty", "0.6"]) == 0
    assert "duty" in capsys.readouterr().out
    assert main(["555", "monostable", "-c", "100u", "--width", "5"]) == 0
    assert main(["solve", "does-not-exist.cir"]) == 1
    assert main(["555", "astable", "-c", "10n"]) == 1
