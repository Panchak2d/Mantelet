"""How much of a protection survives the fixed pipeline, for many crop positions.

The fixed pipeline always crops from the centre, which starts the crop at one
fixed place compared with the 8 pixel grid of JPEG (claim C-021). This module
measures survival for the centre crop, for seeded random crops, and for every
crop corner that lies on the 8 pixel grid, so a result cannot depend on one lucky
position. The pipeline numbers stay the fixed ones.

Survival here is the share of the protection's own change that is left after the
pipeline. The ideal change is the protection's change (protected minus original)
shrunk and cropped without JPEG. The actual change is the protected photo minus
the original photo, both run through the pipeline. Survival is how far the actual
change lies along the ideal one. 1 means JPEG and resizing removed nothing.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

from mantelet import image

DEFAULT_RANDOM_CROPS = 16
GRID = 8
ALIGNED_PER_AXIS = 6


def _shrink(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Resize a float array of shape (height, width, 3) the way the pipeline resizes a photo."""
    channels = [
        np.asarray(
            Image.fromarray(np.ascontiguousarray(values[:, :, c], dtype=np.float32)).resize(
                size, image.Resampling.LANCZOS
            ),
            dtype=np.float64,
        )
        for c in range(3)
    ]
    return np.stack(channels, axis=2)


def _spread_out(offsets: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep at most ``ALIGNED_PER_AXIS`` evenly spaced left and top values, for speed.

    The first and last values are always kept, and every kept corner is on the grid.
    """

    def pick(values: list[int]) -> set[int]:
        if len(values) <= ALIGNED_PER_AXIS:
            return set(values)
        positions = np.linspace(0, len(values) - 1, ALIGNED_PER_AXIS).round().astype(int)
        return {values[i] for i in positions}

    lefts = pick(sorted({left for left, _ in offsets}))
    tops = pick(sorted({top for _, top in offsets}))
    return [(left, top) for left, top in offsets if left in lefts and top in tops]


def crop_offsets(
    size: tuple[int, int], seed: int, random_crops: int = DEFAULT_RANDOM_CROPS
) -> dict:
    """The crop corners to test for a photo of this size, grouped by kind.

    ``size`` is the size of the photo before the pipeline. Corners are in the
    resized photo.
    """
    if random_crops < 0:
        raise ValueError(f"random_crops must not be negative, got {random_crops}")
    resized = image.resized_size(size)
    keep = image.PIPELINE_CROP_KEEP
    seeds = np.random.SeedSequence(seed).spawn(random_crops)
    return {
        "centre": [image.centre_crop_offset(resized, keep)],
        "random": [
            image.random_crop_offset(resized, keep, int(s.generate_state(1)[0])) for s in seeds
        ],
        "aligned": _spread_out(image.grid_aligned_offsets(resized, keep, GRID)),
    }


def survival_at_offsets(
    original: Image.Image,
    protected: Image.Image,
    offsets: list[tuple[int, int]],
) -> list[float | None]:
    """Survival after the fixed pipeline for each crop corner. None when the change vanished."""
    for img in (original, protected):
        if img.mode != "RGB":
            raise ValueError(f"expected an RGB image, got mode {img.mode}")
    if original.size != protected.size:
        raise ValueError("the two images must be the same size")
    target = image.resized_size(original.size)
    shrunk_original = image.resize_long_side(original, image.PIPELINE_LONG_SIDE)
    shrunk_protected = image.resize_long_side(protected, image.PIPELINE_LONG_SIDE)
    change = np.asarray(protected, dtype=np.float64) - np.asarray(original, dtype=np.float64)
    ideal_full = _shrink(change, target)
    keep = image.PIPELINE_CROP_KEEP
    for left, top in offsets:
        image.crop_at(Image.new("L", target), left, top, keep)
    results: list[float | None] = []
    for left, top in offsets:
        crop_width, crop_height = image.crop_size(target, keep)
        ideal = ideal_full[top : top + crop_height, left : left + crop_width]
        energy = float(np.sum(ideal**2))
        out_original = _jpeg_crop(shrunk_original, left, top)
        out_protected = _jpeg_crop(shrunk_protected, left, top)
        if energy == 0:
            results.append(None)
            continue
        actual = out_protected - out_original
        results.append(float(np.sum(actual * ideal) / energy))
    return results


def _jpeg_crop(img: Image.Image, left: int, top: int) -> np.ndarray:
    cropped = image.crop_at(img, left, top, image.PIPELINE_CROP_KEEP)
    return np.asarray(image.jpeg_compress(cropped, image.PIPELINE_JPEG_QUALITY), dtype=np.float64)


def summarise(values: list[float | None]) -> dict | None:
    """Mean, lowest and highest of the values that exist. None when none exist."""
    kept = [v for v in values if v is not None and math.isfinite(v)]
    if not kept:
        return None
    return {"mean": float(np.mean(kept)), "worst": min(kept), "best": max(kept), "n": len(kept)}


def sweep(
    original: Image.Image,
    protected: Image.Image,
    seed: int,
    random_crops: int = DEFAULT_RANDOM_CROPS,
) -> dict:
    """Survival after the fixed pipeline at the centre, at random corners and at grid corners."""
    groups = crop_offsets(original.size, seed, random_crops)
    flat = [offset for group in groups.values() for offset in group]
    values = survival_at_offsets(original, protected, flat)
    out, start = {}, 0
    for name, group in groups.items():
        out[name] = summarise(values[start : start + len(group)])
        start += len(group)
    every = summarise(values)
    out["all"] = every
    out["worst"] = None if every is None else every["worst"]
    return out
