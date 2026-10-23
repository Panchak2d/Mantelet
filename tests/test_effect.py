import pytest

from mantelet import effect


def row(image, protection, match, similarity):
    return {"image": image, "protection": protection, "face_match": match, "similarity": similarity}


def pipeline_rows():
    control = [
        row("a", "none", True, 0.9),
        row("b", "none", True, 0.8),
        row("c", "none", True, 0.7),
        row("d", "none", False, None),
        row("e", "none", False, 0.1),
        row("f", "none", None, None),
    ]
    protected = [
        row("a", "p", True, 0.5),
        row("b", "p", False, 0.0),
        row("c", "p", False, None),
        row("d", "p", False, None),
        row("e", "p", False, 0.0),
        row("f", "p", None, None),
    ]
    return control + protected


def test_a_face_state_is_lost_without_a_similarity_and_unknown_without_an_original_face():
    assert effect.face_state(row("a", "p", False, None)) == "lost"
    assert effect.face_state(row("a", "p", False, 0.1)) == "no_match"
    assert effect.face_state(row("a", "p", True, 0.5)) == "match"
    assert effect.face_state(row("a", "p", None, None)) is None


def test_faces_lost_by_the_pipeline_alone_are_left_out_and_a_protected_miss_is_an_attacker_win():
    result = effect.pipeline_effect(pipeline_rows(), "p")
    assert result["with_face"] == 5
    assert result["lost_by_pipeline"] == 1 and result["control_no_match"] == 1
    assert result["eligible"] == 3
    assert result["states"] == {"lost": 1, "no_match": 1, "match": 1}
    assert result["strict"]["wins"] == 2 and result["as_counted"]["wins"] == 1
    assert result["drop"] == pytest.approx(100 / 3)


def test_the_effect_is_none_without_a_control_or_without_any_face():
    without_control = [r for r in pipeline_rows() if r["protection"] == "p"]
    assert effect.pipeline_effect(without_control, "p") is None
    assert effect.pipeline_effect(pipeline_rows(), "missing") is None


def record(image, attack, level, match, similarity, admissible=True, found=True):
    return {
        "image": image,
        "protection": "p",
        "attack": attack,
        "level": level,
        "admissible": admissible,
        "original_face_found": found,
        "face_match": match,
        "similarity": similarity,
    }


def test_a_lost_unattacked_face_is_a_win_and_an_attack_that_loses_the_face_is_not_credit():
    records = [
        record("a", "identity", 0, False, 0.0),
        record("a", "median", 2, True, 0.6),
        record("b", "identity", 0, False, None),
        record("c", "identity", 0, False, 0.0),
        record("c", "median", 2, False, None),
        record("c", "blur", 3, True, 0.9),
        record("d", "identity", 0, None, None, admissible=False),
        record("e", "identity", 0, None, None, found=False),
    ]
    result = effect.level_effect(records, "p", 2)
    assert result["photos"] == 3
    assert result["strict"]["wins"] == 2 and result["as_counted"]["wins"] == 1
    assert result["drop"] == pytest.approx(100 / 3)
    assert effect.level_effect(records, "p", 3)["strict"]["wins"] == 3
    assert effect.level_effect(records, "other", 2) is None
