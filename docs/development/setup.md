# Setup on EndeavourOS

Reader: a beginner who wants to run the project on an EndeavourOS laptop (Arch-based Linux). You need a terminal and basic comfort typing commands.

Last reviewed: 21 October 2026

This page gets the project running on the CPU. The graphics card is not used. We have not yet tested these steps on EndeavourOS itself. If a step fails, open a [documentation issue](https://github.com/Panchak2d/mantelet/issues/new/choose) and say which step.

## What you get

A Python 3.13 environment with the three libraries the code uses, Pillow (opens and saves images), NumPy (works with pixel numbers) and OpenCV (runs the face models), and the two checking tools: `pytest` (runs tests) and `ruff` (checks code style).

## Steps

1. Install git and uv. `uv` is a tool that downloads the right Python version and makes the environment.

   ```bash
   sudo pacman -S git uv
   ```

2. Download the project and go into its folder.

   ```bash
   git clone https://github.com/Panchak2d/mantelet.git
   cd mantelet
   ```

3. Get Python 3.13. The file `.python-version` tells uv which one. The Python that came with your system is not touched.

   ```bash
   uv python install
   ```

4. Make a virtual environment and install the project with its checking tools. The environment is a private folder of tools for this project only. `uv sync` installs the exact versions listed in `uv.lock`.

   ```bash
   uv sync --extra dev
   source .venv/bin/activate
   ```

5. Check that everything works. Each command should finish without errors.

   ```bash
   pytest
   ruff check .
   python scripts/check_docs.py
   ```

The last command should end with "No problems found."

Every time you open a new terminal, go into the project folder and run `source .venv/bin/activate` again. If your shell is fish, run `source .venv/bin/activate.fish` instead. You can also skip activation and put `uv run` in front of each command, for example `uv run pytest`.

## Measure a baseline (optional)

This needs a dataset and the face model files. The baseline shows what ordinary photo processing does to a photo and to a face match. It does not protect anything.

1. Read [datasets and models](../../research/datasets-and-models.md). The datasets are non-commercial research data. Download the 100 image sample of Face Synthetics from its [repository page](https://github.com/microsoft/FaceSynthetics) into a `data/` folder. Git ignores that folder.
2. Look through the sample yourself. If every face looks like an adult, change the status of `facesynthetics` to `approved` in `src/mantelet/datasets.py` and in the register page.
3. Download the two face model files. The script checks their hashes and keeps them only if they match.

   ```bash
   python scripts/fetch_models.py
   ```

4. Run the baseline. The zip is read in place and is not unpacked.

   ```bash
   python scripts/run_baseline.py --dataset-id facesynthetics --source data/dataset_100.zip
   ```

The results, a CSV and a report are written to `outputs/`. To rebuild a report from a results file, run `python scripts/make_report.py outputs/baseline-facesynthetics-seed0/results.json`. If the report says many faces were not found, tell us in a documentation issue before you read anything into the numbers.

## Attack the toy protections (optional)

The red team tries to undo toy protections. A toy adds a hidden pattern and does nothing against any model, so this tests the attack tools and not a protection. It needs a dataset from the register with the status `approved`, as in the baseline above, but no model files.

```bash
python scripts/run_redteam.py --dataset-id facesynthetics --source data/dataset_100.zip --count 20
```

Each photo is protected by the script itself. The script never reads a photo that someone else protected. A 512 pixel photo takes about 50 seconds on a laptop CPU for all three toys, so 20 photos take around 17 minutes. The results, a CSV and a report are written to `outputs/redteam-facesynthetics-seed0/`. To rebuild the report from a results file, run `python scripts/make_report.py` on its `results.json`, as for the baseline.

## Pinned versions

| Tool | Version | Why |
|---|---|---|
| Python | 3.13 in `.python-version`. The code accepts 3.11 and newer | PyTorch 2.14 lists 3.13 as supported. Python 3.13 is still receiving fixes |
| Pillow | 12.3 or newer in the 12 series | Releases before 12.1.1 have a known memory corruption bug when opening crafted image files, and 12.2.0 and 12.3.0 fix more. Checked 8 October 2026 against the Pillow release notes |
| NumPy | 2.2 or newer, below 2.6 | Tests pass on 2.4.4 and 2.5.3 |
| OpenCV (`opencv-python-headless`) | 4.14.0.94 or newer in the 4 series | Runs the face detector and recogniser. Version 5.0.0.93 exists. The OpenCV Zoo says the version 5 engine handles the fixed-size detector file differently, and we have not tested it. Checked 9 October 2026 on PyPI |
| pytest | 9.1.1 or newer in the 9 series | Current when checked |
| ruff | 0.16.10 or newer in the 0.16 series | Current when checked |
| uv | whatever `pacman` gives you | Arch lists `uv` in its extra repository |

All of these were checked on 5 October 2026 against PyPI, the Arch package pages, and the Python developer guide.

## Your graphics card and PyTorch (for later)

Nothing uses PyTorch. This section is a note for later steps.

- Your laptop has an NVIDIA MX330 with about 2 GB of video memory. It is a Pascal card (compute capability 6.1). We confirmed the card family and memory from spec sheets. We have not yet checked the compute capability on your own machine. To check it later, run `nvidia-smi` once the driver is installed.
- PyTorch maintainers wrote on the PyTorch developer forum that the CUDA 12.8 and newer builds drop Pascal cards. They also wrote that version 2.14 is the last release with CUDA 12.x builds. After that, a Pascal card needs a PyTorch built from source. This is **Reported**. We will check it again before we pin PyTorch.
- Because of that, the plan is CPU first. later steps run on the CPU.
- 2 GB of video memory cannot realistically run the image editing models used in later steps. Those steps need an outside GPU. 

## One-time step for the maintainer

In the GitHub repository settings, open "Code security" and turn on "Private vulnerability reporting". [SECURITY.md](../../SECURITY.md) links to this form. Until it is on, the form will not work and the email address is the only way to report.
