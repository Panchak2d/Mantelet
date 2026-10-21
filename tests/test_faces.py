import hashlib
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mantelet import faces

REPO_MODELS = Path(__file__).resolve().parent.parent / "data" / "models"


def fake_model(content=b"model bytes"):
    return faces.ModelFile(
        folder="f",
        filename="m.onnx",
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        licence="test",
    )


def test_cosine_similarity_of_equal_opposite_and_unrelated_vectors():
    a = np.array([1.0, 0.0])
    assert faces.cosine_similarity(a, a * 3) == pytest.approx(1.0)
    assert faces.cosine_similarity(a, -a) == pytest.approx(-1.0)
    assert faces.cosine_similarity(a, np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_cosine_similarity_rejects_zero_and_mismatched_vectors():
    with pytest.raises(ValueError):
        faces.cosine_similarity(np.zeros(3), np.ones(3))
    with pytest.raises(ValueError):
        faces.cosine_similarity(np.ones(3), np.ones(4))


def test_same_person_includes_the_threshold_and_never_matches_without_a_face():
    assert faces.same_person(faces.COSINE_MATCH_THRESHOLD)
    assert not faces.same_person(faces.COSINE_MATCH_THRESHOLD - 0.001)
    assert not faces.same_person(None)


def test_verified_model_bytes_are_returned_for_the_pinned_file(tmp_path):
    (tmp_path / "m.onnx").write_bytes(b"model bytes")
    assert faces.read_verified_model(tmp_path, fake_model()) == b"model bytes"


def test_a_changed_model_file_is_rejected(tmp_path):
    (tmp_path / "m.onnx").write_bytes(b"model bytez")
    with pytest.raises(faces.ModelFileError, match="not the pinned"):
        faces.read_verified_model(tmp_path, fake_model())


def test_a_missing_model_file_says_how_to_fetch_it(tmp_path):
    with pytest.raises(faces.ModelFileError, match="fetch_models"):
        faces.read_verified_model(tmp_path, fake_model())


def test_loading_the_face_model_refuses_a_tampered_file_before_opencv_reads_it(tmp_path):
    (tmp_path / faces.DETECTOR.filename).write_bytes(b"not an onnx file")
    with pytest.raises(faces.ModelFileError):
        faces.OpenCVFaceModel(tmp_path)


@pytest.mark.skipif(not REPO_MODELS.is_dir(), reason="run scripts/fetch_models.py first")
def test_the_real_detector_finds_no_face_in_a_plain_photo():
    model = faces.OpenCVFaceModel(REPO_MODELS)
    assert model.embed(Image.new("RGB", (256, 256), (120, 130, 140))) is None
    assert model.embed(Image.new("RGB", (8, 8))) is None
