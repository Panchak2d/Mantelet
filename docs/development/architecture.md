# Architecture

Reader: a contributor or learner who wants to know what is in each folder.

Last reviewed: 8 October 2026

There is no machine learning code yet. This page lists what exists today. It grows as the code grows.

## Folders

| Path | What it holds |
|---|---|
| `README.md`, `SAFETY.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | The front door and the rules |
| `LICENSE`, `LICENSE-docs.md` | Apache-2.0 for the code, CC BY 4.0 for the text |
| `pyproject.toml` | Package name, Python version, the libraries the code needs, and the checking tools |
| `uv.lock` | The exact version of every library, so everyone installs the same ones |
| `.python-version` | The exact Python version used for development |
| `.github/` | Automatic checks and the forms for issues and pull requests |
| `docs/` | The documents for readers and contributors |
| `research/` | The claims ledger and the bibliography |
| `learning/` | Practice tasks written by the project owner |
| `scripts/` | Small tools that run from the command line, such as the docs checker and `demo_pipeline.py` |
| `src/mantelet/` | The Python package. `image.py` loads and saves images and applies the changes platforms make to a photo |
| `tests/` | Automatic tests |

## The docs checker

`scripts/check_docs.py` reads every Markdown file and runs a list of small checks on its text. Each check is one function. It takes the text and returns a list of problems. The function `check_file` runs all the checks on one file, and `main` runs it on every file and prints the result.

It also checks that the "Last reviewed" date is a real date and is not in the future. Tests for it are in `tests/test_check_docs.py`.

## The image toolkit

`src/mantelet/image.py` holds one function for each change a platform makes: resize, centre crop, JPEG compression, blur, and noise. The function `platform_pipeline` runs resize, crop, and JPEG in the fixed order and with the fixed numbers from the [test plan](../research/test-plan.md). The numbers are not options.

The pipeline imitates a social site. It is meant to change the photo in plain sight. It is not a protection. Whether a protection is visible is measured by comparing the original photo with the protected photo before the pipeline runs.

Every function rejects settings that would give a broken image, such as a crop that keeps nothing or a blur radius that is not a finite number. The functions that need colour images refuse other image modes instead of guessing.

`load_image` turns the photo upright using its rotation tag, so a phone photo is not processed sideways. It fills transparent areas with white and refuses 16-bit images, which cannot be converted without clipping. It opens only photo formats (JPEG, PNG, WebP, BMP, GIF and TIFF). The Pillow library can read many other formats, and several of its security fixes concern those readers.

To see the pipeline on one photo, run `python scripts/demo_pipeline.py photo.png out.png`. Save the result as PNG. A JPEG file adds a second lossy pass. The script stops instead of overwriting a file unless you add `--force`, and it never writes over its input.

## Automatic checks

On every push and pull request, GitHub runs `.github/workflows/ci.yml`. It installs the project on Python 3.11 and 3.13, then checks that `uv.lock` matches `pyproject.toml`, and runs `ruff check .`, `pytest`, and the docs checker.
