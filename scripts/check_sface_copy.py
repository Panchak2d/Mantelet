"""Check that the PyTorch copy of SFace gives the same face vectors as OpenCV.

    python scripts/check_sface_copy.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --models-dir data/models

It finds and aligns a face in each sampled photo, gets one vector from OpenCV and
one from the copy, and compares them against the limits fixed in
src/mantelet/sface_copy.py. It needs the ``ml`` extra. The dataset must be in the
register with the status 'approved'. Results go to outputs/ by default.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from mantelet import datasets, faces, sface_copy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("sface-copy.json", "sface-copy.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument(
        "--models-dir", required=True, type=Path, help="Folder with the model files"
    )
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling")
    parser.add_argument("--out", type=Path, default=None, help="Folder for the results")
    parser.add_argument("--force", action="store_true", help="Overwrite earlier results")
    args = parser.parse_args(argv)

    if not 1 <= args.count <= 200:
        return fail("--count must be from 1 to 200")
    try:
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
        face_model = faces.OpenCVFaceModel(args.models_dir)
    except (ValueError, faces.ModelFileError, OSError) as error:
        return fail(error)

    out = args.out or ROOT / "outputs" / f"sface-copy-{entry.id}-seed{args.seed}"
    if not args.force and any((out / name).exists() for name in OUTPUT_FILES):
        return fail(f"results already exist in '{out}'. Use --force to overwrite them")

    try:
        module = sface_copy.load_copy(args.models_dir)
        with datasets.ImageSource(args.source, entry.skip_suffixes) as source:
            if not source.names:
                return fail(f"no photos found in '{args.source}'")
            names = datasets.sample_names(source.names, args.count, args.seed)
            aligned = []
            for name in names:
                crop = face_model.align(source.load(name))
                if crop is not None:
                    aligned.append(crop)
    except (sface_copy.CopyError, OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    if not aligned:
        return fail("no face was found in any sampled photo")
    try:
        reference = np.stack([face_model.embed_aligned(crop) for crop in aligned])
        result = sface_copy.compare(reference, sface_copy.copy_vectors(module, aligned))
    except (sface_copy.CopyError, ValueError) as error:
        return fail(error)
    meta = {
        "dataset_name": entry.name,
        "dataset_licence": entry.licence,
        "sampled": len(names),
        "no_face": len(names) - len(aligned),
        "seed": args.seed,
    }
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "sface-copy.json").write_text(
            json.dumps({"meta": meta, "result": result}, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (out / "sface-copy.md").write_text(sface_copy.render_report(result, meta), encoding="utf-8")
    except OSError as error:
        return fail(f"could not write the results: {error}")
    verdict = "PASSED" if result["passed"] else "FAILED"
    print(
        f"Copy check {verdict}: lowest cosine {result['lowest_cosine']:.6f}, "
        f"pair gap {result['pair_gap']:.6f}. Wrote the results to {out}"
    )
    return 0 if result["passed"] else 2


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
