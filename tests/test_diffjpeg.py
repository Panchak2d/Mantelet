import io

import numpy as np
import pytest
from conftest import smooth_photo
from PIL import Image

from mantelet import image

torch = pytest.importorskip("torch")

from mantelet import diffjpeg  # noqa: E402


def as_tensor(img):
    return torch.from_numpy(np.asarray(img, dtype=np.float32).transpose(2, 0, 1))[None]


@pytest.mark.parametrize("quality", [50, 75, 90])
def test_the_standard_tables_scaled_by_quality_match_the_ones_pillow_writes(quality):
    buffer = io.BytesIO()
    smooth_photo(1, 64).save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    tables = Image.open(buffer).quantization
    assert diffjpeg.quantisation_table(diffjpeg._LUMA, quality).flatten()[:8].tolist() == list(
        tables[0][:8]
    )
    assert diffjpeg.quantisation_table(diffjpeg._CHROMA, quality).flatten()[:8].tolist() == list(
        tables[1][:8]
    )


def test_the_approximation_stays_close_to_pillow_and_damages_the_photo_as_much():
    img = smooth_photo(2, 160)
    original = np.asarray(img, dtype=np.float32)
    reference = np.asarray(image.jpeg_compress(img, 75), dtype=np.float32)
    mine = diffjpeg.jpeg(as_tensor(img), 75)[0].numpy().transpose(1, 2, 0)
    assert np.abs(mine - reference).mean() < 1.0
    assert abs(np.abs(mine - original).mean() - np.abs(reference - original).mean()) < 0.3


def test_the_size_need_not_be_a_multiple_of_the_block_and_the_gradient_passes_through():
    values = as_tensor(smooth_photo(3, 50)).requires_grad_(True)
    out = diffjpeg.jpeg(values, 60)
    assert out.shape == values.shape
    assert 0 <= float(out.detach().min()) and float(out.detach().max()) <= 255
    out.sum().backward()
    assert values.grad is not None and float(values.grad.abs().sum()) > 0


def test_a_bad_quality_or_shape_is_refused():
    with pytest.raises(ValueError, match="quality"):
        diffjpeg.quantisation_table(diffjpeg._LUMA, 0)
    with pytest.raises(ValueError, match="shape"):
        diffjpeg.jpeg(torch.zeros(3, 8, 8), 75)
