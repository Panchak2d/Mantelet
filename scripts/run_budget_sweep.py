"""Run a PGD protection over a list of budgets and write the budget graph.

    uv run python scripts/run_budget_sweep.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --models-dir data/models

For each budget and each protection kind it protects the sampled photos, measures PSNR,
SSIM, survival through the fixed pipeline and the face match beside the unprotected
photo, and writes one SVG graph per kind. The band each protection declares is
measured on photos kept apart from the sampled ones. No attack runs here. It needs the
``ml`` extra and passed copy and protection checks. Results go to outputs/ by default.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from PIL import Image

from mantelet import baseline, budgetgraph, budgetsweep, datasets, faces, redteam, sface_copy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("sweep.json", "sweep-rows.csv")
DEFAULT_BUDGETS = "1,2,3,4,6,8,12,16"
ROW_FIELDS = (
    "protection",
    "budget",
    "image",
    "psnr",
    "ssim",
    "admissible",
    "changed",
    "centre",
    "random",
    "aligned",
    "worst",
    "face_match",
    "similarity",
)


def parse_budgets(text):
    try:
        budgets = sorted({int(part) for part in text.split(",")})
    except ValueError:
        raise ValueError("--budgets must be whole numbers separated by commas") from None
    if not budgets or budgets[0] < 1 or budgets[-1] > 64:
        raise ValueError("every budget must be from 1 to 64")
    return budgets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--models-dir", required=True, type=Path, help="Folder with the models")
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--calibration-count", type=int, default=8, help="Photos for the band")
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS, help="Comma separated budgets")
    parser.add_argument("--kinds", default="pgd,pgd-jpeg", help="Comma separated protections")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling and PGD")
    parser.add_argument("--out", type=Path, default=None, help="Folder for the results")
    parser.add_argument("--force", action="store_true", help="Overwrite earlier results")
    args = parser.parse_args(argv)

    if not 1 <= args.count <= redteam.MAX_IMAGES or args.calibration_count < 1:
        return fail(f"--count must be from 1 to {redteam.MAX_IMAGES}, calibration at least 1")
    try:
        budgets = parse_budgets(args.budgets)
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
        face_model = faces.OpenCVFaceModel(args.models_dir)
    except (ValueError, faces.ModelFileError, OSError) as error:
        return fail(error)
    out = args.out or ROOT / "outputs" / f"sweep-{entry.id}-seed{args.seed}"
    if not args.force and any((out / name).exists() for name in OUTPUT_FILES):
        return fail(f"results already exist in '{out}'. Use --force to overwrite them")

    try:
        from mantelet import protect

        kinds = [kind.strip() for kind in args.kinds.split(",")]
        unknown = [kind for kind in kinds if kind not in protect.KINDS]
        if unknown:
            return fail(f"unknown protection {unknown}. Choose from {list(protect.KINDS)}")
        module = sface_copy.load_copy(args.models_dir)
        with datasets.ImageSource(args.source, entry.skip_suffixes) as source:
            if not source.names:
                return fail(f"no photos found in '{args.source}'")
            names = datasets.sample_names(source.names, args.count, args.seed)
            rest = [name for name in source.names if name not in set(names)]
            if not rest:
                return fail("no photos are left for the band calibration. Lower --count")
            calibration_names = datasets.sample_names(rest, args.calibration_count, args.seed + 1)
            calibration, _ = redteam.load_photos(calibration_names, source.load)
            photos, skipped = redteam.load_photos(names, source.load)
            original_faces = {name: face_model.embed(photo) for _, name, photo in photos}
            results = {
                "meta": {
                    "seed": args.seed,
                    "budgets": budgets,
                    "kinds": kinds,
                    "dataset": {"id": entry.id, "name": entry.name, "licence": entry.licence},
                    "photos": len(photos),
                    "skipped": skipped,
                    "libraries": baseline.library_versions(),
                },
                "kinds": {},
            }
            every = []
            for kind in kinds:
                make, record = protect.protection_factory(
                    kind, module, face_model, [photo for _, _, photo in calibration], args.seed
                )
                print(f"{kind}: band {record['band']}, running {len(budgets)} budgets")
                started = time.monotonic()
                summaries, rows = budgetsweep.run_sweep(
                    photos, original_faces, make, budgets, face_model, args.seed
                )
                print(f"{kind}: done in {time.monotonic() - started:.0f} seconds")
                results["kinds"][kind] = {
                    "calibration": record,
                    "points": summaries,
                    "gate_budget": budgetsweep.gate_budget(summaries),
                }
                every.extend({"protection": kind, **row} for row in rows)
    except ImportError as error:
        return fail(f"{error}. The ml extra is needed: uv sync --extra dev --extra ml")
    except (sface_copy.CopyError, OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "sweep.json").write_text(
            json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        with open(out / "sweep-rows.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=ROW_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(every)
        for kind, data in results["kinds"].items():
            title = (
                f"{kind}: budget sweep on {len(photos)} {entry.name} photos "
                "(scores are the lowest photo)"
            )
            budgetgraph.write_budget_graph(
                budgetsweep.graph_points(data["points"]), out / f"budget-{kind}.svg", title
            )
    except OSError as error:
        return fail(f"could not write the results: {error}")
    print(f"Wrote the results and graphs to {out}")
    return 0


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
