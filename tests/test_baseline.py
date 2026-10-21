import csv
import json

import numpy as np
import pytest
from PIL import Image

from mantelet import baseline, report

RED, GREEN = (200, 20, 20), (20, 200, 20)


def solid(colour, size=(96, 96)):
    return Image.new("RGB", size, colour)


class ColourEmbedder:
    """Stand-in face model: the vector says which colour channel the top-left pixel favours."""

    def __init__(self, found=lambda img: True):
        self.found = found

    def embed(self, img):
        if not self.found(img):
            return None
        return np.eye(3)[int(np.argmax(img.getpixel((0, 0))))] + 0.001


def run_images(images: dict, embedder=None, seed=0):
    return baseline.run_baseline(list(images), images.__getitem__, embedder, seed, {})


def condition_rows(results, name):
    return [row for row in results["records"] if row["condition"] == name]


def test_every_photo_is_measured_under_every_condition():
    results = run_images({"a": solid(RED), "b": solid(GREEN)})
    assert len(results["records"]) == 2 * len(baseline.CONDITIONS)


def test_identity_control_matches_itself_and_has_no_pixel_change():
    results = run_images({"a": solid(RED)}, ColourEmbedder())
    (row,) = condition_rows(results, "identity")
    assert row["mse"] == 0 and row["max_abs_difference"] == 0
    assert row["psnr"] is None
    assert row["matched"] is True


def test_results_can_be_written_as_strict_json():
    json.dumps(run_images({"a": solid(RED)}, ColourEmbedder()), allow_nan=False)


def test_a_face_not_found_after_processing_counts_as_no_match():
    only_full_size = ColourEmbedder(found=lambda img: img.size == (96, 96))
    results = run_images({"a": solid(RED)}, only_full_size)
    (row,) = condition_rows(results, "platform-pipeline")
    assert row["processed_face_found"] is False and row["matched"] is False
    face = next(s for s in baseline.summarise(results) if s["condition"] == "platform-pipeline")
    assert face["face"]["eligible"] == 1 and face["face"]["match_rate"] == 0.0


def test_photos_without_an_original_face_are_left_out_of_the_face_numbers():
    embedder = ColourEmbedder(found=lambda img: img.getpixel((0, 0))[0] > 100)
    results = run_images({"red": solid(RED), "dark": solid((10, 10, 10))}, embedder)
    face = next(s for s in baseline.summarise(results) if s["condition"] == "identity")["face"]
    assert (face["original_not_found"], face["eligible"], face["matches"]) == (1, 1, 1)


def test_unreadable_and_tiny_photos_are_skipped_with_a_reason():
    def load(name):
        if name == "broken":
            raise ValueError("bad file")
        return solid(RED, (20, 20))

    results = baseline.run_baseline(["broken", "tiny"], load, None, 0, {})
    assert results["records"] == []
    reasons = {item["image"]: item["reason"] for item in results["skipped"]}
    assert "bad file" in reasons["broken"] and "smaller than" in reasons["tiny"]


def test_the_same_seed_repeats_the_run_and_a_new_seed_changes_the_noise():
    images = {"a": solid(RED)}
    assert run_images(images, seed=3)["records"] == run_images(images, seed=3)["records"]
    first = condition_rows(run_images(images, seed=3), "noise-15")[0]["mse"]
    second = condition_rows(run_images(images, seed=4), "noise-15")[0]["mse"]
    assert first != second


def test_without_a_face_model_only_pixel_numbers_are_recorded():
    results = run_images({"a": solid(RED)})
    assert results["impostor"] is None
    assert results["records"][0]["matched"] is None
    assert all(s["face"] is None for s in baseline.summarise(results))


def test_different_colours_do_not_falsely_match_and_equal_ones_do():
    different = run_images({"a": solid(RED), "b": solid(GREEN)}, ColourEmbedder())
    assert different["impostor"]["pairs"] == 1
    assert different["impostor"]["false_matches"] == 0
    same = run_images({"a": solid(RED), "b": solid(RED)}, ColourEmbedder())
    assert same["impostor"]["false_matches"] == 1


def test_more_photos_than_the_limit_are_refused():
    names = [str(i) for i in range(baseline.MAX_IMAGES + 1)]
    with pytest.raises(ValueError, match="at most"):
        baseline.run_baseline(names, solid, None, 0, {})


def test_wilson_interval_gives_known_values_and_handles_no_trials():
    assert baseline.wilson_interval(0, 0) is None
    low, high = baseline.wilson_interval(5, 10)
    assert (low, high) == pytest.approx((0.2366, 0.7634), abs=1e-3)
    low, high = baseline.wilson_interval(10, 10)
    assert high == 1.0 and low == pytest.approx(0.722, abs=1e-3)


def test_each_photo_and_condition_get_their_own_repeatable_seed():
    seeds = {baseline.derive_seed(1, i, c) for i in range(5) for c in range(5)}
    assert len(seeds) == 25
    assert baseline.derive_seed(1, 2, 3) == baseline.derive_seed(1, 2, 3)


def test_records_are_written_as_csv(tmp_path):
    results = run_images({"a": solid(RED)})
    path = tmp_path / "records.csv"
    baseline.write_records_csv(results["records"], path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == len(baseline.CONDITIONS)
    assert tuple(rows[0]) == baseline.RECORD_FIELDS


def meta():
    return baseline.build_meta(
        {"id": "x", "name": "X set", "licence": "Test licence", "status": "approved"}, 1, True
    ) | {"created": "now"}


def test_report_states_dataset_licence_and_never_claims_protection():
    results = baseline.run_baseline(["a"], lambda n: solid(RED), ColourEmbedder(), 0, meta())
    text = report.render_report(results)
    assert "Test licence" in text and "No protection was applied" in text
    assert "protects" not in text.lower()
    assert "Only 1 photos" in text


def test_report_without_faces_says_so_and_lists_skipped_photos():
    def load(name):
        raise OSError("gone")

    results = baseline.run_baseline(["a"], load, None, 0, meta())
    text = report.render_report(results)
    assert "Face matching was not run." in text and "a: could not be read" in text
