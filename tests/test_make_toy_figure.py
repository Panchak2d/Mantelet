import make_toy_figure
import pytest


def test_svg_contains_every_value_and_the_threshold_label():
    svg = make_toy_figure.build_svg()
    for value in ("0.056", "0.009", "0.963", "0.465"):
        assert value in svg
    assert "50 percent pass number" in svg
    assert "not a Mantelet protection result" in svg


def test_value_outside_zero_to_one_is_rejected():
    with pytest.raises(ValueError):
        make_toy_figure.build_svg(bars=(("x", 1.2),))
