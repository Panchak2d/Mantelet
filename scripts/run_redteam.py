"""Attack the toy protections on a set of test photos and write the results and a report.

    python scripts/run_redteam.py --dataset-id facesynthetics \\
        --source data/facesynthetics/dataset_100.zip --count 20

The script protects each photo itself with a toy protection from
src/mantelet/toy.py and then tries every attack in src/mantelet/attacks.py. It
never reads a photo that someone else protected. The toy protections do nothing
against any model, so the run tests the attack tools and not a protection. The
dataset must be in the register (src/mantelet/datasets.py) with the status
'approved'. Results go to outputs/ by default, which git ignores.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from mantelet import datasets, redteam, report, toy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("results.json", "records.csv", "report.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling and noise")
    parser.add_argument("--out", type=Path, default=None, help="Folder for the results")
    parser.add_argument("--force", action="store_true", help="Overwrite earlier results")
    args = parser.parse_args(argv)

    if not 1 <= args.count <= redteam.MAX_IMAGES:
        return fail(f"--count must be from 1 to {redteam.MAX_IMAGES}")
    try:
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
    except ValueError as error:
        return fail(error)

    out = args.out or ROOT / "outputs" / f"redteam-{entry.id}-seed{args.seed}"
    if not args.force and any((out / name).exists() for name in OUTPUT_FILES):
        return fail(f"results already exist in '{out}'. Use --force to overwrite them")

    try:
        with datasets.ImageSource(args.source, entry.skip_suffixes) as source:
            if not source.names:
                return fail(f"no photos found in '{args.source}'")
            names = datasets.sample_names(source.names, args.count, args.seed)
            dataset_meta = {
                "id": entry.id,
                "name": entry.name,
                "licence": entry.licence,
                "status": entry.status,
            }
            meta = redteam.build_meta(dataset_meta, len(names))
            print(f"Attacking {len(names)} photos under {len(toy.TOY_PROTECTIONS)} toy protections")
            results = redteam.run_redteam(names, source.load, toy.TOY_PROTECTIONS, args.seed, meta)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(
            json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        redteam.write_records_csv(results["records"], out / "records.csv")
        (out / "report.md").write_text(report.render_redteam_report(results), encoding="utf-8")
    except OSError as error:
        return fail(f"could not write the results: {error}")
    skipped = len(results["skipped"])
    print(f"Wrote results.json, records.csv and report.md to {out} ({skipped} photos skipped)")
    return 0


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
