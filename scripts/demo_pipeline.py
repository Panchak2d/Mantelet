"""Run one image through the fixed platform pipeline and save the result.

    python scripts/demo_pipeline.py photo.png out.png
    python scripts/demo_pipeline.py photo.png out.png --noise --seed 1

The pipeline imitates what a social site does to a photo: shrink it, crop it,
compress it. The output is meant to look different from the input. This is not
a protection and does not hide anything. With --noise, random noise is added
first and the pipeline runs second, the order used in the experiments.

The script never overwrites a file unless you pass --force, and never writes
over its own input.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

from mantelet import image

LOSSY_SUFFIXES = {".jpg", ".jpeg"}
NOISE_STD = 15.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", type=Path, help="Path to the input image")
    parser.add_argument("output", type=Path, help="Where to save the result (.png is exact)")
    parser.add_argument("--noise", action="store_true", help="Add random noise first")
    parser.add_argument("--seed", type=int, default=None, help="Makes --noise repeatable")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        return fail(f"could not find '{args.input}'")
    if args.output.exists() and args.output.samefile(args.input):
        return fail("the output is the same file as the input. Choose a different output path")
    if args.output.exists() and not args.force:
        return fail(f"'{args.output}' already exists. Use --force to overwrite it")
    if not args.output.parent.is_dir():
        return fail(f"the folder '{args.output.parent}' does not exist")

    try:
        img = image.load_image(args.input)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(f"could not read '{args.input}' as a photo: {error}")
    print(f"Original size: {img.size}")

    if args.noise:
        img = image.add_gaussian_noise(img, std=NOISE_STD, seed=args.seed)
        print(f"Added Gaussian noise, std {NOISE_STD}, seed {args.seed}")

    processed = image.platform_pipeline(img)
    print(f"After pipeline (resize to 512, crop to 80 percent, JPEG 75): {processed.size}")

    if args.output.suffix.lower() in LOSSY_SUFFIXES:
        print("Note: saving as JPEG adds a second lossy pass. Use .png to keep the output exact.")
    try:
        image.save_image(processed, args.output)
    except (OSError, ValueError) as error:
        return fail(f"could not save '{args.output}': {error}")
    print(f"Saved to {args.output}")
    return 0


def fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
