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


def run(photos, protections=toy.TOY_PROTECTIONS[:1], seed=0, names=None, **extra):
    names = names or list(photos)
    meta = redteam.build_meta(
        {"id": "x", "name": "X set", "licence": "Test licence", "status": "approved"}, len(names)
    )
    return redteam.run_redteam(names, photos.__getitem__, protections, seed, meta, **extra)


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


class FaceFor:
    """A stand-in face model. It finds a face only in photos whose first pixel is listed."""

    def __init__(self, found_in):
        self.found_in = found_in

    def embed(self, img):
        return (
            np.array([1.0, 0.0, 0.0])
            if int(np.asarray(img)[0, 0, 0]) % 2 in self.found_in
            else None
        )


class OnlyTheFirstCall:
    """Finds the face in the first photo it sees, which is the original, and never again."""

    def __init__(self):
        self.calls = 0

    def embed(self, _img):
        self.calls += 1
        return np.array([1.0, 0.0]) if self.calls == 1 else None


class AlwaysEdits:
    name = "stand-in edit"

    def succeeds(self, original, candidate, seed):
        return True


def small_photos(count=2):
    from conftest import smooth_photo

    return {f"p{index}": smooth_photo(index, 64) for index in range(count)}


def test_the_known_band_attack_runs_only_on_protections_that_declare_a_band():
    assert toy.TOY_PROTECTIONS[0].band is None
    assert toy.TOY_PROTECTIONS[1].band == toy.TOY_PROTECTIONS[2].band
    without = [a.name for a in redteam.attack_catalogue(band=None)]
    with_band = [a.name for a in redteam.attack_catalogue(band=(4.0, 16.0))]
    assert "known-band-removal" not in without and "known-band-removal" in with_band
    run_result = run(small_photos(), toy.TOY_PROTECTIONS[:2])
    assert {
        r["protection"] for r in run_result["records"] if r["attack"] == "known-band-removal"
    } == {"toy-band"}
    assert "known-band-removal" in [a[0] for a in run_result["meta"]["attacks"]]


def test_a_protection_can_declare_its_own_band_and_the_attack_removes_that_band():
    from conftest import smooth_photo

    def apply(img, seed):
        pattern = toy.band_pattern((img.size[1], img.size[0], 3), seed, 2.0, 5.0)
        return toy._add(img, pattern)

    own = toy.Protection("own", "A band of its own", apply, band=(2.0, 5.0))
    original = smooth_photo(3, 128)
    shielded = own.apply(original, 1)
    attack = {a.name: a for a in redteam.attack_catalogue(band=own.band)}["known-band-removal"]
    cleaned = attack.run(shielded, 0.25, 0)
    assert redteam.survival(original, shielded, cleaned) < 0.3
    wrong = {a.name: a for a in redteam.attack_catalogue(band=(8.0, 32.0))}["known-band-removal"]
    assert redteam.survival(original, shielded, wrong.run(shielded, 0.25, 0)) > 0.6


def test_without_a_face_model_or_editor_the_new_columns_are_empty_and_the_report_says_so():
    result = run(small_photos())
    assert all(
        r["face_match"] is None and r["edit_success"] is None and r["similarity"] is None
        for r in result["records"]
    )
    assert result["meta"]["face_model"] is False and result["meta"]["editor"] is None
    text = report.render_redteam_report(result)
    assert "Face match: not measured" in text and "Edit success: not measured" in text


def test_every_admissible_result_is_matched_against_the_original_face():
    photos = small_photos()
    result = run(photos, face_model=FaceFor({0, 1}))
    admissible = [r for r in result["records"] if r["admissible"]]
    assert admissible and all(r["face_match"] is True for r in admissible)
    assert all(r["original_face_found"] is True for r in result["records"])
    assert all(r["face_match"] is None for r in result["records"] if not r["admissible"])
    top = redteam.summarise(result)[0]["levels"][-1]["face_match"]
    assert top["wins"] == top["photos"] == len(photos)


def test_a_face_not_found_afterwards_counts_as_no_match_and_a_missing_original_is_left_out():
    result = run(small_photos(1), face_model=OnlyTheFirstCall())
    assert all(r["original_face_found"] for r in result["records"])
    assert all(r["face_match"] is False for r in result["records"] if r["admissible"])
    assert redteam.summarise(result)[0]["levels"][0]["face_match"]["wins"] == 0
    nothing = run(small_photos(1), face_model=FaceFor(set()))
    assert all(r["original_face_found"] is False for r in nothing["records"])
    assert all(r["face_match"] is None for r in nothing["records"])
    assert redteam.summarise(nothing)[0]["levels"][0]["face_match"] is None


def test_an_editor_is_run_on_every_admissible_result_and_the_attacker_wins_if_any_edit_works():
    result = run(small_photos(), editor=AlwaysEdits())
    assert all(r["edit_success"] is True for r in result["records"] if r["admissible"])
    assert result["meta"]["editor"] == "stand-in edit"
    rate = redteam.summarise(result)[0]["levels"][0]["edit_success"]
    assert rate["rate"] == 1.0
    assert "stand-in edit" in report.render_redteam_report(result)


def protected_rows(result):
    return [r for r in result["pipeline"] if r["protection"] != "none"]


def test_the_pipeline_record_has_survival_at_many_crop_positions_and_the_centre_face_match():
    result = run(small_photos(), face_model=FaceFor({0, 1}))
    assert len(protected_rows(result)) == 2
    row = protected_rows(result)[0]
    assert row["worst"] <= row["centre"] and row["face_match"] is True
    pipe = redteam.summarise(result)[0]["pipeline"]
    assert pipe["photos"] == 2 and pipe["face_photos"] == 2
    assert "Corners on the 8 pixel grid" in report.render_redteam_report(result)


class FaceOnlyAtFullSize:
    """A stand-in model whose vector differs between the full photo and a cropped one."""

    def __init__(self, size):
        self.size = size

    def embed(self, img):
        return np.array([1.0, 0.0]) if img.size == self.size else np.array([0.0, 1.0])


def test_the_pipeline_face_match_is_counted_against_the_unprotected_original():
    photos = small_photos()
    size = next(iter(photos.values())).size
    result = run(photos, face_model=FaceOnlyAtFullSize(size))
    assert all(r["original_face_found"] for r in result["records"])
    assert all(
        r["face_match"] is False and r["similarity"] == 0.0 for r in protected_rows(result)
    )
    assert redteam.summarise(result)[0]["pipeline"]["face_matched"] == 0


def test_a_face_lost_in_the_pipeline_counts_as_no_match_with_no_similarity():
    result = run(small_photos(1), face_model=OnlyTheFirstCall())
    row = protected_rows(result)[0]
    assert row["face_match"] is False and row["similarity"] is None


def test_the_unprotected_photo_goes_through_the_same_pipeline_as_a_control_without_survival():
    result = run(small_photos(), face_model=FaceFor({0, 1}))
    control = [r for r in result["pipeline"] if r["protection"] == "none"]
    assert [r["image"] for r in control] == [r["image"] for r in protected_rows(result)]
    assert all(r["face_match"] is True and r["centre"] is None for r in control)
    nothing = run(small_photos())
    assert all(r["protection"] != "none" for r in nothing["pipeline"])


def test_results_from_before_these_columns_still_render():
    result = run(small_photos())
    del result["pipeline"], result["meta"]["face_model"], result["meta"]["editor"]
    assert "Not measured in this run." in report.render_redteam_report(result)


def test_a_run_of_a_real_protection_does_not_call_itself_a_toy_run_and_shows_its_band():
    result = run(small_photos(), face_model=FaceFor({0, 1}))
    result["meta"]["subject"] = "pgd"
    result["meta"]["calibration"] = {
        "kind": "pgd",
        "calibration_photos": 8,
        "calibration_budget": 8,
        "band": [0.5, 3.0],
        "band_energy_share": 0.61,
    }
    text = report.render_redteam_report(result)
    assert "Every protection in this run is a toy" not in text
    assert "tuned against a PyTorch copy of SFace" in text
    assert "Declared band: Gaussian sigmas 0.5 and 3 pixels" in text
    assert "Face match beside the unprotected photo" in text
    assert "Toy pattern strength" not in text
