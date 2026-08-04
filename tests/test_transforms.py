import pytest
from macropulse.metrics.transforms import percent_change, weighted_coverage

def test_percent_change() -> None:
    assert percent_change(110, 100) == pytest.approx(10.0)

def test_percent_change_rejects_zero_base() -> None:
    with pytest.raises(ValueError): percent_change(1, 0)

def test_coverage() -> None:
    assert weighted_coverage([0.5, 0.2], [0.5, 0.3, 0.2]) == pytest.approx(0.7)
