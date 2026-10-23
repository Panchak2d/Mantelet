import json

import make_report
import run_redteam
from test_baseline_scripts import approved_dataset


def run(*args):
    return run_redteam.main([str(arg) for arg in args])


def test_red_team_refuses_a_dataset_that_has_not_been_approved(tmp_path, capsys):
    folder = tmp_path / "photos"
    folder.mkdir()
    assert run("--dataset-id", "digiface1m", "--source", folder) == 1
    assert "needs review" in capsys.readouterr().err


def test_red_team_writes_results_csv_and_report_and_make_report_rebuilds_it(
    monkeypatch, tmp_path, capsys
):
    folder = approved_dataset(monkeypatch, tmp_path)
    out = tmp_path / "out"
    assert run("--dataset-id", "unit-test-set", "--source", folder, "--out", out) == 0
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert results["meta"]["kind"] == "redteam" and results["records"]
    assert (out / "records.csv").is_file()
    assert "Red team report" in (out / "report.md").read_text(encoding="utf-8")
    capsys.readouterr()
    assert make_report.main([str(out / "results.json")]) == 0
    assert "Red team report" in capsys.readouterr().out


def test_red_team_does_not_overwrite_results_without_force_and_checks_the_count(
    monkeypatch, tmp_path, capsys
):
    folder = approved_dataset(monkeypatch, tmp_path)
    args = ("--dataset-id", "unit-test-set", "--source", folder, "--out", tmp_path / "o")
    assert run(*args, "--count", 1) == 0
    assert run(*args, "--count", 1) == 1
    assert "--force" in capsys.readouterr().err
    assert run("--dataset-id", "unit-test-set", "--source", folder, "--count", 0) == 1
    assert "--count" in capsys.readouterr().err


def test_red_team_refuses_a_models_folder_that_has_no_model_files(monkeypatch, tmp_path, capsys):
    folder = approved_dataset(monkeypatch, tmp_path)
    args = ("--dataset-id", "unit-test-set", "--source", folder, "--out", tmp_path / "o")
    assert run(*args, "--models-dir", tmp_path / "no-models") == 1
    assert "fetch_models.py" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


def test_a_pgd_protection_needs_a_budget_and_models_and_a_toy_run_takes_no_budget(
    monkeypatch, tmp_path, capsys
):
    folder = approved_dataset(monkeypatch, tmp_path)
    base = ("--dataset-id", "unit-test-set", "--source", folder, "--out", tmp_path / "o")
    assert run(*base, "--protection", "pgd") == 1
    assert "--models-dir and --budget" in capsys.readouterr().err
    assert run(*base, "--budget", 8) == 1
    assert "--budget applies to a PGD protection only" in capsys.readouterr().err
    assert run(*base, "--protection", "pgd", "--budget", 99, "--models-dir", tmp_path) == 1
    assert "from 1 to 64" in capsys.readouterr().err


def test_a_missing_source_is_reported_as_a_missing_source_and_not_as_a_missing_extra(
    monkeypatch, tmp_path, capsys
):
    approved_dataset(monkeypatch, tmp_path)
    missing = tmp_path / "nowhere.zip"
    code = run(
        "--dataset-id", "unit-test-set", "--source", missing, "--out", tmp_path / "o",
        "--protection", "pgd", "--budget", 4, "--models-dir", tmp_path,
    )
    assert code == 1
    assert "ml extra" not in capsys.readouterr().err
