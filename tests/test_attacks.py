import numpy as np
import pytest
from PIL import Image

from mantelet import attacks, redteam, toy


def pixels(img):
    return np.asarray(img, dtype=np.int16)


@pytest.mark.parametrize("attack", attacks.standard_attacks(), ids=lambda attack: attack.name)
def test_every_attack_returns_an_rgb_photo_of_the_same_size(attack, photos):
    original = photos["photo0"]
    for strength in (attack.strengths[0], attack.strengths[-1]):
        result = attack.run(original, strength, 1)
        assert result.size == original.size and result.mode == "RGB"


def test_attacks_repeat_for_one_seed_and_noise_attacks_change_with_the_seed(photos):
    original = photos["photo0"]
    noisy = next(a for a in attacks.standard_attacks() if a.name == "noise-then-jpeg")
    first = noisy.run(original, 6, 1)
    assert np.array_equal(pixels(first), pixels(noisy.run(original, 6, 1)))
    assert not np.array_equal(pixels(first), pixels(noisy.run(original, 6, 2)))


def test_the_identity_attack_changes_nothing_and_is_a_copy(photos):
    original = photos["photo0"]
    result = attacks.standard_attacks()[0].run(original, 0.0, 0)
    assert result is not original and np.array_equal(pixels(result), pixels(original))


def test_bit_depth_keeps_only_the_asked_number_of_levels(photos):
    bit_depth = next(a for a in attacks.standard_attacks() if a.name == "bit-depth")
    assert len(np.unique(pixels(bit_depth.run(photos["photo0"], 2, 0)))) <= 4


def test_attack_settings_that_make_no_sense_are_refused(photos):
    by_name = {a.name: a for a in attacks.standard_attacks()}
    original = photos["photo0"]
    for name, bad in (("median-filter", 4), ("bit-depth", 0), ("shrink-and-enlarge", 0)):
        with pytest.raises(ValueError):
            by_name[name].run(original, bad, 0)
    with pytest.raises(ValueError, match="narrow_sigma"):
        attacks.known_band_attack(5, 2)
    with pytest.raises(ValueError, match="cutoffs"):
        attacks.collusion_attack([], cutoffs=(0,))


def test_known_band_removal_strips_a_pattern_in_the_band_it_was_told_about(photos):
    original = photos["photo0"]
    shape = (128, 128, 3)
    marked = toy._add(original, toy.band_pattern(shape, 5, 0.7, 1.5))
    result = attacks.known_band_attack(0.7, 1.5).run(marked, 1.0, 0)
    assert redteam.survival(original, marked, result) < 0.4


def protect_all(name, photos):
    item = next(p for p in toy.TOY_PROTECTIONS if p.name == name)
    return [item.apply(photo, index) for index, photo in enumerate(photos.values())]


def surviving(name, photos):
    """Mean survival under the collusion attack, at the cutoff that works best."""
    protected = protect_all(name, photos)
    attack = attacks.collusion_attack(protected)
    return min(
        float(
            np.mean(
                [
                    redteam.survival(photo, shielded, attack.run(shielded, cutoff, 0))
                    for photo, shielded in zip(photos.values(), protected, strict=True)
                ]
            )
        )
        for cutoff in attack.strengths
    )


def test_collusion_removes_a_pattern_shared_by_every_photo_but_not_one_that_differs(photos):
    assert surviving("toy-band-shared", photos) < 0.4
    assert surviving("toy-band", photos) > 0.8


def test_collusion_says_when_it_has_too_few_photos_or_a_photo_of_another_size(photos):
    few = attacks.collusion_attack(list(photos.values())[: attacks.MIN_COLLUDERS - 1])
    with pytest.raises(attacks.AttackNotApplicable, match="at least"):
        few.run(photos["photo0"], 8.0, 0)
    enough = attacks.collusion_attack(list(photos.values()))
    with pytest.raises(attacks.AttackNotApplicable, match="built for"):
        enough.run(Image.new("RGB", (64, 64)), 8.0, 0)
