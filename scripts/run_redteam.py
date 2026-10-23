"""Attack protections on a set of test photos and write the results and a report.

    uv run python scripts/run_redteam.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --count 20 --models-dir data/models

    uv run python scripts/run_redteam.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --models-dir data/models \\
        --protection pgd --budget 8

The script protects each photo itself, with a toy protection from src/mantelet/toy.py
or with a PGD protection from src/mantelet/protect.py (which needs the ``ml`` extra),
and then tries every attack in src/mantelet/attacks.py. It never reads a photo that
someone else protected. The toy protections do nothing against any model, so a toy run
tests the attack tools and not a protection. The dataset must be in the register
(src/mantelet/datasets.py) with the status 'approved'. Results go to outputs/ by
default, which git ignores.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from mantelet import datasets, faces, redteam, report, sface_copy, toy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("results.json", "records.csv", "pipeline.csv", "report.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling and noise")
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=None,
        help="Folder with the face model files (scripts/fetch_models.py). Adds the face match",
    )
    parser.add_argument(
        "--protection",
        choices=("toys", "pgd", "pgd-jpeg"),
        default="toys",
        help="Which protection to attack. The default is the three toys",
    )
    parser.add_argument("--budget", type=int, default=None, help="L-infinity budget for PGD")
    parser.add_argument(
        "--calibration-count", type=int, default=8, help="Photos kept apart to declare the band"
    )
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

    if args.protection != "toys" and (args.models_dir is None or args.budget is None):
        return fail("a PGD protection needs --models-dir and --budget")
    if args.protection == "toys" and args.budget is not None:
        return fail("--budget applies to a PGD protection only")
    if args.calibration_count < 1:
        return fail("--calibration-count must be at least 1")
    if args.budget is not None and not 1 <= args.budget <= 64:
        return fail("--budget must be from 1 to 64")
    face_model = None
    if args.models_dir is not None:
        try:
            face_model = faces.OpenCVFaceModel(args.models_dir)
        except (faces.ModelFileError, OSError, ValueError) as error:
            return fail(error)

    label = args.protection if args.budget is None else f"{args.protection}-{args.budget}"
    out = args.out or ROOT / "outputs" / f"redteam-{entry.id}-{label}-seed{args.seed}"
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
            meta = redteam.build_meta(dataset_meta, len(names), subject=args.protection)
            protections = toy.TOY_PROTECTIONS
            if args.protection != "toys":
                protections, meta["calibration"] = pgd_protections(
                    args, source, names, face_model
                )
            print(f"Attacking {len(names)} photos under {len(protections)} protections")
            results = redteam.run_redteam(
                names, source.load, protections, args.seed, meta, face_model=face_model
            )
    except ImportError as error:
        return fail(f"{error}. A PGD protection needs: uv sync --extra dev --extra ml")
    except (sface_copy.CopyError, OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(
            json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        redteam.write_records_csv(results["records"], out / "records.csv")
        redteam.write_pipeline_csv(results["pipeline"], out / "pipeline.csv")
        (out / "report.md").write_text(report.render_redteam_report(results), encoding="utf-8")
    except OSError as error:
        return fail(f"could not write the results: {error}")
    skipped = len(results["skipped"])
    print(
        f"Wrote the results and report to {out} ({skipped} photos skipped)"
    )
    return 0


def pgd_protections(args, source, names, face_model):
    """The PGD protection for one budget, with its band measured on photos kept apart."""
    from mantelet import protect

    module = sface_copy.load_copy(args.models_dir)
    rest = [name for name in source.names if name not in set(names)]
    if not rest:
        raise ValueError("no photos are left for the band calibration. Lower --count")
    calibration_names = datasets.sample_names(rest, args.calibration_count, args.seed + 1)
    calibration, _ = redteam.load_photos(calibration_names, source.load)
    make, record = protect.protection_factory(
        args.protection, module, face_model, [photo for _, _, photo in calibration], args.seed
    )
    return [make(args.budget)], record


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
