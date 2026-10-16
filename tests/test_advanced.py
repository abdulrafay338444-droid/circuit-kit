import math

import pytest

from circuitkit import eseries, impedance, opamp, rlc
from circuitkit.cli import main


# ---- impedance ----------------------------------------------------------

def test_capacitor_and_inductor_impedance():
    zc = impedance.z_capacitor(1e-6, 1000)
    assert zc.real == 0
    assert zc.imag == pytest.approx(-1 / (2 * math.pi * 1000 * 1e-6))
    zl = impedance.z_inductor(10e-3, 1000)
    assert zl.imag == pytest.approx(2 * math.pi * 1000 * 10e-3)


def test_series_rc_phase_is_minus_45_at_cutoff():
    r, c = 1000, 1e-6
    fc = 1 / (2 * math.pi * r * c)
    z = impedance.z_series([impedance.z_resistor(r), impedance.z_capacitor(c, fc)])
    mag, ang = impedance.polar(z)
    assert mag == pytest.approx(r * math.sqrt(2))
    assert ang == pytest.approx(-45)


def test_series_lc_cancels_at_resonance():
    l, c = 10e-3, 100e-9
    f0 = rlc.resonant_frequency(l, c)
    z = impedance.z_series([impedance.z_inductor(l, f0), impedance.z_capacitor(c, f0)])
    assert abs(z) == pytest.approx(0, abs=1e-9)


def test_parallel_impedance_matches_resistors():
    z = impedance.z_parallel([impedance.z_resistor(100), impedance.z_resistor(100)])
    assert z == pytest.approx(complex(50, 0))


def test_ac_current():
    assert impedance.ac_current(10, complex(5, 0)) == pytest.approx(complex(2, 0))
    with pytest.raises(ValueError):
        impedance.z_capacitor(1e-6, 0)


# ---- RL / RLC -----------------------------------------------------------

def test_rl_basics():
    assert rlc.rl_time_constant(100, 10e-3) == pytest.approx(1e-4)
    assert rlc.rl_cutoff_frequency(100, 10e-3) == pytest.approx(1591.55, rel=1e-4)
    i = rlc.inductor_current(1e-4, 5, 100, 10e-3)
    assert i == pytest.approx(0.05 * (1 - math.exp(-1)))


def test_rlc_resonance_q_bandwidth():
    r, l, c = 10, 10e-3, 100e-9
    f0 = rlc.resonant_frequency(l, c)
    assert f0 == pytest.approx(5032.9, rel=1e-4)
    q = rlc.quality_factor(r, l, c)
    assert q == pytest.approx(math.sqrt(l / c) / r)
    assert rlc.bandwidth(r, l, c) == pytest.approx(f0 / q)
    assert rlc.damping_ratio(r, l, c) == pytest.approx(1 / (2 * q))


def test_damping_classification():
    l, c = 10e-3, 100e-9
    rc = rlc.critical_resistance(l, c)
    assert rlc.damping_type(rc, l, c) == "critically damped"
    assert rlc.damping_type(rc / 10, l, c) == "underdamped"
    assert rlc.damping_type(rc * 10, l, c) == "overdamped"
    rp = rlc.critical_resistance(l, c, "parallel")
    assert rlc.damping_type(rp, l, c, "parallel") == "critically damped"
    # in a parallel RLC, *larger* R means less damping
    assert rlc.damping_type(rp * 10, l, c, "parallel") == "underdamped"


# ---- E-series -----------------------------------------------------------

@pytest.mark.parametrize("value,series,expected", [
    (4600, "E12", 4700), (5000, "E12", 4700), (1040, "E24", 1000),
    (1080, "E24", 1100), (95, "E12", 100), (0.48, "E12", 0.47),
])
def test_nearest(value, series, expected):
    assert eseries.nearest(value, series) == pytest.approx(expected)


def test_standard_values_range():
    vals = eseries.standard_values("E12", 1000, 10000)
    assert vals[0] == 1000 and vals[-1] == 10000
    assert len(vals) == 13


def test_best_ratio_pair():
    a, b = eseries.best_ratio_pair(2.0)
    assert a / b == pytest.approx(2.0, rel=0.05)
    with pytest.raises(ValueError):
        eseries.nearest(-5)


# ---- op-amp -------------------------------------------------------------

def test_gain_formulas():
    assert opamp.inverting_gain(10_000, 1_000) == pytest.approx(-10)
    assert opamp.non_inverting_gain(9_000, 1_000) == pytest.approx(10)
    assert opamp.gain_db(10) == pytest.approx(20)


def test_output_clips_at_rails():
    assert opamp.output_voltage(2, 10, v_supply=12) == 12
    assert opamp.output_voltage(-2, 10, v_supply=12) == -12
    assert opamp.output_voltage(0.5, 10, v_supply=12) == 5


@pytest.mark.parametrize("kind,target", [
    ("non-inverting", 10), ("non-inverting", 2), ("inverting", 4.7), ("inverting", 22),
    ("non-inverting", 3.3), ("inverting", 15),
])
def test_e24_design_hits_target_within_2_percent(kind, target):
    d = opamp.design(target, kind, series="E24")
    assert abs(d["error_percent"]) < 2
    for r in (d["rf"], d["r_other"]):
        assert eseries.nearest(r, "E24") == pytest.approx(r)  # real standard part


def test_e24_beats_or_matches_e12():
    e12 = abs(opamp.design(10)["error_percent"])
    e24 = abs(opamp.design(10, series="E24")["error_percent"])
    assert e24 <= e12


# ---- CLI ---------------------------------------------------------------

def test_cli_new_commands(capsys):
    assert main(["rlc", "10", "10m", "100n"]) == 0
    assert "underdamped" in capsys.readouterr().out
    assert main(["impedance", "-f", "1k", "-r", "1k", "-c", "1u"]) == 0
    assert "°" in capsys.readouterr().out
    assert main(["nearest", "4.6k"]) == 0
    assert "4.7 kΩ" in capsys.readouterr().out
    assert main(["opamp", "10", "--kind", "inverting"]) == 0
    assert "Rf" in capsys.readouterr().out
    assert main(["rl", "100", "10m"]) == 0
    assert main(["impedance", "-f", "1k"]) == 1


@pytest.mark.parametrize("scale", [0.1, 1.0, 10.0])
def test_step_response_starts_at_zero_and_settles(scale):
    l, c = 10e-3, 100e-9
    r = rlc.critical_resistance(l, c) * scale
    assert rlc.series_step_response(0, 5, r, l, c) == pytest.approx(0, abs=1e-9)
    assert rlc.series_step_response(1.0, 5, r, l, c) == pytest.approx(5, abs=1e-6)


def test_underdamped_overshoots_overdamped_does_not():
    l, c = 10e-3, 100e-9
    rc = rlc.critical_resistance(l, c)
    ts = [i * 1e-6 for i in range(5000)]
    under = max(rlc.series_step_response(t, 1, rc * 0.1, l, c) for t in ts)
    over = max(rlc.series_step_response(t, 1, rc * 10, l, c) for t in ts)
    assert under > 1.5
    assert over <= 1.0 + 1e-9
