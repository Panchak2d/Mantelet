import numpy as np
import pytest
from conftest import smooth_photo
from PIL import Image

torch = pytest.importorskip("torch")
cv2 = pytest.importorskip("cv2")

from mantelet import protect, toy  # noqa: E402

LANDMARKS = (protect._TARGETS - protect._TARGET_MEAN) * 1.5 + np.array([64.0, 60.0])


def stand_in_network():
    torch.manual_seed(0)
    network = torch.nn.Sequential(
        torch.nn.Conv2d(3, 8, 5, 4),
        torch.nn.PReLU(8),
        torch.nn.Conv2d(8, 8, 3, 2),
        torch.nn.Flatten(),
        torch.nn.Linear(8 * 13 * 13, 32),
    ).eval()
    for parameter in network.parameters():
        parameter.requires_grad_(False)
    return network


def similarity_to_clean(network, clean, other, matrix):
    with torch.no_grad():
        first = protect.embed(network, protect.aligned_crop(protect._tensor(clean), matrix))
        second = protect.embed(network, protect.aligned_crop(protect._tensor(other), matrix))
    return float((first * second).sum())


def test_the_matrix_is_the_least_squares_similarity_onto_the_fixed_targets():
    rng = np.random.default_rng(0)
    points = LANDMARKS + rng.normal(0, 1.0, (5, 2))
    matrix = protect.similarity_matrix(points)
    assert matrix[0, 0] == pytest.approx(matrix[1, 1])
    assert matrix[0, 1] == pytest.approx(-matrix[1, 0])
    rows, goal = [], []
    for (x, y), (u, v) in zip(points, protect._TARGETS, strict=True):
        rows += [[x, -y, 1, 0], [y, x, 0, 1]]
        goal += [u, v]
    a, b, tx, ty = np.linalg.lstsq(np.array(rows), np.array(goal), rcond=None)[0]
    assert matrix[0, 0] == pytest.approx(a, abs=1e-6)
    assert matrix[1, 0] == pytest.approx(b, abs=1e-6)
    assert matrix[0, 2] == pytest.approx(tx, abs=1e-3)
    assert matrix[1, 2] == pytest.approx(ty, abs=1e-3)


def test_landmarks_in_a_line_or_of_the_wrong_shape_are_refused():
    with pytest.raises(ValueError, match="line"):
        protect.similarity_matrix(np.column_stack([np.arange(5.0), np.arange(5.0)]))
    with pytest.raises(ValueError, match="shape"):
        protect.similarity_matrix(np.zeros((4, 2)))


def test_the_differentiable_crop_agrees_with_opencv_warp_affine():
    img = smooth_photo(3, 128)
    matrix = protect.similarity_matrix(LANDMARKS + np.random.default_rng(1).normal(0, 1, (5, 2)))
    expected = cv2.warpAffine(np.asarray(img), matrix, (112, 112), flags=cv2.INTER_LINEAR)
    got = protect.aligned_crop(protect._tensor(np.asarray(img)), matrix)[0].numpy()
    assert np.abs(got.transpose(1, 2, 0) - expected).mean() < 0.05
    assert np.array_equal(got, np.round(got))
    smooth = protect.aligned_crop(protect._tensor(np.asarray(img)), matrix, quantise=False)
    assert np.abs(smooth[0].numpy().transpose(1, 2, 0) - expected).mean() < 0.5


def test_the_rounding_in_the_crop_lets_the_gradient_straight_through():
    values = protect._tensor(np.asarray(smooth_photo(2, 128))).requires_grad_(True)
    crop = protect.aligned_crop(values, protect.similarity_matrix(LANDMARKS))
    crop.sum().backward()
    assert float(values.grad.abs().sum()) > 0


def test_the_gradient_through_the_crop_and_the_network_matches_a_finite_difference():
    pixels = np.asarray(smooth_photo(4, 128))
    matrix = protect.similarity_matrix(LANDMARKS)
    assert protect.gradient_check(stand_in_network(), pixels, matrix, 0) < 1e-2


@pytest.mark.parametrize("jpeg", [False, True])
def test_pgd_stays_in_the_budget_leaves_the_rest_alone_and_lowers_the_similarity(jpeg):
    network = stand_in_network()
    pixels = np.asarray(smooth_photo(5, 128))
    matrix = protect.similarity_matrix(LANDMARKS * 0.4 + np.array([38.0, 36.0]))
    changed = protect.pgd(network, pixels, matrix, 6, 0, jpeg=jpeg, steps=15)
    difference = changed.astype(int) - pixels.astype(int)
    assert changed.dtype == np.uint8 and np.abs(difference).max() <= 6 and difference.any()
    edge = 124 if jpeg else 100
    assert not difference[:, edge:].any()
    assert similarity_to_clean(network, pixels, changed, matrix) < 0.999
    again = protect.pgd(network, pixels, matrix, 6, 0, jpeg=jpeg, steps=15)
    assert np.array_equal(changed, again)


def test_pgd_refuses_a_bad_budget_or_photo():
    network, matrix = stand_in_network(), protect.similarity_matrix(LANDMARKS)
    pixels = np.asarray(smooth_photo(5, 128))
    for budget in (0, 65, 2.5):
        with pytest.raises(ValueError, match="budget"):
            protect.pgd(network, pixels, matrix, budget, 0)
    with pytest.raises(ValueError, match="uint8"):
        protect.pgd(network, pixels.astype(np.float32), matrix, 4, 0)


class OneFace:
    def __init__(self, landmarks):
        self._landmarks = landmarks

    def landmarks(self, img):
        return self._landmarks


def test_a_photo_with_no_face_is_returned_unchanged_and_a_photo_with_one_is_changed():
    img = smooth_photo(6, 128)
    network = stand_in_network()
    none = protect.pgd_protection("pgd-4", network, OneFace(None), 4)
    assert none.apply(img, 0) is img
    some = protect.pgd_protection("pgd-4", network, OneFace(LANDMARKS), 4, band=(1.0, 2.0))
    assert some.band == (1.0, 2.0) and "without compression" in some.description
    assert np.asarray(some.apply(img, 0)).shape == (128, 128, 3)
    assert not np.array_equal(np.asarray(some.apply(img, 0)), np.asarray(img))


def test_the_measured_band_finds_where_a_coarse_pattern_lives_and_none_without_a_change():
    originals = [smooth_photo(i, 128) for i in range(3)]
    protected = [
        Image.fromarray(
            np.clip(np.asarray(o, dtype=float) + toy.band_pattern((128, 128, 3), i), 0, 255)
            .round()
            .astype(np.uint8)
        )
        for i, o in enumerate(originals)
    ]
    (narrow, wide), share = protect.measure_band(originals, protected)
    assert share > 0.5 and narrow < wide and wide >= 4.0
    assert protect.measure_band(originals, originals) is None
    with pytest.raises(ValueError, match="one protected photo"):
        protect.measure_band(originals, protected[:2])


class StandInFaces:
    """Face model stand-in: fixed landmarks, and a vector from the stand-in network."""

    def __init__(self, network):
        self.network = network
        self.matrix = protect.similarity_matrix(LANDMARKS)

    def landmarks(self, img):
        return LANDMARKS

    def embed(self, img):
        with torch.no_grad():
            tensor = protect._tensor(np.asarray(img))
            crop = protect.aligned_crop(tensor, self.matrix)
            return protect.embed(self.network, crop)[0].numpy()


@pytest.mark.parametrize("kind", protect.KINDS)
def test_a_sweep_of_a_pgd_protection_runs_end_to_end_with_its_band_declared_apart(kind):
    from mantelet import budgetsweep, redteam

    network = stand_in_network()
    faces_stand_in = StandInFaces(network)
    photos = [(i, f"p{i}", smooth_photo(i, 128)) for i in range(2)]
    vectors = {name: faces_stand_in.embed(photo) for _, name, photo in photos}
    calibration = [smooth_photo(10 + i, 128) for i in range(2)]
    make, record = protect.protection_factory(kind, network, faces_stand_in, calibration, 0)
    assert record["kind"] == kind and record["calibration_photos"] == 2
    assert record["band"] is not None and 0 < record["band_energy_share"] <= 1
    assert make(4).band == tuple(record["band"]) and make(4).name == f"{kind}-4"
    summaries, rows = budgetsweep.run_sweep(photos, vectors, make, [2, 4], faces_stand_in, 0)
    assert [s["budget"] for s in summaries] == [2, 4] and len(rows) == 4
    assert all(row["changed"] and row["admissible"] for row in rows)
    results = redteam.run_redteam(
        [n for _, n, _ in photos],
        dict((n, p) for _, n, p in photos).__getitem__,
        [make(4)],
        0,
        redteam.build_meta({"id": "x", "name": "X", "licence": "L", "status": "approved"}, 2, kind),
        face_model=faces_stand_in,
    )
    assert {r["protection"] for r in results["pipeline"]} == {"none", f"{kind}-4"}
    with pytest.raises(ValueError, match="kind"):
        protect.protection_factory("fgsm", network, faces_stand_in, calibration, 0)


class OpenCVStandIn(StandInFaces):
    """Adds what ``crop_variants`` asks of the face model: OpenCV's crop and its vector."""

    def align(self, img):
        warped = cv2.warpAffine(np.asarray(img), self.matrix, (112, 112), flags=cv2.INTER_LINEAR)
        return np.ascontiguousarray(warped[:, :, ::-1])

    def embed_aligned(self, crop_bgr):
        with torch.no_grad():
            tensor = torch.from_numpy(
                np.ascontiguousarray(crop_bgr[:, :, ::-1].transpose(2, 0, 1), np.float32)
            )[None]
            return protect.embed(self.network, tensor)[0].numpy()


def test_the_crop_variants_split_the_gap_and_our_matrix_reproduces_the_stand_in_exactly():
    network = stand_in_network()
    model = OpenCVStandIn(network)
    values = protect.crop_variants(network, model, smooth_photo(7, 128))
    assert values["copy_on_opencv_crop"] == pytest.approx(1.0, abs=1e-5)
    assert values["opencv_warp_our_matrix"] == pytest.approx(1.0, abs=1e-5)
    assert values["gap_opencv_warp_our_matrix"] == 0.0
    assert 0.9 < values["ours_unrounded"] <= 1.0 and values["gap_ours"] < 0.05
    assert protect.crop_variants(network, OneFaceNone(), smooth_photo(7, 128)) is None


class OneFaceNone:
    def landmarks(self, img):
        return None

    def align(self, img):
        return None
