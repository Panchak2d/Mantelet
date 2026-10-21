"""Download the two face model files into data/models and check their hashes.

    python scripts/fetch_models.py
    python scripts/fetch_models.py --dest some/other/folder

The files come from the OpenCV Zoo at one pinned commit. Each download is checked
against a pinned size and SHA-256 hash and is only kept if both match. The files
are not stored in the repository. A file that is already there and correct is left alone.
"""

import argparse
import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from mantelet import faces

DEFAULT_DEST = Path(__file__).resolve().parent.parent / "data" / "models"
TIMEOUT_SECONDS = 60
CHUNK_BYTES = 1 << 16


def download(model, dest, opener=urllib.request.urlopen):
    """Fetch one model file into ``dest``. Raises ModelFileError if the bytes are wrong."""
    target = dest / model.filename
    try:
        faces.read_verified_model(dest, model)
        print(f"{model.filename}: already there and correct")
        return
    except faces.ModelFileError:
        pass

    print(f"{model.filename}: downloading {model.size} bytes from {model.url}")
    received = bytearray()
    with opener(model.url, timeout=TIMEOUT_SECONDS) as response:
        while len(received) <= model.size:
            chunk = response.read(CHUNK_BYTES)
            if not chunk:
                break
            received.extend(chunk)
    if len(received) != model.size or hashlib.sha256(received).hexdigest() != model.sha256:
        raise faces.ModelFileError(
            f"the download of {model.filename} is not the pinned file. Nothing was saved"
        )

    handle, temporary = tempfile.mkstemp(dir=dest, suffix=".part")
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(received)
        os.replace(temporary, target)
    except BaseException:
        os.unlink(temporary)
        raise
    print(f"{model.filename}: saved and checked")


def main(argv=None, opener=urllib.request.urlopen):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Folder for the files")
    args = parser.parse_args(argv)

    try:
        args.dest.mkdir(parents=True, exist_ok=True)
        for model in faces.MODEL_FILES:
            download(model, args.dest, opener)
    except (faces.ModelFileError, OSError, urllib.error.URLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print("All model files are in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
