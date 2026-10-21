import numpy as np
import pytest
from PIL import Image


def smooth_photo(seed: int, size: int = 128) -> Image.Image:
    """A made-up photo: blurry colour texture with a few flat shapes. Never a real person."""
    rng = np.random.default_rng(seed)
    freq = np.fft.fftfreq(size)
    radius = np.sqrt(freq[:, None] ** 2 + freq[None, :] ** 2)
    radius[0, 0] = 1
    channels = []
    for _ in range(3):
        spectrum = (
            rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))
        ) / radius**1.8
        texture = np.fft.ifft2(spectrum).real
        channels.append((texture - texture.mean()) / texture.std() * 30 + 128)
    pixels = np.stack(channels, axis=2)
    rows, cols = np.mgrid[:size, :size]
    for _ in range(3):
        centre_row, centre_col = rng.integers(size // 8, size - size // 8, 2)
        half_row, half_col = rng.integers(size // 10, size // 4, 2)
        inside = ((rows - centre_row) / half_row) ** 2 + ((cols - centre_col) / half_col) ** 2 < 1
        pixels[inside] = rng.integers(40, 220, 3)
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


@pytest.fixture
def photos():
    """Twelve made-up photos of one size, keyed by name."""
    return {f"photo{index}": smooth_photo(index) for index in range(12)}
