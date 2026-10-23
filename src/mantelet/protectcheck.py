"""The check of the pieces a protection is tuned through, and its fixed pass limits.

The copy check (``sface_copy``) shows that the PyTorch copy of SFace gives OpenCV's
face vectors for crops OpenCV aligned. A protection also depends on three other
pieces: our own differentiable crop, the gradient through crop and network, and the
differentiable JPEG. ``scripts/check_protection.py`` measures each on real faces and
compares it with the limits below. They are fixed here before any result exists and
are a Guess: two float32 implementations of the same warp and network should agree
far more closely, so a miss means a wrong piece and not noise.
"""

from __future__ import annotations

from collections.abc import Sequence

MIN_FACES = 10
MIN_CROP_COSINE = 0.999
MAX_GRADIENT_ERROR = 1e-2
MAX_JPEG_GAP = 1.0
GRADIENT_FACES = 3


def evaluate(
    crop_cosines: Sequence[float], gradient_errors: Sequence[float], jpeg_gaps: Sequence[float]
) -> dict:
    """Compare the measurements with the fixed limits.

    ``crop_cosines`` hold, for each face, the cosine between OpenCV's vector for OpenCV's
    crop and the copy's vector for our crop. ``gradient_errors`` hold the relative gap
    between autograd and a finite difference. ``jpeg_gaps`` hold, for each photo, the mean
    absolute pixel gap between our JPEG and Pillow's at quality 75.
    """
    for values in (crop_cosines, gradient_errors, jpeg_gaps):
        if any(value != value for value in values):
            raise ValueError("measurements must not contain NaN")
    crop_ok = len(crop_cosines) >= MIN_FACES and min(crop_cosines, default=0) >= MIN_CROP_COSINE
    gradient_ok = (
        len(gradient_errors) >= 1 and max(gradient_errors, default=1) <= MAX_GRADIENT_ERROR
    )
    jpeg_ok = len(jpeg_gaps) >= 1 and sum(jpeg_gaps) / len(jpeg_gaps) <= MAX_JPEG_GAP
    return {
        "faces": len(crop_cosines),
        "lowest_crop_cosine": min(crop_cosines, default=None),
        "gradient_faces": len(gradient_errors),
        "worst_gradient_error": max(gradient_errors, default=None),
        "jpeg_photos": len(jpeg_gaps),
        "mean_jpeg_gap": sum(jpeg_gaps) / len(jpeg_gaps) if jpeg_gaps else None,
        "crop_ok": bool(crop_ok),
        "gradient_ok": bool(gradient_ok),
        "jpeg_ok": bool(jpeg_ok),
        "passed": bool(crop_ok and gradient_ok and jpeg_ok),
    }


def _number(value: float | None, pattern: str) -> str:
    return "n/a" if value is None else format(value, pattern)


def render_report(result: dict, meta: dict) -> str:
    """Plain Markdown report of one check, with the fixed limits beside the numbers."""
    verdict = "PASSED" if result["passed"] else "FAILED"
    return "\n".join(
        [
            "# Protection pieces check",
            "",
            f"Result: {verdict}",
            "",
            f"- Dataset: {meta['dataset_name']} ({meta['dataset_licence']})",
            f"- Photos sampled: {meta['sampled']}. Photos with no face found: {meta['no_face']}",
            f"- Crop: {result['faces']} faces (at least {MIN_FACES}), lowest cosine between "
            f"OpenCV's vector for OpenCV's crop and the copy's vector for our crop "
            f"{_number(result['lowest_crop_cosine'], '.6f')} (at least {MIN_CROP_COSINE}). "
            f"{'Met' if result['crop_ok'] else 'Not met'}",
            f"- Gradient: {result['gradient_faces']} faces, worst relative gap between autograd "
            f"and a finite difference {_number(result['worst_gradient_error'], '.2e')} "
            f"(at most {MAX_GRADIENT_ERROR:g}). {'Met' if result['gradient_ok'] else 'Not met'}",
            f"- JPEG: {result['jpeg_photos']} photos, mean pixel gap between our JPEG and "
            f"Pillow's at quality 75 {_number(result['mean_jpeg_gap'], '.3f')} "
            f"(at most {MAX_JPEG_GAP:g}). {'Met' if result['jpeg_ok'] else 'Not met'}",
            f"- Seed: {meta['seed']}",
            "",
            "The limits were fixed before this run and are a Guess. A pass says the pieces "
            "reproduce OpenCV and Pillow on these faces. It says nothing about any protection.",
            "",
        ]
    )
