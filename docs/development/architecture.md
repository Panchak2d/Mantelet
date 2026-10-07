# Architecture

Reader: a contributor or learner who wants to know what is in each folder.

Last reviewed: 8 October 2026

There is no machine learning code yet. This page lists what exists today. It grows as the code grows.

## Folders

| Path | What it holds |
|---|---|
| `README.md`, `SAFETY.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | The front door and the rules |
| `../the project plan` | The project plan |
| `LICENSE`, `LICENSE-docs.md` | Apache-2.0 for the code, CC BY 4.0 for the text |
| `pyproject.toml` | Package name, Python version, and the checking tools |
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

Tests for it are in `tests/test_check_docs.py`.

## The image toolkit

`src/mantelet/image.py` holds one function for each change a platform makes: resize, centre crop, JPEG compression, blur, and noise. The function `platform_pipeline` runs resize, crop, and JPEG in the fixed order and with the fixed numbers from the [test plan](../research/test-plan.md). The numbers are not options.

The pipeline imitates a social site. It is meant to change the photo in plain sight. It is not a protection. Whether a protection is visible is measured by comparing the original photo with the protected photo before the pipeline runs.

Every function rejects settings that would give a broken image, such as a crop that keeps nothing. `load_image` turns the photo upright using its rotation tag, so a phone photo is not processed sideways.

To see the pipeline on one photo, run `python scripts/demo_pipeline.py photo.png out.png`. Save the result as PNG. A JPEG file adds a second lossy pass.

## Automatic checks

On every push and pull request, GitHub runs `.github/workflows/ci.yml`. It installs the project on Python 3.11 and 3.13, then runs `ruff check .`, `pytest`, and the docs checker.
