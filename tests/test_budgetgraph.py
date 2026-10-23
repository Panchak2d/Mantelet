import xml.etree.ElementTree as ET

import pytest

from mantelet import budgetgraph

POINTS = [
    {"budget": 2, "psnr": 42.1, "ssim": 0.99, "face_match": 0.95, "survival": 0.9},
    {"budget": 8, "psnr": 31.0, "ssim": 0.93, "face_match": 0.40, "survival": 0.45},
    {"budget": 4, "psnr": 36.5, "ssim": 0.97, "face_match": 0.70, "survival": 0.7},
]


def parse(points, title="Budget"):
    return ET.fromstring(budgetgraph.render_budget_graph(points, title))


def tag(element):
    return element.tag.split("}")[1]


def test_the_graph_is_valid_svg_with_four_panels_and_a_line_per_panel_in_budget_order():
    root = parse(POINTS)
    names = [tag(e) for e in root.iter()]
    assert names.count("polyline") == 4 and names.count("circle") == 12
    first = next(e for e in root.iter() if tag(e) == "polyline").get("points").split()
    xs = [float(p.split(",")[0]) for p in first]
    assert xs == sorted(xs)


def test_thresholds_are_drawn_for_psnr_ssim_and_survival_but_not_face_match():
    svg = budgetgraph.render_budget_graph(POINTS, "Budget")
    assert svg.count("stroke-dasharray") == 3
    assert "30 dB floor" in svg and "0.90 floor" in svg and "50 percent" in svg


def test_a_missing_value_leaves_a_gap_and_a_lone_point_is_still_drawn():
    gapped = [dict(p) for p in POINTS]
    gapped[1]["survival"] = None
    gapped[2]["survival"] = None
    root = parse(gapped)
    assert [tag(e) for e in root.iter()].count("polyline") == 3
    assert [tag(e) for e in root.iter()].count("circle") == 10


def test_a_title_is_escaped_so_it_cannot_inject_markup():
    svg = budgetgraph.render_budget_graph(POINTS, "<script>x</script> & more")
    assert "<script>" not in svg
    assert parse(POINTS, "<script>x</script> & more") is not None


@pytest.mark.parametrize(
    "bad",
    [[], [{"budget": 0}], [{"budget": 2}, {"budget": 2}], [{"budget": float("nan")}]],
)
def test_bad_budgets_are_refused(bad):
    with pytest.raises(ValueError):
        budgetgraph.render_budget_graph(bad, "x")


def test_a_non_finite_measure_is_refused_and_a_single_point_renders(tmp_path):
    with pytest.raises(ValueError):
        budgetgraph.render_budget_graph([{"budget": 2, "psnr": float("inf")}], "x")
    target = tmp_path / "graph.svg"
    budgetgraph.write_budget_graph([{"budget": 2, "psnr": 40.0}], target, "One point")
    assert ET.parse(target).getroot() is not None
