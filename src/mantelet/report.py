"""Turn baseline and red team results into short Markdown reports.

The report states what was measured, on what, and with which settings. It never
says that Mantelet protects anyone. It carries the dataset licence and review
status so a report cannot be separated from the rules the data came with.
"""

from __future__ import annotations

from mantelet import baseline, redteam

FEW_PHOTOS = 30


def _number(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _with_worst(score: dict | None, digits: int = 2) -> str:
    if score is None:
        return "n/a"
    return f"{_number(score['mean'], digits)} (worst {_number(score['worst'], digits)})"


def _pixel_table(summaries: list[dict]) -> list[str]:
    rows = [
        "| Condition | Photos scored | PSNR in dB, mean (worst) | SSIM, mean (worst) "
        "| Largest pixel change, mean (worst) |",
        "|---|---|---|---|---|",
    ]
    for item in summaries:
        scored = item["ssim"]["n"] if item["ssim"] else 0
        rows.append(
            f"| {item['condition']} | {scored} | {_with_worst(item['psnr'])} "
            f"| {_with_worst(item['ssim'], 4)} | {_with_worst(item['max_abs_difference'], 0)} |"
        )
    return rows


def _face_table(summaries: list[dict]) -> list[str]:
    rows = [
        "| Condition | Original face found | Face found after | Matches "
        "| Match rate (95% interval) | Mean similarity | Lowest similarity |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in summaries:
        face = item["face"]
        interval = face["match_interval"]
        interval_text = (
            "n/a" if interval is None else f"{_percent(interval[0])} to {_percent(interval[1])}"
        )
        rows.append(
            f"| {item['condition']} | {face['eligible']} of {item['photos']} "
            f"| {face['processed_found']} | {face['matches']} "
            f"| {_percent(face['match_rate'])} ({interval_text}) "
            f"| {_number(face['mean_similarity'], 3)} | {_number(face['min_similarity'], 3)} |"
        )
    return rows


def render_report(results: dict) -> str:
    """Return the report for one baseline run as Markdown text."""
    meta = results["meta"]
    dataset = meta["dataset"]
    summaries = baseline.summarise(results)
    used = max((item["photos"] for item in summaries), default=0)
    lines = [
        "# Baseline report",
        "",
        "No protection was applied to any photo in this run. The numbers show what ordinary "
        "processing does to a photo and to a face match on its own. A later protection result "
        "must be compared with these numbers, not with a perfect score.",
        "",
        "Results on these test photos are assumed to carry over to real photos. That is a "
        "**Guess** (claim C-002).",
        "",
        "## Run",
        "",
        f"- Dataset: {dataset['name']} (`{dataset['id']}`)",
        f"- Dataset licence: {dataset['licence']}",
        f"- Dataset review status: {dataset['status']}",
        f"- Created: {meta['created']}",
        f"- Seed: {meta['seed']}",
        f"- Photos sampled: {meta['photos_sampled']}. Photos used: {used}. "
        f"Photos skipped: {len(results['skipped'])}",
    ]
    if 0 < used < FEW_PHOTOS:
        lines += ["", f"Only {used} photos were used, so every interval below is wide."]

    lines += ["", "## Pixel change", ""]
    lines += _pixel_table(summaries)
    lines += [
        "",
        "PSNR and SSIM are described in `docs/how-it-works.md`. A condition that changes the size "
        "of the photo cannot be scored pixel by pixel, so it shows 0 photos scored. "
        "The worst case is the lowest PSNR and SSIM and the largest pixel change.",
    ]

    lines += ["", "## Face match", ""]
    if all(item["face"] is None for item in summaries):
        lines.append("Face matching was not run.")
    else:
        lines += _face_table(summaries)
        lines += [
            "",
            "A photo whose original face was not found is left out of the face numbers. "
            "A face not found after processing counts as no match. The match rate is matches "
            f"divided by the photos whose original face was found. The match threshold is a "
            f"cosine similarity of {meta['thresholds']['cosine_match']}.",
        ]
        impostor = results["impostor"]
        if impostor is not None:
            lines += [
                "",
                f"Different photos compared with each other: {impostor['pairs']} pairs, "
                f"{impostor['false_matches']} false matches, highest similarity "
                f"{_number(impostor['max_similarity'], 3)}. This assumes two photos never show "
                "the same person. If they do, the false match count is too high.",
            ]

    if results["skipped"]:
        lines += ["", "## Skipped photos", ""]
        lines += [f"- {item['image']}: {item['reason']}" for item in results["skipped"]]

    lines += ["", "## Settings", ""]
    fixed, mild = meta["fixed_pipeline"], meta["mild_pipeline"]
    lines += [
        f"- Fixed pipeline: long side {fixed['long_side']}, centre crop "
        f"{round(100 * fixed['crop_keep'])} percent, JPEG {fixed['jpeg_quality']}",
        f"- Milder pipeline: shrink only above {mild['max_long_side']}, "
        f"JPEG {mild['jpeg_quality']}, no crop",
        f"- Detection score threshold: {meta['thresholds']['detection_score']}",
    ]
    if meta["face_models"]:
        lines += [f"- Model file: {m['file']}, SHA-256 {m['sha256']}" for m in meta["face_models"]]
    lines += [f"- {name}: {number}" for name, number in meta["libraries"].items()]
    return "\n".join(lines) + "\n"


def _spread_text(spread: dict | None) -> str:
    if spread is None:
        return "n/a"
    return f"{_number(spread['mean'], 3)} (lowest {_number(spread['worst'], 3)})"


def _level_table(summary: dict) -> list[str]:
    rows = [
        "| Attackers up to level | Photos | Survival of the best attack, mean (lowest) "
        "| Photos with survival at least 50% (95% interval) |",
        "|---|---|---|---|",
    ]
    for item in summary["levels"]:
        interval = item["held_interval"]
        interval_text = (
            "n/a" if interval is None else f"{_percent(interval[0])} to {_percent(interval[1])}"
        )
        rows.append(
            f"| {item['max_level']} | {item['photos']} | {_spread_text(item['survival'])} "
            f"| {item['held']} ({_percent(item['held_rate'])}, {interval_text}) |"
        )
    return rows


def _attack_table(summary: dict) -> list[str]:
    rows = [
        "| Attack | Level | Photos attacked | Photos with an admissible result "
        "| Survival, mean (lowest) |",
        "|---|---|---|---|---|",
    ]
    for item in summary["attacks"]:
        admissible = item["survival"]["n"] if item["survival"] else 0
        rows.append(
            f"| {item['attack']} | {item['level']} | {item['photos_run']} | {admissible} "
            f"| {_spread_text(item['survival'])} |"
        )
    return rows


def render_redteam_report(results: dict) -> str:
    """Return the report for one red team run as Markdown text."""
    meta = results["meta"]
    dataset = meta["dataset"]
    floor = meta["quality_floor"]
    lines = [
        "# Red team report",
        "",
        "Every protection in this run is a toy. A toy adds a hidden pattern that we know "
        "exactly, and it does nothing against any editing model or face matcher. The run "
        "checks the attack tools, not a protection. It says nothing about whether a real "
        "protection works.",
        "",
        "## Run",
        "",
        f"- Dataset: {dataset['name']} (`{dataset['id']}`)",
        f"- Dataset licence: {dataset['licence']}",
        f"- Dataset review status: {dataset['status']}",
        f"- Created: {meta['created']}",
        f"- Seed: {meta['seed']}",
        f"- Photos sampled: {meta['photos_sampled']}. Photos skipped: {len(results['skipped'])}",
        "",
        "## How to read the numbers",
        "",
        "Survival is the share of the protection's own change that is still in the attacked "
        "photo. 1 means all of it and 0 means none. It can go below 0 or above 1. It measures "
        "whether the change is still there, not whether a model is still fooled.",
        "",
        f"An attack result counts only when the attacked photo stays close to the unprotected "
        f"original: PSNR at least {floor['psnr']:g} dB and SSIM at least {floor['ssim']:g}. "
        "Both limits are a **Guess** until the human study. For each photo the attacker "
        "keeps the admissible result with the lowest survival. The results are not averaged "
        "across attacks. A photo whose protection fails 50 percent survival against the best "
        "attack counts as one the attacker beat.",
    ]
    for summary in redteam.summarise(results):
        lines += ["", f"## {summary['protection']}", "", summary["description"], ""]
        lines.append(
            f"Photos: {summary['photos']}. Photos left out because the protected photo "
            f"itself is below the quality floor, or the protection changed no pixel: "
            f"{summary['unusable']}."
        )
        lines += ["", "Best attack by attacker level:", ""] + _level_table(summary)
        lines += ["", "Each attack alone, at its best strength for each photo:", ""]
        lines += _attack_table(summary)
    if results["not_applicable"]:
        lines += ["", "## Attacks that could not run", ""]
        lines += [
            f"- {item['attack']} on {item['protection']}, {item['photos']} photos: {item['reason']}"
            for item in results["not_applicable"]
        ]
    if results["skipped"]:
        lines += ["", "## Skipped photos", ""]
        lines += [f"- {item['image']}: {item['reason']}" for item in results["skipped"]]
    lines += ["", "## Settings", ""]
    lines += [
        f"- Toy pattern strength: RMS {meta['toy']['pattern_rms']:g} pixel values",
        f"- Toy band: Gaussian sigmas {meta['toy']['band_sigmas'][0]:g} and "
        f"{meta['toy']['band_sigmas'][1]:g} pixels",
        f"- Survival needed: {round(100 * meta['survival_floor'])} percent",
    ]
    lines += [f"- {name}: {number}" for name, number in meta["libraries"].items()]
    return "\n".join(lines) + "\n"
