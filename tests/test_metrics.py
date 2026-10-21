import math

import numpy as np
import pytest
from PIL import Image

from mantelet import metrics


def random_pair(shape=(24, 30, 3), seed=0):
    rng = np.random.default_rng(seed)
    first = rng.integers(0, 256, shape, dtype=np.uint8)
    noise = rng.normal(0, 20, shape)
    second = np.clip(first + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(first), Image.fromarray(second)


def naive_ssim(first, second):
    """Slow reference: loop over every window and apply the published formula."""
    a, b = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    size, sigma = 11, 1.5
    axis = np.arange(size) - 5
    kernel_1d = np.exp(-(axis**2) / (2 * sigma**2))
    weights = np.outer(kernel_1d, kernel_1d)
    weights /= weights.sum()
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    scores = []
    for channel in range(3):
        for top in range(a.shape[0] - size + 1):
            for left in range(a.shape[1] - size + 1):
                x = a[top : top + size, left : left + size, channel]
                y = b[top : top + size, left : left + size, channel]
                mx, my = (weights * x).sum(), (weights * y).sum()
                vx = (weights * x * x).sum() - mx**2
                vy = (weights * y * y).sum() - my**2
                cov = (weights * x * y).sum() - mx * my
                scores.append(
                    (2 * mx * my + c1) * (2 * cov + c2) / ((mx**2 + my**2 + c1) * (vx + vy + c2))
                )
    return float(np.mean(scores))


def test_identical_images_score_as_unchanged():
    img, _ = random_pair()
    scores = metrics.compare(img, img.copy())
    assert scores.mse == 0
    assert scores.psnr == math.inf
    assert scores.max_abs_difference == 0
    assert scores.ssim == pytest.approx(1.0)


def test_a_constant_change_gives_the_values_from_the_formulas():
    base = Image.new("RGB", (32, 32), (100, 100, 100))
    shifted = Image.new("RGB", (32, 32), (110, 110, 110))
    scores = metrics.compare(base, shifted)
    assert scores.mse == 100
    assert scores.psnr == pytest.approx(10 * math.log10(255**2 / 100))
    assert scores.max_abs_difference == 10


def test_ssim_matches_a_slow_reference_implementation():
    first, second = random_pair((16, 20, 3), seed=5)
    assert metrics.ssim(first, second) == pytest.approx(naive_ssim(first, second), abs=1e-9)


def test_more_noise_gives_a_lower_ssim():
    first, mild = random_pair(seed=1)
    rng = np.random.default_rng(1)
    heavy = np.clip(np.asarray(first) + rng.normal(0, 60, (24, 30, 3)), 0, 255).astype(np.uint8)
    assert metrics.ssim(first, Image.fromarray(heavy)) < metrics.ssim(first, mild)


def test_scores_reject_images_of_different_sizes():
    with pytest.raises(ValueError, match="same size"):
        metrics.mse(Image.new("RGB", (20, 20)), Image.new("RGB", (21, 20)))


def test_scores_reject_images_that_are_not_rgb():
    with pytest.raises(ValueError, match="RGB"):
        metrics.mse(Image.new("L", (20, 20)), Image.new("L", (20, 20)))


def test_ssim_rejects_images_smaller_than_the_window():
    with pytest.raises(ValueError, match="at least 11"):
        metrics.ssim(Image.new("RGB", (10, 40)), Image.new("RGB", (10, 40)))
