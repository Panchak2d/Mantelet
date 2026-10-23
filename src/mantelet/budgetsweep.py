"""Run one protection over a list of L-infinity budgets and measure what each budget costs.

For every budget the sweep protects each sampled photo and records how far the photo
moved (PSNR and SSIM against the original), how much of the change survives the
fixed pipeline, and what the face match does through the same pipeline beside the
unprotected photo (``effect``). The numbers feed the budget graph
(``budgetgraph``). The sweep uses no attack, so it says nothing about the red team.

The budget used for Gate 1 is chosen by a rule fixed before any result: the largest
budget in the list at which every counted photo stays at or above the quality floor
(``gate_budget``). A photo that is below the floor is left out of that budget's survival
and face numbers and counted on its own.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image

from mantelet import effect, faces, metrics, redteam, toy


def measure_budget(
    photos: Sequence[tuple[int, str, Image.Image]],
    original_faces: dict,
    protection: toy.Protection,
    budget: int,
    face_model: faces.FaceEmbedder | None,
    seed: int,
) -> list[dict]:
    """One row per photo: quality scores, and the pipeline row with the face match."""
    rows = []
    for index, name, original in photos:
        shielded = protection.apply(original, redteam.seed_for(seed, index, budget))
        psnr = metrics.psnr(original, shielded)
        ssim = metrics.ssim(original, shielded) if psnr >= redteam.QUALITY_FLOOR_PSNR else None
        pipeline = redteam.pipeline_record(
            name,
            protection.name,
            original,
            shielded,
            face_model,
            original_faces[name],
            redteam.seed_for(seed, index, budget, 99),
        )
        rows.append(
            {
                "budget": budget,
                "psnr": redteam.finite(psnr),
                "ssim": ssim,
                "admissible": redteam.is_admissible(psnr, ssim),
                "changed": bool(np.any(np.asarray(original) != np.asarray(shielded))),
                **pipeline,
            }
        )
    return rows


def summarise_budget(rows: Sequence[dict], controls: Sequence[dict], protection: str) -> dict:
    """The numbers for one budget. Photos below the quality floor are left out and counted."""
    counted = [row for row in rows if row["admissible"]]
    centre = [row["centre"] for row in counted if row["centre"] is not None]
    face = effect.pipeline_effect([*controls, *counted], protection)
    psnr = [row["psnr"] for row in rows if row["psnr"] is not None]
    ssim = [row["ssim"] for row in rows if row["ssim"] is not None]
    return {
        "budget": rows[0]["budget"] if rows else None,
        "photos": len(rows),
        "below_floor": len(rows) - len(counted),
        "unchanged": sum(1 for row in counted if not row["changed"]),
        "psnr_worst": min(psnr) if psnr else None,
        "ssim_worst": min(ssim) if len(ssim) == len(rows) and ssim else None,
        "survival_centre_mean": float(np.mean(centre)) if centre else None,
        "survival_centre_lowest": min(centre) if centre else None,
        "survival_centre_held": sum(1 for value in centre if value >= redteam.SURVIVAL_FLOOR),
        "survival_photos": len(centre),
        "face": face,
    }


def gate_budget(points: Sequence[dict]) -> int | None:
    """The largest budget at which no photo is below the quality floor, or None."""
    clean = [p["budget"] for p in points if p["photos"] and p["below_floor"] == 0]
    return max(clean) if clean else None


def graph_points(points: Sequence[dict]) -> list[dict]:
    """Points in the form ``budgetgraph`` draws: the worst photo for the scores."""
    out = []
    for point in points:
        face = point["face"]
        out.append(
            {
                "budget": point["budget"],
                "psnr": point["psnr_worst"],
                "ssim": point["ssim_worst"],
                "face_match": None if face is None else face["strict"]["rate"],
                "survival": point["survival_centre_mean"],
            }
        )
    return out


def run_sweep(
    photos: Sequence[tuple[int, str, Image.Image]],
    original_faces: dict,
    make: Callable[[int], toy.Protection],
    budgets: Sequence[int],
    face_model: faces.FaceEmbedder,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    """Return the per-budget summaries and every per-photo row."""
    controls = redteam.control_rows(photos, original_faces, face_model, seed)
    summaries, every = [], []
    for budget in budgets:
        protection = make(budget)
        rows = measure_budget(photos, original_faces, protection, budget, face_model, seed)
        summaries.append(summarise_budget(rows, controls, protection.name))
        every.extend(rows)
    return summaries, every
