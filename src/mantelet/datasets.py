"""The register of face datasets we may use, and a safe way to read images from one.

A dataset can only be used for an experiment after it is in ``REGISTER`` with its
licence and its status set to ``APPROVED``. The same list, with the reasons, is in
research/datasets-and-models.md. Datasets are never stored in the repository.

``ImageSource`` reads photos from a folder or straight out of a zip file. A zip
file is never unpacked to disk: each photo is read into memory, with a size limit,
and opened through the same photo-only loader the rest of the project uses.
"""

from __future__ import annotations

import random
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import TracebackType

from PIL import Image

from mantelet import image

APPROVED = "approved"
NEEDS_REVIEW = "needs review"

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
MAX_IMAGE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class DatasetEntry:
    """What we know about one dataset before we use it."""

    id: str
    name: str
    licence: str
    licence_url: str
    source_url: str
    adult_basis: str
    status: str
    skip_suffixes: tuple[str, ...] = ()


REGISTER: dict[str, DatasetEntry] = {
    "facesynthetics": DatasetEntry(
        id="facesynthetics",
        name="Face Synthetics (Microsoft), 512 pixel rendered portraits",
        licence="Research Use of Data Agreement v1.0 (non-commercial research)",
        licence_url="https://github.com/microsoft/FaceSynthetics/blob/main/LICENSE.txt",
        source_url="https://github.com/microsoft/FaceSynthetics",
        adult_basis="Reviewed all 100 sample images on 2026-10-21. All faces look adult",
        status=APPROVED,
        skip_suffixes=("_seg.png",),
    ),
    "digiface1m": DatasetEntry(
        id="digiface1m",
        name="DigiFace-1M (Microsoft), 112 pixel rendered face crops",
        licence="Research Use of Data Agreement v1.0 (non-commercial research)",
        licence_url="https://github.com/microsoft/DigiFace1M/blob/main/LICENSE",
        source_url="https://github.com/microsoft/DigiFace1M",
        adult_basis="Not documented by the publisher. The owner must look at the sample first",
        status=NEEDS_REVIEW,
    ),
}


def get_entry(dataset_id: str) -> DatasetEntry:
    """Return the register entry, or explain which ids exist."""
    try:
        return REGISTER[dataset_id]
    except KeyError:
        known = ", ".join(sorted(REGISTER)) or "none"
        raise ValueError(f"'{dataset_id}' is not in the dataset register. Known: {known}") from None


def require_approved(entry: DatasetEntry) -> None:
    """Stop unless the dataset has been reviewed and approved."""
    if entry.status != APPROVED:
        raise ValueError(
            f"dataset '{entry.id}' has status '{entry.status}', not '{APPROVED}'. "
            "Read research/datasets-and-models.md, then change the status in "
            "src/mantelet/datasets.py once the review is done"
        )


def sample_names(names: list[str], count: int, seed: int) -> list[str]:
    """Pick ``count`` names the same way every time for one seed. Returns them sorted."""
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count}")
    ordered = sorted(names)
    if count >= len(ordered):
        return ordered
    return sorted(random.Random(seed).sample(ordered, count))


class ImageSource:
    """Photos in a folder or in a zip file. Use it with ``with``."""

    def __init__(self, path: str | Path, skip_suffixes: tuple[str, ...] = ()):
        self._path = Path(path)
        self._skip = tuple(suffix.lower() for suffix in skip_suffixes)
        self._zip: zipfile.ZipFile | None = None
        if self._path.is_dir():
            self.names = self._folder_names()
        elif zipfile.is_zipfile(self._path):
            self._zip = zipfile.ZipFile(self._path)
            self.names = self._zip_names(self._zip)
        else:
            raise ValueError(f"'{path}' is not a folder or a zip file")

    def _wanted(self, name: str) -> bool:
        lowered = name.lower()
        return lowered.endswith(IMAGE_SUFFIXES) and not lowered.endswith(self._skip)

    def _folder_names(self) -> list[str]:
        return sorted(
            item.relative_to(self._path).as_posix()
            for item in self._path.rglob("*")
            if item.is_file() and self._wanted(item.name)
        )

    def _zip_names(self, archive: zipfile.ZipFile) -> list[str]:
        return sorted(
            info.filename
            for info in archive.infolist()
            if not info.is_dir() and self._wanted(info.filename)
        )

    def load(self, name: str) -> Image.Image:
        """Open one photo by name as an upright RGB image."""
        if name not in self.names:
            raise ValueError(f"'{name}' is not a photo in '{self._path}'")
        if self._zip is None:
            file = self._path / name
            if file.stat().st_size > MAX_IMAGE_BYTES:
                raise ValueError(f"'{name}' is larger than {MAX_IMAGE_BYTES} bytes")
            return image.load_image(file)
        with self._zip.open(name) as member:
            data = member.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f"'{name}' is larger than {MAX_IMAGE_BYTES} bytes")
        return image.load_image(BytesIO(data))

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def __enter__(self) -> ImageSource:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
