"""Measure the baseline on a set of test photos and write the results and a report.

    python scripts/fetch_models.py
    python scripts/run_baseline.py --dataset-id facesynthetics \\
        --source data/facesynthetics/dataset_100.zip

No protection is applied. The run shows what ordinary photo processing does to
the pixels and to a face match. The dataset must be in the register
(src/mantelet/datasets.py) with the status 'approved'. The photos are read from a
folder or straight from a zip file and are never copied into the repository.
Results go to outputs/ by default, which git ignores.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from mantelet import baseline, datasets, faces, report

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("results.json", "records.csv", "report.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--count", type=int, default=100, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling and noise")
    parser.add_argument("--out", type=Path, default=None, help="Folder for the results")
    parser.add_argument("--models", type=Path, default=ROOT / "data" / "models")
    parser.add_argument("--no-faces", action="store_true", help="Skip face matching")
    parser.add_argument("--force", action="store_true", help="Overwrite earlier results")
    args = parser.parse_args(argv)

    if not 1 <= args.count <= baseline.MAX_IMAGES:
        return fail(f"--count must be from 1 to {baseline.MAX_IMAGES}")
    try:
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
    except ValueError as error:
        return fail(error)

    out = args.out or ROOT / "outputs" / f"baseline-{entry.id}-seed{args.seed}"
    if not args.force and any((out / name).exists() for name in OUTPUT_FILES):
        return fail(f"results already exist in '{out}'. Use --force to overwrite them")

    embedder = None
    if not args.no_faces:
        try:
            embedder = faces.OpenCVFaceModel(args.models)
        except faces.ModelFileError as error:
            return fail(error)

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
            meta = baseline.build_meta(dataset_meta, len(names), embedder is not None)
            print(f"Measuring {len(names)} photos under {len(baseline.CONDITIONS)} conditions")
            results = baseline.run_baseline(names, source.load, embedder, args.seed, meta)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(
            json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        baseline.write_records_csv(results["records"], out / "records.csv")
        (out / "report.md").write_text(report.render_report(results), encoding="utf-8")
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
