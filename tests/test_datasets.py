import zipfile
from pathlib import Path

import pytest
from PIL import Image

from mantelet import datasets

DOCS = Path(__file__).resolve().parent.parent / "research" / "datasets-and-models.md"


def save_png(path, size=(16, 16)):
    Image.new("RGB", size, (1, 2, 3)).save(path)


def test_every_registered_dataset_is_in_the_licence_page_with_its_status():
    lines = DOCS.read_text(encoding="utf-8").splitlines()
    for entry in datasets.REGISTER.values():
        row = [line for line in lines if f"`{entry.id}`" in line]
        assert row, entry.id
        assert entry.status in row[0]
        assert entry.licence_url in row[0]


def test_unknown_dataset_id_lists_the_known_ones():
    with pytest.raises(ValueError, match="facesynthetics"):
        datasets.get_entry("nope")


def test_a_dataset_that_needs_review_is_refused():
    with pytest.raises(ValueError, match="needs review"):
        datasets.require_approved(datasets.get_entry("digiface1m"))


def test_sampling_is_repeatable_sorted_and_capped():
    names = [f"{i}.png" for i in range(20)]
    first = datasets.sample_names(names, 5, seed=1)
    assert first == datasets.sample_names(list(reversed(names)), 5, seed=1)
    assert first == sorted(first)
    assert datasets.sample_names(names, 99, seed=1) == sorted(names)
    with pytest.raises(ValueError):
        datasets.sample_names(names, 0, seed=1)


def test_zip_source_lists_photos_skips_other_files_and_reads_without_unpacking(tmp_path):
    archive = tmp_path / "set.zip"
    save_png(tmp_path / "a.png", (20, 10))
    with zipfile.ZipFile(archive, "w") as z:
        z.write(tmp_path / "a.png", "000001.png")
        z.write(tmp_path / "a.png", "000001_seg.png")
        z.writestr("000001_ldmks.txt", "1 2")
    with datasets.ImageSource(archive, skip_suffixes=("_seg.png",)) as source:
        assert source.names == ["000001.png"]
        assert source.load("000001.png").size == (20, 10)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.png", "set.zip"]


def test_folder_source_finds_photos_in_subfolders(tmp_path):
    (tmp_path / "sub").mkdir()
    save_png(tmp_path / "sub" / "x.png")
    (tmp_path / "notes.txt").write_text("hi")
    with datasets.ImageSource(tmp_path) as source:
        assert source.names == ["sub/x.png"]
        assert source.load("sub/x.png").mode == "RGB"


def test_source_rejects_a_path_that_is_neither_folder_nor_zip_and_unknown_names(tmp_path):
    plain = tmp_path / "file.txt"
    plain.write_text("x")
    with pytest.raises(ValueError, match="folder or a zip"):
        datasets.ImageSource(plain)
    with datasets.ImageSource(tmp_path) as source, pytest.raises(ValueError, match="not a photo"):
        source.load("../outside.png")


def test_an_oversized_zip_member_is_refused(tmp_path, monkeypatch):
    archive = tmp_path / "big.zip"
    save_png(tmp_path / "a.png")
    with zipfile.ZipFile(archive, "w") as z:
        z.write(tmp_path / "a.png", "a.png")
    monkeypatch.setattr(datasets, "MAX_IMAGE_BYTES", 10)
    with datasets.ImageSource(archive) as source, pytest.raises(ValueError, match="larger than"):
        source.load("a.png")
