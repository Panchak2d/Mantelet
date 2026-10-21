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
not measure whether an editing model or a face matcher is still fooled. That
needs the protection and the model from a later step.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from mantelet import attacks as attack_tools
from mantelet import baseline, metrics, toy

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
)


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
) -> tuple[attack_tools.Attack, ...]:
    """Every attack the runner uses, in the order the report lists them.

    ``protected`` is the set of protected photos the collusion attack learns from.
    """
    return (
        *attack_tools.standard_attacks(),
        attack_tools.known_band_attack(toy.BAND_NARROW_SIGMA, toy.BAND_WIDE_SIGMA),
        attack_tools.collusion_attack(protected),
    )


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
) -> dict:
    """Attack every photo under every protection and return the results as plain data."""
    if len(names) > MAX_IMAGES:
        raise ValueError(f"at most {MAX_IMAGES} photos per run, got {len(names)}")
    photos, skipped = _load_photos(names, load)
    records: list[dict] = []
    not_applicable: dict[tuple[str, str], dict] = {}
    for protection_index, protection in enumerate(protections):
        protected = [
            protection.apply(photo, _seed(seed, index, protection_index))
            for index, _, photo in photos
        ]
        attacks = attack_catalogue(protected)
        for (index, name, original), shielded in zip(photos, protected, strict=True):
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
                            name, protection.name, attack, strength, original, shielded, attacked
                        )
                    )
    return {
        "meta": meta
        | {
            "kind": "redteam",
            "seed": seed,
            "protections": [(p.name, p.description) for p in protections],
            "attacks": [
                (a.name, a.level, a.description, list(a.strengths)) for a in attack_catalogue()
            ],
        },
        "records": records,
        "skipped": skipped,
        "not_applicable": [
            entry | {"photos": len(entry["photos"])} for entry in not_applicable.values()
        ],
    }


def _record(name, protection, attack, strength, original, shielded, attacked) -> dict:
    psnr = metrics.psnr(original, attacked)
    ssim = metrics.ssim(original, attacked) if psnr >= QUALITY_FLOOR_PSNR else None
    return {
        "image": name,
        "protection": protection,
        "attack": attack.name,
        "level": attack.level,
        "strength": float(strength),
        "psnr": _finite(psnr),
        "ssim": ssim,
        "admissible": is_admissible(psnr, ssim),
        "survival": _finite(survival(original, shielded, attacked)),
    }


def _best_per_photo(rows: list[dict]) -> dict[str, float]:
    """For each photo, the lowest survival among the admissible rows that have one."""
    best: dict[str, float] = {}
    for row in rows:
        if row["admissible"] and row["survival"] is not None:
            best[row["image"]] = min(best.get(row["image"], math.inf), row["survival"])
    return best


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
            image
            for image, row in controls.items()
            if row["admissible"] and row["survival"] is not None
        }
        scored = [row for row in rows if row["image"] in usable]
        levels = []
        for max_level in range(MAX_LEVEL + 1):
            best = _best_per_photo([row for row in scored if row["level"] <= max_level])
            held = sum(1 for value in best.values() if value >= SURVIVAL_FLOOR)
            levels.append(
                {
                    "max_level": max_level,
                    "photos": len(best),
                    "survival": _spread(list(best.values())),
                    "held": held,
                    "held_rate": held / len(best) if best else None,
                    "held_interval": baseline.wilson_interval(held, len(best)),
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
        summaries.append(
            {
                "protection": name,
                "description": description,
                "photos": len(controls),
                "unusable": len(controls) - len(usable),
                "levels": levels,
                "attacks": per_attack,
            }
        )
    return summaries


def write_records_csv(records: Sequence[dict], path: str | Path) -> None:
    """Write one row per photo, protection, attack and strength."""
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writeheader()
        writer.writerows(records)


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
