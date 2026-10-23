"""Show why our differentiable crop differs from OpenCV's, face by face.

    uv run python scripts/diagnose_crop.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --models-dir data/models

Run it only to diagnose a failed ``check_protection.py``. It measures and changes
nothing, and it does not touch the limits. It prints one row per face and a summary.
Needs the ``ml`` extra.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

from mantelet import datasets, faces, redteam, sface_copy

COLUMNS = (
    "copy_on_opencv_crop",
    "ours",
    "ours_unrounded",
    "opencv_warp_our_matrix",
    "gap_ours",
    "gap_opencv_warp_our_matrix",
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--models-dir", required=True, type=Path, help="Folder with the models")
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling")
    args = parser.parse_args(argv)
    if not 1 <= args.count <= redteam.MAX_IMAGES:
        return fail(f"--count must be from 1 to {redteam.MAX_IMAGES}")
    try:
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
        face_model = faces.OpenCVFaceModel(args.models_dir)
        from mantelet import protect

        module = sface_copy.load_copy(args.models_dir)
        rows = []
        with datasets.ImageSource(args.source, entry.skip_suffixes) as source:
            names = datasets.sample_names(source.names, args.count, args.seed)
            photos, _ = redteam.load_photos(names, source.load)
            for _, name, photo in photos:
                values = protect.crop_variants(module, face_model, photo)
                if values is not None:
                    rows.append((name, values))
    except ImportError as error:
        return fail(f"{error}. The ml extra is needed: uv sync --extra dev --extra ml")
    except (sface_copy.CopyError, faces.ModelFileError, OSError, ValueError) as error:
        return fail(error)
    except Image.DecompressionBombError as error:
        return fail(error)
    if not rows:
        return fail("no face was found in any sampled photo")
    print("image," + ",".join(COLUMNS))
    for name, values in rows:
        print(name + "," + ",".join(f"{values[c]:.6f}" for c in COLUMNS))
    print("lowest," + ",".join(f"{min(v[c] for _, v in rows):.6f}" for c in COLUMNS[:4]))
    means = (sum(v[c] for _, v in rows) / len(rows) for c in COLUMNS[4:])
    print("mean pixel gap,,,," + ",".join(f"{mean:.4f}" for mean in means))
    return 0


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
