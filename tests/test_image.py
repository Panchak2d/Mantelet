import numpy as np
from PIL import Image

from mantelet import image


def make_image(size=(64, 48), fill=(10, 20, 30)):
    return Image.new("RGB", size, fill)


def test_load_image_converts_to_rgb(tmp_path):
    file = tmp_path / "gray.png"
    Image.new("L", (8, 8), 128).save(file)
    assert image.load_image(file).mode == "RGB"


def test_save_image_round_trip_preserves_size(tmp_path):
    file = tmp_path / "out.png"
    img = make_image((50, 40))
    image.save_image(img, file)
    assert image.load_image(file).size == (50, 40)


def test_resize_long_side_scales_the_longer_edge():
    portrait = make_image((100, 200))
    assert image.resize_long_side(portrait, 512).size == (256, 512)
    landscape = make_image((300, 100))
    assert image.resize_long_side(landscape, 512).size == (512, 170)


def test_resize_long_side_preserves_aspect_ratio():
    img = make_image((300, 200))
    resized = image.resize_long_side(img, 600)
    ratio = img.size[0] / img.size[1]
    resized_ratio = resized.size[0] / resized.size[1]
    assert abs(ratio - resized_ratio) < 0.01


def test_centre_crop_keeps_central_fraction():
    cropped = image.centre_crop(make_image((100, 60)), keep=0.8)
    assert cropped.size == (80, 48)


def test_jpeg_compress_returns_same_size():
    img = make_image((64, 48))
    assert image.jpeg_compress(img).size == (64, 48)


def test_jpeg_compress_changes_pixels():
    array = np.zeros((16, 16, 3), dtype=np.uint8)
    array[::2, ::2] = 255
    img = Image.fromarray(array)
    out = np.asarray(image.jpeg_compress(img, quality=50))
    assert not np.array_equal(np.asarray(img), out)


def test_gaussian_blur_reduces_detail():
    rng = np.random.default_rng(0)
    array = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
    sharp = np.asarray(Image.fromarray(array), dtype=np.int16)
    blurred = np.asarray(image.gaussian_blur(Image.fromarray(array), radius=2.0), dtype=np.int16)
    sharp_diff = np.abs(np.diff(sharp, axis=0)).mean()
    blurred_diff = np.abs(np.diff(blurred, axis=0)).mean()
    assert blurred_diff < sharp_diff


def test_add_gaussian_noise_is_deterministic_with_seed():
    img = make_image((32, 32), fill=(100, 100, 100))
    first = np.asarray(image.add_gaussian_noise(img, std=15.0, seed=42))
    second = np.asarray(image.add_gaussian_noise(img, std=15.0, seed=42))
    assert np.array_equal(first, second)


def test_add_gaussian_noise_stays_in_uint8_range():
    all_black = make_image((32, 32), fill=(0, 0, 0))
    all_white = make_image((32, 32), fill=(255, 255, 255))
    for img in (all_black, all_white):
        out = np.asarray(image.add_gaussian_noise(img, std=30.0, seed=1))
        assert out.min() >= 0
        assert out.max() <= 255


def test_platform_pipeline_resizes_then_crops_then_compresses():
    img = make_image((1024, 768))
    assert image.platform_pipeline(img).size == (409, 307)


def test_platform_pipeline_matches_running_steps_separately():
    img = make_image((800, 600), fill=(120, 90, 60))
    via_pipeline = np.asarray(image.platform_pipeline(img))
    manual = image.jpeg_compress(image.centre_crop(image.resize_long_side(img, 512), 0.8), 75)
    via_steps = np.asarray(manual)
    assert np.array_equal(via_pipeline, via_steps)
