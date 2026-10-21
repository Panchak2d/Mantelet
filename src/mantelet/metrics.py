"""Score how different two images are.

All scores compare two RGB images of the same size. Pixel values run from 0 to
255. These scores measure pixel change, not what a person notices. A change
that is invisible to people can score badly and the other way round, so the
human study decides the visibility question and these numbers support it.

Mean squared error (``mse``), peak signal to noise ratio (``psnr``), the largest
single pixel change (``max_abs_difference``) and structural similarity
(``ssim``) are calculated from their published formulas. ``ssim`` follows Wang,
Bovik, Sheikh and Simoncelli (2004): an 11 by 11 Gaussian window with sigma 1.5,
and constants K1 = 0.01 and K2 = 0.03.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

PEAK_VALUE = 255.0
SSIM_WINDOW_SIZE = 11
SSIM_SIGMA = 1.5
_SSIM_C1 = (0.01 * PEAK_VALUE) ** 2
_SSIM_C2 = (0.03 * PEAK_VALUE) ** 2


@dataclass(frozen=True)
class DifferenceScores:
    """All four scores for one pair of images. ``psnr`` is infinite for identical images."""

    mse: float
    psnr: float
    max_abs_difference: float
    ssim: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _pair_to_arrays(first: Image.Image, second: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    for img in (first, second):
        if img.mode != "RGB":
            raise ValueError(f"expected an RGB image, got mode {img.mode}")
    if first.size != second.size:
        raise ValueError(f"images must be the same size, got {first.size} and {second.size}")
    return np.asarray(first, dtype=np.float64), np.asarray(second, dtype=np.float64)


def mse(first: Image.Image, second: Image.Image) -> float:
    """Mean of the squared pixel differences. Zero means identical."""
    a, b = _pair_to_arrays(first, second)
    return float(np.mean((a - b) ** 2))


def _psnr_from_mse(error: float) -> float:
    if error == 0:
        return math.inf
    return 10.0 * math.log10(PEAK_VALUE**2 / error)


def psnr(first: Image.Image, second: Image.Image) -> float:
    """Peak signal to noise ratio in decibels. Higher means more alike."""
    return _psnr_from_mse(mse(first, second))


def max_abs_difference(first: Image.Image, second: Image.Image) -> float:
    """The largest change to any single pixel value, from 0 to 255."""
    a, b = _pair_to_arrays(first, second)
    return float(np.max(np.abs(a - b)))


def _gaussian_kernel() -> np.ndarray:
    offsets = np.arange(SSIM_WINDOW_SIZE) - (SSIM_WINDOW_SIZE - 1) / 2
    kernel = np.exp(-(offsets**2) / (2 * SSIM_SIGMA**2))
    return kernel / kernel.sum()


def _filter_valid(channel: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Blur with the kernel along both axes, keeping only windows that fit inside the image."""
    rows = np.tensordot(sliding_window_view(channel, SSIM_WINDOW_SIZE, axis=0), kernel, axes=1)
    return np.tensordot(sliding_window_view(rows, SSIM_WINDOW_SIZE, axis=1), kernel, axes=1)


def ssim(first: Image.Image, second: Image.Image) -> float:
    """Structural similarity, averaged over the colour channels. 1 means identical."""
    a, b = _pair_to_arrays(first, second)
    if min(a.shape[:2]) < SSIM_WINDOW_SIZE:
        raise ValueError(
            f"images must be at least {SSIM_WINDOW_SIZE} pixels on each side for ssim, "
            f"got {first.size}"
        )
    kernel = _gaussian_kernel()
    channel_scores = []
    for index in range(a.shape[2]):
        x, y = a[:, :, index], b[:, :, index]
        mean_x, mean_y = _filter_valid(x, kernel), _filter_valid(y, kernel)
        var_x = _filter_valid(x * x, kernel) - mean_x**2
        var_y = _filter_valid(y * y, kernel) - mean_y**2
        covariance = _filter_valid(x * y, kernel) - mean_x * mean_y
        numerator = (2 * mean_x * mean_y + _SSIM_C1) * (2 * covariance + _SSIM_C2)
        denominator = (mean_x**2 + mean_y**2 + _SSIM_C1) * (var_x + var_y + _SSIM_C2)
        channel_scores.append(float(np.mean(numerator / denominator)))
    return float(np.mean(channel_scores))


def compare(first: Image.Image, second: Image.Image) -> DifferenceScores:
    """Calculate every difference score for a pair of images of the same size."""
    error = mse(first, second)
    return DifferenceScores(
        mse=error,
        psnr=_psnr_from_mse(error),
        max_abs_difference=max_abs_difference(first, second),
        ssim=ssim(first, second),
    )
