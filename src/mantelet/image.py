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
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

Resampling = Image.Resampling

# Only photo formats are opened. Pillow also reads PSD, FITS, PDF and many other
# formats, and several of its security fixes concern those readers.
ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF")

# Larger radii are meaningless for photos, and Pillow crashes on extreme values.
MAX_BLUR_RADIUS = 1000.0

_ALPHA_MODES = {"RGBA", "RGBa", "LA", "La", "PA"}
_HIGH_BIT_DEPTH_MODES = {"I", "F", "I;16", "I;16L", "I;16B", "I;16N"}


def _require_rgb(img: Image.Image) -> None:
    if img.mode != "RGB":
        raise ValueError(f"expected an RGB image, got mode {img.mode}")


def _check_quality(quality: int) -> None:
    if isinstance(quality, bool) or not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError(f"quality must be a whole number from 1 to 100, got {quality!r}")


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Convert to RGB. Transparent areas become white, as in a browser."""
    if img.mode in _HIGH_BIT_DEPTH_MODES:
        raise ValueError(f"images with mode {img.mode} are not supported, use an 8-bit image")
    if img.mode in _ALPHA_MODES or "transparency" in img.info:
        rgba = img.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(white, rgba).convert("RGB")
    return img.convert("RGB")


def load_image(path: str | Path) -> Image.Image:
    """Open an image file and return it as RGB, upright.

    Phone photos store their rotation as a tag instead of turning the pixels.
    The tag is applied here so every later step sees the photo the way a person does.
    Transparent areas are filled with white. Only the formats in ``ACCEPTED_FORMATS``
    are opened, and 16-bit or floating point images are rejected, because
    converting them would silently clip the pixel values.
    """
    with Image.open(path, formats=ACCEPTED_FORMATS) as img:
        return _flatten_to_rgb(ImageOps.exif_transpose(img))


def save_image(img: Image.Image, path: str | Path, quality: int = 90) -> None:
    """Save an image. The file extension picks the format."""
    _check_quality(quality)
    img.save(path, quality=quality)


def resize_long_side(img: Image.Image, target: int = 512) -> Image.Image:
    """Resize so the longer edge is ``target`` pixels, keeping the aspect ratio."""
    if target < 1:
        raise ValueError(f"target must be at least 1 pixel, got {target}")
    width, height = img.size
    if width >= height:
        new_width = target
        new_height = max(1, int(height * target / width))
    else:
        new_height = target
        new_width = max(1, int(width * target / height))
    return img.resize((new_width, new_height), Resampling.LANCZOS)


def centre_crop(img: Image.Image, keep: float = 0.8) -> Image.Image:
    """Crop the central ``keep`` fraction of the width and height."""
    if not 0 < keep <= 1:
        raise ValueError(f"keep must be above 0 and at most 1, got {keep}")
    width, height = img.size
    new_width = int(width * keep)
    new_height = int(height * keep)
    if new_width < 1 or new_height < 1:
        raise ValueError(f"keep={keep} leaves nothing of a {width}x{height} image")
    left = (width - new_width) // 2
    top = (height - new_height) // 2
    return img.crop((left, top, left + new_width, top + new_height))


def jpeg_compress(img: Image.Image, quality: int = 75) -> Image.Image:
    """Encode to JPEG in memory and decode back. JPEG is lossy, so pixels change."""
    _require_rgb(img)
    _check_quality(quality)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as reloaded:
        return reloaded.convert("RGB")


def gaussian_blur(img: Image.Image, radius: float = 1.0) -> Image.Image:
    """Apply a Gaussian blur. A larger radius blurs more."""
    if not math.isfinite(radius) or not 0 <= radius <= MAX_BLUR_RADIUS:
        raise ValueError(f"radius must be from 0 to {MAX_BLUR_RADIUS:g}, got {radius}")
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def add_gaussian_noise(
    img: Image.Image, std: float = 10.0, seed: int | None = None
) -> Image.Image:
    """Add Gaussian noise to every pixel and clip back to the 0 to 255 range.

    ``seed`` makes the output reproducible. Experiments pass an integer and log
    it so a run can be repeated.
    """
    _require_rgb(img)
    if not math.isfinite(std) or std < 0:
        raise ValueError(f"std must be a finite number and not negative, got {std}")
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
    _require_rgb(img)
    img = resize_long_side(img, target=512)
    img = centre_crop(img, keep=0.8)
    img = jpeg_compress(img, quality=75)
    return img
