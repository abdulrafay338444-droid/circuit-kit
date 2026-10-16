import math

import pytest

from circuitkit import (capacitor_charge, cutoff_frequency, format_si, gain,
                        gain_db, parse, phase_deg, time_constant)
from circuitkit.cli import main


R, C = 1_000, 1e-6  # 1 kΩ, 1 µF -> f_c ≈ 159.15 Hz


def test_cutoff_and_tau():
    assert time_constant(R, C) == pytest.approx(1e-3)
    assert cutoff_frequency(R, C) == pytest.approx(159.155, rel=1e-4)


def test_minus_3db_at_cutoff():
    fc = cutoff_frequency(R, C)
    assert gain_db(fc, R, C) == pytest.approx(-3.0103, abs=1e-3)
    assert gain_db(fc, R, C, "highpass") == pytest.approx(-3.0103, abs=1e-3)
    assert phase_deg(fc, R, C) == pytest.approx(-45)
    assert phase_deg(fc, R, C, "highpass") == pytest.approx(45)


def test_lowpass_passes_dc_highpass_blocks_it():
    assert gain(0, R, C) == pytest.approx(1)
    assert gain(0, R, C, "highpass") == pytest.approx(0)


def test_capacitor_reaches_63_percent_after_one_tau():
    v = capacitor_charge(time_constant(R, C), 5, R, C)
    assert v == pytest.approx(5 * (1 - math.exp(-1)))


@pytest.mark.parametrize("text,expected", [
    ("4.7k", 4700), ("100n", 1e-7), ("10uF", 1e-5), ("2.2MΩ", 2.2e6),
    ("330", 330), ("1.5e3", 1500), (47, 47.0),
])
def test_parse(text, expected):
    assert parse(text) == pytest.approx(expected)


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse("lots")


def test_format_si():
    assert format_si(4700, "Ω") == "4.7 kΩ"
    assert format_si(0.0025, "A") == "2.5 mA"


def test_cli_rc(capsys):
    assert main(["rc", "1k", "1u"]) == 0
    out = capsys.readouterr().out
    assert "159 Hz" in out and "1 ms" in out


def test_cli_reports_errors(capsys):
    assert main(["parallel", "100", "0"]) == 1
    assert "error" in capsys.readouterr().err
