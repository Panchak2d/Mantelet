import subprocess

import check_gpu
import pytest

PASCAL = (6, 1)
CUDA_126_LIST = ["sm_50", "sm_60", "sm_70", "sm_75", "sm_80", "sm_86", "sm_90"]
CUDA_128_LIST = ["sm_75", "sm_80", "sm_86", "sm_90", "sm_100", "sm_120"]


def test_capability_text_becomes_a_pair_and_junk_becomes_none():
    assert check_gpu.parse_capability("6.1") == (6, 1)
    assert check_gpu.parse_capability(" 12.0 ") == (12, 0)
    assert check_gpu.parse_capability("[N/A]") is None
    assert check_gpu.parse_capability(None) is None


def test_a_pascal_card_runs_on_a_build_with_sm_60_but_not_on_one_that_starts_at_sm_75():
    assert check_gpu.can_run(CUDA_126_LIST, PASCAL)
    assert not check_gpu.can_run(CUDA_128_LIST, PASCAL)


def test_binary_code_needs_the_same_major_number_and_portable_code_needs_an_older_target():
    assert not check_gpu.can_run(["sm_62"], PASCAL)
    assert not check_gpu.can_run(["sm_70"], PASCAL)
    assert check_gpu.can_run(["sm_61"], PASCAL)
    assert check_gpu.can_run(["sm_75", "compute_60"], PASCAL)
    assert not check_gpu.can_run(["sm_75", "compute_75"], PASCAL)
    assert not check_gpu.can_run(["junk", "sm_x"], PASCAL)


def test_a_missing_nvidia_smi_gives_a_plain_message(monkeypatch):
    monkeypatch.setattr(check_gpu.shutil, "which", lambda _name: None)
    assert "not found" in check_gpu.read_card()


def test_nvidia_smi_output_is_read_and_a_failure_is_reported(monkeypatch):
    monkeypatch.setattr(check_gpu.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")

    def good(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            [], 0, "NVIDIA GeForce MX330, 6.1, 2048 MiB, 580.95\n", ""
        )

    monkeypatch.setattr(check_gpu.subprocess, "run", good)
    card = check_gpu.read_card()
    assert card["name"] == "NVIDIA GeForce MX330" and card["compute_cap"] == "6.1"

    def old_driver(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 2, "", 'Field "compute_cap" is not a valid field')

    monkeypatch.setattr(check_gpu.subprocess, "run", old_driver)
    assert "failed" in check_gpu.read_card()


def test_main_runs_without_a_card_and_does_not_crash(monkeypatch, capsys):
    monkeypatch.setattr(check_gpu, "read_card", lambda: "no card here")
    assert check_gpu.main() == 0
    assert "no card here" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["", "a,b", "a,b,c,d,e"])
def test_an_unexpected_nvidia_smi_shape_is_reported(monkeypatch, bad):
    monkeypatch.setattr(check_gpu.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        check_gpu.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, bad, "")
    )
    assert isinstance(check_gpu.read_card(), str)
