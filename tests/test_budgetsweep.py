import numpy as np
import pytest
from conftest import smooth_photo
from PIL import Image

from mantelet import budgetgraph, budgetsweep, protectcheck, toy


def noise_at(budget):
    def apply(img, seed):
        noise = np.random.default_rng(seed).integers(-budget, budget + 1, (*img.size[::-1], 3))
        return Image.fromarray(np.clip(np.asarray(img) + noise, 0, 255).astype(np.uint8))

    return toy.Protection(f"noise-{budget}", "Random grain", apply)


class SameFaceUnlessLoud:
    """A stand-in model: the vector turns away from the original as the photo gets noisier."""

    def __init__(self, reference):
        self.reference = np.asarray(reference, dtype=np.float64)

    def embed(self, img):
        pixels = np.asarray(img, dtype=np.float64)
        if pixels.shape[0] < 32:
            return None
        loud = float(np.abs(pixels - pixels.mean(axis=(0, 1))).std() > 200)
        return np.array([1.0 - loud, loud])


def photos_and_faces(count=3, size=128):
    photos = [(i, f"p{i}", smooth_photo(i, size)) for i in range(count)]
    return photos, {name: np.array([1.0, 0.0]) for _, name, _ in photos}


def test_a_sweep_gives_one_summary_per_budget_with_scores_that_fall_as_the_budget_grows():
    photos, vectors = photos_and_faces()
    summaries, rows = budgetsweep.run_sweep(
        photos, vectors, noise_at, [1, 4, 40], SameFaceUnlessLoud([1, 0]), seed=0
    )
    assert [s["budget"] for s in summaries] == [1, 4, 40]
    assert len(rows) == 9 and all(set(r) >= {"budget", "psnr", "ssim", "centre"} for r in rows)
    assert summaries[0]["psnr_worst"] > summaries[1]["psnr_worst"] > summaries[2]["psnr_worst"]
    assert summaries[0]["below_floor"] == 0
    assert summaries[2]["below_floor"] == 3 and summaries[2]["survival_photos"] == 0
    assert summaries[0]["face"]["eligible"] == 3


def test_the_gate_budget_is_the_largest_one_with_no_photo_below_the_floor():
    points = [
        {"budget": 2, "photos": 3, "below_floor": 0},
        {"budget": 8, "photos": 3, "below_floor": 0},
        {"budget": 16, "photos": 3, "below_floor": 1},
        {"budget": 4, "photos": 3, "below_floor": 0},
    ]
    assert budgetsweep.gate_budget(points) == 8
    assert budgetsweep.gate_budget([{"budget": 4, "photos": 3, "below_floor": 3}]) is None
    assert budgetsweep.gate_budget([]) is None


def test_the_graph_points_carry_the_worst_scores_and_draw_without_error():
    photos, vectors = photos_and_faces()
    summaries, _ = budgetsweep.run_sweep(
        photos, vectors, noise_at, [1, 4], SameFaceUnlessLoud([1, 0]), seed=0
    )
    points = budgetsweep.graph_points(summaries)
    assert points[0]["psnr"] == summaries[0]["psnr_worst"]
    assert points[0]["face_match"] == summaries[0]["face"]["strict"]["rate"]
    assert "<svg" in budgetgraph.render_budget_graph(points, "noise sweep")


def test_the_pieces_check_passes_inside_the_limits_and_fails_on_any_one_miss():
    good = protectcheck.evaluate([0.9995] * 10, [1e-4] * 3, [0.6] * 5)
    assert good["passed"]
    assert not protectcheck.evaluate([0.9995] * 9, [1e-4], [0.6])["crop_ok"]
    assert not protectcheck.evaluate([0.9995] * 10, [0.02], [0.6])["gradient_ok"]
    assert not protectcheck.evaluate([0.9995] * 10, [1e-4], [1.5])["jpeg_ok"]
    assert not protectcheck.evaluate([0.998] + [0.9995] * 9, [1e-4], [0.6])["passed"]
    with pytest.raises(ValueError, match="NaN"):
        protectcheck.evaluate([float("nan")], [1e-4], [0.6])


def test_the_pieces_report_says_what_was_measured_and_that_it_proves_nothing_about_protection():
    result = protectcheck.evaluate([0.9995] * 10, [1e-4], [0.6])
    meta = {
        "dataset_name": "X set",
        "dataset_licence": "Test licence",
        "sampled": 12,
        "no_face": 2,
        "seed": 0,
    }
    text = protectcheck.render_report(result, meta)
    assert "Result: PASSED" in text and "says nothing about any protection" in text
