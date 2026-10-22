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
from typing import IO

import numpy as np
from PIL import Image, ImageFilter, ImageOps

Resampling = Image.Resampling

# Only photo formats are opened. Pillow also reads PSD, FITS, PDF and many other
# formats, and several of its security fixes concern those readers.
ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF")

# Larger radii are meaningless for photos, and Pillow crashes on extreme values.
MAX_BLUR_RADIUS = 1000.0

# The fixed platform pipeline. docs/research/test-plan.md explains each number.
PIPELINE_LONG_SIDE = 512
PIPELINE_CROP_KEEP = 0.8
PIPELINE_JPEG_QUALITY = 75

# The milder second profile. It never enlarges a photo and never crops it.
MILD_PIPELINE_MAX_LONG_SIDE = 1080
MILD_PIPELINE_JPEG_QUALITY = 85

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


def load_image(source: str | Path | IO[bytes]) -> Image.Image:
    """Open an image file, or an open binary file object, and return it as RGB, upright.

    Phone photos store their rotation as a tag instead of turning the pixels.
    The tag is applied here so every later step sees the photo the way a person does.
    Transparent areas are filled with white. Only the formats in ``ACCEPTED_FORMATS``
    are opened, and 16-bit or floating point images are rejected, because
    converting them would silently clip the pixel values.
    """
    with Image.open(source, formats=ACCEPTED_FORMATS) as img:
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


def crop_size(size: tuple[int, int], keep: float) -> tuple[int, int]:
    if not 0 < keep <= 1:
        raise ValueError(f"keep must be above 0 and at most 1, got {keep}")
    width, height = size
    new_width = int(width * keep)
    new_height = int(height * keep)
    if new_width < 1 or new_height < 1:
        raise ValueError(f"keep={keep} leaves nothing of a {width}x{height} image")
    return new_width, new_height


def centre_crop_offset(size: tuple[int, int], keep: float = 0.8) -> tuple[int, int]:
    """The (left, top) corner of the central ``keep`` crop of an image of this size."""
    new_width, new_height = crop_size(size, keep)
    return (size[0] - new_width) // 2, (size[1] - new_height) // 2


def crop_at(img: Image.Image, left: int, top: int, keep: float = 0.8) -> Image.Image:
    """Crop a ``keep`` fraction of the width and height with its corner at (left, top)."""
    new_width, new_height = crop_size(img.size, keep)
    if not (0 <= left <= img.size[0] - new_width and 0 <= top <= img.size[1] - new_height):
        raise ValueError(
            f"a {new_width}x{new_height} crop at ({left}, {top}) does not fit in {img.size}"
        )
    return img.crop((left, top, left + new_width, top + new_height))


def centre_crop(img: Image.Image, keep: float = 0.8) -> Image.Image:
    """Crop the central ``keep`` fraction of the width and height."""
    left, top = centre_crop_offset(img.size, keep)
    return crop_at(img, left, top, keep)


def random_crop_offset(
    size: tuple[int, int], keep: float = 0.8, seed: int | None = None
) -> tuple[int, int]:
    """A seeded (left, top) corner anywhere a ``keep`` crop fits.

    The same seed gives the same corner.
    """
    new_width, new_height = crop_size(size, keep)
    rng = np.random.default_rng(seed)
    return (
        int(rng.integers(0, size[0] - new_width + 1)),
        int(rng.integers(0, size[1] - new_height + 1)),
    )


def grid_aligned_offsets(
    size: tuple[int, int], keep: float = 0.8, grid: int = 8
) -> list[tuple[int, int]]:
    """Every crop corner whose left and top are both multiples of ``grid``, in reading order."""
    if grid < 1:
        raise ValueError(f"grid must be at least 1, got {grid}")
    new_width, new_height = crop_size(size, keep)
    return [
        (left, top)
        for top in range(0, size[1] - new_height + 1, grid)
        for left in range(0, size[0] - new_width + 1, grid)
    ]


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


def platform_pipeline_at(img: Image.Image, left: int, top: int) -> Image.Image:
    """The fixed pipeline with the crop corner at (left, top) of the resized photo.

    The numbers are the fixed ones. Only the place where the crop starts is free.
    Use ``resized_size`` to find the size of the resized photo.
    """
    _require_rgb(img)
    img = resize_long_side(img, target=PIPELINE_LONG_SIDE)
    img = crop_at(img, left, top, keep=PIPELINE_CROP_KEEP)
    return jpeg_compress(img, quality=PIPELINE_JPEG_QUALITY)


def resized_size(size: tuple[int, int], target: int = PIPELINE_LONG_SIDE) -> tuple[int, int]:
    """The size ``resize_long_side`` gives a photo of this size."""
    return resize_long_side(Image.new("L", size), target).size


def platform_pipeline(img: Image.Image) -> Image.Image:
    """Apply the fixed platform processing pipeline.

    The steps and numbers are fixed in docs/research/test-plan.md: resize the
    long side to 512, centre crop to 80 percent, then JPEG compress at quality
    75. They are the stand-in for what a typical social site does to a photo.
    """
    _require_rgb(img)
    left, top = centre_crop_offset(resized_size(img.size), PIPELINE_CROP_KEEP)
    return platform_pipeline_at(img, left, top)


def platform_pipeline_random_crop(img: Image.Image, seed: int | None = None) -> Image.Image:
    """The fixed pipeline with a seeded random crop corner instead of the centre.

    Same 512, 80 percent and quality 75. It is reported beside the centre crop
    result and never replaces it. The same seed gives the same photo.
    """
    _require_rgb(img)
    left, top = random_crop_offset(resized_size(img.size), PIPELINE_CROP_KEEP, seed)
    return platform_pipeline_at(img, left, top)


def mild_platform_pipeline(img: Image.Image) -> Image.Image:
    """Apply the milder second profile: shrink only above 1080 pixels, then JPEG 85.

    Real sites shrink a photo only when it is larger than a size limit and do not
    crop it, so this profile is closer to what a photo meets after upload than the
    fixed pipeline. It is reported next to the fixed pipeline and never replaces it.
    """
    _require_rgb(img)
    if max(img.size) > MILD_PIPELINE_MAX_LONG_SIDE:
        img = resize_long_side(img, target=MILD_PIPELINE_MAX_LONG_SIDE)
    return jpeg_compress(img, quality=MILD_PIPELINE_JPEG_QUALITY)
