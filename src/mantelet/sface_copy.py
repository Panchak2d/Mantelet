"""A PyTorch copy of the SFace recogniser, and the check that the copy matches OpenCV.

A protection that is tuned with gradients needs a model PyTorch can differentiate.
The face match in the red team runs the original ONNX file through OpenCV. If the
copy and OpenCV disagree, a result on the copy says nothing about the red team's
face match. So the copy is checked first, on real aligned faces, against OpenCV.

OpenCV feeds the network an aligned 112 by 112 crop as an RGB array with values 0
to 255, no mean and no scaling, and returns the raw vector (``FaceRecognizerSF.feature``
calls ``blobFromImage`` with scale 1, zero mean and red-blue swapping on). The
copy takes the same input.

The pass limits are fixed here before any copy result exists. They are a Guess:
float32 arithmetic in two libraries should agree to far better than these limits,
so a copy that misses them is wrong and not merely noisy.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from mantelet import faces

INPUT_SIDE = 112
MIN_FACES = 10
MIN_COPY_COSINE = 0.999
MAX_PAIR_GAP = 0.01


class CopyError(Exception):
    """The PyTorch copy could not be built or run."""


def to_network_input(aligned_bgr: np.ndarray) -> np.ndarray:
    """Turn an aligned BGR crop into the network input: float32, RGB, channels first, 0 to 255."""
    if aligned_bgr.shape != (INPUT_SIDE, INPUT_SIDE, 3) or aligned_bgr.dtype != np.uint8:
        raise ValueError(
            f"expected a {INPUT_SIDE} by {INPUT_SIDE} by 3 uint8 crop, "
            f"got {aligned_bgr.shape} of {aligned_bgr.dtype}"
        )
    return np.ascontiguousarray(aligned_bgr[:, :, ::-1].transpose(2, 0, 1), dtype=np.float32)


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("cannot compare a vector of zeros")
    return vectors / norms


def compare(reference: np.ndarray, copy: np.ndarray) -> dict:
    """Compare OpenCV vectors with copy vectors for the same faces, one row per face.

    ``cosines`` holds the agreement of each face. ``pair_gap`` is the largest
    difference in cosine similarity between any two faces, measured by OpenCV's
    vectors and by the copy's. ``disagreements`` counts pairs where the two sides
    differ on whether the faces are the same person.
    """
    reference, copy = np.asarray(reference, np.float64), np.asarray(copy, np.float64)
    if reference.ndim != 2 or reference.shape != copy.shape:
        raise ValueError(
            f"expected two arrays of the same 2D shape, got {reference.shape}, {copy.shape}"
        )
    if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(copy)):
        raise ValueError("vectors must be finite")
    a, b = _unit_rows(reference), _unit_rows(copy)
    cosines = np.sum(a * b, axis=1)
    upper = np.triu_indices(len(a), k=1)
    gap_matrix = np.abs(a @ a.T - b @ b.T)[upper]
    threshold = faces.COSINE_MATCH_THRESHOLD
    disagreements = int(np.sum(((a @ a.T)[upper] >= threshold) != ((b @ b.T)[upper] >= threshold)))
    pair_gap = float(gap_matrix.max()) if gap_matrix.size else 0.0
    lowest = float(cosines.min()) if cosines.size else float("nan")
    passed = len(a) >= MIN_FACES and lowest >= MIN_COPY_COSINE and pair_gap <= MAX_PAIR_GAP
    return {
        "faces": len(a),
        "cosines": [float(c) for c in cosines],
        "lowest_cosine": lowest,
        "pair_gap": pair_gap,
        "pairs": int(gap_matrix.size),
        "disagreements": disagreements,
        "passed": bool(passed),
    }


def render_report(result: dict, meta: dict) -> str:
    """Plain Markdown report of one copy check, with the fixed limits beside the numbers."""
    verdict = "PASSED" if result["passed"] else "FAILED"
    lines = [
        "# SFace copy check",
        "",
        f"Result: {verdict}",
        "",
        f"- Dataset: {meta['dataset_name']} ({meta['dataset_licence']})",
        f"- Photos sampled: {meta['sampled']}. Photos with no face found: {meta['no_face']}",
        f"- Faces compared: {result['faces']} (at least {MIN_FACES} needed)",
        f"- Lowest cosine between the copy and OpenCV for one face: "
        f"{result['lowest_cosine']:.6f} (at least {MIN_COPY_COSINE} needed)",
        f"- Largest difference in pair similarity: {result['pair_gap']:.6f} "
        f"over {result['pairs']} pairs (at most {MAX_PAIR_GAP} allowed)",
        f"- Pairs where the copy and OpenCV disagree on the same person decision: "
        f"{result['disagreements']}",
        f"- Seed: {meta['seed']}",
        "",
        "The limits were fixed before this run and are a Guess. A pass says the copy "
        "reproduces OpenCV on these faces. It says nothing about any protection.",
        "",
    ]
    return "\n".join(lines)


def load_copy(models_dir: str | Path):
    """Build the PyTorch copy from the verified SFace file. Needs the ``ml`` extra."""
    try:
        import onnx
        from onnx2torch import convert
    except ImportError as error:
        raise CopyError(
            f"{error}. Install the extra with: uv sync --extra dev --extra ml"
        ) from error
    data = faces.read_verified_model(models_dir, faces.RECOGNISER)
    try:
        module = convert(onnx.load_model_from_string(data))
    except Exception as error:  # the converter raises many types for an unsupported operator
        raise CopyError(f"onnx2torch could not convert the SFace file: {error}") from error
    module.eval()
    for parameter in module.parameters():
        parameter.requires_grad_(False)
    return module


def copy_vectors(module, aligned: Sequence[np.ndarray]) -> np.ndarray:
    """Run the copy on each aligned crop, one at a time, and return one row per crop."""
    import torch

    rows = []
    with torch.no_grad():
        for crop in aligned:
            batch = torch.from_numpy(to_network_input(crop)).unsqueeze(0)
            try:
                rows.append(module(batch).reshape(-1).numpy())
            except Exception as error:
                raise CopyError(f"the copy failed on a face crop: {error}") from error
    return np.stack(rows)
