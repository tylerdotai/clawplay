"""
Match-report generator: pre-game previews and post-game recaps.

Pulls rich per-match data from multiple sources (aggregator pattern), then
renders a self-contained HTML report at two quality levels:

  - PREVIEW  → handout-quality preview (8.5×11 sheet by default)
  - LIVE     → live state (live score block, sources, live dot)
  - RECAP    → post-game recap (handout-quality, final score, sources)

Sources per sport (aggregator picks one or more):
  Soccer:       Goal.com, BBC Sport, FMHY (where-to-watch), Wikipedia
  US sports:    ESPN, BBC Sport (where covered), FMHY, Wikipedia
  Other:        ESPN, official site

Status detection:
  status == "PRE"/"NS"/"SCHEDULED"          -> render PREVIEW
  status in ("FT", "FINAL", "AET", "AP")    -> render RECAP
  anything else with score                  -> render LIVE
  no data                                   -> render UPCOMING (sparse preview)
"""

from __future__ import annotations

import argparse
import html as _html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .report import render_css
from .time_utils import countdown_to_kickoff, format_local, local_now, parse_iso

FMHY_URLS = {
    "soccer_live": "https://fmhy.net/video",
    "nfl": "https://fmhy.net/video",
    "nba": "https://fmhy.net/video",
    "nhl": "https://fmhy.net/video",
    "mlb": "https://fmhy.net/video",
    "mls": "https://fmhy.net/video",
    "ufc": "https://fmhy.net/video",
    "f1": "https://fmhy.net/video",
    "worldcup": "https://fmhy.net/video",
    "epl": "https://fmhy.net/video",
    "ucl": "https://fmhy.net/video",
}

BBC_URLS = {
    "soccer_live": "https://www.bbc.com/sport/football/scores-fixtures",
    "epl": "https://www.bbc.com/sport/football/premier-league/scores-fixtures",
    "worldcup": "https://www.bbc.com/sport/football/world-cup/scores-fixtures",
    "nfl": "https://www.bbc.com/sport/american-football/nfl/scores-fixtures",
    "nba": "https://www.bbc.com/sport/basketball/nba/scores-fixtures",
}

WIKI_URLS = {
    "worldcup": "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup",
    "epl": "https://en.wikipedia.org/wiki/Premier_League",
    "nba": "https://en.wikipedia.org/wiki/NBA",
    "nfl": "https://en.wikipedia.org/wiki/NFL",
}

_PRIMARY_URLS: Dict[str, str] = {}


def _build_source_urls() -> Dict[str, Dict[str, str]]:
    """Build per-sport source URL map from live_scores.SPORTS (single source of truth)."""
    try:
        from .live_scores import SPORTS
    except ImportError:
        from live_scores import SPORTS
    global _PRIMARY_URLS
    _PRIMARY_URLS = dict(SPORTS)
    out: Dict[str, Dict[str, str]] = {}
    for sport, url in _PRIMARY_URLS.items():
        out[sport] = {"primary": url}
    for sport, url in BBC_URLS.items():
        if sport in out:
            out[sport]["bbc"] = url
    for sport, url in FMHY_URLS.items():
        if sport in out:
            out[sport]["fmhy"] = url
    for sport, url in WIKI_URLS.items():
        if sport in out:
            out[sport]["wiki"] = url
    return out


SOURCE_URLS = _build_source_urls()


# ---- Match data model ------------------------------------------------------


class MatchReport:
    """A single match with data aggregated from multiple sources."""

    def __init__(self, sport: str, home: str, away: str, **kwargs):
        self.sport = sport
        self.home = home
        self.away = away
        self.competition = kwargs.get("competition", "")
        self.kickoff = kwargs.get("kickoff") or kwargs.get("start_time")
        self.venue = kwargs.get("venue")
        self.status = kwargs.get("status", "SCHEDULED")
        self.home_score = kwargs.get("home_score")
        self.away_score = kwargs.get("away_score")
        self.score = kwargs.get("score")
        self.sources: List[Dict[str, Any]] = []
        self.notes: List[str] = []
        self.metadata: Dict[str, Any] = {}

    @property
    def is_preview(self) -> bool:
        s = (self.status or "").upper()
        return s in ("NS", "PRE", "PRE_GAME", "SCHEDULED", "TBD", "POSTPONED")

    @property
    def is_final(self) -> bool:
        s = (self.status or "").upper()
        return s in ("FT", "FINAL", "F", "AET", "AFTER_OT", "AFTER_PEN", "AP")

    @property
    def is_live(self) -> bool:
        return not self.is_preview and not self.is_final

    @property
    def match_type(self) -> str:
        if self.is_preview:
            return "preview"
        if self.is_final:
            return "recap"
        return "live"

    def add_source(self, name: str, url: str, data: Any) -> None:
        self.sources.append({"name": name, "url": url, "data": data})

    def add_note(self, note: str) -> None:
        if note and note not in self.notes:
            self.notes.append(note)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sport": self.sport,
            "home": self.home,
            "away": self.away,
            "competition": self.competition,
            "kickoff": self.kickoff,
            "venue": self.venue,
            "status": self.status,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "score": self.score,
            "match_type": self.match_type,
            "sources": [{"name": s["name"], "url": s["url"]} for s in self.sources],
            "notes": self.notes,
            "metadata": self.metadata,
        }


# ---- Aggregator ------------------------------------------------------------


class Aggregator:
    """Pulls data from multiple sources for a single match."""

    def __init__(self, clawplay=None):
        try:
            from .clawplay import Clawplay
        except (ImportError, ValueError):
            from clawplay import Clawplay
        self.cp = clawplay or Clawplay()

    def _fetch(self, url: str, js: str, timeout_ms: int = 18000) -> Tuple[bool, Any, Optional[str]]:
        try:
            r = self.cp.eval(url, js, timeout_ms=timeout_ms)
        except Exception as e:
            return False, None, str(e)
        if not r.get("ok"):
            return False, None, r.get("error")
        try:
            return True, json.loads(r["content"]), None
        except Exception:
            return True, r.get("content"), None

    def aggregate_match(self, match: MatchReport) -> MatchReport:
        sources = SOURCE_URLS.get(match.sport, {})

        if "primary" in sources:
            ok, data, err = self._fetch_source(sources["primary"], match, kind="primary")
            if ok:
                match.add_source("primary", sources["primary"], data)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            self._merge_match_data(match, item)
            else:
                match.add_note(f"primary fetch failed: {err}")

        if "bbc" in sources:
            ok, data, err = self._fetch_source(sources["bbc"], match, kind="bbc")
            if ok:
                match.add_source("bbc", sources["bbc"], data)
            else:
                match.add_note(f"bbc fetch failed: {err}")

        if "fmhy" in sources:
            fmhy_js = _fmhy_template_for_sport(match.sport or "")
            js = fmhy_js.replace("__HOME__", match.home or "").replace("__AWAY__", match.away or "")
            ok, data, err = self._fetch(sources["fmhy"], js, timeout_ms=30000)
            if ok:
                match.add_source("fmhy", sources["fmhy"], data)
            else:
                match.add_note(f"fmhy fetch failed: {err}")

        if "wiki" in sources:
            ok, data, err = self._fetch_source(sources["wiki"], match, kind="wiki")
            if ok:
                match.add_source("wiki", sources["wiki"], data)
            else:
                match.add_note(f"wiki fetch failed: {err}")

        match.metadata["aggregated_at"] = format_local(local_now(), "%Y-%m-%d %H:%M:%S")
        match.add_note(f"aggregated from {len(match.sources)} sources")
        return match

    def _fetch_source(
        self, url: str, match: MatchReport, kind: str
    ) -> Tuple[bool, Any, Optional[str]]:
        tmpl = SOURCE_JS_TEMPLATES.get(kind, SOURCE_JS_TEMPLATES["primary"])
        js = tmpl.replace("__HOME__", match.home or "").replace("__AWAY__", match.away or "")
        timeout = 30000 if kind in ("fmhy", "wiki", "bbc") else 18000
        return self._fetch(url, js, timeout_ms=timeout)

    def _merge_match_data(self, match: MatchReport, item: Dict[str, Any]) -> None:
        if item.get("competition") and not match.competition:
            match.competition = item["competition"]
        if item.get("venue") and not match.venue:
            match.venue = item["venue"]
        nums = item.get("numbers") or []
        if nums and len(nums) >= 2 and (not match.home_score or not match.away_score):
            match.away_score = str(nums[0])
            match.home_score = str(nums[1])


# ---- JS templates ---------------------------------------------------------

SOURCE_JS_TEMPLATES = {
    "primary": r"""
(function(){
  const cards = Array.from(document.querySelectorAll(
    'section, [class*="Scoreboard"], [data-testid*="game"], [class*="GameCard"], [class*="sb-card"], li[class*="game"]'
  ));
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const homeN = norm('__HOME__');
  const awayN = norm('__AWAY__');
  const matches = [];
  for (const c of cards) {
    const t = norm(c.innerText);
    if (!t) continue;
    const nums = (t.match(/\b\d{1,3}\b/g) || []).map(Number);
    const homeLast = (homeN.split(' ').filter(Boolean).slice(-1)[0]) || '';
    const awayLast = (awayN.split(' ').filter(Boolean).slice(-1)[0]) || '';
    if ((homeLast && t.includes(homeLast)) || (awayLast && t.includes(awayLast))) {
      matches.push({
        raw: (c.innerText || '').slice(0, 500),
        numbers: nums.slice(0, 6),
        competition: (c.querySelector('h2, h3, [class*="title"]') || {}).innerText || document.title,
      });
    }
  }
  return matches.slice(0, 5);
})()
""",
    "goal": r"""
(function(){
  const rows = Array.from(document.querySelectorAll('[class*="match-row"], [class*="MatchRow"]'));
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const homeN = norm('__HOME__'); const awayN = norm('__AWAY__');
  const out = [];
  for (const r of rows) {
    const t = norm(r.innerText);
    if (!t) continue;
    const homeLast = (homeN.split(' ').filter(Boolean).slice(-1)[0]) || '';
    const awayLast = (awayN.split(' ').filter(Boolean).slice(-1)[0]) || '';
    if ((homeLast && t.includes(homeLast)) || (awayLast && t.includes(awayLast))) {
      out.push({ raw: (r.innerText || '').slice(0, 500), href: (r.querySelector('a') || {}).href || null });
    }
  }
  return out.slice(0, 5);
})()
""",
    "bbc": r"""
(function(){
  const cards = Array.from(document.querySelectorAll('article, [class*="Match"], [data-testid*="match"], [class*="fixture"]'));
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const homeN = norm('__HOME__'); const awayN = norm('__AWAY__');
  const homeLast = (homeN.split(' ').filter(Boolean).slice(-1)[0]) || '';
  const awayLast = (awayN.split(' ').filter(Boolean).slice(-1)[0]) || '';
  const out = [];
  for (const c of cards) {
    const t = norm(c.innerText);
    if (!t) continue;
    if ((homeLast && t.includes(homeLast)) || (awayLast && t.includes(awayLast))) {
      out.push({ raw: (c.innerText || '').slice(0, 500), href: (c.querySelector('a') || {}).href || null });
    }
  }
  return out.slice(0, 5);
})()
""",
    "fmhy": r"""
(function(){
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
  let chosen = null;
  for (const h of headings) {
    const t = norm(h.innerText || '').replace(/\s+/g,' ').trim();
    if (t === 'live sports' || t.startsWith('live sports')) { chosen = h; break; }
  }
  let container = null;
  if (chosen) {
    let cur = chosen.parentElement;
    while (cur && cur !== document.body) {
      const linkCount = cur.querySelectorAll('a').length;
      if (linkCount >= 5) { container = cur; break; }
      cur = cur.parentElement;
    }
    if (!container) container = chosen.nextElementSibling || chosen.parentElement;
  }
  if (!container) container = document.querySelector('main') || document.body;
  const allLinks = Array.from(container.querySelectorAll('a'));
  const links = allLinks
    .filter(a => {
      const t = (a.innerText || '').trim();
      const h = a.href || '';
      return t.length > 0 && t.length < 80 && h && !h.startsWith('javascript:') && !h.includes('#');
    })
    .slice(0, 50)
    .map(a => ({ text: (a.innerText || '').trim(), href: a.href }));
  const seen = new Set();
  const deduped = links.filter(l => {
    const k = l.href + '|' + l.text;
    if (seen.has(k)) return false;
    seen.add(k); return true;
  }).slice(0, 40);
  return {
    raw: (container.innerText || '').slice(0, 1500),
    links: deduped,
    title: document.title,
    url: location.href,
    heading_found: chosen ? chosen.innerText : null,
  };
})()
""",
    "wiki": r"""
(function(){
  const lead = (document.querySelector('#mw-content-text p') || {}).innerText || '';
  const infobox = (document.querySelector('.infobox') || {}).innerText || '';
  const sections = Array.from(document.querySelectorAll('#mw-content-text h2, h3')).slice(0, 20).map(h => h.innerText);
  return { raw: (infobox + '\n\n' + lead).slice(0, 2000), sections, title: document.title };
})()
""",
}

ESPN_GAME_JS_TEMPLATE = SOURCE_JS_TEMPLATES["primary"]
GOAL_GAME_JS_TEMPLATE = SOURCE_JS_TEMPLATES["goal"]
BBC_GAME_JS_TEMPLATE = SOURCE_JS_TEMPLATES["bbc"]


def _fmhy_template_for_sport(sport: str) -> str:
    return SOURCE_JS_TEMPLATES["fmhy"].replace("__SPORT__", sport)


# ---- Rich content extraction -----------------------------------------------

PREVIEW_KEYS = [
    "head_to_head",
    "form",
    "lineups",
    "key_players",
    "prediction",
    "odds",
    "where_to_watch",
]
RECAP_KEYS = ["scorers", "key_moments", "stats", "man_of_the_match", "table_impact", "what_next"]


def extract_rich_content(sources: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Pull best-effort text content per topic from raw source data."""
    out: Dict[str, List[Any]] = {k: [] for k in set(PREVIEW_KEYS) | set(RECAP_KEYS)}
    out["where_to_watch_links"] = []
    out["fmhy_excerpt"] = []
    for src in sources:
        data = src.get("data")
        if not data:
            continue
        name = src.get("name", "")
        if name == "fmhy" and isinstance(data, dict):
            links = data.get("links") or []
            out["where_to_watch_links"].extend(links[:15])
            raw = data.get("raw") or ""
            if raw:
                out["fmhy_excerpt"].append(f"[fmhy] {raw[:240]}")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                if item.get("raw"):
                    txt = item["raw"] if isinstance(item["raw"], str) else " ".join(item["raw"])
                    out["form"].append(f"[{name}] {txt[:240]}")
        elif isinstance(data, dict) and name != "fmhy":
            for k, v in data.items():
                if k in out and k != "where_to_watch_links" and v:
                    out[k].append(f"[{name}] {str(v)[:240]}")
    for k in out:
        if k != "where_to_watch_links":
            out[k] = out[k][:3]
    return out


# ---- RENDERING — Spark handout aesthetic ----------------------------------


def _ko_str(match: MatchReport) -> str:
    """Format kickoff time in viewer's local TZ."""
    if not match.kickoff:
        return ""
    ko_dt = parse_iso(match.kickoff)
    if not ko_dt:
        return _html.escape(match.kickoff)
    return _html.escape(format_local(ko_dt, "%a %b %-d · %-I:%M %p"))


def _meta_row(label: str, value: str) -> str:
    if not value:
        return ""
    return (
        f'<div class="meta-row"><span class="meta-label">{_html.escape(label)}</span>'
        f'<span class="meta-val">{value}</span></div>'
    )


def _handout_topline(label: str, generated: str) -> str:
    return f"""
    <div class="topline">
      <span>Clawplay · Match Report</span>
      <span>●</span>
      <span class="right">{_html.escape(generated)} CT</span>
    </div>
    """


def _handout_bottomline(label: str, src_count: int, generated: str) -> str:
    return f"""
    <div class="bottomline">
      <span>{label}</span>
      <span>●</span>
      <span class="right">{src_count} sources · {_html.escape(generated)} CT</span>
    </div>
    """


def _handout_header(match: MatchReport, mode_label: str) -> str:
    eyebrow = match.competition or match.sport.upper() or "Match"
    venue = _html.escape(match.venue or "")
    return f"""
    <header>
      <div class="logo-box"><span class="badge-glyph">C</span></div>
      <div>
        <div class="eyebrow">{_html.escape(eyebrow)} · {_html.escape(mode_label)}</div>
        <h1>{_html.escape(match.away)} <em>vs</em> {_html.escape(match.home)}</h1>
      </div>
    </header>
    <div class="speaker-row">
      <div class="speaker-card">
        <div class="label">Away</div>
        <div class="name">{_html.escape(match.away)}</div>
        <div class="role">{_html.escape(match.sport or "").title()}{(" · " + _html.escape(venue)) if venue else ""}</div>
      </div>
      <div class="speaker-card">
        <div class="label">Home</div>
        <div class="name">{_html.escape(match.home)}</div>
        <div class="role">{_html.escape(venue) if venue else "—"}</div>
      </div>
    </div>
    """


def _handout_stats(match: MatchReport) -> str:
    """Stat cells: kickoff, venue, status, sources."""
    ko_dt = parse_iso(match.kickoff) if match.kickoff else None
    ko_str = format_local(ko_dt, "%a %-m/%-d") if ko_dt else "TBD"
    ko_time = format_local(ko_dt, "%-I:%M %p") if ko_dt else ""

    countdown = countdown_to_kickoff(match.kickoff or "") if match.is_preview else ""
    status_disp = (
        "FULL TIME"
        if match.is_final
        else (
            match.status
            if match.status and match.status != "TBD"
            else (countdown.upper() if countdown else "PREVIEW")
        )
    )

    return f"""
    <div class="stats">
      <div class="stat"><strong>{_html.escape(ko_str)}</strong><span>Kickoff</span></div>
      <div class="stat"><strong>{_html.escape(ko_time or "—")}</strong><span>Local Time</span></div>
      <div class="stat"><strong>{_html.escape(status_disp)}</strong><span>Status</span></div>
      <div class="stat"><strong>{len(match.sources):02d}</strong><span>Sources</span></div>
    </div>
    """


def _handout_thesis(match: MatchReport, content: Dict[str, List[Any]]) -> str:
    """Big quote block: lead with the most relevant piece of info."""
    body = ""
    if match.is_final:
        # Final: lead with scoreline headline
        if match.home_score not in (None, "") and match.away_score not in (None, ""):
            body = (
                f"{_html.escape(match.away)} {_html.escape(str(match.away_score))} · "
                f"{_html.escape(match.home)} {_html.escape(str(match.home_score))} · FULL TIME"
            )
        else:
            body = "Match complete."
    elif match.is_live:
        if match.home_score not in (None, "") and match.away_score not in (None, ""):
            body = (
                f"{_html.escape(match.away)} {_html.escape(str(match.away_score))} · "
                f"{_html.escape(match.home)} {_html.escape(str(match.home_score))} · "
                f"{_html.escape(match.status or 'LIVE')}"
            )
        else:
            body = "Live now."
    else:
        # Preview: lead with countdown
        ko_dt = parse_iso(match.kickoff) if match.kickoff else None
        ko_str = format_local(ko_dt, "%a %b %-d at %-I:%M %p") if ko_dt else "TBD"
        body = f"Kicks off {_html.escape(ko_str)} CT"

    return f"""
    <div class="thesis">
      <div class="label">Headline</div>
      <p class="body">{body}</p>
    </div>
    """


def _handout_scoreboard(match: MatchReport) -> str:
    """Big Georgia scoreboard — Spark style."""
    cls = "final" if match.is_final else ("live" if match.is_live else "")
    if match.is_preview:
        countdown = countdown_to_kickoff(match.kickoff or "")
        center_status = "PREVIEW"
        center_clock = countdown.upper() if countdown else "TBD"
        center_sub = "to kickoff"
        away_disp = match.away
        home_disp = match.home
        away_score = ""
        home_score = ""
    else:
        away_score = str(match.away_score) if match.away_score not in (None, "") else ""
        home_score = str(match.home_score) if match.home_score not in (None, "") else ""
        if match.is_final:
            center_status = "FULL TIME"
            center_clock = "FT"
            center_sub = "final"
        else:
            center_status = "LIVE"
            center_clock = match.status or ""
            center_sub = "live"
        away_disp = match.away
        home_disp = match.home

    return f"""
    <div class="scoreboard {cls}">
      <div class="team-side">
        <div class="name">{_html.escape(away_disp)}</div>
        <div class="score">{_html.escape(away_score or "—")}</div>
        <div class="record">Away</div>
      </div>
      <div class="vs-center">
        <div class="status">{_html.escape(center_status)}</div>
        <div class="clock">{_html.escape(center_clock)}</div>
        <div class="sub">{_html.escape(center_sub)}</div>
      </div>
      <div class="team-side">
        <div class="name">{_html.escape(home_disp)}</div>
        <div class="score">{_html.escape(home_score or "—")}</div>
        <div class="record">Home</div>
      </div>
    </div>
    """


def _handout_quote(match: MatchReport) -> str:
    """Spark-style quote callout — pulls from FMHY excerpt or competition."""
    if match.notes:
        text = match.notes[0]
    else:
        text = f"Pulled live from {len(match.sources) or 0} sources. Refresh for updates."
    return f'<div class="quote">{_html.escape(text)}</div>'


def _handout_tags(match: MatchReport) -> str:
    tags = []
    if match.competition:
        tags.append(match.competition)
    if match.sport:
        tags.append(match.sport.upper())
    if match.venue:
        tags.append(match.venue)
    for s in match.sources:
        tags.append(s["name"].upper())
    seen = set()
    out = []
    for t in tags:
        tl = t.lower()
        if tl in seen:
            continue
        seen.add(tl)
        out.append(f'<span class="tag">{_html.escape(t)}</span>')
    return f'<div class="tag-row">{"".join(out)}</div>' if out else ""


def _handout_section_box(title: str, items: List[str], side: str = "left") -> str:
    if not items:
        return ""
    body = "\n".join(f"<li>{_html.escape(it)}</li>" for it in items)
    return (
        f'<div class="box"><div class="box-head">{_html.escape(title)}</div><ul>{body}</ul></div>'
    )


def _handout_links_box(title: str, links: List[Dict[str, str]]) -> str:
    if not links:
        return ""
    chips = "\n".join(
        f'<a class="chip" href="{_html.escape(link.get("href", ""))}" target="_blank" rel="noopener">'
        f"{_html.escape(link.get('text', '(link)'))}</a>"
        for link in links
        if link.get("href")
    )
    return f'<div class="box"><div class="box-head">{_html.escape(title)}</div><div class="chips">{chips}</div></div>'


def _handout_content(match: MatchReport, content: Dict[str, List[Any]]) -> str:
    """Two-column content grid, Spark-style."""
    boxes = []
    if match.is_preview:
        boxes.append(_handout_section_box("Recent Form", content.get("form", [])))
        boxes.append(_handout_section_box("Head-to-Head", content.get("head_to_head", [])))
        boxes.append(_handout_section_box("Key Players", content.get("key_players", [])))
        boxes.append(_handout_section_box("Predicted Lineups", content.get("lineups", [])))
        boxes.append(_handout_section_box("Betting Odds", content.get("odds", [])))
        boxes.append(_handout_section_box("Prediction", content.get("prediction", [])))
        wt_links = content.get("where_to_watch_links") or []
        if wt_links:
            boxes.append(_handout_links_box("Where to Watch (FMHY)", wt_links))
            boxes.append(_handout_section_box("Notes", content.get("fmhy_excerpt", [])))
    elif match.is_final:
        boxes.append(_handout_section_box("Goalscorers", content.get("scorers", [])))
        boxes.append(_handout_section_box("Key Moments", content.get("key_moments", [])))
        boxes.append(_handout_section_box("Match Stats", content.get("stats", [])))
        boxes.append(_handout_section_box("Man of the Match", content.get("man_of_the_match", [])))
        boxes.append(_handout_section_box("Table Impact", content.get("table_impact", [])))
        boxes.append(_handout_section_box("What's Next", content.get("what_next", [])))
    else:
        boxes.append(
            _handout_section_box(
                "Live Updates",
                content.get("key_moments", []) or ["Match in progress — refresh for live data."],
            )
        )

    body = "\n".join(b for b in boxes if b)
    if not body:
        body = (
            '<div class="box"><div class="box-head">Sources</div>'
            '<div class="note">Sources did not return content for this match yet. '
            "The aggregator needs a kickoff time and at least one source with structured data.</div></div>"
        )
    return f'<div class="content">{body}</div>'


def _handout_next(match: MatchReport) -> str:
    """Three next-up cards."""
    cards = []
    if match.is_preview:
        cards.append(("Coming up", f"Kickoff {_ko_str(match)}"))
        cards.append(("Where to watch", "FMHY-sourced streams"))
        cards.append(("Refresh", "Live data on game day"))
    elif match.is_final:
        cards.append(("What's next", "Table impact / playoff picture"))
        cards.append(("Replay", "Sources linked below"))
        cards.append(("Refresh", "Latest from the wire"))
    else:
        cards.append(("Live", "Refresh for in-game updates"))
        cards.append(("Sources", f"{len(match.sources)} aggregated"))
        cards.append(("Next", "Final state when full time"))
    body = "".join(
        f'<div class="next-card"><b>{_html.escape(t)}</b><span>{_html.escape(s)}</span></div>'
        for t, s in cards
    )
    return f'<div class="next">{body}</div>'


def _handout_sources(match: MatchReport) -> str:
    if not match.sources:
        return ""
    chips = "\n".join(
        f'<a class="chip" href="{_html.escape(s["url"])}" target="_blank" rel="noopener">'
        f"{_html.escape(s['name'])} ↗</a>"
        for s in match.sources
    )
    return f"""
    <div class="content">
      <div class="box"><div class="box-head">Sources</div><div class="chips">{chips}</div></div>
      <div class="box"><div class="box-head">Aggregator Notes</div>
      {"".join(f'<div class="note">{_html.escape(n)}</div>' for n in match.notes[:3]) or '<div class="note">All sources fetched successfully.</div>'}
      </div>
    </div>
    """


def _handout_cta(match: MatchReport) -> str:
    label = "PREVIEW" if match.is_preview else ("FULL TIME" if match.is_final else "LIVE")
    msg = (
        "Refresh for live updates"
        if match.is_live
        else f"Score sourced from {len(match.sources)} sources"
        if match.is_final
        else f"Kickoff {_ko_str(match)}"
    )
    return f"""
    <div class="cta">
      <strong>{_html.escape(msg)}</strong>
      <span>clawplay · {_html.escape(label)}</span>
    </div>
    """


def render_match_report(
    match: MatchReport, *, title: Optional[str] = None, generated_at=None
) -> str:
    """Render a complete match report HTML — handout quality, 8.5×11 sheet."""
    if generated_at is None:
        generated_at = local_now()
    title = title or f"{match.away} vs {match.home} — {match.match_type.upper()}"
    mode_label = {"preview": "PREVIEW", "recap": "FULL TIME", "live": "LIVE"}[match.match_type]
    content = extract_rich_content(match.sources)
    gen_str = format_local(generated_at, "%a %b %-d · %-I:%M %p")
    date_str = format_local(generated_at, "%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<style>
{render_css()}
</style>
</head>
<body>
<div class="sheet">
  {_handout_topline(mode_label, gen_str)}
  {_handout_header(match, mode_label)}
  {_handout_stats(match)}
  {_handout_thesis(match, content)}
  {_handout_scoreboard(match)}
  {_handout_quote(match)}
  {_handout_tags(match)}
  {_handout_content(match, content)}
  {_handout_sources(match)}
  {_handout_next(match)}
  {_handout_cta(match)}
  {_handout_bottomline(date_str, len(match.sources), gen_str)}
</div>
</body>
</html>
"""


def write_match_report(match: MatchReport, out_path, **kwargs) -> str:
    html_doc = render_match_report(match, **kwargs)
    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    return str(out)


# ---- Find a specific match from a scoreboard -------------------------------


def find_match(games: List[dict], query: str) -> Optional[MatchReport]:
    q = query.lower()
    for g in games:
        home = g.get("home", "")
        away = g.get("away", "")
        comp = g.get("competition", "")
        if any(
            part in str(field).lower()
            for part in q.split()
            for field in (home, away, comp)
            if field
        ):
            return MatchReport(
                sport=g.get("sport", ""),
                home=home,
                away=away,
                competition=comp,
                kickoff=g.get("kickoff") or g.get("start_time"),
                venue=g.get("venue"),
                status=g.get("status", "TBD"),
                home_score=g.get("home_score"),
                away_score=g.get("away_score"),
                score=g.get("score"),
            )
    return None


# ---- CLI -------------------------------------------------------------------


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clawplay-match",
        description="Generate a pre-game preview or post-game recap for a specific match.",
    )
    parser.add_argument("query", help="Team name or competition to find")
    parser.add_argument("--sport", default=None)
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--no-aggregate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        from .live_scores import scores
    except (ImportError, ValueError):
        from live_scores import scores

    if args.sport:
        method_candidates = [f"{args.sport}_today", args.sport]
        result = None
        for m in method_candidates:
            if hasattr(scores, m):
                result = getattr(scores, m)()
                break
        if result is None:
            print(f"Unknown sport: {args.sport}", file=sys.stderr)
            return 2
        games = []
        if isinstance(result, dict):
            games = result.get("games", []) or []
            sport_label = result.get("sport", args.sport)
        elif isinstance(result, list):
            for d in result:
                if isinstance(d, dict):
                    games.extend(d.get("games", []) or [])
            sport_label = args.sport
        else:
            sport_label = args.sport
        for g in games:
            if isinstance(g, dict) and not g.get("sport"):
                g["sport"] = sport_label or args.sport
    else:
        all_results = scores.all_today()
        games = []
        for d in all_results.get("us") or []:
            if isinstance(d, dict):
                s = d.get("sport", "")
                for g in d.get("games", []):
                    if isinstance(g, dict) and not g.get("sport"):
                        g["sport"] = s
                games.extend(d.get("games", []))
        for d in all_results.get("soccer") or []:
            if isinstance(d, dict):
                s = d.get("sport", "")
                for g in d.get("games", []):
                    if isinstance(g, dict) and not g.get("sport"):
                        g["sport"] = s
                games.extend(d.get("games", []))
        soc_live = all_results.get("soccer_live_any") or {}
        if isinstance(soc_live, dict):
            s = soc_live.get("sport", "soccer_live")
            for g in soc_live.get("games", []):
                if isinstance(g, dict) and not g.get("sport"):
                    g["sport"] = s
            games.extend(soc_live.get("games", []))

    match = find_match(games, args.query)
    if match is None:
        print(f"No match found for {args.query!r}", file=sys.stderr)
        return 1

    if not args.no_aggregate:
        agg = Aggregator()
        try:
            agg.aggregate_match(match)
            print(f"✓ Aggregated from {len(match.sources)} sources")
        except Exception as e:
            print(f"⚠ Aggregation failed: {e}", file=sys.stderr)

    if args.output is None:
        stamp = local_now().strftime("%Y%m%d_%H%M%S")
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", f"{match.away}_vs_{match.home}").strip("_").lower()
        args.output = f"./clawplay_match_{safe}_{stamp}.html"

    out = write_match_report(match, args.output)
    size_kb = os.path.getsize(out) / 1024
    print(f"✓ {match.match_type.upper()} report → {out} ({size_kb:.1f} KB)")
    print(f"  {match.away} @ {match.home} ({match.status})")

    if args.json:
        json_path = out.rsplit(".", 1)[0] + ".json"
        Path(json_path).write_text(
            json.dumps(match.to_dict(), indent=2, default=str), encoding="utf-8"
        )
        print(f"✓ Raw match data → {json_path}")

    return 0


def _cli_entry():
    sys.exit(_cli())


if __name__ == "__main__":
    _cli_entry()
