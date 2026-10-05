"""Load, save, and transform images.

The transformations match the changes real platforms apply to a photo before
anyone sees it: shrinking, cropping, JPEG compression, blur, and noise. The
fixed platform processing pipeline (``platform_pipeline``) encodes the exact
steps from docs/research/test-plan.md so the experiments can never drift from
the numbers fixed before any result was seen.

Everything operates on RGB images. Pixel arrays are uint8 NumPy arrays with
shape (height, width, 3), the layout Pillow and the rest of the project use.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

Resampling = Image.Resampling


def load_image(path: str | Path) -> Image.Image:
    """Open an image file and return it as RGB."""
    with Image.open(path) as img:
        return img.convert("RGB")


def save_image(img: Image.Image, path: str | Path, quality: int = 90) -> None:
    """Save an image. The file extension picks the format."""
    img.save(path, quality=quality)


def resize_long_side(img: Image.Image, target: int = 512) -> Image.Image:
    """Resize so the longer edge is ``target`` pixels, keeping the aspect ratio."""
    width, height = img.size
    if width >= height:
        new_width = target
        new_height = int(height * target / width)
    else:
        new_height = target
        new_width = int(width * target / height)
    return img.resize((new_width, new_height), Resampling.LANCZOS)


def centre_crop(img: Image.Image, keep: float = 0.8) -> Image.Image:
    """Crop the central ``keep`` fraction of the width and height."""
    width, height = img.size
    new_width = int(width * keep)
    new_height = int(height * keep)
    left = (width - new_width) // 2
    top = (height - new_height) // 2
    return img.crop((left, top, left + new_width, top + new_height))


def jpeg_compress(img: Image.Image, quality: int = 75) -> Image.Image:
    """Encode to JPEG in memory and decode back. JPEG is lossy, so pixels change."""
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as reloaded:
        return reloaded.convert("RGB")


def gaussian_blur(img: Image.Image, radius: float = 1.0) -> Image.Image:
    """Apply a Gaussian blur. A larger radius blurs more."""
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def add_gaussian_noise(
    img: Image.Image, std: float = 10.0, seed: int | None = None
) -> Image.Image:
    """Add Gaussian noise to every pixel and clip back to the 0 to 255 range.

    ``seed`` makes the output reproducible. Experiments pass an integer and log
    it so a run can be repeated.
    """
    rng = np.random.default_rng(seed)
    array = np.asarray(img, dtype=np.float32)
    noise = rng.normal(0.0, std, array.shape).astype(np.float32)
    noisy = np.clip(array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)


def platform_pipeline(img: Image.Image) -> Image.Image:
    """Apply the fixed platform processing pipeline.

    The steps and numbers are fixed in docs/research/test-plan.md: resize the
    long side to 512, centre crop to 80 percent, then JPEG compress at quality
    75. They are the stand-in for what a typical social site does to a photo.
    """
    img = resize_long_side(img, target=512)
    img = centre_crop(img, keep=0.8)
    img = jpeg_compress(img, quality=75)
    return img
