"""Protections tuned with gradients against the PyTorch copy of SFace.

A protection here is a small change to the pixels, found by projected gradient
descent (PGD) with an L-infinity budget, that pushes the face vector of the aligned
crop away from the vector of the unprotected face. The change is tuned through the
same alignment OpenCV uses: five landmarks, a similarity transform to fixed target
points, and a bilinear warp to 112 by 112 (``similarity_matrix`` and
``aligned_crop``). The real face model in the red team is still OpenCV's; the copy
is only used to find the change.

Two protections are built:

* ``pgd`` tunes the change on the photo as it is.
* ``pgd-jpeg`` also tunes it through a random shift and a differentiable JPEG
  at a random quality, because a change tuned without compression is known to
  lose most of its effect under JPEG.

Only pixels that reach the aligned crop get a gradient, so the change stays near the
face and the rest of the photo is untouched. A photo with no face found is returned
unchanged. Needs the ``ml`` extra.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from mantelet import diffjpeg, faces, toy

CROP = 112
PGD_STEPS = 40
PGD_STEP_FRACTION = 1 / 20
EOT_QUALITY_RANGE = (60, 90)
EOT_MAX_SHIFT = 7
BAND_SIGMAS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0)
BAND_REMOVAL_STRENGTH = 0.1
BAND_MAX_AREA = 0.25

# The target points and their mean are the constants OpenCV's alignCrop uses.
_TARGETS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ]
)
_TARGET_MEAN = np.array([56.0262, 71.9008])


def similarity_matrix(landmarks: np.ndarray) -> np.ndarray:
    """The 2 by 3 matrix that maps five landmarks onto the fixed targets, as OpenCV computes it."""
    points = np.asarray(landmarks, dtype=np.float64)
    if points.shape != (5, 2) or not np.all(np.isfinite(points)):
        raise ValueError(f"expected five finite landmarks of shape (5, 2), got {points.shape}")
    source_mean = points.mean(axis=0)
    source = points - source_mean
    target = _TARGETS - _TARGET_MEAN
    cross = target.T @ source / 5
    left, singular, right = np.linalg.svd(cross)
    spread = float(np.sum(source**2) / 5)
    if singular[1] < singular[0] * 1e-9 or spread == 0:
        raise ValueError("the landmarks are in a line or on one point")
    signs = np.array([1.0, -1.0 if np.linalg.det(cross) < 0 else 1.0])
    rotation = left @ np.diag(signs) @ right
    scale = float(singular @ signs) / spread
    shift = _TARGET_MEAN - scale * rotation @ source_mean
    return np.hstack([scale * rotation, shift[:, None]])


def _grid(matrix: np.ndarray, height: int, width: int) -> torch.Tensor:
    """Sampling grid, in grid_sample's coordinates, for warping a photo with ``matrix``."""
    inverse = np.linalg.inv(np.vstack([matrix, [0.0, 0.0, 1.0]]))
    columns, rows = np.meshgrid(np.arange(CROP), np.arange(CROP))
    homogeneous = np.stack([columns, rows, np.ones_like(columns)]).reshape(3, -1).astype(np.float64)
    source = (inverse @ homogeneous)[:2]
    grid = np.stack(
        [2 * source[0] / max(width - 1, 1) - 1, 2 * source[1] / max(height - 1, 1) - 1], axis=-1
    ).reshape(1, CROP, CROP, 2)
    return torch.from_numpy(grid).to(torch.float32)


def aligned_crop(rgb: torch.Tensor, matrix: np.ndarray, quantise: bool = True) -> torch.Tensor:
    """Warp a photo tensor (1, 3, h, w), values 0 to 255, to the 112 by 112 crop. Differentiable.

    Bilinear sampling with zeros outside the photo matches ``warpAffine`` with linear
    interpolation and its default border. OpenCV hands the recogniser a crop of whole
    pixel values, so by default the crop is rounded the same way and the gradient passes
    straight through the rounding. ``quantise=False`` keeps the smooth values, which a
    finite difference needs.
    """
    height, width = rgb.shape[-2:]
    grid = _grid(matrix, height, width).to(device=rgb.device, dtype=rgb.dtype)
    crop = F.grid_sample(rgb, grid, mode="bilinear", padding_mode="zeros", align_corners=True)
    return crop + (torch.round(crop) - crop).detach() if quantise else crop


def embed(module, crop: torch.Tensor) -> torch.Tensor:
    """The unit length face vector of a crop tensor (1, 3, 112, 112), shape (1, n)."""
    return F.normalize(module(crop).reshape(crop.shape[0], -1), dim=1)


def _tensor(pixels: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(pixels.transpose(2, 0, 1), np.float32))[None]


def _shifted_matrix(matrix: np.ndarray, left: int, top: int) -> np.ndarray:
    moved = matrix.copy()
    moved[:, 2] = matrix[:, 2] + matrix[:, :2] @ np.array([left, top], dtype=np.float64)
    return moved


def pgd(
    module,
    pixels: np.ndarray,
    matrix: np.ndarray,
    budget: int,
    seed: int,
    jpeg: bool = False,
    steps: int = PGD_STEPS,
) -> np.ndarray:
    """Return a copy of ``pixels`` (uint8, h by w by 3) changed by at most ``budget`` per value.

    The step is ``budget / 20`` with a random start, 40 steps and one restart.
    """
    if pixels.dtype != np.uint8 or pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError(f"expected a uint8 array of shape (h, w, 3), got {pixels.shape}")
    if not isinstance(budget, int) or not 1 <= budget <= 64:
        raise ValueError(f"budget must be a whole number from 1 to 64, got {budget!r}")
    if steps < 1:
        raise ValueError(f"steps must be at least 1, got {steps}")
    generator = torch.Generator().manual_seed(seed)
    choices = np.random.default_rng(seed)
    photo = _tensor(pixels)
    step_size = budget * PGD_STEP_FRACTION
    with torch.no_grad():
        reference = embed(module, aligned_crop(photo, matrix))
    delta = (torch.rand(photo.shape, generator=generator) * 2 - 1) * budget
    delta = torch.clamp(photo + delta, 0, 255) - photo
    touched = torch.zeros(photo.shape, dtype=torch.bool)
    for _ in range(steps):
        delta.requires_grad_(True)
        view, view_matrix = photo + delta, matrix
        if jpeg:
            left, top = (int(v) for v in choices.integers(0, EOT_MAX_SHIFT + 1, 2))
            quality = int(choices.integers(EOT_QUALITY_RANGE[0], EOT_QUALITY_RANGE[1] + 1))
            view = diffjpeg.jpeg(view[:, :, top:, left:], quality)
            view_matrix = _shifted_matrix(matrix, left, top)
        similarity = (embed(module, aligned_crop(view, view_matrix)) * reference).sum()
        (gradient,) = torch.autograd.grad(similarity, delta)
        with torch.no_grad():
            touched |= gradient != 0
            delta = (delta - step_size * gradient.sign()) * touched
            delta = torch.clamp(delta, -budget, budget)
            delta = torch.clamp(photo + delta, 0, 255) - photo
    changed = torch.clamp(torch.round(photo + delta.detach()), 0, 255)
    return changed[0].numpy().transpose(1, 2, 0).astype(np.uint8)


def pgd_protection(
    name: str,
    module,
    face_model: faces.OpenCVFaceModel,
    budget: int,
    jpeg: bool = False,
    band: tuple[float, float] | None = None,
) -> toy.Protection:
    """A protection that applies ``pgd`` to the face in each photo."""

    def apply(img: Image.Image, seed: int) -> Image.Image:
        landmarks = face_model.landmarks(img)
        if landmarks is None:
            return img
        changed = pgd(
            module, np.asarray(img), similarity_matrix(landmarks), budget, seed, jpeg=jpeg
        )
        return Image.fromarray(changed)

    kind = "with a differentiable JPEG in the loop" if jpeg else "without compression in the loop"
    return toy.Protection(
        name,
        f"PGD against a PyTorch copy of SFace, L-infinity budget {budget} of 255, {kind}",
        apply,
        band=band,
    )


def gradient_check(module, pixels: np.ndarray, matrix: np.ndarray, seed: int) -> float:
    """Relative gap between autograd and a finite difference, in float64, along one direction.

    The direction is random and the change in the face similarity is measured through
    the same alignment the protection uses. A copy or a warp whose gradient is wrong
    would make a protection tune against noise.
    """
    model = copy.deepcopy(module).double()
    photo = _tensor(pixels).double()
    direction = torch.from_numpy(
        np.random.default_rng(seed).normal(size=tuple(photo.shape))
    ).double()
    with torch.no_grad():
        reference = embed(model, aligned_crop(photo, matrix, quantise=False))

    def similarity(values: torch.Tensor) -> torch.Tensor:
        return (embed(model, aligned_crop(values, matrix, quantise=False)) * reference).sum()

    point = (photo + 0.5 * direction).requires_grad_(True)
    (gradient,) = torch.autograd.grad(similarity(point), point)
    analytic = float((gradient * direction).sum())
    step = 1e-3
    with torch.no_grad():
        numeric = float(similarity(point + step * direction) - similarity(point - step * direction))
    numeric /= 2 * step
    return abs(numeric - analytic) / max(abs(analytic), 1e-12)


def measure_band(
    originals: Sequence[Image.Image], protected: Sequence[Image.Image]
) -> tuple[tuple[float, float], float] | None:
    """The band of spatial frequencies that holds most of a protection's change.

    Returns the pair of Gaussian sigmas, in the form the known band attack takes, and
    the share of the change's energy inside the band, or None when no photo changed.
    Among pairs whose band covers at most a quarter of all frequencies, it picks the one
    that holds the most energy. The band the attack removes at its widest strength is
    the one counted, so the declaration and the attack agree.
    """
    if len(originals) != len(protected):
        raise ValueError("need one protected photo for each original")
    energy = None
    for before, after in zip(originals, protected, strict=True):
        change = np.asarray(after, dtype=np.float64) - np.asarray(before, dtype=np.float64)
        if not change.any():
            continue
        spectrum = sum(np.abs(np.fft.rfft2(change[:, :, c])) ** 2 for c in range(3))
        spectrum = spectrum / spectrum.sum()
        energy = spectrum if energy is None else energy + spectrum
    if energy is None:
        return None
    height = energy.shape[0]
    width = 2 * (energy.shape[1] - 1)
    freq_sq = np.fft.fftfreq(height)[:, None] ** 2 + np.fft.rfftfreq(width)[None, :] ** 2
    weights = np.full(energy.shape, 2.0)
    weights[:, 0] = 1.0
    weights[:, -1] = 1.0
    weights = weights / weights.sum()
    best: tuple[float, tuple[float, float]] | None = None
    for narrow in BAND_SIGMAS:
        for wide in BAND_SIGMAS:
            if narrow >= wide:
                continue
            gain = np.abs(
                np.exp(-2 * np.pi**2 * narrow**2 * freq_sq)
                - np.exp(-2 * np.pi**2 * wide**2 * freq_sq)
            )
            inside = gain >= BAND_REMOVAL_STRENGTH * gain.max()
            if float(weights[inside].sum()) > BAND_MAX_AREA:
                continue
            share = float(energy[inside].sum() / energy.sum())
            if best is None or share > best[0]:
                best = (share, (narrow, wide))
    if best is None:
        return None
    return best[1], best[0]


CALIBRATION_BUDGET = 8


def declare_band(
    make: Callable[[int], toy.Protection], photos: Sequence[Image.Image], seed: int
) -> tuple[tuple[float, float], float] | None:
    """Measure the band a protection writes its change into, on photos kept apart from the test set.

    ``make`` builds the protection for a budget. The band is measured at
    ``CALIBRATION_BUDGET`` and used for every budget, so it is declared before any
    sweep result and never tuned against one. Returns what ``measure_band`` returns.
    """
    base = make(CALIBRATION_BUDGET)
    protected = [base.apply(photo, seed + index) for index, photo in enumerate(photos)]
    return measure_band(photos, protected)


KINDS = ("pgd", "pgd-jpeg")


def protection_factory(
    kind: str,
    module,
    face_model: faces.OpenCVFaceModel,
    calibration: Sequence[Image.Image],
    seed: int,
) -> tuple[Callable[[int], toy.Protection], dict]:
    """A function from budget to protection, with the band already declared, and the record.

    The band is measured on the ``calibration`` photos, which the caller keeps apart from
    the photos under test. The record holds the band and the share of the change inside it,
    both None when no calibration photo had a face.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    jpeg = kind == "pgd-jpeg"

    def build(budget: int, band: tuple[float, float] | None = None) -> toy.Protection:
        return pgd_protection(f"{kind}-{budget}", module, face_model, budget, jpeg, band)

    measured = declare_band(build, calibration, seed)
    band, share = (None, None) if measured is None else measured
    record = {
        "kind": kind,
        "calibration_photos": len(calibration),
        "calibration_budget": CALIBRATION_BUDGET,
        "band": None if band is None else list(band),
        "band_energy_share": share,
    }
    return (lambda budget: build(budget, band)), record


def crop_variants(module, face_model: faces.OpenCVFaceModel, photo: Image.Image) -> dict | None:
    """Split the gap between our crop and OpenCV's into its possible causes, for one photo.

    Every cosine is against OpenCV's vector for OpenCV's own crop. ``copy_on_opencv_crop`` is
    the copy fed OpenCV's crop (the copy check), ``ours`` is the copy fed our crop as the
    pieces check judges it (rounded to whole pixel values), ``ours_unrounded`` is the copy fed
    the smooth crop, and ``opencv_warp_our_matrix`` is the copy fed OpenCV's own warp run
    with our matrix. If that last one is as close as the first, our matrix is right and any
    gap is interpolation and rounding. The pixel gaps are mean absolute differences from
    OpenCV's crop.
    Returns None when no face is found.
    """
    import cv2

    landmarks = face_model.landmarks(photo)
    official = face_model.align(photo)
    if landmarks is None or official is None:
        return None
    matrix = similarity_matrix(landmarks)
    pixels = np.asarray(photo)
    opencv_rgb = official[:, :, ::-1].astype(np.float32)
    reference = F.normalize(torch.from_numpy(face_model.embed_aligned(official))[None], dim=1)
    warped = cv2.warpAffine(pixels, matrix, (CROP, CROP), flags=cv2.INTER_LINEAR)

    def cosine(crop_rgb: np.ndarray) -> float:
        tensor = torch.from_numpy(np.ascontiguousarray(crop_rgb, np.float32).transpose(2, 0, 1))
        with torch.no_grad():
            return float((embed(module, tensor[None]) * reference).sum())

    tensor = _tensor(pixels)
    ours = aligned_crop(tensor, matrix)[0].detach().numpy().transpose(1, 2, 0)
    smooth = aligned_crop(tensor, matrix, quantise=False)[0].numpy().transpose(1, 2, 0)
    return {
        "copy_on_opencv_crop": cosine(opencv_rgb),
        "ours": cosine(ours),
        "ours_unrounded": cosine(smooth),
        "opencv_warp_our_matrix": cosine(warped),
        "gap_ours": float(np.abs(ours - opencv_rgb).mean()),
        "gap_opencv_warp_our_matrix": float(np.abs(warped.astype(np.float32) - opencv_rgb).mean()),
    }
