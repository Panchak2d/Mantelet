"""How much a protection lowers the face match, judged beside the unprotected photo.

A face can be missing after processing for two reasons: the processing lost it, or the
protection made the detector miss it. The baseline counting rule calls both "no match",
which would credit the protection with faces that the processing lost on its own. This
module separates them, using the same photos, the same pipeline and the same code for
the unprotected photo (the ``none`` control in the red team run).

Rules, fixed in docs/research/test-plan.md before any protection result exists:

* Only photos whose unprotected, processed face still matches the original count. These
  are the photos an attacker could use without the protection. A photo whose face the
  processing alone lost is left out and counted on its own.
* On those photos, a protected photo whose face is no longer found counts as an attacker
  win. A real attacker can find the face with another detector, so a detector miss is
  not credit to the protection. The figure that counts it as no match is reported beside it.
* The drop is 100 percentage points minus the attacker win rate, because the unprotected
  baseline is a match on every counted photo by construction.
"""

from __future__ import annotations

from collections.abc import Sequence

from mantelet import baseline

CONTROL_NAME = "none"
LOST, NO_MATCH, MATCH = "lost", "no_match", "match"


def face_state(row: dict) -> str | None:
    """``lost``, ``no_match`` or ``match`` for a pipeline row. None without an original face."""
    if row.get("face_match") is None:
        return None
    if row.get("similarity") is None:
        return LOST
    return MATCH if row["face_match"] else NO_MATCH


def _rate(wins: int, total: int) -> dict:
    return {
        "wins": wins,
        "photos": total,
        "rate": wins / total if total else None,
        "interval": baseline.wilson_interval(wins, total),
    }


def pipeline_effect(rows: Sequence[dict], protection: str) -> dict | None:
    """Face states through the fixed pipeline for one protection, beside the control.

    Returns None when there are no control rows or no photo with a face in both. The keys:
    ``with_face`` photos with an original face, ``lost_by_pipeline`` control photos whose face
    the processing alone lost, ``control_no_match`` control photos that stayed found but did
    not match, ``eligible`` the photos counted, ``states`` the protected states on them,
    ``strict`` the attacker win rate with a lost face counted as a win, ``as_counted`` the
    rate with a lost face counted as no match, and ``drop`` in points under the strict rule.
    """
    control = {r["image"]: face_state(r) for r in rows if r["protection"] == CONTROL_NAME}
    protected = {r["image"]: face_state(r) for r in rows if r["protection"] == protection}
    shared = [name for name in protected if name in control]
    with_face = [name for name in shared if protected[name] is not None and control[name]]
    if not with_face:
        return None
    eligible = [name for name in with_face if control[name] == MATCH]
    seen = [protected[name] for name in eligible]
    states = {state: seen.count(state) for state in (LOST, NO_MATCH, MATCH)}
    strict = states[MATCH] + states[LOST]
    return {
        "with_face": len(with_face),
        "lost_by_pipeline": sum(control[name] == LOST for name in with_face),
        "control_no_match": sum(control[name] == NO_MATCH for name in with_face),
        "eligible": len(eligible),
        "states": states,
        "strict": _rate(strict, len(eligible)),
        "as_counted": _rate(states[MATCH], len(eligible)),
        "drop": None if not eligible else 100.0 * (1 - strict / len(eligible)),
    }


def level_effect(records: Sequence[dict], protection: str, max_level: int) -> dict | None:
    """The attacker win rate on face match up to ``max_level``, with a lost unattacked face a win.

    The unattacked protected photo is the ``identity`` row. A photo is counted when its
    original face was found and its identity row stays above the quality floor. The attacker
    wins when any admissible result up to ``max_level`` matches, or when the unattacked
    photo's face is lost. An attack that loses the face does not count as credit for the
    protection, since the attacker picks the best result. The unprotected baseline is a match
    on every counted photo, because the unprotected photo matches itself.
    """
    rows = [r for r in records if r["protection"] == protection]
    identity = {r["image"]: r for r in rows if r["attack"] == "identity"}
    counted = [
        name
        for name, row in identity.items()
        if row["admissible"] and row["original_face_found"]
    ]
    if not counted:
        return None
    wins = dict.fromkeys(counted, False)
    for name in counted:
        row = identity[name]
        wins[name] = bool(row["face_match"]) or row["similarity"] is None
    as_counted = dict.fromkeys(counted, False)
    for row in rows:
        if row["image"] in wins and row["admissible"] and row["level"] <= max_level:
            if row["face_match"]:
                wins[row["image"]] = True
                as_counted[row["image"]] = True
    total = len(counted)
    strict = sum(wins.values())
    return {
        "max_level": max_level,
        "photos": total,
        "strict": _rate(strict, total),
        "as_counted": _rate(sum(as_counted.values()), total),
        "drop": 100.0 * (1 - strict / total),
    }
