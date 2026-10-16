import pytest

from circuitkit import ohms_law, parallel, power, series, voltage_divider


def test_ohms_law_solves_each_unknown():
    assert ohms_law(voltage=12, resistance=4)["current"] == pytest.approx(3)
    assert ohms_law(current=2, resistance=5)["voltage"] == pytest.approx(10)
    assert ohms_law(voltage=9, current=0.5)["resistance"] == pytest.approx(18)


def test_ohms_law_needs_exactly_two():
    with pytest.raises(ValueError):
        ohms_law(voltage=5)
    with pytest.raises(ValueError):
        ohms_law(voltage=5, current=1, resistance=5)


def test_power():
    assert power(voltage=10, current=2) == pytest.approx(20)
    assert power(current=2, resistance=10) == pytest.approx(40)


def test_series_and_parallel():
    assert series([100, 220, 330]) == pytest.approx(650)
    assert parallel([100, 100]) == pytest.approx(50)
    assert parallel([1000, 2000, 2000]) == pytest.approx(500)


def test_parallel_rejects_zero():
    with pytest.raises(ValueError):
        parallel([100, 0])


def test_voltage_divider():
    assert voltage_divider(5, 10_000, 10_000) == pytest.approx(2.5)
    assert voltage_divider(12, 1000, 2000) == pytest.approx(8)
