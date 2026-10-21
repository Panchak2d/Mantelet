import hashlib
import io
import json

import fetch_models
import make_report
import pytest
import run_baseline
from PIL import Image

from mantelet import datasets, faces


def approved_dataset(monkeypatch, tmp_path):
    entry = datasets.DatasetEntry(
        id="unit-test-set",
        name="Unit test set",
        licence="Test licence",
        licence_url="https://example.invalid/licence",
        source_url="https://example.invalid",
        adult_basis="Not a face set",
        status=datasets.APPROVED,
    )
    monkeypatch.setitem(datasets.REGISTER, entry.id, entry)
    folder = tmp_path / "photos"
    folder.mkdir()
    for index in range(3):
        Image.new("RGB", (80, 80), (index * 40, 90, 120)).save(folder / f"{index}.png")
    return folder


def run(*args):
    return run_baseline.main([str(arg) for arg in args])


def test_baseline_refuses_a_dataset_that_has_not_been_approved(tmp_path, capsys):
    folder = tmp_path / "photos"
    folder.mkdir()
    assert run("--dataset-id", "digiface1m", "--source", folder) == 1
    assert "needs review" in capsys.readouterr().err


def test_baseline_writes_results_csv_and_report(monkeypatch, tmp_path):
    folder = approved_dataset(monkeypatch, tmp_path)
    out = tmp_path / "out"
    assert run("--dataset-id", "unit-test-set", "--source", folder, "--out", out, "--no-faces") == 0
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert results["meta"]["dataset"]["id"] == "unit-test-set"
    assert len(results["records"]) == 3 * len(results["meta"]["conditions"])
    assert (out / "records.csv").is_file()
    assert "Baseline report" in (out / "report.md").read_text(encoding="utf-8")


def test_baseline_does_not_overwrite_results_without_force(monkeypatch, tmp_path, capsys):
    folder = approved_dataset(monkeypatch, tmp_path)
    args = ("--dataset-id", "unit-test-set", "--source", folder, "--out", tmp_path / "o")
    assert run(*args, "--no-faces") == 0
    assert run(*args, "--no-faces") == 1
    assert "--force" in capsys.readouterr().err
    assert run(*args, "--no-faces", "--force") == 0


def test_baseline_says_how_to_get_missing_models(monkeypatch, tmp_path, capsys):
    folder = approved_dataset(monkeypatch, tmp_path)
    args = ["--dataset-id", "unit-test-set", "--source", folder, "--out", tmp_path / "o"]
    assert run(*args, "--models", tmp_path / "none") == 1
    assert "fetch_models" in capsys.readouterr().err


def test_baseline_rejects_a_count_outside_the_limits(monkeypatch, tmp_path, capsys):
    folder = approved_dataset(monkeypatch, tmp_path)
    assert run("--dataset-id", "unit-test-set", "--source", folder, "--count", 0) == 1
    assert "--count" in capsys.readouterr().err


def test_make_report_rebuilds_the_report_and_rejects_other_files(monkeypatch, tmp_path, capsys):
    folder = approved_dataset(monkeypatch, tmp_path)
    out = tmp_path / "out"
    run("--dataset-id", "unit-test-set", "--source", folder, "--out", out, "--no-faces")
    assert make_report.main([str(out / "results.json")]) == 0
    assert "Baseline report" in capsys.readouterr().out
    other = tmp_path / "other.json"
    other.write_text("{}")
    assert make_report.main([str(other)]) == 1


CONTENT = b"pretend model file"
FAKE = faces.ModelFile(
    folder="f",
    filename="fake.onnx",
    sha256=hashlib.sha256(CONTENT).hexdigest(),
    size=len(CONTENT),
    licence="test",
)


def opener_returning(data, calls):
    def opener(url, timeout):
        calls.append(url)
        return io.BytesIO(data)

    return opener


def test_a_correct_download_is_saved(tmp_path):
    calls = []
    fetch_models.download(FAKE, tmp_path, opener_returning(CONTENT, calls))
    assert (tmp_path / "fake.onnx").read_bytes() == CONTENT
    assert [p.name for p in tmp_path.iterdir()] == ["fake.onnx"]


def test_a_download_with_the_wrong_bytes_is_rejected_and_nothing_is_saved(tmp_path):
    with pytest.raises(faces.ModelFileError, match="Nothing was saved"):
        fetch_models.download(FAKE, tmp_path, opener_returning(b"x" * len(CONTENT), []))
    assert list(tmp_path.iterdir()) == []


def test_a_file_that_is_already_correct_is_not_downloaded_again(tmp_path):
    (tmp_path / "fake.onnx").write_bytes(CONTENT)
    calls = []
    fetch_models.download(FAKE, tmp_path, opener_returning(b"other", calls))
    assert calls == []
