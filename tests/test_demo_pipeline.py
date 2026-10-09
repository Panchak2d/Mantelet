import demo_pipeline
from PIL import Image


def make_photo(path, size=(64, 48)):
    Image.new("RGB", size, (90, 120, 150)).save(path)
    return path


def run(*args):
    return demo_pipeline.main([str(arg) for arg in args])


def test_demo_writes_the_processed_photo(tmp_path):
    photo = make_photo(tmp_path / "in.png", (200, 100))
    out = tmp_path / "out.png"
    assert run(photo, out) == 0
    assert Image.open(out).size == (409, 204)


def test_demo_refuses_to_write_over_its_input(tmp_path, capsys):
    photo = make_photo(tmp_path / "in.png")
    before = photo.read_bytes()
    assert run(photo, photo, "--force") == 1
    assert "same file" in capsys.readouterr().err
    assert photo.read_bytes() == before


def test_demo_refuses_to_overwrite_without_force(tmp_path, capsys):
    photo = make_photo(tmp_path / "in.png")
    out = make_photo(tmp_path / "out.png", (8, 8))
    before = out.read_bytes()
    assert run(photo, out) == 1
    assert "--force" in capsys.readouterr().err
    assert out.read_bytes() == before
    assert run(photo, out, "--force") == 0


def test_demo_reports_a_file_that_is_not_a_photo(tmp_path, capsys):
    bad = tmp_path / "notes.png"
    bad.write_text("not an image")
    assert run(bad, tmp_path / "out.png") == 1
    assert "could not read" in capsys.readouterr().err


def test_demo_reports_a_missing_input_and_a_missing_output_folder(tmp_path, capsys):
    assert run(tmp_path / "none.png", tmp_path / "out.png") == 1
    photo = make_photo(tmp_path / "in.png")
    assert run(photo, tmp_path / "no_such_folder" / "out.png") == 1
    assert capsys.readouterr().err.count("Error:") == 2
