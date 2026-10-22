"""Report the graphics card, its driver, and whether the installed PyTorch can use it.

    python scripts/check_gpu.py

Uses only the standard library, and PyTorch when it is installed. It changes nothing.
The card matters from the experiments that need a GPU (docs/development/setup.md,
"Check the graphics card"). Everything before that runs on the CPU.
"""

import re
import shutil
import subprocess
import sys

QUERY = "name,compute_cap,memory.total,driver_version"


def parse_capability(text):
    """Turn '6.1' into (6, 1). Returns None when the text is not a version like that."""
    match = re.fullmatch(r"\s*(\d+)\.(\d+)\s*", text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def can_run(arch_list, capability):
    """True when a PyTorch build with these architectures can run on a card of this capability.

    A compiled binary for sm_XY runs on a card with the same major number X and a minor
    number of at least Y. Portable code for compute_XY runs on any card of capability XY
    or newer, after a slow first start.
    """
    for entry in arch_list:
        match = re.fullmatch(r"(sm|compute)_(\d)(\d+)", entry)
        if not match:
            continue
        kind, major, minor = match.group(1), int(match.group(2)), int(match.group(3))
        if kind == "sm" and major == capability[0] and minor <= capability[1]:
            return True
        if kind == "compute" and (major, minor) <= capability:
            return True
    return False


def read_card():
    """Ask nvidia-smi about the first card. Returns a dict, or a message when it cannot."""
    if shutil.which("nvidia-smi") is None:
        return "nvidia-smi was not found. No NVIDIA driver is installed, or it is not on PATH."
    try:
        done = subprocess.run(
            ["nvidia-smi", f"--query-gpu={QUERY}", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"nvidia-smi could not run: {error}"
    if done.returncode != 0 or not done.stdout.strip():
        detail = (done.stderr or done.stdout).strip()
        return f"nvidia-smi failed. Output: {detail or 'none'}"
    fields = [part.strip() for part in done.stdout.splitlines()[0].split(",")]
    if len(fields) != 4:
        return f"nvidia-smi gave an answer in an unexpected shape: {done.stdout.strip()}"
    return dict(zip(QUERY.split(","), fields, strict=True))


def main():
    card = read_card()
    if isinstance(card, str):
        print(card)
        capability = None
    else:
        capability = parse_capability(card["compute_cap"])
        print(f"Card: {card['name']}")
        print(f"Compute capability: {card['compute_cap']}")
        print(f"Video memory: {card['memory.total']}")
        print(f"Driver: {card['driver_version']}")
        if capability is None:
            print("Could not read the compute capability. Update the NVIDIA driver and try again.")

    try:
        import torch
    except ImportError:
        print("PyTorch is not installed. That is fine until an experiment needs it.")
        return 0
    print(f"PyTorch: {torch.__version__}, built for CUDA {torch.version.cuda}")
    if not torch.cuda.is_available():
        print("PyTorch cannot use a GPU here. Experiments will run on the CPU.")
        return 0
    arch_list = torch.cuda.get_arch_list()
    print(f"Architectures in this PyTorch build: {' '.join(arch_list)}")
    if capability is not None:
        if can_run(arch_list, capability):
            print("This build can run on your card.")
        else:
            print(
                "This build has no code for your card. Use an earlier build, or run on the CPU. "
                "See docs/development/setup.md."
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
