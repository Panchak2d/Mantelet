"""Attacks that try to remove a protection from a photo.

Every attack takes one protected photo and returns a photo of the same size. An
attack never receives the unprotected original, so it cannot cheat by copying it
back. The adaptive attack in ``collusion_attack`` also receives other protected
photos, which is what an attacker who collected several of them would hold.

Each attack has a list of strengths, weakest first. The red team runner tries
every strength, because a real attacker would tune the strength until the photo
is as clean as it can be while still looking good.

Attacker levels follow docs/research/threat-model.md:

* 0 does nothing.
* 1 runs a basic cleanup filter.
* 2 runs the standard attacks from the papers we read, alone or in a row.
* 3 has our code and knows how the protection is built.

The attacks that need a diffusion model (DiffPure and noisy upscaling) are not
here. They need PyTorch and a GPU.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from mantelet import image

MIN_COLLUDERS = 5
MAX_COLLUDER_CUTOFF = 256.0

Run = Callable[[Image.Image, float, int], Image.Image]


class AttackNotApplicable(ValueError):
    """The attack cannot run on this photo, for example because no photos of its size were given."""


@dataclass(frozen=True)
class Attack:
    """One attack. ``run`` gets the photo, one of ``strengths`` and a seed for any randomness."""

    name: str
    level: int
    description: str
    strengths: tuple[float, ...]
    run: Run


def _pixels(img: Image.Image) -> np.ndarray:
    if img.mode != "RGB":
        raise ValueError(f"expected an RGB image, got mode {img.mode}")
    return np.asarray(img)


def _to_image(values: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(np.rint(values), 0, 255).astype(np.uint8))


def _jpeg(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    return image.jpeg_compress(img, int(strength))


def _blur(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    return image.gaussian_blur(img, strength)


def _down_up(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    if not 0 < strength <= 1:
        raise ValueError(f"scale must be above 0 and at most 1, got {strength}")
    width, height = img.size
    small = img.resize(
        (max(1, round(width * strength)), max(1, round(height * strength))),
        image.Resampling.LANCZOS,
    )
    return small.resize(img.size, image.Resampling.BICUBIC)


def _median(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    size = int(strength)
    if size < 3 or size % 2 == 0:
        raise ValueError(f"median size must be an odd number from 3, got {strength}")
    return Image.fromarray(cv2.medianBlur(np.ascontiguousarray(_pixels(img)), size))


def _bit_depth(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    bits = int(strength)
    if not 1 <= bits <= 8:
        raise ValueError(f"bits must be from 1 to 8, got {strength}")
    levels = 2**bits - 1
    return _to_image(np.rint(_pixels(img) / 255.0 * levels) / levels * 255.0)


def _non_local_means(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    if not math.isfinite(strength) or strength <= 0:
        raise ValueError(f"strength must be above 0, got {strength}")
    bgr = np.ascontiguousarray(_pixels(img)[:, :, ::-1])
    cleaned = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
    return Image.fromarray(np.ascontiguousarray(cleaned[:, :, ::-1]))


def _noise_then_jpeg(img: Image.Image, strength: float, seed: int) -> Image.Image:
    return image.jpeg_compress(image.add_gaussian_noise(img, strength, seed), 75)


def _noise_then_non_local_means(img: Image.Image, strength: float, seed: int) -> Image.Image:
    return _non_local_means(image.add_gaussian_noise(img, strength, seed), strength, seed)


def _blur_then_jpeg(img: Image.Image, strength: float, _seed: int) -> Image.Image:
    return image.jpeg_compress(image.gaussian_blur(img, strength), 60)


def standard_attacks() -> tuple[Attack, ...]:
    """The attacks that need nothing but the protected photo itself."""
    return (
        Attack(
            "identity",
            0,
            "No attack. A control: the protection must be fully present",
            (0.0,),
            lambda img, _strength, _seed: img.copy(),
        ),
        Attack("jpeg", 1, "Save again as JPEG at this quality", (90, 75, 60, 45, 30), _jpeg),
        Attack("gaussian-blur", 1, "Gaussian blur with this radius", (0.5, 1, 1.5, 2, 3), _blur),
        Attack(
            "shrink-and-enlarge",
            1,
            "Shrink to this fraction, then enlarge back",
            (0.75, 0.5, 0.35),
            _down_up,
        ),
        Attack(
            "median-filter",
            2,
            "Median filter with this window size (feature squeezing)",
            (3, 5, 7),
            _median,
        ),
        Attack(
            "bit-depth",
            2,
            "Keep only this many bits per colour (feature squeezing)",
            (7, 6, 5, 4),
            _bit_depth,
        ),
        Attack(
            "non-local-means",
            2,
            "Non-local means denoising with this strength (feature squeezing)",
            (3, 5, 7, 10),
            _non_local_means,
        ),
        Attack(
            "noise-then-jpeg",
            2,
            "Add Gaussian noise of this std, then JPEG 75 "
            "(Gaussian noising followed by compression)",
            (3, 6, 10),
            _noise_then_jpeg,
        ),
        Attack(
            "noise-then-non-local-means",
            2,
            "Add Gaussian noise of this std, then denoise with the same strength",
            (5, 10, 15),
            _noise_then_non_local_means,
        ),
        Attack(
            "blur-then-jpeg",
            2,
            "Gaussian blur with this radius, then JPEG 60",
            (1, 1.5, 2),
            _blur_then_jpeg,
        ),
    )


def known_band_attack(narrow_sigma: float, wide_sigma: float) -> Attack:
    """Remove a known band of spatial frequencies from the photo.

    An attacker who has our code knows which band a protection puts its change in.
    The band is the one a difference of two Gaussian filters with these sigmas
    passes. The strength is the share of the band's peak gain below which a
    frequency is left alone, so a smaller number removes a wider band.
    """
    if not 0 < narrow_sigma < wide_sigma:
        raise ValueError(f"need 0 < narrow_sigma < wide_sigma, got {narrow_sigma}, {wide_sigma}")

    def run(img: Image.Image, strength: float, _seed: int) -> Image.Image:
        if not 0 < strength <= 1:
            raise ValueError(f"strength must be above 0 and at most 1, got {strength}")
        pixels = _pixels(img).astype(np.float32)
        height, width = pixels.shape[:2]
        freq_sq = np.fft.fftfreq(height)[:, None] ** 2 + np.fft.rfftfreq(width)[None, :] ** 2
        gain = np.abs(
            np.exp(-2 * np.pi**2 * narrow_sigma**2 * freq_sq)
            - np.exp(-2 * np.pi**2 * wide_sigma**2 * freq_sq)
        )
        keep = 1.0 - np.minimum(1.0, gain / (strength * gain.max()))
        cleaned = np.stack(
            [
                np.fft.irfft2(np.fft.rfft2(pixels[:, :, c]) * keep, s=(height, width))
                for c in range(3)
            ],
            axis=2,
        )
        return _to_image(cleaned)

    return Attack(
        "known-band-removal",
        3,
        "Remove the band of spatial frequencies the protection is known to use",
        (1.0, 0.5, 0.25, 0.1),
        run,
    )


def collusion_attack(
    protected_photos: Sequence[Image.Image], cutoffs: Sequence[float] = (8, 16, 32)
) -> Attack:
    """Estimate a pattern shared by many protected photos and subtract it.

    Photos with different content average out and a pattern that every photo
    carries does not. The attacker keeps the fine detail of the average, which
    leaves out the blurry average of the photo content. The strength is the
    blur radius that separates the two. A pattern that is different in every
    photo averages out too, so this attack fails against it. The method is the
    watermark estimation attack of Doerr and Dugelay (2004).
    """
    if any(not 0 < cutoff <= MAX_COLLUDER_CUTOFF for cutoff in cutoffs):
        raise ValueError(f"cutoffs must be above 0 and at most {MAX_COLLUDER_CUTOFF:g}")
    sizes = Counter(photo.size for photo in protected_photos)
    size, count = sizes.most_common(1)[0] if sizes else (None, 0)
    estimates: dict[float, np.ndarray] = {}
    if count >= MIN_COLLUDERS:
        total = np.zeros((size[1], size[0], 3), dtype=np.float64)
        for photo in protected_photos:
            if photo.size == size:
                total += _pixels(photo)
        mean = (total / count).astype(np.float32)
        for cutoff in cutoffs:
            estimates[float(cutoff)] = mean - cv2.GaussianBlur(
                mean, (0, 0), cutoff, borderType=cv2.BORDER_REFLECT_101
            )

    def run(img: Image.Image, strength: float, _seed: int) -> Image.Image:
        if not estimates:
            raise AttackNotApplicable(
                f"needs at least {MIN_COLLUDERS} protected photos of one size, "
                f"got {count} of the most common size"
            )
        if img.size != size:
            raise AttackNotApplicable(f"estimate was built for {size} photos, got {img.size}")
        return _to_image(_pixels(img).astype(np.float32) - estimates[float(strength)])

    return Attack(
        "collusion",
        3,
        "Subtract the pattern shared by many protected photos",
        tuple(float(cutoff) for cutoff in cutoffs),
        run,
    )
