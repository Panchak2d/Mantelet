# Setup on EndeavourOS

Reader: a beginner who wants to run the project on an EndeavourOS laptop (Arch-based Linux). You need a terminal and basic comfort typing commands.

Last reviewed: 23 October 2026

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

Each photo is protected by the script itself. The script never reads a photo that someone else protected. A 512 pixel photo takes about 50 seconds on a laptop CPU for all three toys, plus about 2 seconds for the crop position test, so 20 photos take around 17 minutes. The owner's run took 16 minutes 34 seconds. The results, two CSV files and a report are written to `outputs/redteam-facesynthetics-seed0/`. `records.csv` has one row per attack and `pipeline.csv` has the survival through the fixed pipeline at many crop positions. To rebuild the report from a results file, run `python scripts/make_report.py` on its `results.json`, as for the baseline.

To add the face match, run `python scripts/fetch_models.py` first and add `--models-dir data/models`. Every attacked photo that stays above the quality floor is then matched against the face in the unprotected original. This adds several minutes. The owner's run of 20 photos with the face match took 25 minutes. Without it the face match columns stay empty and the report says so. The edit success column stays empty in every run until an editing model is built.

## Check the PyTorch copy of SFace (optional)

A protection that is tuned with gradients needs a model PyTorch can differentiate. The face match in the red team runs the SFace file through OpenCV, so before anything is tuned we check that a PyTorch copy of SFace gives the same face vectors as OpenCV. Install the extra, then run the check on the photos you already approved:

```text
uv sync --extra dev --extra ml
python scripts/check_sface_copy.py --dataset-id facesynthetics \
    --source data/dataset_100.zip --models-dir data/models
```

The script finds and aligns a face in 20 sampled photos, gets one vector from OpenCV and one from the copy, and writes `sface-copy.md` and `sface-copy.json` to `outputs/sface-copy-facesynthetics-seed0/`. It exits with 0 on a pass, 2 on a fail and 1 when something could not run. The limits are in the [test plan](../research/test-plan.md). The PyPI wheel of PyTorch works on the CPU, and it is large because it carries the CUDA libraries. If the conversion step stops on an operation `onnx2torch` does not know, send the message. Nothing has run this script against the real SFace file yet.

## Check, sweep and attack a PGD protection (optional)

The first protection is projected gradient descent against the PyTorch copy of SFace. It needs the `ml` extra, the model files, an approved dataset and a passed copy check. The commands are for fish. Each one stops the chain if it fails:

```fish
cd mantelet
uv sync --extra dev --extra ml
source .venv/bin/activate.fish
uv run python scripts/check_protection.py --dataset-id facesynthetics \
    --source data/dataset_100.zip --models-dir data/models
and uv run python scripts/run_budget_sweep.py --dataset-id facesynthetics \
    --source data/dataset_100.zip --models-dir data/models
```

`check_protection.py` checks our crop, the gradient and our JPEG against the limits in the [test plan](../research/test-plan.md) and writes `protection-check.md`. It exits with 2 when a limit is missed. If the crop limit is missed, `uv run python scripts/diagnose_crop.py` with the same arguments prints, for each face, how far the copy's vector moves when it is fed OpenCV's crop, our crop, our crop without rounding, and OpenCV's own warp with our matrix. It changes nothing. `run_budget_sweep.py` protects the 20 sampled photos at each budget, for both `pgd` and `pgd-jpeg`, measures PSNR, SSIM, survival and the face match beside the unprotected photo, and writes `sweep.json`, `sweep-rows.csv` and one graph per kind (`budget-pgd.svg`, `budget-pgd-jpeg.svg`) to `outputs/sweep-facesynthetics-seed0/`. It declares each band on 8 photos kept apart from the 20. It prints how many seconds each kind took. Nobody has timed it on a laptop CPU yet.

Then attack one protection at the budget the sweep reports as `gate_budget` in `sweep.json`:

```fish
uv run python scripts/run_redteam.py --dataset-id facesynthetics \
    --source data/dataset_100.zip --models-dir data/models \
    --protection pgd --budget 8
```

The report adds the face match beside the unprotected photo, with the three states, and the declared band. Open the graphs in a browser to look at them.

## Pinned versions

| Tool | Version | Why |
|---|---|---|
| Python | 3.13 in `.python-version`. The code accepts 3.11 and newer | PyTorch 2.14 lists 3.13 as supported. Python 3.13 is still receiving fixes |
| Pillow | 12.3 or newer in the 12 series | Releases before 12.1.1 have a known memory corruption bug when opening crafted image files, and 12.2.0 and 12.3.0 fix more. Checked 8 October 2026 against the Pillow release notes |
| NumPy | 2.2 or newer, below 2.6 | Tests pass on 2.4.4 and 2.5.3 |
| OpenCV (`opencv-python-headless`) | 4.14.0.94 or newer in the 4 series | Runs the face detector and recogniser. Version 5.0.0.93 exists. The OpenCV Zoo says the version 5 engine handles the fixed-size detector file differently, and we have not tested it. Checked 9 October 2026 on PyPI |
| PyTorch (extra `ml`) | 2.14, below 2.15 | Optional. Install with `uv sync --extra dev --extra ml`. Keep `--extra dev`, because `uv sync` removes anything not listed. Version 2.14 is the last release with a CUDA 12.x build, which is the only one that covers a Pascal card (claim C-004). The newest 2.14 release on PyPI was 2.14.1 when checked on 22 October 2026. The copy check, the protection checks and the PGD protections import it, together with `onnx2torch` 1.5 from the same extra |
| pytest | 9.1.1 or newer in the 9 series | Current when checked |
| ruff | 0.16.10 or newer in the 0.16 series | Current when checked |
| uv | whatever `pacman` gives you | Arch lists `uv` in its extra repository |

All of these were checked on 5 October 2026 against PyPI, the Arch package pages, and the Python developer guide.

## Your graphics card and PyTorch

Everything so far runs on the CPU, and so do the first protection experiments, because a small face model fits in ordinary memory. A GPU is optional until the steps that run diffusion models.

**Check the card.** Run this once the NVIDIA driver is installed. It changes nothing.

```bash
python scripts/check_gpu.py
```

It prints the card, its compute capability, its memory and its driver, and, if PyTorch is installed, whether that PyTorch build has code for the card. The MX330 should show compute capability 6.1 (claim C-040). Three sources agree, but none of them is NVIDIA's own list, so send us the output if it shows something else.

What we found when we rechecked on 22 October 2026 (claim C-004, **Reported**):

- The MX330 is a Pascal card with 2 GB of video memory. 2 GB cannot realistically run the image editing models used in steps 9 to 12, so those steps need an outside GPU, see [compute options](../../research/compute-options.md).
- PyTorch builds for CUDA 12.8 and newer do not include Pascal. The CUDA 12.6 build does, and it is the last one: version 2.14 is the last release with a CUDA 12.x build. That build is served from `download.pytorch.org` and not from PyPI. The PyPI wheels of 2.14 are built for newer cards. This is why we pin PyTorch to the 2.14 series. Version 2.15 would drop the card.
- **The driver matters more than PyTorch on EndeavourOS.** NVIDIA's 580 series is the last driver series that supports Pascal. Arch Linux moved its normal packages to the 590 series in December 2025, which does not support the card. If the card does not show up in `nvidia-smi`, install the older driver from the AUR, for example `nvidia-580xx-dkms` with `nvidia-580xx-utils`, and remove the newer `nvidia` packages first. We have not tested this on your machine.
- To use the card with PyTorch, install the CUDA 12.6 build of 2.14 from the PyTorch download site, then run `scripts/check_gpu.py` again. The install line is on pytorch.org, and we did not run it. If you skip this step, PyTorch from PyPI works on the CPU.
- We have not run any PyTorch build on a Pascal card. The CUDA 12.6 build lists code for sm_60 and not sm_61. NVIDIA's rule is that a binary for sm_60 runs on a 6.x card with a higher minor number. `scripts/check_gpu.py` applies that rule and prints the result.

## One-time step for the maintainer

In the GitHub repository settings, open "Code security" and turn on "Private vulnerability reporting". [SECURITY.md](../../SECURITY.md) links to this form. Until it is on, the form will not work and the email address is the only way to report.
