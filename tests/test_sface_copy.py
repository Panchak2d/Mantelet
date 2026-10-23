import sys

import check_sface_copy
import numpy as np
import pytest
from test_baseline_scripts import approved_dataset

from mantelet import sface_copy


def vectors(count=12, dim=128, seed=0):
    return np.random.default_rng(seed).normal(size=(count, dim))


def test_the_network_input_is_rgb_channels_first_float_and_unscaled():
    crop = np.zeros((112, 112, 3), dtype=np.uint8)
    crop[0, 0] = (10, 20, 30)
    result = sface_copy.to_network_input(crop)
    assert result.shape == (3, 112, 112) and result.dtype == np.float32
    assert list(result[:, 0, 0]) == [30.0, 20.0, 10.0]


@pytest.mark.parametrize(
    "bad",
    [np.zeros((112, 112), np.uint8), np.zeros((64, 64, 3), np.uint8), np.zeros((112, 112, 3))],
)
def test_a_crop_of_the_wrong_shape_or_type_is_refused(bad):
    with pytest.raises(ValueError):
        sface_copy.to_network_input(bad)


def test_an_identical_copy_passes_and_a_scaled_copy_still_passes_because_only_direction_counts():
    reference = vectors()
    for copy in (reference, reference * 3.0):
        result = sface_copy.compare(reference, copy)
        assert result["passed"] and result["disagreements"] == 0
        assert result["lowest_cosine"] == pytest.approx(1.0)


def test_a_copy_with_noise_above_the_limits_fails_on_the_cosine_and_the_pair_gap():
    reference = vectors()
    result = sface_copy.compare(
        reference, reference + np.random.default_rng(1).normal(size=reference.shape)
    )
    assert not result["passed"] and result["lowest_cosine"] < sface_copy.MIN_COPY_COSINE
    assert result["pair_gap"] > sface_copy.MAX_PAIR_GAP


def test_too_few_faces_cannot_pass_and_bad_input_is_refused():
    few = vectors(count=sface_copy.MIN_FACES - 1)
    assert not sface_copy.compare(few, few)["passed"]
    with pytest.raises(ValueError):
        sface_copy.compare(vectors(), vectors(count=11))
    with pytest.raises(ValueError):
        sface_copy.compare(np.zeros((12, 4)), np.ones((12, 4)))
    broken = vectors()
    broken[0, 0] = np.nan
    with pytest.raises(ValueError):
        sface_copy.compare(broken, vectors())


def test_the_report_states_the_verdict_the_limits_and_that_it_says_nothing_about_a_protection():
    meta = {"dataset_name": "X", "dataset_licence": "L", "sampled": 12, "no_face": 0, "seed": 0}
    text = sface_copy.render_report(sface_copy.compare(vectors(), vectors(seed=1)), meta)
    assert "Result: FAILED" in text and "0.999" in text and "nothing about any protection" in text


def test_without_the_ml_extra_the_copy_says_how_to_install_it(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "onnx2torch", None)
    with pytest.raises(sface_copy.CopyError, match="--extra ml"):
        sface_copy.load_copy(tmp_path)


def test_the_script_refuses_unapproved_data_and_a_folder_without_models(
    monkeypatch, tmp_path, capsys
):
    assert (
        check_sface_copy.main(
            ["--dataset-id", "digiface1m", "--source", str(tmp_path), "--models-dir", str(tmp_path)]
        )
        == 1
    )
    assert "needs review" in capsys.readouterr().err
    folder = approved_dataset(monkeypatch, tmp_path)
    args = ["--dataset-id", "unit-test-set", "--source", str(folder)]
    assert check_sface_copy.main([*args, "--models-dir", str(tmp_path / "none")]) == 1
    assert "fetch_models.py" in capsys.readouterr().err
