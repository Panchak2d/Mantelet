"""Toy protections, made to test the red team tools and for nothing else.

A toy protection adds a small hidden pattern to a photo. It does nothing against
any editing model or face matcher. Its only use is that we know exactly what it
did and how it is weak, so we can check that the red team tools find the weak
ones and do not claim to break the strong one.

* ``toy-white`` adds fine, random grain, different in every photo. Any cleanup
  filter should remove it.
* ``toy-band`` adds a smooth pattern in a band of coarse spatial frequencies,
  different in every photo. Cleanup filters should remove less of it than of
  ``toy-white``.
* ``toy-band-shared`` adds the same smooth pattern to every photo. Cleanup
  filters should remove as little of it as of ``toy-band``, but an attacker holding
  several protected photos can estimate it and subtract it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

PATTERN_RMS = 2.0
BAND_NARROW_SIGMA = 4.0
BAND_WIDE_SIGMA = 16.0
SHARED_KEY = 20261021


@dataclass(frozen=True)
class Protection:
    """One protection. ``apply`` gets the photo and a seed that is different for every photo.

    ``band`` is the pair of Gaussian sigmas that bound the spatial frequencies the
    protection writes its change into, or None when it has no such band. The level 3
    known band attack uses the band the protection itself declares.
    """

    name: str
    description: str
    apply: Callable[[Image.Image, int], Image.Image]
    band: tuple[float, float] | None = None


def _add(img: Image.Image, pattern: np.ndarray) -> Image.Image:
    if img.mode != "RGB":
        raise ValueError(f"expected an RGB image, got mode {img.mode}")
    pixels = np.asarray(img, dtype=np.float32) + pattern
    return Image.fromarray(np.clip(np.rint(pixels), 0, 255).astype(np.uint8))


def white_pattern(shape: tuple[int, int, int], seed: int) -> np.ndarray:
    """Random plus or minus ``PATTERN_RMS`` on every value."""
    signs = np.random.default_rng(seed).integers(0, 2, shape) * 2 - 1
    return (signs * PATTERN_RMS).astype(np.float32)


def band_pattern(
    shape: tuple[int, int, int],
    seed: int,
    narrow_sigma: float = BAND_NARROW_SIGMA,
    wide_sigma: float = BAND_WIDE_SIGMA,
) -> np.ndarray:
    """Random pattern held to one band of spatial frequencies, with an RMS of ``PATTERN_RMS``.

    The band is what a difference of two Gaussian filters with the given sigmas passes.
    """
    noise = np.random.default_rng(seed).normal(0.0, 1.0, shape).astype(np.float32)
    band = cv2.GaussianBlur(
        noise, (0, 0), narrow_sigma, borderType=cv2.BORDER_REFLECT_101
    ) - cv2.GaussianBlur(noise, (0, 0), wide_sigma, borderType=cv2.BORDER_REFLECT_101)
    return band * (PATTERN_RMS / float(band.std()))


def _shape(img: Image.Image) -> tuple[int, int, int]:
    return img.size[1], img.size[0], 3


TOY_PROTECTIONS = (
    Protection(
        "toy-white",
        "Fine random grain, different in every photo",
        lambda img, seed: _add(img, white_pattern(_shape(img), seed)),
    ),
    Protection(
        "toy-band",
        "Smooth pattern in one band of spatial frequencies, different in every photo",
        lambda img, seed: _add(img, band_pattern(_shape(img), seed)),
        band=(BAND_NARROW_SIGMA, BAND_WIDE_SIGMA),
    ),
    Protection(
        "toy-band-shared",
        "The same smooth pattern in every photo",
        lambda img, _seed: _add(img, band_pattern(_shape(img), SHARED_KEY)),
        band=(BAND_NARROW_SIGMA, BAND_WIDE_SIGMA),
    ),
)
