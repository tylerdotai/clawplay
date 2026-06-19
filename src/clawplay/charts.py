"""clawplay.charts — Inline SVG visualizations for match reports.

Renders xG timelines (soccer) and NFL drive diagrams as self-contained
inline SVG strings. Embeds into report HTML directly via Jinja2 string
substitution, so no external chart libraries are required.
"""

from __future__ import annotations

from typing import Sequence, Tuple

XGPoint = Tuple[int, float]  # (minute, cumulative_xg)
PlayEvent = dict  # {'type': str, 'yard_start': int, 'yard_end': int, 'score': bool}


def xg_timeline_svg(
    home_team: str,
    home_color: str,
    away_team: str,
    away_color: str,
    points: Sequence[XGPoint],
    *,
    width: int = 800,
    height: int = 280,
    match_minutes: int = 90,
) -> str:
    """Render a cumulative xG chart as inline SVG."""
    if not points:
        points = [
            (5, 0.08),
            (12, 0.12),
            (18, 0.18),
            (24, 0.21),
            (32, 0.27),
            (38, 0.31),
            (41, 0.55),
            (45, 0.62),
            (50, 0.66),
            (57, 0.72),
            (64, 0.81),
            (72, 1.05),
            (78, 1.21),
            (84, 1.38),
            (90, 1.48),
        ]
    max_xg = max((p[1] for p in points), default=1.5) * 1.1
    max_xg = max(max_xg, 0.5)
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def x(minute: int) -> float:
        return pad_l + (minute / match_minutes) * plot_w

    def y(xg: float) -> float:
        return pad_t + plot_h - (xg / max_xg) * plot_h

    path_d = " ".join(
        ("M" if i == 0 else "L") + f" {x(m):.1f} {y(g):.1f}" for i, (m, g) in enumerate(points)
    )
    area_d = path_d + f" L {x(points[-1][0]):.1f} {y(0):.1f} L {x(points[0][0]):.1f} {y(0):.1f} Z"

    goal_markers = []
    prev_xg = 0.0
    for minute, xg in points:
        if xg - prev_xg >= 0.4:
            goal_markers.append(
                f'<circle cx="{x(minute):.1f}" cy="{y(xg):.1f}" r="5" fill="{home_color}" '
                f'stroke="#0a0a0a" stroke-width="1.5" />'
            )
        prev_xg = xg

    x_ticks = []
    for tick in (0, 15, 30, 45, 60, 75, 90):
        if tick > match_minutes:
            continue
        tx = x(tick)
        x_ticks.append(
            f'<line x1="{tx:.1f}" y1="{pad_t + plot_h}" x2="{tx:.1f}" y2="{pad_t + plot_h + 4}" '
            f'stroke="#525252" />'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 18}" fill="#a3a3a3" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono, monospace">{tick}\'</text>'
        )

    y_ticks = []
    for tick in (0, 0.5, 1.0, 1.5, 2.0):
        if tick > max_xg:
            continue
        ty = y(tick)
        y_ticks.append(
            f'<line x1="{pad_l - 4}" y1="{ty:.1f}" x2="{pad_l + plot_w}" y2="{ty:.1f}" '
            f'stroke="#262626" stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 8}" y="{ty + 3:.1f}" fill="#a3a3a3" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono, monospace">{tick:.1f}</text>'
        )

    return f"""
<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
  <rect width="{width}" height="{height}" fill="#131313" />
  {"".join(y_ticks)}
  <path d="{area_d}" fill="{home_color}" fill-opacity="0.25" stroke="none" />
  <path d="{path_d}" fill="none" stroke="{home_color}" stroke-width="2.5" stroke-linejoin="round" />
  {"".join(goal_markers)}
  {"".join(x_ticks)}
  <text x="{pad_l}" y="20" fill="#fafafa" font-size="13" font-family="Georgia, serif" font-weight="bold">
    {home_team} xG trajectory
  </text>
  <text x="{width - pad_r}" y="20" fill="#a3a3a3" font-size="10" text-anchor="end"
        font-family="JetBrains Mono, monospace">
    cumulative expected goals
  </text>
</svg>""".strip()


def drive_diagram_svg(
    plays: Sequence[PlayEvent],
    *,
    width: int = 800,
    height: int = 320,
    home_color: str = "#1e40af",
    away_color: str = "#dc2626",
) -> str:
    """Render an NFL drive as a horizontal field diagram."""
    if not plays:
        plays = [
            {"type": "run", "yard_start": 25, "yard_end": 28, "score": False},
            {"type": "pass", "yard_start": 28, "yard_end": 41, "score": False},
            {"type": "run", "yard_start": 41, "yard_end": 44, "score": False},
            {"type": "pass", "yard_start": 44, "yard_end": 78, "score": False},
            {"type": "pass", "yard_start": 78, "yard_end": 100, "score": True},
        ]
    pad_l, pad_r, pad_t, pad_b = 40, 40, 60, 50
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def x(yard: int) -> float:
        return pad_l + (yard / 100) * plot_w

    yard_marks = []
    for yard in range(0, 101, 10):
        tx = x(yard)
        label = (
            ""
            if yard in (0, 100)
            else ("50" if yard == 50 else str(yard if yard <= 50 else 100 - yard))
        )
        yard_marks.append(
            f'<line x1="{tx:.1f}" y1="{pad_t}" x2="{tx:.1f}" y2="{pad_t + plot_h}" '
            f'stroke="#262626" stroke-width="1" />'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 18}" fill="#a3a3a3" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono, monospace">{label}</text>'
        )

    path_d = " ".join(
        ("M" if i == 0 else "L")
        + f" {x(p['yard_start']):.1f} {pad_t + plot_h * 0.5 + (i - len(plays) / 2) * 8:.1f}"
        for i, p in enumerate(plays)
    )

    markers = []
    for i, p in enumerate(plays):
        cx = x(p["yard_end"])
        cy = pad_t + plot_h * 0.5 + (i - len(plays) / 2) * 8
        color = home_color if i % 2 == 0 else away_color
        if p.get("score"):
            marker = (
                f'<polygon points="{cx:.1f},{cy - 8:.1f} {cx + 7:.1f},{cy + 5:.1f} '
                f'{cx - 7:.1f},{cy + 5:.1f}" fill="#fbbf24" stroke="#0a0a0a" stroke-width="1.5" />'
            )
        elif p["type"] == "run":
            marker = (
                f'<polygon points="{cx:.1f},{cy - 7:.1f} {cx + 6:.1f},{cy + 6:.1f} '
                f'{cx - 6:.1f},{cy + 6:.1f}" fill="{color}" stroke="#0a0a0a" stroke-width="1" />'
            )
        else:
            marker = (
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{color}" '
                f'stroke="#0a0a0a" stroke-width="1.5" />'
            )
        markers.append(marker)

    return f"""
<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
  <rect width="{width}" height="{height}" fill="#131313" />
  <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#0a3d0a"
        stroke="#1f6b1f" stroke-width="1" />
  {"".join(yard_marks)}
  <path d="{path_d}" fill="none" stroke="#fafafa" stroke-width="1.5" stroke-dasharray="4,4" />
  {"".join(markers)}
  <text x="{pad_l}" y="30" fill="#fafafa" font-size="14" font-family="Georgia, serif" font-weight="bold">
    Drive chart — {len(plays)} plays
  </text>
  <text x="{pad_l}" y="48" fill="#a3a3a3" font-size="10" font-family="JetBrains Mono, monospace">
    run &#9651;  pass &#9679;  score &#9733;
  </text>
</svg>""".strip()


__all__ = [
    "xg_timeline_svg",
    "drive_diagram_svg",
    "XGPoint",
    "PlayEvent",
]
