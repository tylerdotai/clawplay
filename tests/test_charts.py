"""Tests for clawplay.charts."""

from __future__ import annotations

from clawplay.charts import drive_diagram_svg, xg_timeline_svg


def test_xg_timeline_svg_returns_string() -> None:
    out = xg_timeline_svg("USA", "#1e40af", "Mexico", "#dc2626", [])
    assert isinstance(out, str)
    assert "<svg" in out
    assert "viewBox=" in out
    assert "USA xG trajectory" in out


def test_xg_timeline_svg_with_points() -> None:
    points = [(0, 0.0), (15, 0.1), (45, 0.5), (75, 0.8), (90, 1.2)]
    out = xg_timeline_svg("USA", "#1e40af", "Mexico", "#dc2626", points)
    assert "<path" in out
    assert "M " in out  # path data
    assert "fill-opacity" in out  # area fill


def test_xg_timeline_svg_includes_goal_markers() -> None:
    # A 0.4+ xG jump should trigger a goal marker (circle).
    points = [(0, 0.0), (45, 0.0), (46, 0.5), (90, 0.6)]
    out = xg_timeline_svg("USA", "#1e40af", "Mexico", "#dc2626", points)
    assert "<circle" in out


def test_xg_timeline_svg_includes_axis_ticks() -> None:
    out = xg_timeline_svg("USA", "#1e40af", "Mexico", "#dc2626", [])
    assert "15'" in out
    assert "45'" in out
    assert "90'" in out


def test_drive_diagram_svg_returns_string() -> None:
    plays = [
        {"type": "run", "yard_start": 25, "yard_end": 30, "score": False},
        {"type": "pass", "yard_start": 30, "yard_end": 60, "score": False},
    ]
    out = drive_diagram_svg(plays)
    assert isinstance(out, str)
    assert "<svg" in out
    assert "Drive chart" in out


def test_drive_diagram_svg_with_mock_data() -> None:
    """Empty play list falls back to a 5-play mock drive."""
    out = drive_diagram_svg([])
    assert "5 plays" in out


def test_drive_diagram_svg_marks_score_with_star() -> None:
    plays = [
        {"type": "pass", "yard_start": 80, "yard_end": 100, "score": True},
    ]
    out = drive_diagram_svg(plays)
    assert "polygon" in out  # star uses polygon


def test_drive_diagram_svg_uses_run_triangle() -> None:
    plays = [{"type": "run", "yard_start": 25, "yard_end": 30, "score": False}]
    out = drive_diagram_svg(plays)
    assert "polygon" in out  # run marker is also polygon (triangle)


def test_drive_diagram_svg_uses_pass_circle() -> None:
    plays = [{"type": "pass", "yard_start": 25, "yard_end": 35, "score": False}]
    out = drive_diagram_svg(plays)
    assert "<circle" in out


def test_drive_diagram_svg_field_is_green() -> None:
    out = drive_diagram_svg([])
    assert "#0a3d0a" in out  # field color
