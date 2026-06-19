"""clawplay.espn — Public ESPN summary API + Sleeper fantasy sync (no key required).

Pulls structured play-by-play for any NFL game via the public
``site.api.espn.com`` summary endpoint. Caches successful responses
to ``~/.cache/clawplay/nfl_pbp/{game_id}.json`` for 24 hours.

Falls back to ``MockNFLPlayByPlay.play(game_id)`` on any error so
callers always get a list of plays.

Sleeper fantasy data is unauthenticated and lives at
``https://api.sleeper.app/v1/players/{sport}``.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


CACHE_DIR = Path.home() / ".cache" / "clawplay" / "nfl_pbp"
CACHE_TTL = 24 * 60 * 60
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
SLEEPER_BASE = "https://api.sleeper.app/v1/players"
DEFAULT_TIMEOUT = 10
USER_AGENT = "clawplay/1.1 (https://github.com/tylerdotai/clawplay)"


def _cache_path(game_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{game_id}.json"


def _sleeper_cache_path(sport: str) -> Path:
    p = Path.home() / ".cache" / "clawplay"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"sleeper_{sport}.json"


def _cache_valid(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < CACHE_TTL


def _parse_plays_from_espn(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Translate ESPN's nested JSON into a flat list of plays."""
    out: List[Dict[str, Any]] = []
    drives = payload.get("drives", {}) or {}
    previous = drives.get("previous", []) or []
    for drive in previous:
        plays = drive.get("plays", []) or []
        for p in plays:
            start = p.get("start", {}) or {}
            end = p.get("end", {}) or {}
            text = (p.get("text") or "").lower()
            play_type = (
                "pass"
                if "pass" in text
                else ("run" if ("rush" in text or "run" in text) else "other")
            )
            out.append(
                {
                    "id": p.get("id"),
                    "drive": drive.get("id"),
                    "quarter": (p.get("period", {}) or {}).get("number"),
                    "clock": (p.get("clock", {}) or {}).get("displayValue"),
                    "down": start.get("down"),
                    "distance": start.get("distance"),
                    "yard_start": start.get("yardLine", 25) or 25,
                    "yard_end": end.get("yardLine", 25) or 25,
                    "yards": (start.get("yardsToEndzone", 0) or 0)
                    - (end.get("yardsToEndzone", 0) or 0),
                    "type": play_type,
                    "text": p.get("text"),
                    "score": bool(p.get("scoringPlay")),
                    "home_score": p.get("homeScore") or 0,
                    "away_score": p.get("awayScore") or 0,
                }
            )
    return out


class MockNFLPlayByPlay:
    """Procedural NFL play-by-play generator. Deterministic per game_id."""

    PLAY_TYPES = ["pass", "run", "pass", "run", "pass"]

    @classmethod
    def play(cls, game_id: str, num_plays: int = 12) -> List[Dict[str, Any]]:
        rng = random.Random(game_id)
        yard = 25
        plays: List[Dict[str, Any]] = []
        for i in range(num_plays):
            play_type = rng.choice(cls.PLAY_TYPES)
            yards = rng.randint(3, 28) if play_type == "pass" else rng.randint(-2, 12)
            yard = max(1, min(99, yard + yards))
            score = yard >= 100 or (i == num_plays - 1 and rng.random() < 0.05)
            if score:
                yard = 100
            plays.append(
                {
                    "id": f"mock-{game_id}-{i}",
                    "drive": "1",
                    "quarter": (i // 3) + 1,
                    "clock": f"{14 - (i % 3) * 4}:{(i * 13) % 60:02d}",
                    "down": (i % 4) + 1,
                    "distance": 10,
                    "yard_start": max(0, yard - yards),
                    "yard_end": yard,
                    "yards": yards,
                    "type": play_type,
                    "text": f"{play_type.title()} for {yards} yards",
                    "score": score,
                    "home_score": sum(7 for q in plays if q.get("score")),
                    "away_score": 0,
                }
            )
        return plays


def nfl_play_by_play(game_id: str, *, force_mock: bool = False) -> List[Dict[str, Any]]:
    """Pull structured play-by-play for an NFL game."""
    if force_mock or os.environ.get("CLAWPLAY_MOCK") == "1":
        return MockNFLPlayByPlay.play(game_id)
    cache = _cache_path(game_id)
    if _cache_valid(cache):
        return json.loads(cache.read_text())
    if requests is None:
        return MockNFLPlayByPlay.play(game_id)
    try:
        resp = requests.get(
            ESPN_SUMMARY_URL,
            params={"event": game_id},
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return MockNFLPlayByPlay.play(game_id)
    plays = _parse_plays_from_espn(payload)
    if not plays:
        return MockNFLPlayByPlay.play(game_id)
    cache.write_text(json.dumps(plays, default=str))
    return plays


def _mock_sleeper_payload() -> Dict[str, Any]:
    """Small mock player database for offline tests."""
    return {
        "4017": {
            "player_id": "4017",
            "first_name": "Patrick",
            "last_name": "Mahomes",
            "position": "QB",
            "team": "KC",
            "status": "Active",
            "fantasy_positions": ["QB"],
            "injury_status": None,
        },
        "4866": {
            "player_id": "4866",
            "first_name": "Travis",
            "last_name": "Kelce",
            "position": "TE",
            "team": "KC",
            "status": "Active",
            "fantasy_positions": ["TE"],
            "injury_status": None,
        },
        "8111": {
            "player_id": "8111",
            "first_name": "Justin",
            "last_name": "Jefferson",
            "position": "WR",
            "team": "MIN",
            "status": "Active",
            "fantasy_positions": ["WR"],
            "injury_status": None,
        },
    }


def fantasy_players_sleeper(sport: str = "nfl", *, force_mock: bool = False) -> Dict[str, Any]:
    """Pull the Sleeper fantasy player database (~5MB)."""
    cache = _sleeper_cache_path(sport)
    if not force_mock and _cache_valid(cache):
        return json.loads(cache.read_text())
    if force_mock or requests is None:
        return _mock_sleeper_payload()
    try:
        resp = requests.get(
            f"{SLEEPER_BASE}/{sport}",
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _mock_sleeper_payload()
    cache.write_text(json.dumps(data, default=str))
    return data


def top_waiver_targets(
    position: Optional[str] = None,
    count: int = 5,
    *,
    sport: str = "nfl",
    force_mock: bool = False,
) -> List[Dict[str, Any]]:
    """Top waiver-wire targets at a position."""
    players = fantasy_players_sleeper(sport, force_mock=force_mock)
    out: List[Dict[str, Any]] = []
    for _pid, p in players.items():
        if position and p.get("position") != position:
            continue
        if p.get("status") != "Active":
            continue
        if p.get("injury_status") in ("Out", "IR"):
            continue
        out.append(p)
        if len(out) >= count:
            break
    return out


__all__ = [
    "nfl_play_by_play",
    "fantasy_players_sleeper",
    "top_waiver_targets",
    "MockNFLPlayByPlay",
]
