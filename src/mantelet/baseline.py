"""Measure the baseline: what ordinary photo processing does when nothing protects the photo.

For every photo and every condition in ``CONDITIONS`` the runner records how much
the pixels changed and, when a face model is given, whether the face still matches
the original. Later experiments compare their numbers against these. The runner
keeps no pixels. The results hold only numbers and photo names.

Rules for the face numbers, fixed before any protection result exists:

* A photo whose original face is not found is left out of the face numbers and
  counted separately.
* When the processed face is not found, that counts as no match.
* The match rate is matches divided by the photos whose original face was found.
"""

from __future__ import annotations

import csv
import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image

from mantelet import faces, image, metrics

MAX_IMAGES = 2000
MIN_IMAGE_SIDE = 64
WILSON_Z = 1.96

SCORE_NAMES = ("mse", "psnr", "max_abs_difference", "ssim")
# For each score, which direction is the worst case.
_WORST = {"mse": max, "psnr": min, "max_abs_difference": max, "ssim": min}

RECORD_FIELDS = (
    "image",
    "condition",
    *SCORE_NAMES,
    "original_face_found",
    "processed_face_found",
    "similarity",
    "matched",
)


@dataclass(frozen=True)
class Condition:
    """One thing done to a photo. ``apply`` gets the photo and a seed for any randomness."""

    name: str
    description: str
    apply: Callable[[Image.Image, int], Image.Image]


CONDITIONS = (
    Condition(
        "identity", "No change. A control: a face must match itself", lambda img, _: img.copy()
    ),
    Condition("jpeg-75", "JPEG at quality 75", lambda img, _: image.jpeg_compress(img, 75)),
    Condition("blur-1", "Gaussian blur, radius 1", lambda img, _: image.gaussian_blur(img, 1.0)),
    Condition(
        "noise-5", "Gaussian noise, std 5", lambda img, s: image.add_gaussian_noise(img, 5.0, s)
    ),
    Condition(
        "noise-15", "Gaussian noise, std 15", lambda img, s: image.add_gaussian_noise(img, 15.0, s)
    ),
    Condition(
        "platform-pipeline",
        "Fixed pipeline: long side 512, centre crop 80 percent, JPEG 75",
        lambda img, _: image.platform_pipeline(img),
    ),
    Condition(
        "mild-pipeline",
        "Milder pipeline: shrink only above 1080 pixels, JPEG 85, no crop",
        lambda img, _: image.mild_platform_pipeline(img),
    ),
    Condition(
        "noise-15-then-pipeline",
        "Noise std 15, then the fixed pipeline",
        lambda img, s: image.platform_pipeline(image.add_gaussian_noise(img, 15.0, s)),
    ),
)


def derive_seed(seed: int, image_index: int, condition_index: int) -> int:
    """A different, repeatable seed for each photo and condition."""
    return int(np.random.SeedSequence([seed, image_index, condition_index]).generate_state(1)[0])


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def wilson_interval(successes: int, total: int) -> tuple[float, float] | None:
    """95 percent Wilson score interval for a rate. None when there are no trials."""
    if total == 0:
        return None
    p = successes / total
    z2 = WILSON_Z**2
    centre = (p + z2 / (2 * total)) / (1 + z2 / total)
    half = WILSON_Z * math.sqrt(p * (1 - p) / total + z2 / (4 * total**2)) / (1 + z2 / total)
    return max(0.0, centre - half), min(1.0, centre + half)


def library_versions() -> dict[str, str]:
    names = ("mantelet", "numpy", "pillow", "opencv-python-headless")
    return {name: version(name) for name in names} | {"python": sys.version.split()[0]}


def impostor_summary(vectors: Sequence[np.ndarray]) -> dict | None:
    """Compare every pair of different photos. A match between two photos is a false match.

    This assumes two different photos show two different people. If a dataset has
    two photos of one person, that pair counts as a false match, so the result is
    an upper bound.
    """
    if len(vectors) < 2:
        return None
    unit = np.stack([vector / np.linalg.norm(vector) for vector in vectors])
    similarities = (unit @ unit.T)[np.triu_indices(len(unit), k=1)]
    return {
        "pairs": int(similarities.size),
        "false_matches": int(np.sum(similarities >= faces.COSINE_MATCH_THRESHOLD)),
        "max_similarity": float(similarities.max()),
        "mean_similarity": float(similarities.mean()),
    }


def run_baseline(
    names: Sequence[str],
    load: Callable[[str], Image.Image],
    embedder: faces.FaceEmbedder | None,
    seed: int,
    meta: dict,
    conditions: Sequence[Condition] = CONDITIONS,
) -> dict:
    """Run every condition on every photo and return the results as plain data."""
    if len(names) > MAX_IMAGES:
        raise ValueError(f"at most {MAX_IMAGES} photos per run, got {len(names)}")
    records, skipped, original_vectors = [], [], []
    for index, name in enumerate(names):
        try:
            original = load(name)
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            skipped.append({"image": name, "reason": f"could not be read: {error}"})
            continue
        if min(original.size) < MIN_IMAGE_SIDE:
            skipped.append({"image": name, "reason": f"smaller than {MIN_IMAGE_SIDE} pixels"})
            continue
        original_vector = embedder.embed(original) if embedder is not None else None
        if original_vector is not None:
            original_vectors.append(original_vector)
        for condition_index, condition in enumerate(conditions):
            processed = condition.apply(original, derive_seed(seed, index, condition_index))
            records.append(
                _record(name, condition.name, original, processed, embedder, original_vector)
            )
    return {
        "meta": meta | {"seed": seed, "conditions": [(c.name, c.description) for c in conditions]},
        "records": records,
        "skipped": skipped,
        "impostor": impostor_summary(original_vectors) if embedder is not None else None,
    }


def _record(name, condition, original, processed, embedder, original_vector) -> dict:
    record = dict.fromkeys(RECORD_FIELDS)
    record |= {"image": name, "condition": condition}
    if processed.size == original.size:
        scores = metrics.compare(original, processed).to_dict()
        record |= {key: _finite(value) for key, value in scores.items()}
    if embedder is not None:
        vector = embedder.embed(processed)
        similarity = None
        if original_vector is not None and vector is not None:
            similarity = faces.cosine_similarity(original_vector, vector)
        record |= {
            "original_face_found": original_vector is not None,
            "processed_face_found": vector is not None,
            "similarity": similarity,
            "matched": faces.same_person(similarity),
        }
    return record


def summarise(results: dict) -> list[dict]:
    """One summary per condition: mean and worst case of each score, and face match numbers."""
    summaries = []
    for name, description in results["meta"]["conditions"]:
        rows = [row for row in results["records"] if row["condition"] == name]
        summary = {"condition": name, "description": description, "photos": len(rows)}
        for score in SCORE_NAMES:
            values = [row[score] for row in rows if row[score] is not None]
            summary[score] = (
                {"mean": float(np.mean(values)), "worst": _WORST[score](values), "n": len(values)}
                if values
                else None
            )
        summary["face"] = _face_summary(rows)
        summaries.append(summary)
    return summaries


def _face_summary(rows: list[dict]) -> dict | None:
    if not rows or rows[0]["original_face_found"] is None:
        return None
    eligible = [row for row in rows if row["original_face_found"]]
    matches = sum(1 for row in eligible if row["matched"])
    found = sum(1 for row in eligible if row["processed_face_found"])
    similarities = [row["similarity"] for row in eligible if row["similarity"] is not None]
    return {
        "original_not_found": len(rows) - len(eligible),
        "eligible": len(eligible),
        "processed_found": found,
        "matches": matches,
        "match_rate": matches / len(eligible) if eligible else None,
        "match_interval": wilson_interval(matches, len(eligible)),
        "mean_similarity": float(np.mean(similarities)) if similarities else None,
        "min_similarity": min(similarities) if similarities else None,
    }


def write_records_csv(records: Sequence[dict], path: str | Path) -> None:
    """Write one row per photo and condition."""
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def build_meta(dataset: dict, sampled: int, with_faces: bool) -> dict:
    """Facts that let someone repeat the run: the dataset, tools, models and fixed numbers."""
    return {
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": dataset,
        "photos_sampled": sampled,
        "libraries": library_versions(),
        "face_models": (
            [
                {"file": m.filename, "sha256": m.sha256, "licence": m.licence}
                for m in faces.MODEL_FILES
            ]
            if with_faces
            else None
        ),
        "thresholds": {
            "cosine_match": faces.COSINE_MATCH_THRESHOLD,
            "detection_score": faces.DETECTION_SCORE_THRESHOLD,
        },
        "fixed_pipeline": {
            "long_side": image.PIPELINE_LONG_SIDE,
            "crop_keep": image.PIPELINE_CROP_KEEP,
            "jpeg_quality": image.PIPELINE_JPEG_QUALITY,
        },
        "mild_pipeline": {
            "max_long_side": image.MILD_PIPELINE_MAX_LONG_SIDE,
            "jpeg_quality": image.MILD_PIPELINE_JPEG_QUALITY,
        },
    }
