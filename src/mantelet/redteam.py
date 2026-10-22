"""Run the red team: try every attack on protected photos and measure what is left.

For each photo and each protection the runner protects the photo, attacks it with
every attack at every strength, and records two things:

* how much of the protection survived. This is the share of the protection's own
  change that is still in the attacked photo, measured against the unprotected
  original (``survival``). 1 means all of it, 0 means none.
* how much the attack damaged the photo, as PSNR and SSIM against the unprotected
  original. An attack counts only when its output stays above the quality floor,
  because an attacker needs a photo that still looks good.

The summary gives the attacker the best admissible result for every photo and
every attacker level. Results are never averaged across attacks to hide one that
works. The numbers in this file are fixed in docs/research/test-plan.md before
any protection result exists.

Survival measures whether the protection's change is still in the photo. It does
not measure whether an editing model or a face matcher is still fooled. When a
face model is given, each admissible result is also matched against the face in
the original photo, and when an editor is given, each is also run through the
stand-in edit. The attacker succeeds on a photo when any admissible result up to
the attacker level still matches or still edits, which is the worst case again.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from mantelet import attacks as attack_tools
from mantelet import baseline, cropsweep, faces, image, metrics, toy

QUALITY_FLOOR_PSNR = 30.0
QUALITY_FLOOR_SSIM = 0.90
SURVIVAL_FLOOR = 0.5

MAX_IMAGES = 200
MAX_LONG_SIDE = 1024
MAX_LEVEL = 3

RECORD_FIELDS = (
    "image",
    "protection",
    "attack",
    "level",
    "strength",
    "psnr",
    "ssim",
    "admissible",
    "survival",
    "original_face_found",
    "similarity",
    "face_match",
    "edit_success",
)

PIPELINE_FIELDS = (
    "image",
    "protection",
    "centre",
    "random",
    "aligned",
    "worst",
    "face_match",
)


class Editor(Protocol):
    """A stand-in edit. It runs on one photo and says whether the edit worked."""

    name: str

    def succeeds(self, original: Image.Image, candidate: Image.Image, seed: int) -> bool: ...


def survival(original: Image.Image, protected: Image.Image, attacked: Image.Image) -> float | None:
    """The share of the protection's change that is still in the attacked photo.

    The change is ``protected - original``. The result is how far the attacked
    photo sits from the original along that change: 1 when the attack did nothing,
    0 when it removed the change or only added changes unrelated to it. It can go
    below 0 or above 1. It is None when the protection changed no pixel.
    """
    for img in (original, protected, attacked):
        if img.mode != "RGB":
            raise ValueError(f"expected an RGB image, got mode {img.mode}")
    if not original.size == protected.size == attacked.size:
        raise ValueError("the three images must be the same size")
    base = np.asarray(original, dtype=np.float64)
    change = np.asarray(protected, dtype=np.float64) - base
    energy = float(np.sum(change**2))
    if energy == 0:
        return None
    return float(np.sum((np.asarray(attacked, dtype=np.float64) - base) * change) / energy)


def is_admissible(psnr: float, ssim: float | None) -> bool:
    """True when an attack's output is still close enough to the original to be useful."""
    return psnr >= QUALITY_FLOOR_PSNR and ssim is not None and ssim >= QUALITY_FLOOR_SSIM


def _seed(*parts: int) -> int:
    return int(np.random.SeedSequence(list(parts)).generate_state(1)[0])


def _finite(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None


def attack_catalogue(
    protected: Sequence[Image.Image] = (),
    band: tuple[float, float] | None = None,
) -> tuple[attack_tools.Attack, ...]:
    """The attacks the runner uses on one protection, in the order the report lists them.

    ``protected`` is the set of protected photos the collusion attack learns from.
    ``band`` is the band the protection declares. The known band attack is left out
    when the protection declares none, because there is no band to remove.
    """
    known_band = () if band is None else (attack_tools.known_band_attack(*band),)
    return (
        *attack_tools.standard_attacks(),
        *known_band,
        attack_tools.collusion_attack(protected),
    )


def _all_attacks(protections: Sequence[toy.Protection]) -> list[attack_tools.Attack]:
    """Every attack any of the protections meets, each listed once."""
    seen: dict[str, attack_tools.Attack] = {}
    for protection in protections:
        for attack in attack_catalogue(band=protection.band):
            seen.setdefault(attack.name, attack)
    return list(seen.values())


def _load_photos(
    names: Sequence[str], load: Callable[[str], Image.Image]
) -> tuple[list[tuple[int, str, Image.Image]], list[dict]]:
    kept, skipped = [], []
    for index, name in enumerate(names):
        try:
            photo = load(name)
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            skipped.append({"image": name, "reason": f"could not be read: {error}"})
            continue
        if min(photo.size) < baseline.MIN_IMAGE_SIDE:
            skipped.append(
                {"image": name, "reason": f"smaller than {baseline.MIN_IMAGE_SIDE} pixels"}
            )
        elif max(photo.size) > MAX_LONG_SIDE:
            skipped.append({"image": name, "reason": f"longer side above {MAX_LONG_SIDE} pixels"})
        else:
            kept.append((index, name, photo))
    return kept, skipped


def run_redteam(
    names: Sequence[str],
    load: Callable[[str], Image.Image],
    protections: Sequence[toy.Protection],
    seed: int,
    meta: dict,
    face_model: faces.FaceEmbedder | None = None,
    editor: Editor | None = None,
) -> dict:
    """Attack every photo under every protection and return the results as plain data.

    With ``face_model`` every admissible result is matched against the face in the
    unprotected original. With ``editor`` every admissible result gets the stand-in
    edit. Without them those columns stay empty and the report says they were not measured.
    """
    if len(names) > MAX_IMAGES:
        raise ValueError(f"at most {MAX_IMAGES} photos per run, got {len(names)}")
    photos, skipped = _load_photos(names, load)
    original_faces = {
        name: face_model.embed(photo) if face_model is not None else None
        for _, name, photo in photos
    }
    records: list[dict] = []
    pipeline: list[dict] = []
    not_applicable: dict[tuple[str, str], dict] = {}
    for protection_index, protection in enumerate(protections):
        protected = [
            protection.apply(photo, _seed(seed, index, protection_index))
            for index, _, photo in photos
        ]
        attacks = attack_catalogue(protected, protection.band)
        for (index, name, original), shielded in zip(photos, protected, strict=True):
            pipeline.append(
                _pipeline_record(
                    name,
                    protection.name,
                    original,
                    shielded,
                    face_model,
                    original_faces[name],
                    _seed(seed, index, protection_index, 99),
                )
            )
            for attack_index, attack in enumerate(attacks):
                for strength_index, strength in enumerate(attack.strengths):
                    attack_seed = _seed(seed, index, protection_index, attack_index, strength_index)
                    try:
                        attacked = attack.run(shielded, strength, attack_seed)
                    except attack_tools.AttackNotApplicable as error:
                        entry = not_applicable.setdefault(
                            (protection.name, attack.name),
                            {
                                "protection": protection.name,
                                "attack": attack.name,
                                "photos": set(),
                                "reason": str(error),
                            },
                        )
                        entry["photos"].add(name)
                        break
                    records.append(
                        _record(
                            name,
                            protection.name,
                            attack,
                            strength,
                            original,
                            shielded,
                            attacked,
                            face_model,
                            original_faces[name],
                            editor,
                            attack_seed,
                        )
                    )
    return {
        "meta": meta
        | {
            "kind": "redteam",
            "seed": seed,
            "protections": [(p.name, p.description) for p in protections],
            "attacks": [
                (a.name, a.level, a.description, list(a.strengths))
                for a in _all_attacks(protections)
            ],
            "face_model": face_model is not None,
            "editor": None if editor is None else editor.name,
        },
        "records": records,
        "pipeline": pipeline,
        "skipped": skipped,
        "not_applicable": [
            entry | {"photos": len(entry["photos"])} for entry in not_applicable.values()
        ],
    }


def _match(face_model, original_vector, candidate: Image.Image) -> tuple[float | None, bool]:
    """Similarity to the original face and whether it counts as the same person.

    A face not found in the candidate counts as no match, the rule fixed in the
    baseline. Callers only call this when the original face was found.
    """
    vector = face_model.embed(candidate)
    if vector is None:
        return None, False
    similarity = faces.cosine_similarity(original_vector, vector)
    return similarity, faces.same_person(similarity)


def _record(
    name,
    protection,
    attack,
    strength,
    original,
    shielded,
    attacked,
    face_model=None,
    original_vector=None,
    editor=None,
    seed=0,
) -> dict:
    psnr = metrics.psnr(original, attacked)
    ssim = metrics.ssim(original, attacked) if psnr >= QUALITY_FLOOR_PSNR else None
    admissible = is_admissible(psnr, ssim)
    original_found = None if face_model is None else original_vector is not None
    similarity, face_match = None, None
    if admissible and original_found:
        similarity, face_match = _match(face_model, original_vector, attacked)
    edit_success = editor.succeeds(original, attacked, seed) if admissible and editor else None
    return {
        "image": name,
        "protection": protection,
        "attack": attack.name,
        "level": attack.level,
        "strength": float(strength),
        "psnr": _finite(psnr),
        "ssim": ssim,
        "admissible": admissible,
        "survival": _finite(survival(original, shielded, attacked)),
        "original_face_found": original_found,
        "similarity": _finite(similarity),
        "face_match": face_match,
        "edit_success": edit_success,
    }


def _pipeline_record(name, protection, original, shielded, face_model, original_vector, seed):
    """Survival through the fixed pipeline at many crop corners, and the centre face match."""
    sweep = cropsweep.sweep(original, shielded, seed)
    face_match = None
    if face_model is not None and original_vector is not None:
        centre = image.platform_pipeline(shielded)
        reference = face_model.embed(image.platform_pipeline(original))
        face_match = False if reference is None else _match(face_model, reference, centre)[1]
    return {
        "image": name,
        "protection": protection,
        "centre": _mean_of(sweep["centre"]),
        "random": _mean_of(sweep["random"]),
        "aligned": _mean_of(sweep["aligned"]),
        "worst": _finite(sweep["worst"]),
        "face_match": face_match,
    }


def _mean_of(summary: dict | None) -> float | None:
    return None if summary is None else _finite(summary["mean"])


def _best_per_photo(rows: list[dict]) -> dict[str, float]:
    """For each photo, the lowest survival among the admissible rows that have one."""
    best: dict[str, float] = {}
    for row in rows:
        if row["admissible"] and row["survival"] is not None:
            best[row["image"]] = min(best.get(row["image"], math.inf), row["survival"])
    return best


def _attacker_wins(rows: list[dict], column: str, eligible: set[str]) -> dict[str, bool]:
    """For each eligible photo, whether any admissible row still has ``column`` true."""
    wins = {image_name: False for image_name in eligible}
    for row in rows:
        if row["admissible"] and row["image"] in wins and row[column]:
            wins[row["image"]] = True
    return wins


def _rate(wins: dict[str, bool]) -> dict | None:
    if not wins:
        return None
    count = sum(wins.values())
    return {
        "photos": len(wins),
        "wins": count,
        "rate": count / len(wins),
        "interval": baseline.wilson_interval(count, len(wins)),
    }


def _spread(values: Sequence[float]) -> dict | None:
    if not values:
        return None
    return {"mean": float(np.mean(values)), "worst": min(values), "n": len(values)}


def summarise(results: dict) -> list[dict]:
    """One summary per protection: the best attack at each attacker level, and each attack alone."""
    summaries = []
    for name, description in results["meta"]["protections"]:
        rows = [row for row in results["records"] if row["protection"] == name]
        controls = {row["image"]: row for row in rows if row["attack"] == "identity"}
        usable = {
            image_name
            for image_name, row in controls.items()
            if row["admissible"] and row["survival"] is not None
        }
        scored = [row for row in rows if row["image"] in usable]
        face_photos = {
            image_name for image_name in usable if controls[image_name]["original_face_found"]
        }
        levels = []
        for max_level in range(MAX_LEVEL + 1):
            at_level = [row for row in scored if row["level"] <= max_level]
            best = _best_per_photo(at_level)
            held = sum(1 for value in best.values() if value >= SURVIVAL_FLOOR)
            levels.append(
                {
                    "max_level": max_level,
                    "photos": len(best),
                    "survival": _spread(list(best.values())),
                    "held": held,
                    "held_rate": held / len(best) if best else None,
                    "held_interval": baseline.wilson_interval(held, len(best)),
                    "face_match": _rate(_attacker_wins(at_level, "face_match", face_photos))
                    if results["meta"].get("face_model")
                    else None,
                    "edit_success": _rate(_attacker_wins(at_level, "edit_success", usable))
                    if results["meta"].get("editor")
                    else None,
                }
            )
        per_attack = []
        for attack_name, level, attack_description, _ in results["meta"]["attacks"]:
            attack_rows = [row for row in scored if row["attack"] == attack_name]
            best = _best_per_photo(attack_rows)
            per_attack.append(
                {
                    "attack": attack_name,
                    "level": level,
                    "description": attack_description,
                    "photos_run": len({row["image"] for row in attack_rows}),
                    "survival": _spread(list(best.values())),
                }
            )
        pipeline_rows = [
            row
            for row in results.get("pipeline", [])
            if row["protection"] == name and row["image"] in usable
        ]
        worst = [row["worst"] for row in pipeline_rows if row["worst"] is not None]
        face_pipeline = [
            row["face_match"] for row in pipeline_rows if row["face_match"] is not None
        ]
        summaries.append(
            {
                "protection": name,
                "description": description,
                "photos": len(controls),
                "unusable": len(controls) - len(usable),
                "levels": levels,
                "attacks": per_attack,
                "pipeline": {
                    "photos": len(pipeline_rows),
                    "centre": _spread(
                        [r["centre"] for r in pipeline_rows if r["centre"] is not None]
                    ),
                    "random": _spread(
                        [r["random"] for r in pipeline_rows if r["random"] is not None]
                    ),
                    "aligned": _spread(
                        [r["aligned"] for r in pipeline_rows if r["aligned"] is not None]
                    ),
                    "worst": _spread(worst),
                    "held": sum(1 for value in worst if value >= SURVIVAL_FLOOR),
                    "face_matched": sum(face_pipeline),
                    "face_photos": len(face_pipeline),
                },
            }
        )
    return summaries


def write_records_csv(records: Sequence[dict], path: str | Path) -> None:
    """Write one row per photo, protection, attack and strength."""
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def write_pipeline_csv(rows: Sequence[dict], path: str | Path) -> None:
    """Write one row per photo and protection with survival through the fixed pipeline."""
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=PIPELINE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_meta(dataset: dict, sampled: int) -> dict:
    """Facts that let someone repeat the run: the dataset, tools and fixed numbers."""
    return {
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": dataset,
        "photos_sampled": sampled,
        "libraries": baseline.library_versions(),
        "quality_floor": {"psnr": QUALITY_FLOOR_PSNR, "ssim": QUALITY_FLOOR_SSIM},
        "survival_floor": SURVIVAL_FLOOR,
        "toy": {
            "pattern_rms": toy.PATTERN_RMS,
            "band_sigmas": [toy.BAND_NARROW_SIGMA, toy.BAND_WIDE_SIGMA],
        },
    }
