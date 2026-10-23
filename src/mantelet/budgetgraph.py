"""Draw the perceptual budget graph as an SVG file, with no plotting library.

The graph has four small panels that share one horizontal axis, the L-infinity
budget in pixel values out of 255: PSNR, SSIM, face match rate and survival
through the fixed pipeline. Dashed lines mark the fixed thresholds that exist
for a panel. A missing value leaves a gap in the line. Nothing is smoothed.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from html import escape
from pathlib import Path

PANEL_WIDTH = 360
PANEL_HEIGHT = 230
MARGIN_LEFT = 58
MARGIN_RIGHT = 16
MARGIN_TOP = 34
MARGIN_BOTTOM = 40
COLUMNS = 2
LINE_COLOUR = "#1f5fa8"
THRESHOLD_COLOUR = "#b3261e"
TEXT_COLOUR = "#222222"
GRID_COLOUR = "#d9d9d9"

PANELS = (
    ("psnr", "PSNR against the original (dB)", 30.0, "30 dB floor"),
    ("ssim", "SSIM against the original", 0.90, "0.90 floor"),
    ("face_match", "Face match rate", None, ""),
    ("survival", "Survival through the fixed pipeline", 0.5, "50 percent"),
)


def _clean(point: dict, key: str) -> float | None:
    value = point.get(key)
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number or None, got {value}")
    return value


def _axis_range(key: str, values: list[float], threshold: float | None) -> tuple[float, float]:
    if key in ("ssim", "face_match"):
        return 0.0, 1.0
    pool = values + ([threshold] if threshold is not None else [])
    if key == "survival":
        pool += [0.0, 1.0]
    low, high = min(pool), max(pool)
    pad = (high - low) * 0.08 or 1.0
    return low - pad, high + pad


def _tick_text(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".") if abs(value) < 10 else f"{value:.0f}"


def _panel(
    index: int, points: Sequence[dict], key: str, label: str, threshold, threshold_label
) -> str:
    column, row = index % COLUMNS, index // COLUMNS
    left = column * PANEL_WIDTH
    top = row * PANEL_HEIGHT
    plot_width = PANEL_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    plot_height = PANEL_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    values = [v for v in (_clean(p, key) for p in points) if v is not None]
    low, high = _axis_range(key, values, threshold)

    def x_at(position: int) -> float:
        steps = max(len(points) - 1, 1)
        return MARGIN_LEFT + plot_width * (position / steps if len(points) > 1 else 0.5)

    def y_at(value: float) -> float:
        return MARGIN_TOP + plot_height * (1 - (value - low) / (high - low))

    parts = [f'<g transform="translate({left} {top})" font-family="sans-serif" font-size="11">']
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="18" font-size="12" font-weight="bold" '
        f'fill="{TEXT_COLOUR}">{escape(label)}</text>'
    )
    for step in range(5):
        value = low + (high - low) * step / 4
        y = y_at(value)
        parts.append(
            f'<line x1="{MARGIN_LEFT}" x2="{MARGIN_LEFT + plot_width}" y1="{y:.1f}" '
            f'y2="{y:.1f}" stroke="{GRID_COLOUR}" stroke-width="1"/>'
            f'<text x="{MARGIN_LEFT - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{TEXT_COLOUR}">{_tick_text(value)}</text>'
        )
    for position, point in enumerate(points):
        x = x_at(position)
        parts.append(
            f'<text x="{x:.1f}" y="{PANEL_HEIGHT - MARGIN_BOTTOM + 16}" text-anchor="middle" '
            f'fill="{TEXT_COLOUR}">{_tick_text(float(point["budget"]))}</text>'
        )
    parts.append(
        f'<text x="{MARGIN_LEFT + plot_width / 2}" y="{PANEL_HEIGHT - 6}" text-anchor="middle" '
        f'fill="{TEXT_COLOUR}">L-infinity budget (of 255)</text>'
    )
    if threshold is not None:
        y = y_at(threshold)
        parts.append(
            f'<line x1="{MARGIN_LEFT}" x2="{MARGIN_LEFT + plot_width}" y1="{y:.1f}" '
            f'y2="{y:.1f}" stroke="{THRESHOLD_COLOUR}" stroke-width="1.5" '
            f'stroke-dasharray="6 4"/>'
            f'<text x="{MARGIN_LEFT + plot_width}" y="{y - 4:.1f}" text-anchor="end" '
            f'fill="{THRESHOLD_COLOUR}">{escape(threshold_label)}</text>'
        )
    run: list[str] = []
    runs: list[list[str]] = []
    for position, point in enumerate(points):
        value = _clean(point, key)
        if value is None:
            if run:
                runs.append(run)
            run = []
            continue
        run.append(f"{x_at(position):.1f},{y_at(value):.1f}")
    if run:
        runs.append(run)
    for coordinates in runs:
        if len(coordinates) > 1:
            parts.append(
                f'<polyline points="{" ".join(coordinates)}" fill="none" '
                f'stroke="{LINE_COLOUR}" stroke-width="2"/>'
            )
        for coordinate in coordinates:
            x, y = coordinate.split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{LINE_COLOUR}"/>')
    parts.append("</g>")
    return "".join(parts)


def render_budget_graph(points: Sequence[dict], title: str) -> str:
    """Return the SVG text.

    Each point has ``budget`` and optional ``psnr``, ``ssim``, ``face_match`` and
    ``survival``. Points are drawn in budget order. A point missing a measure
    leaves a gap in that panel.
    """
    if not points:
        raise ValueError("at least one budget point is needed")
    ordered = sorted(points, key=lambda p: float(p["budget"]))
    budgets = [float(p["budget"]) for p in ordered]
    if not all(math.isfinite(b) and b > 0 for b in budgets):
        raise ValueError("every budget must be a finite number above 0")
    if len(set(budgets)) != len(budgets):
        raise ValueError("every budget must appear once")
    rows = math.ceil(len(PANELS) / COLUMNS)
    width, height = PANEL_WIDTH * COLUMNS, PANEL_HEIGHT * rows + 30
    body = "".join(
        _panel(index, ordered, key, label, threshold, threshold_label)
        for index, (key, label, threshold, threshold_label) in enumerate(PANELS)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="graph-title">'
        f'<title id="graph-title">{escape(title)}</title>'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
        f'<g transform="translate(0 30)">{body}</g>'
        f'<text x="{MARGIN_LEFT}" y="20" font-family="sans-serif" font-size="14" '
        f'font-weight="bold" fill="{TEXT_COLOUR}">{escape(title)}</text>'
        "</svg>\n"
    )


def write_budget_graph(points: Sequence[dict], path: str | Path, title: str) -> None:
    """Write the graph to ``path``. An existing file is replaced."""
    Path(path).write_text(render_budget_graph(points, title), encoding="utf-8")
