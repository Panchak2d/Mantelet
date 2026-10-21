import numpy as np
import pytest
from PIL import Image

from mantelet import toy


def protection(name):
    return next(item for item in toy.TOY_PROTECTIONS if item.name == name)


def change(original, protected):
    return np.asarray(protected, dtype=np.float64) - np.asarray(original, dtype=np.float64)


def test_patterns_have_the_stated_strength(photos):
    shape = (128, 128, 3)
    assert toy.white_pattern(shape, 1).std() == pytest.approx(toy.PATTERN_RMS, rel=0.01)
    assert toy.band_pattern(shape, 1).std() == pytest.approx(toy.PATTERN_RMS, rel=0.01)


def test_a_protection_keeps_the_size_and_changes_pixels_only_a_little(photos):
    original = photos["photo0"]
    for item in toy.TOY_PROTECTIONS:
        protected = item.apply(original, 3)
        assert protected.size == original.size and protected.mode == "RGB"
        assert 0 < np.abs(change(original, protected)).max() <= 12


def test_per_photo_patterns_differ_with_the_seed_and_the_shared_pattern_does_not(photos):
    original = photos["photo0"]
    for name in ("toy-white", "toy-band"):
        first = change(original, protection(name).apply(original, 1))
        second = change(original, protection(name).apply(original, 2))
        assert not np.allclose(first, second)
    shared = protection("toy-band-shared")
    one = change(original, shared.apply(original, 1))
    two = change(original, shared.apply(original, 2))
    assert np.allclose(one, two)


def test_a_protection_is_repeatable_for_one_seed(photos):
    original = photos["photo0"]
    first = toy.TOY_PROTECTIONS[1].apply(original, 5)
    second = toy.TOY_PROTECTIONS[1].apply(original, 5)
    assert np.array_equal(np.asarray(first), np.asarray(second))


def test_a_protection_refuses_a_photo_that_is_not_rgb():
    with pytest.raises(ValueError, match="RGB"):
        toy.TOY_PROTECTIONS[0].apply(Image.new("L", (64, 64)), 0)
