import numpy as np
import pytest
from conftest import smooth_photo
from PIL import Image

from mantelet import cropsweep, image, toy

BAND, WHITE = toy.TOY_PROTECTIONS[1], toy.TOY_PROTECTIONS[0]


@pytest.fixture(scope="module")
def original():
    return smooth_photo(1, 512)


def test_offsets_cover_the_centre_seeded_random_corners_and_grid_corners(original):
    groups = cropsweep.crop_offsets(original.size, seed=4)
    assert groups["centre"] == [image.centre_crop_offset((512, 512), 0.8)]
    assert len(groups["random"]) == cropsweep.DEFAULT_RANDOM_CROPS
    assert groups["random"] == cropsweep.crop_offsets(original.size, seed=4)["random"]
    assert groups["random"] != cropsweep.crop_offsets(original.size, seed=5)["random"]
    assert groups["aligned"] and all(
        left % 8 == 0 and top % 8 == 0 for left, top in groups["aligned"]
    )
    assert len(groups["aligned"]) <= cropsweep.ALIGNED_PER_AXIS**2


def test_a_smooth_pattern_mostly_survives_the_pipeline_and_fine_grain_does_not(original):
    smooth = cropsweep.sweep(original, BAND.apply(original, 1), seed=0)
    grain = cropsweep.sweep(original, WHITE.apply(original, 1), seed=0)
    assert smooth["worst"] > 0.8
    assert grain["all"]["best"] < 0.2


def test_survival_at_the_centre_matches_for_both_ways_of_asking(original):
    protected = BAND.apply(original, 2)
    centre = image.centre_crop_offset(image.resized_size(original.size), 0.8)
    [value] = cropsweep.survival_at_offsets(original, protected, [centre])
    assert value == pytest.approx(cropsweep.sweep(original, protected, 0)["centre"]["mean"])


def test_a_protection_that_changed_nothing_has_no_survival(original):
    assert cropsweep.sweep(original, original.copy(), seed=0)["worst"] is None


def test_larger_photos_are_shrunk_first_and_sizes_must_match():
    big = smooth_photo(2, 1024)
    value = cropsweep.sweep(big, BAND.apply(big, 1), seed=0, random_crops=2)
    assert value["all"]["n"] >= 3 and 0.5 < value["worst"] < 1.5
    with pytest.raises(ValueError, match="same size"):
        cropsweep.survival_at_offsets(big, Image.new("RGB", (64, 64)), [(0, 0)])
    with pytest.raises(ValueError, match="does not fit"):
        cropsweep.survival_at_offsets(big, big, [(900, 0)])
    with pytest.raises(ValueError, match="negative"):
        cropsweep.crop_offsets(big.size, 0, random_crops=-1)


def test_summarise_ignores_missing_values():
    assert cropsweep.summarise([None, None]) is None
    assert cropsweep.summarise([None, 0.5, 1.0]) == {
        "mean": 0.75,
        "worst": 0.5,
        "best": 1.0,
        "n": 2,
    }


def test_the_sweep_leaves_the_images_unchanged(original):
    protected = BAND.apply(original, 3)
    before = np.asarray(protected).copy()
    cropsweep.sweep(original, protected, 0, random_crops=1)
    assert np.array_equal(np.asarray(protected), before)
