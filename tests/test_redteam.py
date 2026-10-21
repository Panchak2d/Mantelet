import json

import numpy as np
import pytest
from PIL import Image

from mantelet import redteam, report, toy


def noise_protection(amount):
    def apply(img, seed):
        noise = np.random.default_rng(seed).integers(-amount, amount + 1, (*img.size[::-1], 3))
        return Image.fromarray(np.clip(np.asarray(img) + noise, 0, 255).astype(np.uint8))

    return toy.Protection("loud", "Visible grain", apply)


def run(photos, protections=toy.TOY_PROTECTIONS[:1], seed=0, names=None):
    names = names or list(photos)
    meta = redteam.build_meta(
        {"id": "x", "name": "X set", "licence": "Test licence", "status": "approved"}, len(names)
    )
    return redteam.run_redteam(names, photos.__getitem__, protections, seed, meta)


@pytest.fixture(scope="module")
def small_run():
    from conftest import smooth_photo

    photos = {f"p{index}": smooth_photo(index, 64) for index in range(3)}
    return run(photos)


def test_survival_is_one_for_no_attack_zero_for_a_perfect_removal_and_none_without_a_change(photos):
    original = photos["photo0"]
    protected = toy.TOY_PROTECTIONS[0].apply(original, 1)
    assert redteam.survival(original, protected, protected) == 1.0
    assert redteam.survival(original, protected, original) == 0.0
    assert redteam.survival(original, original, protected) is None


def test_survival_ignores_changes_that_have_nothing_to_do_with_the_protection(photos):
    original = photos["photo0"]
    protected = toy.TOY_PROTECTIONS[1].apply(original, 1)
    unrelated_image = Image.fromarray(
        np.clip(
            np.asarray(original, dtype=np.float64)
            + np.random.default_rng(9).normal(0, 6, (128, 128, 3)),
            0,
            255,
        ).astype(np.uint8)
    )
    assert abs(redteam.survival(original, protected, unrelated_image)) < 0.1


def test_survival_refuses_images_of_different_sizes(photos):
    original = photos["photo0"]
    with pytest.raises(ValueError, match="same size"):
        redteam.survival(original, original, Image.new("RGB", (64, 64)))


def test_an_attack_result_counts_only_above_both_quality_limits():
    assert redteam.is_admissible(redteam.QUALITY_FLOOR_PSNR, redteam.QUALITY_FLOOR_SSIM)
    assert not redteam.is_admissible(redteam.QUALITY_FLOOR_PSNR - 0.1, 0.99)
    assert not redteam.is_admissible(40.0, redteam.QUALITY_FLOOR_SSIM - 0.01)
    assert not redteam.is_admissible(40.0, None)


def test_fine_grain_is_removed_by_a_cleanup_filter_at_acceptable_quality(photos):
    only = {name: photos[name] for name in list(photos)[:4]}
    (summary,) = redteam.summarise(run(only))
    assert summary["levels"][0]["survival"]["mean"] == 1.0
    assert summary["levels"][1]["survival"]["mean"] < 0.3
    assert summary["levels"][1]["held"] == 0


def test_the_best_attack_never_gets_worse_when_the_attacker_may_use_more_levels(small_run):
    (summary,) = redteam.summarise(small_run)
    means = [level["survival"]["mean"] for level in summary["levels"]]
    assert means == sorted(means, reverse=True)


def test_every_photo_is_attacked_at_every_strength_and_collusion_reports_it_could_not_run(
    small_run,
):
    strengths = sum(len(a[3]) for a in small_run["meta"]["attacks"] if a[0] != "collusion")
    assert len(small_run["records"]) == 3 * strengths
    (missing,) = small_run["not_applicable"]
    assert missing["attack"] == "collusion" and missing["photos"] == 3


def test_a_protection_that_already_breaks_the_quality_floor_is_left_out_and_counted(photos):
    only = {name: photos[name] for name in list(photos)[:2]}
    (summary,) = redteam.summarise(run(only, [noise_protection(40)]))
    assert summary["unusable"] == 2
    assert summary["levels"][0]["photos"] == 0 and summary["levels"][0]["survival"] is None


def test_results_repeat_for_one_seed_and_can_be_written_as_strict_json(small_run, photos):
    json.dumps(small_run, allow_nan=False)
    from conftest import smooth_photo

    again = run({f"p{index}": smooth_photo(index, 64) for index in range(3)})
    assert again["records"] == small_run["records"]


def test_unreadable_tiny_and_huge_photos_are_skipped_with_a_reason():
    def load(name):
        if name == "broken":
            raise ValueError("bad file")
        if name == "huge":
            return Image.new("RGB", (redteam.MAX_LONG_SIDE + 1, 64))
        return Image.new("RGB", (20, 20))

    results = redteam.run_redteam(["broken", "tiny", "huge"], load, toy.TOY_PROTECTIONS, 0, {})
    reasons = {item["image"]: item["reason"] for item in results["skipped"]}
    assert "bad file" in reasons["broken"]
    assert "smaller than" in reasons["tiny"] and "longer side" in reasons["huge"]
    assert results["records"] == []


def test_more_photos_than_the_limit_are_refused():
    names = [str(index) for index in range(redteam.MAX_IMAGES + 1)]
    with pytest.raises(ValueError, match="at most"):
        redteam.run_redteam(names, Image.new, toy.TOY_PROTECTIONS, 0, {})


def test_the_report_names_the_toys_carries_the_licence_and_never_claims_protection(small_run):
    text = report.render_redteam_report(small_run)
    assert "Test licence" in text and "Every protection in this run is a toy" in text
    assert "protects" not in text.lower()
    assert "Attacks that could not run" in text and "toy-white" in text


def test_the_records_are_written_as_csv(small_run, tmp_path):
    path = tmp_path / "records.csv"
    redteam.write_records_csv(small_run["records"], path)
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(redteam.RECORD_FIELDS)


def test_the_survival_limit_matches_the_fixed_test_plan_number():
    assert redteam.SURVIVAL_FLOOR == 0.5
