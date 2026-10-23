"""Turn baseline and red team results into short Markdown reports.

The report states what was measured, on what, and with which settings. It never
says that Mantelet protects anyone. It carries the dataset licence and review
status so a report cannot be separated from the rules the data came with.
"""

from __future__ import annotations

from mantelet import baseline, effect, redteam

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


def _effect_table(summary: dict, key: str, what: str) -> list[str]:
    rows = [
        f"| Attackers up to level | Photos | Photos where some admissible result {what} "
        "(95% interval) |",
        "|---|---|---|",
    ]
    for item in summary["levels"]:
        rate = item[key]
        if rate is None:
            rows.append(f"| {item['max_level']} | 0 | n/a |")
            continue
        low, high = rate["interval"] if rate["interval"] else (None, None)
        interval_text = "n/a" if low is None else f"{_percent(low)} to {_percent(high)}"
        rows.append(
            f"| {item['max_level']} | {rate['photos']} | {rate['wins']} "
            f"({_percent(rate['rate'])}, {interval_text}) |"
        )
    return rows


def _pipeline_lines(summary: dict) -> list[str]:
    pipe = summary["pipeline"]
    if not pipe["photos"]:
        return ["No photo reached the pipeline test."]
    lines = [
        "| Crop position | Survival, mean (lowest) |",
        "|---|---|",
        f"| Centre (the fixed pipeline) | {_spread_text(pipe['centre'])} |",
        f"| Seeded random corners | {_spread_text(pipe['random'])} |",
        f"| Corners on the 8 pixel grid | {_spread_text(pipe['aligned'])} |",
        f"| Worst corner for each photo | {_spread_text(pipe['worst'])} |",
        "",
        f"Photos whose worst corner keeps at least {round(100 * redteam.SURVIVAL_FLOOR)} "
        f"percent: {pipe['held']} of {pipe['photos']}.",
    ]
    if pipe["face_photos"]:
        lines += [
            "",
            f"Face still matches after the fixed pipeline: {pipe['face_matched']} of "
            f"{pipe['face_photos']} photos.",
        ]
    return lines


def _rate_text(rate: dict | None) -> str:
    if rate is None or rate["rate"] is None:
        return "n/a"
    low, high = rate["interval"] if rate["interval"] else (None, None)
    interval = "" if low is None else f", 95% interval {_percent(low)} to {_percent(high)}"
    return f"{rate['wins']} of {rate['photos']} ({_percent(rate['rate'])}{interval})"


def _effect_lines(results: dict, name: str) -> list[str]:
    """Face match beside the unprotected photo, for one protection."""
    pipe = effect.pipeline_effect(results.get("pipeline", []), name)
    level = effect.level_effect(results["records"], name, 2)
    if pipe is None and level is None:
        return ["No photo had a face in the original, so there is no effect to report."]
    lines = []
    if pipe is not None:
        states = pipe["states"]
        lines += [
            f"Photos with a face in the original: {pipe['with_face']}. The fixed pipeline alone "
            f"lost the face on {pipe['lost_by_pipeline']} and left it found but not matching on "
            f"{pipe['control_no_match']}. Those are left out. Counted photos (the unprotected "
            f"photo still matches after the pipeline): {pipe['eligible']}.",
            "",
            "| Protected photo after the fixed pipeline | Photos |",
            "|---|---|",
            f"| Face matches | {states['match']} |",
            f"| Face found, no match | {states['no_match']} |",
            f"| Face lost | {states['lost']} |",
            "",
            f"Attacker success, a lost face counted as a win: {_rate_text(pipe['strict'])}. "
            f"Drop against the unprotected photo: {_number(pipe['drop'], 1)} points. "
            f"A lost face counted as no match: {_rate_text(pipe['as_counted'])}.",
        ]
    if level is not None:
        lines += [
            "",
            f"Attackers up to level {level['max_level']}, a lost unattacked face counted as a "
            f"win: {_rate_text(level['strict'])}. Drop: {_number(level['drop'], 1)} points. "
            f"Without that rule: {_rate_text(level['as_counted'])}.",
        ]
    return lines


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
    if meta.get("subject", "toys") == "toys":
        intro = (
            "Every protection in this run is a toy. A toy adds a hidden pattern that we know "
            "exactly, and it does nothing against any editing model or face matcher. The run "
            "checks the attack tools, not a protection. It says nothing about whether a real "
            "protection works."
        )
    else:
        intro = (
            "The protections in this run are tuned against a PyTorch copy of SFace, and the face "
            "match is measured with the original SFace file run through OpenCV. This run covers "
            "photos from one synthetic set, one face model and the attacks listed below. It "
            "does not say that any photo is protected, and it measures nothing about editing "
            "models."
        )
    lines = [
        "# Red team report",
        "",
        intro,
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
        if meta.get("face_model"):
            lines += ["", "Face match, counted against the face in the unprotected original:", ""]
            lines += _effect_table(summary, "face_match", "still matches the face")
        else:
            lines += ["", "Face match: not measured, no face model was given."]
        if meta.get("editor"):
            lines += ["", f"Stand-in edit ({meta['editor']}):", ""]
            lines += _effect_table(summary, "edit_success", "still lets the edit work")
        else:
            lines += ["", "Edit success: not measured. No editing model is built yet."]
        if meta.get("face_model") and "pipeline" in results:
            lines += ["", "Face match beside the unprotected photo:", ""]
            lines += _effect_lines(results, summary["protection"])
        lines += ["", "Survival through the fixed pipeline at many crop positions:", ""]
        if "pipeline" in results:
            lines += _pipeline_lines(summary)
        else:
            lines += ["Not measured in this run."]
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
    if meta.get("subject", "toys") == "toys":
        lines += [
            f"- Toy pattern strength: RMS {meta['toy']['pattern_rms']:g} pixel values",
            f"- Toy band: Gaussian sigmas {meta['toy']['band_sigmas'][0]:g} and "
            f"{meta['toy']['band_sigmas'][1]:g} pixels",
        ]
    elif meta.get("calibration"):
        calibration = meta["calibration"]
        band = calibration["band"]
        band_text = (
            "none found"
            if band is None
            else f"Gaussian sigmas {band[0]:g} and {band[1]:g} pixels"
        )
        lines.append(
            f"- Declared band: {band_text}, measured on {calibration['calibration_photos']} "
            f"photos kept apart from the test set at budget {calibration['calibration_budget']}. "
            f"Share of the change inside it: {_percent(calibration['band_energy_share'])}"
        )
    lines += [
        f"- Survival needed: {round(100 * meta['survival_floor'])} percent",
        f"- Face model: {'used' if meta.get('face_model') else 'not used'}. "
        f"Editor: {meta.get('editor') or 'none'}",
    ]
    lines += [f"- {name}: {number}" for name, number in meta["libraries"].items()]
    return "\n".join(lines) + "\n"
