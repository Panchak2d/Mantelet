# Setup on EndeavourOS

Reader: a beginner who wants to run the project on an EndeavourOS laptop (Arch-based Linux). You need a terminal and basic comfort typing commands.

Last reviewed: Batch 1, 5 October 2026

This page gets the project running on the CPU. The graphics card is not used in Batch 1. We have not yet tested these steps on EndeavourOS itself. If a step fails, open a [documentation issue](https://github.com/Panchak2d/mantelet/issues/new/choose) and say which step.

## What you get

A Python 3.13 environment with the two checking tools: `pytest` (runs tests) and `ruff` (checks code style). Nothing else is needed yet.

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

4. Make a virtual environment. This is a private folder of tools for this project only.

   ```bash
   uv venv
   source .venv/bin/activate
   ```

5. Install the project and its checking tools.

   ```bash
   uv pip install -e ".[dev]"
   ```

6. Check that everything works. Each command should finish without errors.

   ```bash
   pytest
   ruff check .
   python scripts/check_docs.py
   ```

The last command should end with "No problems found."

Every time you open a new terminal, go into the project folder and run `source .venv/bin/activate` again.

## Pinned versions

| Tool | Version | Why |
|---|---|---|
| Python | 3.13 in `.python-version`. The code accepts 3.11 and newer | PyTorch 2.14 lists 3.13 as supported. Python 3.13 is still receiving fixes |
| pytest | 9.1.1 or newer in the 9 series | Current when checked |
| ruff | 0.16.10 or newer in the 0.16 series | Current when checked |
| uv | whatever `pacman` gives you | Arch lists `uv` in its extra repository |

All of these were checked on 5 October 2026 against PyPI, the Arch package pages, and the Python developer guide.

## Your graphics card and PyTorch (for later)

Nothing in Batch 1 uses PyTorch. This section is a note for later batches.

- Your laptop has an NVIDIA MX330 with about 2 GB of video memory. It is a Pascal card (compute capability 6.1). We confirmed the card family and memory from spec sheets. We have not yet checked the compute capability on your own machine. To check it later, run `nvidia-smi` once the driver is installed.
- PyTorch maintainers wrote on the PyTorch developer forum that the CUDA 12.8 and newer builds drop Pascal cards. They also wrote that version 2.14 is the last release with CUDA 12.x builds. After that, a Pascal card needs a PyTorch built from source. This is **Reported**. Batch 6 checks it again before we pin PyTorch.
- Because of that, the plan is CPU first. Batches 1 to 5 run on the CPU.
- 2 GB of video memory cannot realistically run the image editing models used in Batches 9 to 12. Those batches need an outside GPU. See [PLAN.md](../../PLAN.md) section 10.

## One-time step for the maintainer

In the GitHub repository settings, open "Code security" and turn on "Private vulnerability reporting". [SECURITY.md](../../SECURITY.md) links to this form. Until it is on, the form will not work and the email address is the only way to report.
