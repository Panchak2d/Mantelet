"""Find a face in a photo and decide whether two photos show the same person.

Detection uses YuNet and recognition uses SFace, both run through OpenCV from
files in the OpenCV Zoo. Each file is pinned to one repository commit and one
SHA-256 hash, and its hash is checked before OpenCV reads a single byte of it.
The files are never kept in the repository. ``scripts/fetch_models.py`` downloads
them. The licence and training data of each file are recorded in
research/datasets-and-models.md.

A face counts as the same person when the cosine similarity of the two face
vectors is at least ``COSINE_MATCH_THRESHOLD``, the value the SFace authors
publish. The threshold was set on photos of real people. Whether it suits
synthetic faces is a Guess until we measure it (claim C-022).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from mantelet import image

MODEL_COMMIT = "47534e27c9851bb1128ccc0102f1145e27f23f98"

COSINE_MATCH_THRESHOLD = 0.363
DETECTION_SCORE_THRESHOLD = 0.6
DETECTION_NMS_THRESHOLD = 0.3
DETECTION_TOP_K = 5000

# Photos larger than this are shrunk before detection, so one huge file cannot
# use all the memory. Photos smaller than the minimum cannot hold a usable face.
MAX_DETECTION_SIDE = 1024
MIN_DETECTION_SIDE = 32


@dataclass(frozen=True)
class ModelFile:
    """One pinned model file from the OpenCV Zoo."""

    folder: str
    filename: str
    sha256: str
    size: int
    licence: str

    @property
    def url(self) -> str:
        return (
            f"https://github.com/opencv/opencv_zoo/raw/{MODEL_COMMIT}"
            f"/models/{self.folder}/{self.filename}"
        )


DETECTOR = ModelFile(
    folder="face_detection_yunet",
    filename="face_detection_yunet_2023mar.onnx",
    sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    size=232589,
    licence="MIT",
)
RECOGNISER = ModelFile(
    folder="face_recognition_sface",
    filename="face_recognition_sface_2021dec.onnx",
    sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    size=38696353,
    licence="Apache-2.0",
)
MODEL_FILES = (DETECTOR, RECOGNISER)


class ModelFileError(Exception):
    """A model file is missing, or is not the exact file we pinned."""


class FaceEmbedder(Protocol):
    """Anything that turns a photo into a face vector, or None when it finds no face."""

    def embed(self, img: Image.Image) -> np.ndarray | None: ...


def read_verified_model(directory: str | Path, model: ModelFile) -> bytes:
    """Return the bytes of a model file after checking its size and SHA-256 hash."""
    path = Path(directory) / model.filename
    if not path.is_file():
        raise ModelFileError(
            f"model file '{path}' is missing. Run: python scripts/fetch_models.py"
        )
    data = path.read_bytes()
    if len(data) != model.size or hashlib.sha256(data).hexdigest() != model.sha256:
        raise ModelFileError(
            f"model file '{path}' is not the pinned {model.filename}. "
            "Delete it and run: python scripts/fetch_models.py"
        )
    return data


def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
    """Cosine of the angle between two face vectors, from -1 to 1."""
    if first.ndim != 1 or first.shape != second.shape:
        raise ValueError(
            f"expected two vectors of the same length, got {first.shape} and {second.shape}"
        )
    norms = np.linalg.norm(first) * np.linalg.norm(second)
    if norms == 0:
        raise ValueError("cannot compare a vector of zeros")
    return float(np.dot(first, second) / norms)


def same_person(similarity: float | None) -> bool:
    """True when the similarity reaches the fixed threshold. No similarity means no match."""
    return similarity is not None and similarity >= COSINE_MATCH_THRESHOLD


class OpenCVFaceModel:
    """YuNet and SFace loaded from verified bytes. Satisfies ``FaceEmbedder``."""

    def __init__(self, models_dir: str | Path):
        detector_bytes = read_verified_model(models_dir, DETECTOR)
        recogniser_bytes = read_verified_model(models_dir, RECOGNISER)
        no_config = np.empty(0, dtype=np.uint8)
        self._detector = cv2.FaceDetectorYN.create(
            "onnx",
            np.frombuffer(detector_bytes, dtype=np.uint8),
            no_config,
            (320, 320),
            DETECTION_SCORE_THRESHOLD,
            DETECTION_NMS_THRESHOLD,
            DETECTION_TOP_K,
        )
        self._recogniser = cv2.FaceRecognizerSF.create(
            "onnx", np.frombuffer(recogniser_bytes, dtype=np.uint8), no_config
        )

    def embed(self, img: Image.Image) -> np.ndarray | None:
        """Return the face vector of the most confident face, or None if no face is found."""
        if img.mode != "RGB":
            raise ValueError(f"expected an RGB image, got mode {img.mode}")
        if min(img.size) < MIN_DETECTION_SIDE:
            return None
        if max(img.size) > MAX_DETECTION_SIDE:
            img = image.resize_long_side(img, MAX_DETECTION_SIDE)
        bgr = np.ascontiguousarray(np.asarray(img)[:, :, ::-1])
        height, width = bgr.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(bgr)
        if faces is None or len(faces) == 0:
            return None
        best = faces[int(np.argmax(faces[:, -1]))]
        aligned = self._recogniser.alignCrop(bgr, best)
        return np.asarray(self._recogniser.feature(aligned), dtype=np.float32).reshape(-1)
