"""A differentiable approximation of JPEG, so a protection can be tuned through it.

JPEG rounds its frequency values, and rounding has no useful gradient. This module
rounds in the forward pass and passes the gradient straight through (the
straight-through estimator), the same idea the JPEG-resistant face perturbation
papers use. The steps follow Pillow's encoder: colour to YCbCr, chroma shrunk
to half size in both directions, 8 by 8 cosine transform, the standard
quantisation tables scaled by quality the way libjpeg scales them, and the
reverse. It is an approximation. ``scripts/check_protection.py`` and the tests
compare it with Pillow's own JPEG. Needs the ``ml`` extra.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

BLOCK = 8

_LUMA = (
    (16, 11, 10, 16, 24, 40, 51, 61),
    (12, 12, 14, 19, 26, 58, 60, 55),
    (14, 13, 16, 24, 40, 57, 69, 56),
    (14, 17, 22, 29, 51, 87, 80, 62),
    (18, 22, 37, 56, 68, 109, 103, 77),
    (24, 35, 55, 64, 81, 104, 113, 92),
    (49, 64, 78, 87, 103, 121, 120, 101),
    (72, 92, 95, 98, 112, 100, 103, 99),
)
_CHROMA = (
    (17, 18, 24, 47, 99, 99, 99, 99),
    (18, 21, 26, 66, 99, 99, 99, 99),
    (24, 26, 56, 99, 99, 99, 99, 99),
    (47, 66, 99, 99, 99, 99, 99, 99),
    (99, 99, 99, 99, 99, 99, 99, 99),
    (99, 99, 99, 99, 99, 99, 99, 99),
    (99, 99, 99, 99, 99, 99, 99, 99),
    (99, 99, 99, 99, 99, 99, 99, 99),
)


def quantisation_table(base: tuple, quality: int) -> torch.Tensor:
    """The 8 by 8 table for a quality from 1 to 100, scaled the way libjpeg scales it."""
    if not 1 <= quality <= 100:
        raise ValueError(f"quality must be from 1 to 100, got {quality}")
    scale = 5000 // quality if quality < 50 else 200 - quality * 2
    table = torch.tensor(base, dtype=torch.float32)
    return torch.clamp(torch.floor((table * scale + 50) / 100), 1, 255)


def _cosine_matrix() -> torch.Tensor:
    index = torch.arange(BLOCK, dtype=torch.float64)
    matrix = torch.cos((2 * index[None, :] + 1) * index[:, None] * math.pi / (2 * BLOCK))
    matrix[0] *= 1 / math.sqrt(2)
    return (matrix * math.sqrt(2 / BLOCK)).to(torch.float32)


def _round_through(values: torch.Tensor) -> torch.Tensor:
    return values + (torch.round(values) - values).detach()


def _rgb_to_ycbcr(rgb: torch.Tensor) -> torch.Tensor:
    red, green, blue = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    luma = 0.299 * red + 0.587 * green + 0.114 * blue
    blue_diff = 128 - 0.168736 * red - 0.331264 * green + 0.5 * blue
    red_diff = 128 + 0.5 * red - 0.418688 * green - 0.081312 * blue
    return torch.stack([luma, blue_diff, red_diff], dim=1)


def _ycbcr_to_rgb(ycc: torch.Tensor) -> torch.Tensor:
    luma, blue_diff, red_diff = ycc[:, 0], ycc[:, 1] - 128, ycc[:, 2] - 128
    red = luma + 1.402 * red_diff
    green = luma - 0.344136 * blue_diff - 0.714136 * red_diff
    blue = luma + 1.772 * blue_diff
    return torch.stack([red, green, blue], dim=1)


def _blocks_transform(
    plane: torch.Tensor, table: torch.Tensor, cosine: torch.Tensor
) -> torch.Tensor:
    """Cosine transform, quantise, dequantise and invert, for one plane of shape (n, h, w)."""
    count, height, width = plane.shape
    blocks = (plane - 128).reshape(count, height // BLOCK, BLOCK, width // BLOCK, BLOCK)
    blocks = blocks.permute(0, 1, 3, 2, 4)
    coefficients = cosine @ blocks @ cosine.T
    restored = _round_through(coefficients / table) * table
    blocks = cosine.T @ restored @ cosine
    return blocks.permute(0, 1, 3, 2, 4).reshape(count, height, width) + 128


def _pad_to(values: torch.Tensor, multiple: int) -> torch.Tensor:
    height, width = values.shape[-2:]
    pad_height, pad_width = -height % multiple, -width % multiple
    if pad_height == 0 and pad_width == 0:
        return values
    return F.pad(values, (0, pad_width, 0, pad_height), mode="replicate")


def jpeg(rgb: torch.Tensor, quality: int) -> torch.Tensor:
    """Approximate JPEG at ``quality`` on a float tensor of shape (n, 3, h, w), values 0 to 255."""
    if rgb.ndim != 4 or rgb.shape[1] != 3:
        raise ValueError(f"expected a tensor of shape (n, 3, h, w), got {tuple(rgb.shape)}")
    height, width = rgb.shape[-2:]
    cosine = _cosine_matrix().to(rgb.device)
    luma_table = quantisation_table(_LUMA, quality).to(rgb.device)
    chroma_table = quantisation_table(_CHROMA, quality).to(rgb.device)
    ycc = _round_through(_rgb_to_ycbcr(_pad_to(rgb, 2 * BLOCK)))
    luma = _round_through(_blocks_transform(ycc[:, 0], luma_table, cosine))
    half = _round_through(F.avg_pool2d(ycc[:, 1:], 2))
    chroma = torch.stack(
        [_round_through(_blocks_transform(half[:, i], chroma_table, cosine)) for i in range(2)],
        dim=1,
    )
    chroma = F.interpolate(chroma, scale_factor=2, mode="bilinear", align_corners=False)
    out = _round_through(_ycbcr_to_rgb(torch.cat([luma[:, None], chroma], dim=1)))
    return torch.clamp(out[:, :, :height, :width], 0, 255)
