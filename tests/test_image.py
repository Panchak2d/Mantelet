import numpy as np
import pytest
from PIL import Image, UnidentifiedImageError

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


def test_load_image_applies_exif_rotation(tmp_path):
    file = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (40, 20))
    exif = img.getexif()
    exif[274] = 6
    img.save(file, exif=exif)
    assert image.load_image(file).size == (20, 40)


@pytest.mark.parametrize("target", [0, -5])
def test_resize_long_side_rejects_target_below_one(target):
    with pytest.raises(ValueError):
        image.resize_long_side(make_image(), target)


def test_resize_long_side_keeps_extreme_aspect_ratio_at_least_one_pixel():
    assert image.resize_long_side(make_image((1000, 1)), 512).size == (512, 1)


@pytest.mark.parametrize("keep", [-0.1, 0, 1.5])
def test_centre_crop_rejects_keep_outside_zero_to_one(keep):
    with pytest.raises(ValueError):
        image.centre_crop(make_image(), keep)


def test_centre_crop_rejects_crop_with_no_pixels():
    with pytest.raises(ValueError):
        image.centre_crop(make_image((100, 100)), 0.001)


@pytest.mark.parametrize("quality", [0, 101])
def test_jpeg_compress_rejects_quality_outside_range(quality):
    with pytest.raises(ValueError):
        image.jpeg_compress(make_image(), quality)


def test_gaussian_blur_rejects_negative_radius():
    with pytest.raises(ValueError):
        image.gaussian_blur(make_image(), -1.0)


def test_add_gaussian_noise_rejects_negative_std():
    with pytest.raises(ValueError):
        image.add_gaussian_noise(make_image(), std=-1.0)


@pytest.mark.parametrize("radius", [float("inf"), float("nan"), 1e300, image.MAX_BLUR_RADIUS + 1])
def test_gaussian_blur_rejects_radius_that_is_not_finite_or_too_large(radius):
    with pytest.raises(ValueError):
        image.gaussian_blur(make_image(), radius)


@pytest.mark.parametrize("std", [float("inf"), float("nan")])
def test_add_gaussian_noise_rejects_std_that_is_not_finite(std):
    with pytest.raises(ValueError):
        image.add_gaussian_noise(make_image(), std=std)


@pytest.mark.parametrize("quality", [1.5, True, "75"])
def test_jpeg_compress_rejects_quality_that_is_not_a_whole_number(quality):
    with pytest.raises(ValueError):
        image.jpeg_compress(make_image(), quality)


def test_save_image_rejects_quality_outside_range(tmp_path):
    with pytest.raises(ValueError):
        image.save_image(make_image(), tmp_path / "out.jpg", quality=0)


@pytest.mark.parametrize(
    "operation",
    [image.jpeg_compress, image.add_gaussian_noise, image.platform_pipeline],
)
def test_operations_that_need_rgb_reject_other_modes(operation):
    with pytest.raises(ValueError, match="RGB"):
        operation(Image.new("RGBA", (16, 16)))


def test_load_image_fills_transparent_areas_with_white(tmp_path):
    file = tmp_path / "clear.png"
    Image.new("RGBA", (4, 4), (255, 0, 0, 0)).save(file)
    assert image.load_image(file).getpixel((0, 0)) == (255, 255, 255)


def test_load_image_keeps_opaque_pixels_of_an_alpha_image(tmp_path):
    file = tmp_path / "solid.png"
    Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(file)
    assert image.load_image(file).getpixel((0, 0)) == (10, 20, 30)


def test_load_image_fills_transparent_palette_entries_with_white(tmp_path):
    file = tmp_path / "palette.png"
    Image.new("P", (4, 4), 0).save(file, transparency=0)
    assert image.load_image(file).getpixel((0, 0)) == (255, 255, 255)


def test_load_image_rejects_16_bit_images_instead_of_clipping(tmp_path):
    file = tmp_path / "deep.png"
    Image.fromarray(np.full((4, 4), 30000, dtype=np.uint16)).save(file)
    with pytest.raises(ValueError, match="8-bit"):
        image.load_image(file)


def test_load_image_refuses_formats_that_are_not_photos(tmp_path):
    file = tmp_path / "other.ppm"
    Image.new("RGB", (4, 4)).save(file)
    with pytest.raises(UnidentifiedImageError):
        image.load_image(file)
