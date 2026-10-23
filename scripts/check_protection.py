"""Check the pieces a protection is tuned through: our crop, its gradient and our JPEG.

    uv run python scripts/check_protection.py --dataset-id facesynthetics \\
        --source data/dataset_100.zip --models-dir data/models

It compares the crop we differentiate through with OpenCV's alignment, the gradient
with a finite difference, and our JPEG with Pillow's, against the limits fixed in
src/mantelet/protectcheck.py. It needs the ``ml`` extra and a passed copy check. Results
go to outputs/ by default.
"""

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from mantelet import datasets, faces, image, protectcheck, redteam, sface_copy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILES = ("protection-check.json", "protection-check.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-id", required=True, help="Id from the dataset register")
    parser.add_argument("--source", required=True, type=Path, help="Folder or zip of photos")
    parser.add_argument("--models-dir", required=True, type=Path, help="Folder with the models")
    parser.add_argument("--count", type=int, default=20, help="How many photos to sample")
    parser.add_argument("--seed", type=int, default=0, help="Seed for sampling")
    parser.add_argument("--out", type=Path, default=None, help="Folder for the results")
    parser.add_argument("--force", action="store_true", help="Overwrite earlier results")
    args = parser.parse_args(argv)

    if not 1 <= args.count <= redteam.MAX_IMAGES:
        return fail(f"--count must be from 1 to {redteam.MAX_IMAGES}")
    try:
        entry = datasets.get_entry(args.dataset_id)
        datasets.require_approved(entry)
        face_model = faces.OpenCVFaceModel(args.models_dir)
    except (ValueError, faces.ModelFileError, OSError) as error:
        return fail(error)
    out = args.out or ROOT / "outputs" / f"protection-check-{entry.id}-seed{args.seed}"
    if not args.force and any((out / name).exists() for name in OUTPUT_FILES):
        return fail(f"results already exist in '{out}'. Use --force to overwrite them")

    try:
        import torch

        from mantelet import diffjpeg, protect

        module = sface_copy.load_copy(args.models_dir)
        crop_cosines, gradient_errors, jpeg_gaps, found = [], [], [], 0
        with datasets.ImageSource(args.source, entry.skip_suffixes) as source:
            if not source.names:
                return fail(f"no photos found in '{args.source}'")
            names = datasets.sample_names(source.names, args.count, args.seed)
            photos, _ = redteam.load_photos(names, source.load)
            for _, _, photo in photos:
                pixels = np.asarray(photo)
                tensor = torch.from_numpy(pixels.transpose(2, 0, 1).astype(np.float32))[None]
                buffer = io.BytesIO()
                photo.save(buffer, "JPEG", quality=image.PIPELINE_JPEG_QUALITY)
                buffer.seek(0)
                reference = np.asarray(Image.open(buffer).convert("RGB"), dtype=np.float32)
                ours = diffjpeg.jpeg(tensor, image.PIPELINE_JPEG_QUALITY)[0].numpy()
                jpeg_gaps.append(float(np.abs(ours.transpose(1, 2, 0) - reference).mean()))
                landmarks = face_model.landmarks(photo)
                if landmarks is None:
                    continue
                found += 1
                matrix = protect.similarity_matrix(landmarks)
                with torch.no_grad():
                    mine = protect.embed(module, protect.aligned_crop(tensor, matrix))
                official = face_model.embed_aligned(face_model.align(photo))
                crop_cosines.append(
                    float(np.dot(mine[0].numpy(), official) / np.linalg.norm(official))
                )
                if len(gradient_errors) < protectcheck.GRADIENT_FACES:
                    gradient_errors.append(
                        protect.gradient_check(module, pixels, matrix, args.seed)
                    )
    except ImportError as error:
        return fail(f"{error}. The ml extra is needed: uv sync --extra dev --extra ml")
    except (sface_copy.CopyError, OSError, ValueError, Image.DecompressionBombError) as error:
        return fail(error)

    if not crop_cosines:
        return fail("no face was found in any sampled photo")
    result = protectcheck.evaluate(crop_cosines, gradient_errors, jpeg_gaps)
    meta = {
        "dataset_name": entry.name,
        "dataset_licence": entry.licence,
        "sampled": len(names),
        "no_face": len(photos) - found,
        "seed": args.seed,
    }
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "protection-check.json").write_text(
            json.dumps({"meta": meta, "result": result}, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (out / "protection-check.md").write_text(
            protectcheck.render_report(result, meta), encoding="utf-8"
        )
    except OSError as error:
        return fail(f"could not write the results: {error}")
    verdict = "PASSED" if result["passed"] else "FAILED"
    print(f"Protection pieces check {verdict}. Wrote the results to {out}")
    return 0 if result["passed"] else 2


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
