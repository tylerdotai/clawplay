"""
HTML report generator for clawplay.

Two render modes from the same data:
  1. `render_report`  — screen-first scoreboard (mobile-first, dark, pulsing live dots)
  2. `render_handout` — printable 8.5×11" letter sheet (Spark Arlington 06/10 aesthetic)

Both modes share the clawplay / ClawPlex design tokens:
  bg #0a0a0a · text #fafafa · brand #1e40af · accent #3b82f6 · signal #dc2626 · live #fb2c36
  Typography: Georgia (display headlines), Karla (body), JetBrains Mono (labels)
  Visual signature: colored hard-offset shadows (red/blue/black, 7px), radial gradient
                    page bg, mono uppercase tracking labels, two-column content grid.

NO ORANGE. ClawPlex standard.
"""

from __future__ import annotations

import html as _html
import json
from collections.abc import Sequence
from typing import List, Optional

from .time_utils import format_local, local_now, parse_iso

# ---- clawplay / ClawPlex design tokens (source of truth: ~/clawplex/design.md) ----
BG_PAGE = "#0a0a0a"
BG_SURFACE = "#131313"
BG_SURFACE_RAISED = "#1a1a1a"
TEXT_PRIMARY = "#fafafa"
TEXT_MUTED = "#b8b8b8"
TEXT_DIM = "#7a7a7a"
BORDER = "rgba(255,255,255,.14)"
BRAND_BLUE = "#1e40af"
ACCENT_BLUE = "#3b82f6"
ACCENT_BLUE_LIGHT = "#60a5fa"
SIGNAL_RED = "#dc2626"
LIVE_RED = "#fb2c36"
LIVE_GREEN = "#16a34a"
FINAL_GREY = "#525252"

# Typography — match Spark handout system
FONT_DISPLAY = 'Georgia, "Times New Roman", serif'
FONT_HEAD = '"Montserrat", "SF Pro Display", system-ui, -apple-system, sans-serif'
FONT_BODY = '"Karla", "SF Pro Text", system-ui, -apple-system, sans-serif'
FONT_MONO = '"JetBrains Mono", "SF Mono", Menlo, monospace'

# ---- Status helpers ----

LIVE_STATUSES = {"1H", "2H", "HT", "ET", "LIVE", "IN_PROGRESS", "Q1", "Q2", "Q3", "Q4", "OT"}
FINAL_STATUSES = {"FT", "AET", "FINAL", "AFTER_OT", "F", "AFTER_PEN", "AP", "POST"}
UPCOMING_STATUSES = {"NS", "PRE", "PRE_GAME", "SCHEDULED", "TBD", "POSTPONED"}


def _is_live(status: str) -> bool:
    return (
        status.upper() in LIVE_STATUSES
        or "LIVE" in status.upper()
        or "IN_PROGRESS" in status.upper()
    )


def _is_final(status: str) -> bool:
    s = status.upper()
    return s in FINAL_STATUSES


def _is_upcoming(status: str) -> bool:
    return (status or "").upper() in UPCOMING_STATUSES


def _badge_for(status: str) -> tuple[str, str]:
    s = (status or "").upper()
    if _is_live(s):
        return ("LIVE", LIVE_RED)
    if _is_final(s):
        return ("FINAL", FINAL_GREY)
    if _is_upcoming(s):
        return (s or "PRE", ACCENT_BLUE)
    return (s or "—", TEXT_MUTED)


# ---- Data normalization ----------------------------------------------------


def _normalize_game(g: dict) -> dict:
    """Coerce a raw game dict into a render-ready dict.

    Output schema:
        {
            "sport": str,
            "competition": str,
            "status": str,           # raw, e.g. "1H", "HT", "FT", "77'"
            "status_label": str,     # "LIVE" / "FINAL" / "PRE" / "Q3"
            "status_color": str,     # hex
            "minute_or_clock": str,  # "77'" or "Q3 4:12" or "Half" or ""
            "is_live": bool,
            "is_final": bool,
            "is_upcoming": bool,
            "away": {"name": str, "score": str|None},
            "home": {"name": str, "score": str|None},
            "venue": str|None,
            "kickoff": str|None,
            "detail": str|None,
        }
    """
    raw_status = (g.get("status") or "").strip()
    s = raw_status.upper()

    minute_or_clock = ""
    is_live = is_final = is_upcoming = False
    badge_label = raw_status or "—"
    badge_color = TEXT_MUTED

    # Soccer-style minute markers (e.g. "77'", "45'+2")
    if "'" in raw_status:
        minute_or_clock = raw_status
        badge_label = "LIVE"
        badge_color = LIVE_RED
        is_live = True
    elif s in ("HT", "HALFTIME"):
        minute_or_clock = "Half"
        badge_label = "HT"
        badge_color = LIVE_RED
        is_live = True
    elif s in FINAL_STATUSES:
        minute_or_clock = ""
        badge_label = "FINAL"
        badge_color = FINAL_GREY
        is_final = True
    elif s in UPCOMING_STATUSES:
        ko = g.get("kickoff") or g.get("start_time") or ""
        ko_dt = parse_iso(ko) if ko else None
        minute_or_clock = format_local(ko_dt, "%a %-m/%-d · %-I:%M %p") if ko_dt else ""
        badge_label = "PRE"
        badge_color = ACCENT_BLUE
        is_upcoming = True
    elif s in ("Q1", "Q2", "Q3", "Q4", "OT", "OT1", "OT2", "SO"):
        clock = g.get("clock") or ""
        minute_or_clock = f"{s} {clock}".strip()
        badge_label = "LIVE"
        badge_color = LIVE_RED
        is_live = True
    elif s in ("IN_PROGRESS", "LIVE"):
        minute_or_clock = raw_status
        badge_label = "LIVE"
        badge_color = LIVE_RED
        is_live = True
    elif raw_status:
        minute_or_clock = ""
        badge_label = raw_status
        badge_color = TEXT_MUTED

    return {
        "sport": g.get("sport") or "",
        "competition": g.get("competition") or g.get("sport") or "",
        "status": raw_status,
        "status_label": badge_label,
        "status_color": badge_color,
        "minute_or_clock": minute_or_clock,
        "is_live": is_live,
        "is_final": is_final,
        "is_upcoming": is_upcoming,
        "away": _normalize_team(g.get("away"), g.get("away_score")),
        "home": _normalize_team(g.get("home"), g.get("home_score")),
        "venue": g.get("venue"),
        "kickoff": g.get("kickoff") or g.get("start_time"),
        "detail": g.get("detail"),
    }


def _normalize_team(name_or_dict, score=None) -> dict:
    if isinstance(name_or_dict, dict):
        return {
            "name": name_or_dict.get("name") or "",
            "score": name_or_dict.get("score") or score,
        }
    return {
        "name": str(name_or_dict) if name_or_dict else "",
        "score": score,
    }


# ---- Shared CSS tokens (used by both report.py and match_report.py) --------


def _design_tokens_css() -> str:
    return f"""
:root {{
  --void: {BG_PAGE};
  --surface: {BG_SURFACE};
  --surface-2: {BG_SURFACE_RAISED};
  --text: {TEXT_PRIMARY};
  --muted: {TEXT_MUTED};
  --dim: {TEXT_DIM};
  --line: {BORDER};
  --blue-deep: {BRAND_BLUE};
  --blue: {ACCENT_BLUE};
  --blue-light: {ACCENT_BLUE_LIGHT};
  --red: {SIGNAL_RED};
  --live: {LIVE_RED};
  --green: {LIVE_GREEN};
  --grey: {FINAL_GREY};
  --display: {FONT_DISPLAY};
  --head: {FONT_HEAD};
  --body: {FONT_BODY};
  --mono: {FONT_MONO};
}}
""".strip()


# ---- SCREEN report CSS (mobile-first, dark, live pulse) --------------------

_SCREEN_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--void);
  color: var(--text);
  font-family: var(--body);
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.container { max-width: 760px; margin: 0 auto; padding: 28px 18px 64px; }

/* ── Top bar (mirrors Spark handout topline) ───────────────────────── */
.topline {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 14px; align-items: center;
  border-bottom: 1px solid var(--line); padding-bottom: 10px;
  font: 700 10px/1 var(--mono); letter-spacing: .16em; text-transform: uppercase; color: var(--muted);
}
.topline .accent { color: var(--red); }
.topline .right { text-align: right; }

/* ── Header ───────────────────────────────────────────────────────── */
header { padding: 24px 0 18px; border-bottom: 1px solid var(--line); margin-bottom: 26px; }
.eyebrow {
  font: 800 11px/1 var(--mono); letter-spacing: .16em; text-transform: uppercase;
  color: var(--blue-light); margin-bottom: 8px;
}
h1 {
  font-family: var(--head);
  font-weight: 700;
  font-size: 30px;
  line-height: 1.12;
  letter-spacing: -.02em;
  color: var(--text);
}
h1 em { font-style: normal; color: var(--blue); }
.subtitle {
  font-family: var(--body); color: var(--muted); font-size: 14px; margin-top: 8px;
}

/* ── Summary cells ────────────────────────────────────────────────── */
.summary {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  margin-bottom: 28px;
}
.summary-cell {
  background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
  padding: 14px 10px; text-align: center;
}
.summary-num {
  font-family: var(--head); font-weight: 700; font-size: 24px; color: var(--text);
  font-variant-numeric: tabular-nums; display: block;
}
.summary-num.live { color: var(--live); }
.summary-num.final { color: var(--grey); }
.summary-num.upcoming { color: var(--blue); }
.summary-lbl {
  font: 800 9.5px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase;
  color: var(--dim); margin-top: 6px; display: block;
}

/* ── Section ──────────────────────────────────────────────────────── */
.section { margin-bottom: 30px; }
.section-title {
  font: 900 11px/1 var(--mono); letter-spacing: .18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 12px;
  padding-bottom: 10px; border-bottom: 1px solid var(--line);
  display: flex; align-items: center; gap: 10px;
}
.section-title .num {
  font: 700 10px/1 var(--mono); color: var(--blue-light);
  border: 1px solid var(--line); padding: 3px 6px;
}

/* ── Game card (with hard-offset shadows, Spark style) ────────────── */
.game {
  background: var(--surface); border: 1px solid var(--line); border-radius: 0;
  padding: 16px; margin-bottom: 12px;
  box-shadow: 5px 5px 0 #000;
  position: relative;
  transition: transform .12s ease;
}
.game:hover { transform: translate(-1px,-1px); box-shadow: 6px 6px 0 var(--blue-deep); }
.game.live   { box-shadow: 5px 5px 0 var(--red); border-left: 4px solid var(--live); }
.game.final  { box-shadow: 5px 5px 0 #000; border-left: 4px solid var(--grey); }
.game.upcoming { box-shadow: 5px 5px 0 var(--blue-deep); border-left: 4px solid var(--blue); }

.game-head {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
  gap: 10px;
}
.competition {
  font: 700 10.5px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase;
  color: var(--dim); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.badge {
  font: 700 10px/1 var(--mono); letter-spacing: .14em;
  padding: 4px 9px; background: var(--surface-2);
  display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0;
}
.badge.live { background: rgba(251,44,54,.12); color: var(--live); }
.badge.final { background: rgba(82,82,82,.25); color: var(--grey); }
.badge.upcoming { background: rgba(59,130,246,.12); color: var(--blue); }

.live-dot {
  width: 7px; height: 7px; background: var(--live); border-radius: 50%;
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,100% { opacity: 1; transform: scale(1); }
  50%     { opacity: .35; transform: scale(.8); }
}

.matchup {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 14px; align-items: center;
}
.team { display: flex; align-items: center; gap: 10px; min-width: 0; }
.team.away {}
.team.home { flex-direction: row-reverse; text-align: right; }
.team-name {
  font-family: var(--head); font-weight: 600; font-size: 16px; color: var(--text);
  flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.team-score {
  font-family: var(--head); font-weight: 700; font-size: 30px;
  color: var(--text); font-variant-numeric: tabular-nums;
  min-width: 32px; text-align: center;
}
.team-score.winner { color: var(--text); }
.team-score.loser  { color: var(--dim); }
.vs {
  font: 700 10px/1 var(--mono); letter-spacing: .14em; color: var(--dim);
  text-align: center; padding: 0 6px;
}
.detail {
  font-family: var(--body); font-size: 13px; color: var(--muted);
  margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--line);
}
.clock {
  font: 700 10.5px/1 var(--mono); letter-spacing: .14em;
  color: var(--live); text-transform: uppercase; margin-top: 8px;
}
.clock.upcoming { color: var(--blue); }

/* ── Footer ───────────────────────────────────────────────────────── */
footer {
  margin-top: 48px; padding-top: 18px; border-top: 1px solid var(--line);
  text-align: center; font: 700 10px/1.4 var(--mono);
  letter-spacing: .1em; color: var(--dim); text-transform: uppercase;
}
footer a { color: var(--blue); text-decoration: none; }

/* ── Mobile ───────────────────────────────────────────────────────── */
@media (max-width: 520px) {
  h1 { font-size: 24px; }
  .summary { grid-template-columns: repeat(2, 1fr); }
  .game { padding: 14px; }
  .team-score { font-size: 26px; }
  .topline { font-size: 9px; }
}
"""


# ---- HANDOUT (print) report CSS — 8.5×11" letter sheet, Spark 06/10 DNA ----

_HANDOUT_CSS = """
:root {
  --void:#0A0A0A; --surface:#131313; --surface-2:#1A1A1A;
  --text:#FAFAFA; --muted:#B8B8B8; --dim:#7A7A7A;
  --blue-deep:#1E40AF; --blue:#2563EB; --blue-light:#60A5FA;
  --red:#DC2626; --line:rgba(255,255,255,.14);
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--void); color: var(--text);
  font-family: Karla, Inter, ui-sans-serif, system-ui, sans-serif;
  line-height: 1.3;
}
.sheet {
  width: 8.5in; min-height: 11in; margin: 0 auto; padding: .42in .48in .38in;
  position: relative; overflow: hidden;
  background:
    radial-gradient(circle at 88% 4%, rgba(37,99,235,.42), transparent 2.75in),
    radial-gradient(circle at 0% 100%, rgba(220,38,38,.28), transparent 2.45in),
    linear-gradient(135deg,#050505 0%,var(--void) 45%,#0D111B 100%);
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.sheet::before {
  content: ""; position: absolute; inset: .16in;
  border: 1px solid var(--line); pointer-events: none;
}
.topline, .bottomline {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 14px; align-items: center;
  color: var(--muted); font: 700 7.8pt/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .16em; text-transform: uppercase;
}
.topline    { border-bottom: 1px solid var(--line); padding-bottom: .08in; }
.bottomline { position: absolute; left: .48in; right: .48in; bottom: .22in;
              border-top: 1px solid var(--line); padding-top: .08in; }
.topline span:nth-child(2), .bottomline span:nth-child(2) { color: var(--red); }
.topline span:last-child,  .bottomline span:last-child { text-align: right; }

header {
  display: grid; grid-template-columns: .88in 1fr; gap: .22in;
  align-items: center; margin-top: .22in;
}
.logo-box {
  width: .88in; height: .88in; border: 1px solid rgba(255,255,255,.22);
  background: #000; box-shadow: 7px 7px 0 var(--blue-deep);
  display: grid; place-items: center; overflow: hidden;
}
.logo-box .badge-glyph {
  font-family: Georgia, serif; font-size: 36pt; color: var(--red); line-height: 1;
}
.eyebrow {
  margin: 0 0 6pt; color: var(--blue-light);
  font: 800 8.8pt/1 ui-monospace, monospace; letter-spacing: .16em; text-transform: uppercase;
}
h1 {
  margin: 0; max-width: 6.5in;
  font-family: Georgia, "Times New Roman", serif; font-size: 32pt; line-height: .9;
  letter-spacing: -.04em;
}
h1 em { color: var(--red); font-style: italic; font-weight: 700; }

.speaker-row {
  margin-top: .18in; display: grid; grid-template-columns: 1.1fr .9fr; gap: .16in;
}
.speaker-card {
  padding: .14in .16in; background: var(--text); color: #050505;
  box-shadow: 7px 7px 0 var(--red);
}
.speaker-card .label {
  color: var(--blue-deep); font: 900 8pt/1 ui-monospace, monospace;
  letter-spacing: .15em; text-transform: uppercase;
}
.speaker-card .name {
  margin-top: 6pt; font-family: Georgia, serif; font-size: 22pt; line-height: .95;
  letter-spacing: -.04em;
}
.speaker-card .role { margin: 6pt 0 0; color: #222; font-size: 9.5pt; }

.stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: .08in; margin-top: .14in;
}
.stat {
  padding: .11in; border: 1px solid var(--line); background: rgba(19,19,19,.88);
}
.stat strong { display: block; color: var(--blue-light); font-size: 16pt; line-height: .9; }
.stat span {
  display: block; margin-top: 4pt; color: var(--muted);
  font: 800 7.4pt/1.15 ui-monospace, monospace; letter-spacing: .1em; text-transform: uppercase;
}

/* ── Thesis box (the "big quote" of the page) ─────────────────────── */
.thesis {
  margin-top: .18in; padding: .16in .2in;
  border: 1px solid var(--line);
  background: linear-gradient(180deg,rgba(26,26,26,.95),rgba(10,10,10,.95));
  box-shadow: 7px 7px 0 #000;
}
.thesis .label {
  color: var(--red); font: 900 8.4pt/1 ui-monospace, monospace;
  letter-spacing: .14em; text-transform: uppercase; margin-bottom: 6pt;
}
.thesis .body {
  margin: 0; font-family: Georgia, serif; font-size: 19pt; line-height: 1.04;
  letter-spacing: -.035em;
}

/* ── Two-column content grid ──────────────────────────────────────── */
.content {
  display: grid; grid-template-columns: 1fr 1fr; gap: .16in; margin-top: .16in;
}
.box {
  border: 1px solid var(--line); background: rgba(19,19,19,.88);
  padding: .14in .16in;
}
.box-head {
  margin: 0 0 8pt; color: var(--blue-light);
  font: 900 8.4pt/1 ui-monospace, monospace; letter-spacing: .13em; text-transform: uppercase;
}
.box ul { margin: 0; padding-left: .15in; color: var(--muted); font-size: 9pt; }
.box li { margin: 4pt 0; }
.box li strong { color: var(--text); }

/* ── Big scoreboard ───────────────────────────────────────────────── */
.scoreboard {
  margin-top: .18in; display: grid; grid-template-columns: 1fr auto 1fr;
  gap: .16in; align-items: center;
  padding: .18in .2in;
  border: 1px solid var(--line); background: rgba(19,19,19,.92);
  box-shadow: 7px 7px 0 var(--blue-deep);
}
.scoreboard.final { box-shadow: 7px 7px 0 var(--red); }
.scoreboard.live  { box-shadow: 7px 7px 0 var(--red); }
.team-side {
  display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6pt;
}
.team-side .name {
  font-family: Georgia, serif; font-size: 20pt; line-height: .95;
  letter-spacing: -.03em; color: var(--text);
}
.team-side .score {
  font-family: Georgia, serif; font-size: 56pt; line-height: .9;
  letter-spacing: -.04em; color: var(--text);
  font-variant-numeric: tabular-nums;
}
.team-side .record {
  font: 700 8pt/1 ui-monospace, monospace; letter-spacing: .12em;
  text-transform: uppercase; color: var(--dim);
}
.vs-center {
  display: flex; flex-direction: column; align-items: center; gap: 4pt;
  padding: 0 .14in;
}
.vs-center .status {
  font: 900 11pt/1 ui-monospace, monospace; letter-spacing: .14em;
  color: var(--red); text-transform: uppercase;
}
.vs-center .clock {
  font-family: Georgia, serif; font-size: 22pt; line-height: .95; color: var(--text);
}
.vs-center .sub {
  font: 800 7.6pt/1 ui-monospace, monospace; letter-spacing: .16em;
  color: var(--dim); text-transform: uppercase;
}

/* ── Quote callout (Spark signature) ──────────────────────────────── */
.quote {
  margin-top: .14in; padding: .14in .18in;
  background: var(--blue-deep); color: white;
  box-shadow: 7px 7px 0 var(--red);
  font-family: Georgia, serif; font-size: 17pt; line-height: 1.05;
  letter-spacing: -.035em;
}

/* ── Tag row ──────────────────────────────────────────────────────── */
.tag-row { display: flex; flex-wrap: wrap; gap: 6pt; margin-top: .14in; }
.tag {
  border: 1px solid rgba(255,255,255,.18); color: var(--text);
  background: rgba(37,99,235,.22); padding: 5pt 8pt;
  font: 850 7.4pt/1 ui-monospace, monospace; letter-spacing: .08em; text-transform: uppercase;
}

/* ── Source link chips ────────────────────────────────────────────── */
.chips {
  display: flex; flex-wrap: wrap; gap: 5pt; margin-top: 8pt;
}
.chip {
  border: 1px solid var(--line); background: rgba(26,26,26,.94);
  padding: 4pt 8pt;
  font: 800 7.8pt/1 ui-monospace, monospace; letter-spacing: .04em;
  color: var(--text); text-decoration: none;
}
.chip:hover { background: rgba(37,99,235,.4); }

/* ── Next-up row ──────────────────────────────────────────────────── */
.next {
  margin-top: .14in; display: grid; grid-template-columns: repeat(3, 1fr); gap: .1in;
}
.next-card {
  border: 1px solid var(--line); background: rgba(26,26,26,.94);
  padding: .11in .12in; min-height: .7in;
}
.next-card b {
  display: block; color: var(--red);
  font: 900 7.6pt/1 ui-monospace, monospace; letter-spacing: .11em; text-transform: uppercase;
}
.next-card span {
  display: block; margin-top: 4pt; color: var(--muted); font-size: 8pt; line-height: 1.25;
}

/* ── CTA footer ───────────────────────────────────────────────────── */
.cta {
  margin-top: .14in; margin-bottom: .38in;
  display: grid; grid-template-columns: 1fr auto; gap: .12in; align-items: center;
  padding: .13in .18in; background: var(--red); color: white;
  box-shadow: 7px 7px 0 #000;
}
.cta strong {
  font-family: Georgia, serif; font-size: 17pt; line-height: .9; letter-spacing: -.035em;
}
.cta span {
  font: 850 8pt/1 ui-monospace, monospace; letter-spacing: .12em; text-transform: uppercase;
}

/* ── Notes (with red bar — Spark style) ───────────────────────────── */
.note {
  background: rgba(19,19,19,.92); border: 1px solid var(--line);
  border-left: 5px solid var(--red);
  padding: 11pt 13pt; margin-bottom: 8pt;
  font-family: Karla, sans-serif; font-size: 9.5pt;
  color: var(--muted); line-height: 1.55;
}
.note strong { color: var(--text); }

/* ── Print ────────────────────────────────────────────────────────── */
@media print {
  @page { size: letter; margin: 0; }
  body { background: white; }
  .sheet { margin: 0; }
}
"""


# ---- RENDERERS -------------------------------------------------------------


def render_css() -> str:
    """Combined CSS for both screen and print modes (one stylesheet handles both)."""
    return _design_tokens_css() + "\n" + _SCREEN_CSS + "\n" + _HANDOUT_CSS


def _render_team(team: dict, side: str, opponent_score, is_final: bool) -> str:
    score = team.get("score")
    score_str = "—" if score in (None, "") else str(score)
    score_class = ""
    if is_final and opponent_score not in (None, "") and score not in (None, ""):
        try:
            if int(score) > int(opponent_score):
                score_class = "winner"
            elif int(score) < int(opponent_score):
                score_class = "loser"
        except (ValueError, TypeError):
            pass

    name = _html.escape(team.get("name") or "")
    record = _html.escape(team.get("record") or "")
    meta_html = f'<div class="team-meta">{record}</div>' if record else ""

    return f"""
    <div class="team {side}">
      <div style="flex:1;min-width:0;">
        <div class="team-name" title="{name}">{name}</div>
        {meta_html}
      </div>
      <div class="team-score {score_class}">{score_str}</div>
    </div>
    """


def _render_game_screen(g: dict) -> str:
    cls = (
        "live"
        if g["is_live"]
        else "final"
        if g["is_final"]
        else "upcoming"
        if g["is_upcoming"]
        else ""
    )
    badge_cls = cls if cls else ""
    badge_html = (
        f'<span class="badge {badge_cls}">'
        + ('<span class="live-dot"></span>LIVE' if g["is_live"] else g["status_label"])
        + "</span>"
    )

    clock = ""
    if g["minute_or_clock"]:
        clock_cls = "upcoming" if g["is_upcoming"] else ""
        clock = f'<div class="clock {clock_cls}">{_html.escape(g["minute_or_clock"])}</div>'

    detail = f'<div class="detail">{_html.escape(g["detail"])}</div>' if g.get("detail") else ""

    away_team = _render_team(g["away"], "away", g["home"]["score"], g["is_final"])
    home_team = _render_team(g["home"], "home", g["away"]["score"], g["is_final"])

    return f"""
    <div class="game {cls}">
      <div class="game-head">
        <span class="competition">{_html.escape(g["competition"] or g["sport"] or "")}</span>
        {badge_html}
      </div>
      <div class="matchup">
        {away_team}
        <div class="vs">VS</div>
        {home_team}
      </div>
      {clock}
      {detail}
    </div>
    """


def _summary_counts(games: List[dict]) -> dict:
    return {
        "live": sum(1 for g in games if g["is_live"]),
        "final": sum(1 for g in games if g["is_final"]),
        "upcoming": sum(1 for g in games if g["is_upcoming"]),
        "other": sum(1 for g in games if not (g["is_live"] or g["is_final"] or g["is_upcoming"])),
    }


def render_report(
    games: Sequence[dict],
    *,
    title: str = "Today's Games",
    subtitle: Optional[str] = None,
    group_by: str = "status",
    generated_at=None,
    sheet_mode: bool = False,
) -> str:
    """Render the scoreboard HTML. Sheet mode toggles handout layout (8.5×11")."""
    generated_at = generated_at or local_now()

    normed = [_normalize_game(g) for g in games]
    counts = _summary_counts(normed)

    # Group
    if group_by == "sport":
        groups: dict = {}
        for g in normed:
            groups.setdefault(g["sport"] or "other", []).append(g)
    elif group_by == "competition":
        groups = {}
        for g in normed:
            groups.setdefault(g["competition"] or g["sport"] or "other", []).append(g)
    else:  # status
        order = ["live", "upcoming", "final", "other"]
        groups = {k: [] for k in order}
        for g in normed:
            if g["is_live"]:
                groups["live"].append(g)
            elif g["is_upcoming"]:
                groups["upcoming"].append(g)
            elif g["is_final"]:
                groups["final"].append(g)
            else:
                groups["other"].append(g)
        # Drop empty buckets
        groups = {k: v for k, v in groups.items() if v}

    # Sections
    section_titles = {
        "live": ("Live Now", f"{counts['live']} games in progress"),
        "upcoming": ("Upcoming", f"{counts['upcoming']} games on deck"),
        "final": ("Final", f"{counts['final']} games decided"),
        "other": ("Other", f"{counts['other']} games"),
    }
    sections_html = []
    for key, items in groups.items() if isinstance(groups, dict) else []:
        if not items:
            continue
        title_txt, sub = section_titles.get(key, (key.title(), ""))
        body = "\n".join(_render_game_screen(g) for g in items)
        sections_html.append(
            f'<div class="section"><div class="section-title">'
            f'<span class="num">{len(items):02d}</span> '
            f"{_html.escape(title_txt.upper())} "
            f'<span style="margin-left:auto;font-weight:400;color:var(--dim);letter-spacing:.12em;">'
            f"{_html.escape(sub)}</span></div>{body}</div>"
        )
    if not sections_html:
        sections_html = [
            '<div class="section"><div class="section-title">No games</div>'
            '<div class="note">No games found for the given filters.</div></div>'
        ]

    # Summary cells
    summary_html = f"""
    <div class="summary">
      <div class="summary-cell"><span class="summary-num live">{counts["live"]}</span><span class="summary-lbl">Live</span></div>
      <div class="summary-cell"><span class="summary-num upcoming">{counts["upcoming"]}</span><span class="summary-lbl">Upcoming</span></div>
      <div class="summary-cell"><span class="summary-num final">{counts["final"]}</span><span class="summary-lbl">Final</span></div>
      <div class="summary-cell"><span class="summary-num">{len(normed)}</span><span class="summary-lbl">Total</span></div>
    </div>
    """

    stamp = format_local(generated_at, "%a %b %-d · %-I:%M %p")

    # Topline + header
    headline_html = f"""
    <div class="topline">
      <span>Clawplay · Live Scoreboard</span>
      <span class="accent">●</span>
      <span class="right">{_html.escape(stamp)} CT</span>
    </div>
    <header>
      <div class="eyebrow">Multi-Sport Scoreboard</div>
      <h1>{_html.escape(title)}</h1>
      {f'<div class="subtitle">{_html.escape(subtitle)}</div>' if subtitle else ""}
    </header>
    """

    container_open = '<div class="sheet">' if sheet_mode else '<div class="container">'
    container_close = "</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)} — clawplay</title>
<style>
{render_css()}
</style>
</head>
<body>
{container_open}
{headline_html}
{summary_html}
{"".join(sections_html)}
<footer>
  Generated {_html.escape(stamp)} CT · powered by
  <a href="https://github.com/tylerdotai/clawplay">clawplay</a>
  · {len(normed)} games · {counts["live"]} live · {counts["final"]} final
</footer>
{container_close}
</body>
</html>
"""


def write_report(games, out_path, **kwargs) -> str:
    """Render the report to a file. Returns absolute output path."""
    from pathlib import Path

    html_doc = render_report(games, **kwargs)
    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    return str(out)


# ---- CLI -------------------------------------------------------------------


def _cli(argv=None) -> int:
    import argparse
    import os
    import re
    import sys

    parser = argparse.ArgumentParser(
        prog="clawplay-report", description="Generate a live scoreboard HTML report."
    )
    parser.add_argument("sport", help="Sport key or 'all'")
    parser.add_argument("-o", "--output", default=None, help="Output HTML path")
    parser.add_argument("--title", default=None, help="Custom report title")
    parser.add_argument("--subtitle", default=None, help="Custom subtitle")
    parser.add_argument("--group-by", choices=("status", "sport", "competition"), default="status")
    parser.add_argument("--find", default=None, help="Filter games matching this query")
    parser.add_argument("--sheet", action="store_true", help="Render handout (8.5×11) layout")
    parser.add_argument("--json", action="store_true", help="Dump raw JSON next to HTML")
    args = parser.parse_args(argv)

    try:
        from .live_scores import scores
    except (ImportError, ValueError):
        from live_scores import scores

    # Pull data
    if args.sport == "all":
        result = scores.all_today()
        games: list = []
        for d in result.get("us") or []:
            if isinstance(d, dict):
                s = d.get("sport", "")
                for g in d.get("games", []):
                    if isinstance(g, dict):
                        g.setdefault("sport", s)
                        games.append(g)
        for d in result.get("soccer") or []:
            if isinstance(d, dict):
                s = d.get("sport", "")
                for g in d.get("games", []):
                    if isinstance(g, dict):
                        g.setdefault("sport", s)
                        games.append(g)
        soc = result.get("soccer_live_any") or {}
        if isinstance(soc, dict):
            s = soc.get("sport", "soccer_live")
            for g in soc.get("games", []):
                if isinstance(g, dict):
                    g.setdefault("sport", s)
                    games.append(g)
        title = args.title or "All Sports — Today"
    else:
        method = f"{args.sport}_today"
        if not hasattr(scores, method) and hasattr(scores, args.sport):
            method = args.sport
        if not hasattr(scores, method):
            print(f"Unknown sport: {args.sport}", file=sys.stderr)
            return 2
        result = getattr(scores, method)()
        games = result.get("games", []) if isinstance(result, dict) else []
        title = args.title or f"{args.sport.upper()} — Today"

    # Filter
    if args.find:
        q = args.find.lower()
        games = [
            g
            for g in games
            if q in f"{g.get('home', '')} {g.get('away', '')} {g.get('competition', '')}".lower()
        ]

    # Output path
    if args.output is None:
        stamp = local_now().strftime("%Y%m%d_%H%M%S")
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", args.sport).strip("_").lower()
        args.output = f"./clawplay_{safe}_{stamp}.html"

    out = write_report(
        games,
        args.output,
        title=title,
        subtitle=args.subtitle,
        group_by=args.group_by,
        sheet_mode=args.sheet,
    )
    size_kb = os.path.getsize(out) / 1024
    print(f"✓ {len(games)} games → {out} ({size_kb:.1f} KB)")
    print(f"  Title: {title}")
    if args.json:
        jp = out.rsplit(".", 1)[0] + ".json"
        from pathlib import Path

        Path(jp).write_text(json.dumps(games, indent=2, default=str), encoding="utf-8")
        print(f"✓ Raw data → {jp}")
    return 0


def _cli_entry():
    import sys

    sys.exit(_cli())


if __name__ == "__main__":
    _cli_entry()
