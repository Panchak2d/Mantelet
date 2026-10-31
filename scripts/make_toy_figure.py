"""Draw the toy red team survival figure for docs/research/results.md as an SVG file.

    python scripts/make_toy_figure.py

The four values are the means reported in claim C-034 of research/claims-ledger.md.
They come from toy protections and say nothing about a real protection.
"""

import sys
from html import escape
from pathlib import Path

BARS = (
    ("Fine grain,\ncleanup filters", 0.056),
    ("Shared pattern,\ncollusion attack", 0.009),
    ("Per-photo pattern,\ncollusion attack", 0.963),
    ("Per-photo pattern,\nnon-local means", 0.465),
)
THRESHOLD = 0.5
WIDTH, HEIGHT = 640, 360
LEFT, RIGHT, TOP, BOTTOM = 64, 24, 48, 84
BAR_COLOUR = "#1f5fa8"
THRESHOLD_COLOUR = "#b3261e"
TEXT_COLOUR = "#222222"
GRID_COLOUR = "#d9d9d9"
OUTPUT = (
    Path(__file__).resolve().parent.parent / "docs" / "research" / "figures" / "toy-survival.svg"
)


def build_svg(bars=BARS, threshold=THRESHOLD):
    if not bars:
        raise ValueError("bars must not be empty")
    for _, value in bars:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"survival must be between 0 and 1, got {value}")
    plot_w = WIDTH - LEFT - RIGHT
    plot_h = HEIGHT - TOP - BOTTOM
    slot = plot_w / len(bars)
    bar_w = slot * 0.5

    def y_of(value):
        return TOP + plot_h * (1 - value)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" font-family="sans-serif" font-size="12" role="img" '
        f'aria-label="Mean survival of toy protections after toy red team attacks">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<text x="{LEFT}" y="22" font-size="14" fill="{TEXT_COLOUR}">'
        "Mean survival after attack, toy protections on 20 synthetic faces</text>",
        f'<text x="{LEFT}" y="38" font-size="11" fill="{TEXT_COLOUR}">'
        "Toy protections do nothing against any model. "
        "This is not a Mantelet protection result.</text>",
    ]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y_of(tick)
        parts.append(
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{WIDTH - RIGHT}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOUR}"/>'
        )
        parts.append(
            f'<text x="{LEFT - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{TEXT_COLOUR}">{tick:.2f}</text>'
        )
    for index, (label, value) in enumerate(bars):
        x = LEFT + slot * index + (slot - bar_w) / 2
        y = y_of(value)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{y_of(0) - y:.1f}" fill="{BAR_COLOUR}"/>'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'fill="{TEXT_COLOUR}">{value:.3f}</text>'
        )
        for line_no, line in enumerate(label.split("\n")):
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{HEIGHT - BOTTOM + 18 + 14 * line_no}" '
                f'text-anchor="middle" fill="{TEXT_COLOUR}">{escape(line)}</text>'
            )
    ty = y_of(threshold)
    parts.append(
        f'<line x1="{LEFT}" y1="{ty:.1f}" x2="{WIDTH - RIGHT}" y2="{ty:.1f}" '
        f'stroke="{THRESHOLD_COLOUR}" stroke-dasharray="6 4"/>'
    )
    parts.append(
        f'<text x="{WIDTH - RIGHT}" y="{ty - 5:.1f}" text-anchor="end" fill="{THRESHOLD_COLOUR}">'
        "50 percent pass number</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(output=OUTPUT):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
