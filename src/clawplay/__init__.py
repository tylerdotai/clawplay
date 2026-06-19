"""
clawplay — sports aggregator with handout-quality HTML reports.

Quick start:
    from clawplay import scores, write_report
    nba = scores.nba_today()
    write_report(nba["games"], "nba.html", title="NBA — Tonight")

    from clawplay import Aggregator, MatchReport, write_match_report
    match = MatchReport("worldcup", "USA", "Mexico", kickoff="2026-06-19T03:00:00Z", status="PRE")
    Aggregator().aggregate_match(match)
    write_match_report(match, "usa_mexico.html")

CLI:
    clawplay-report nba --output nba.html
    clawplay-match "USA Mexico" --sport worldcup --output usa_mexico.html
    clawplay-live nba   # raw JSON to stdout
"""

from __future__ import annotations

__version__ = "1.0.0"

from . import time_utils  # noqa: F401
from .clawplay import Clawplay, ClawplayError, health  # noqa: F401
from .live_scores import SPORTS, LiveScores, scores  # noqa: F401
from .match_report import (
    Aggregator,
    MatchReport,
    extract_rich_content,
    find_match,
    render_match_report,
    write_match_report,
)  # noqa: F401
from .report import (
    ACCENT_BLUE,
    ACCENT_BLUE_LIGHT,
    BG_PAGE,
    BG_SURFACE,
    BG_SURFACE_RAISED,
    BORDER,
    BRAND_BLUE,
    FINAL_GREY,
    LIVE_GREEN,
    LIVE_RED,
    SIGNAL_RED,
    TEXT_DIM,
    TEXT_MUTED,
    TEXT_PRIMARY,
    render_css,
    render_report,
    write_report,
)  # noqa: F401

__all__ = [
    "__version__",
    # scoreboards
    "scores",
    "LiveScores",
    "SPORTS",
    "render_report",
    "write_report",
    "render_css",
    # match reports
    "MatchReport",
    "Aggregator",
    "find_match",
    "render_match_report",
    "write_match_report",
    "extract_rich_content",
    # browser client
    "Clawplay",
    "ClawplayError",
    "health",
    # design tokens (re-exported so consumers can match the look)
    "ACCENT_BLUE",
    "ACCENT_BLUE_LIGHT",
    "BG_PAGE",
    "BG_SURFACE",
    "BG_SURFACE_RAISED",
    "BORDER",
    "BRAND_BLUE",
    "FINAL_GREY",
    "LIVE_GREEN",
    "LIVE_RED",
    "SIGNAL_RED",
    "TEXT_DIM",
    "TEXT_MUTED",
    "TEXT_PRIMARY",
    "time_utils",
]  # noqa: F401
