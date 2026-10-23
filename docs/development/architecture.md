# Architecture

Reader: a contributor or learner who wants to know what is in each folder.

Last reviewed: 23 October 2026

There is no protection code yet. The only machine learning models are the two face models used for measuring. The only protections are toys, made to test the attack tools. This page lists what exists today. It grows as the code grows.

## Folders

| Path | What it holds |
|---|---|
| `README.md`, `SAFETY.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | The front door and the rules |
| `LICENSE`, `LICENSE-docs.md` | Apache-2.0 for the code, CC BY 4.0 for the text |
| `pyproject.toml` | Package name, Python version, the libraries the code needs, the optional `ml` extra (PyTorch 2.14) and the checking tools |
| `uv.lock` | The exact version of every library, so everyone installs the same ones |
| `.python-version` | The exact Python version used for development |
| `.github/` | Automatic checks and the forms for issues and pull requests |
| `docs/` | The documents for readers and contributors |
| `research/` | The claims ledger, the bibliography, and the register of datasets and models with their licences |
| `scripts/` | Small tools that run from the command line: the docs checker, `check_gpu.py`, `demo_pipeline.py`, `check_sface_copy.py`, `check_protection.py`, `diagnose_crop.py`, `run_budget_sweep.py`, `fetch_models.py`, `run_baseline.py`, `run_redteam.py` and `make_report.py` |
| `src/mantelet/` | The Python package. `image.py` loads, saves and changes images. `cropsweep.py` measures survival through the fixed pipeline at many crop positions. `metrics.py`, `faces.py`, `datasets.py`, `baseline.py` and `report.py` measure. `sface_copy.py` builds a PyTorch copy of the SFace file and compares it with OpenCV. `protect.py` is the first protection, PGD through OpenCV's alignment, and `diffjpeg.py` is the differentiable JPEG it uses. They need the `ml` extra. `protectcheck.py` holds the limits for checking their pieces, `budgetsweep.py` runs a protection over a list of budgets, and `effect.py` judges the face match beside the unprotected photo. `budgetgraph.py` draws the perceptual budget graph as an SVG file with no plotting library. `toy.py`, `attacks.py` and `redteam.py` are the red team |
| `data/`, `outputs/` | Created by you, never committed. Datasets and model files go in `data/`. Results go in `outputs/`. Git and the docs checker ignore both |
| `tests/` | Automatic tests |

## The docs checker

`scripts/check_docs.py` reads every Markdown file and runs a list of small checks on its text. Each check is one function. It takes the text and returns a list of problems. The function `check_file` runs all the checks on one file, and `main` runs it on every file and prints the result.

It also checks that the "Last reviewed" date is a real date and is not in the future. It skips the `data/` and `outputs/` folders, where generated reports go. Tests for it are in `tests/test_check_docs.py`.

## The image toolkit

`src/mantelet/image.py` holds one function for each change a platform makes: resize, centre crop, JPEG compression, blur, and noise. The function `platform_pipeline` runs resize, crop, and JPEG in the fixed order and with the fixed numbers from the [test plan](../research/test-plan.md). The numbers are not options.

The pipeline imitates a social site. It is meant to change the photo in plain sight. It is not a protection. Whether a protection is visible is measured by comparing the original photo with the protected photo before the pipeline runs.

Every function rejects settings that would give a broken image, such as a crop that keeps nothing or a blur radius that is not a finite number. The functions that need colour images refuse other image modes instead of guessing.

`load_image` turns the photo upright using its rotation tag, so a phone photo is not processed sideways. It fills transparent areas with white and refuses 16-bit images, which cannot be converted without clipping. It opens only photo formats (JPEG, PNG, WebP, BMP, GIF and TIFF). The Pillow library can read many other formats, and several of its security fixes concern those readers.

The crop can also start at a seeded random corner (`random_crop_offset`, `platform_pipeline_random_crop`), with the same fixed numbers. `cropsweep.py` runs the pipeline at the centre, at seeded random corners and at corners on the 8 pixel grid, and reports how much of a protection's change is left at each.

`mild_platform_pipeline` is the milder second profile: it shrinks only above 1080 pixels, compresses at JPEG 85 and does not crop. The numbers of both pipelines are named constants at the top of `image.py`.

To see the pipeline on one photo, run `python scripts/demo_pipeline.py photo.png out.png`. Add `--mild` for the milder profile. Save the result as PNG. A JPEG file adds a second lossy pass. The script stops instead of overwriting a file unless you add `--force`, and it never writes over its input.

## The measuring tools

These files measure. None of them protects a photo.

- `metrics.py` gives four difference scores for two images of the same size: mean squared error, PSNR, the largest pixel change and SSIM. Each is written from its formula in NumPy. The tests compare SSIM with a slow loop version of the same formula.
- `faces.py` finds a face and turns it into a list of numbers using OpenCV. The model files are pinned to one commit and one SHA-256 hash. The code reads each file into memory, checks it, and only then gives it to OpenCV. The functions that compare faces are plain NumPy, so tests can use a stand-in model. Photos are always opened by `image.load_image`, never by OpenCV.
- `datasets.py` holds the register of datasets and `ImageSource`, which reads photos from a folder or a zip file. A zip file is never unpacked, each photo has a size limit, and a dataset is refused unless its status is `approved`.
- `baseline.py` runs every photo through a fixed list of conditions and records the scores and face matches. It keeps no pixels. `summarise` turns the records into per-condition numbers, with the worst case beside the mean.
- `report.py` turns a results file into a Markdown report that carries the dataset licence and says what was and was not measured.

`scripts/run_baseline.py` joins these together. `scripts/fetch_models.py` downloads the model files and keeps one only if its size and hash match.

## The red team

These files attack. `toy.py` makes three toy protections. Each adds a hidden pattern and does nothing against any model, so the right answer is known. `attacks.py` holds every attack as an `Attack`: a name, an attacker level, a list of strengths and a function. An attack gets the protected photo and a seed, never the original, and returns a photo of the same size. The collusion attack also gets other protected photos, which is what an attacker who collected several would hold. It refuses with `AttackNotApplicable` when it has too few photos of one size.

`redteam.py` protects each photo, runs every attack at every strength and records the survival of the protection's change and the damage to the photo. An attack result counts only above a fixed quality floor. `summarise` keeps, for each photo, the admissible result with the lowest survival, at each attacker level. It never averages across attacks. The numbers are fixed in the [test plan](../research/test-plan.md). A run holds at most 200 photos in memory and skips photos with a side over 1024 pixels. That keeps the memory use of a full run near 1.5 GB.

`scripts/run_redteam.py` joins these together. It protects the photos itself and reads only datasets with the status `approved`, so it has no way to attack a photo that someone else protected. That is how [SAFETY.md](../../SAFETY.md) rule 7 is kept in the code. `report.py` also writes the red team report, and `make_report.py` picks the right report from the results file.

A `Protection` declares its own `band`, or none. The known band attack is built from that band and left out when there is none. `run_redteam` can take a face model, which fills a `face_match` column for every admissible result, and an editor, which fills `edit_success`. No editor exists yet. It also writes survival through the fixed pipeline at many crop positions to `pipeline.csv`, with the face match and similarity after the pipeline, counted against the face in the unprotected original like every other face number. Adding a real protection later means adding another `Protection` that declares its band or structure, and an attack for any structure that is not a band. The attacks that need a diffusion model are not here yet.

## Automatic checks

On every push and pull request, GitHub runs `.github/workflows/ci.yml`. It installs the project on Python 3.11 and 3.13, then checks that `uv.lock` matches `pyproject.toml`, and runs `ruff check .`, `pytest`, and the docs checker. The tests that need the real face model files skip themselves when the files are not there, so they run only on a machine where `fetch_models.py` has been run.
