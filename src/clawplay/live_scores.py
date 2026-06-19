#!/usr/bin/env python3
"""
clawplay live_scores — multi-sport live scoreboard puller.

Sport-tuned URLs and JS extraction patterns. Add a sport by adding one row
to SPORTS + one method to LiveScores.
"""

import contextlib
import json
import sys
from typing import Optional

from .clawplay import Clawplay

# Source URLs per sport. If a board moves, update here.
SPORTS = {
    # Major US leagues
    "nfl": "https://www.espn.com/nfl/scoreboard",
    "nba": "https://www.espn.com/nba/scoreboard",
    "nhl": "https://www.espn.com/nhl/scoreboard",
    "mlb": "https://www.espn.com/mlb/scoreboard",
    "mls": "https://www.espn.com/mls/scoreboard",
    "wnba": "https://www.espn.com/wnba/scoreboard",
    # College
    "cfb": "https://www.espn.com/college-football/scoreboard",
    "cbb": "https://www.espn.com/mens-college-basketball/scoreboard",
    "cbb_w": "https://www.espn.com/womens-college-basketball/scoreboard",
    # Soccer / football (top leagues + WC)
    "epl": "https://www.espn.com/soccer/scoreboard/_/league/eng.1",
    "ucl": "https://www.espn.com/soccer/scoreboard/_/league/uefa.champions",
    "laliga": "https://www.espn.com/soccer/scoreboard/_/league/esp.1",
    "bundes": "https://www.espn.com/soccer/scoreboard/_/league/ger.1",
    "seriea": "https://www.espn.com/soccer/scoreboard/_/league/ita.1",
    "ligue1": "https://www.espn.com/soccer/scoreboard/_/league/fra.1",
    "mls_soc": "https://www.espn.com/soccer/scoreboard/_/league/usa.1",
    "worldcup": "https://www.espn.com/soccer/scoreboard/_/league/fifa.world",
    # All live soccer matches (any league) — Goal.com
    "soccer_live": "https://www.goal.com/en/live-scores",
    # Other
    "ufc": "https://www.espn.com/mma/scoreboard",
    "f1": "https://www.formula1.com/en/live-timing",
    "tennis": "https://www.espn.com/tennis/scoreboard",
    "golf": "https://www.espn.com/golf/leaderboard",
    "cricket": "https://www.espn.com/cricket/scoreboard",
    "rugby": "https://www.espn.com/rugby/scoreboard",
}

# ESPN scoreboard layout — used by most US/international boards
ESPN_JS = """
(function(){
  const games = [];
  document.querySelectorAll('section.Scoreboard__Game, [data-testid="Scoreboard.Game"], article.Scoreboard__GameCard').forEach(g => {
    const teams = g.querySelectorAll('[data-testid="TeamStack"], .Scoreboard__GameTeam, .TeamName');
    const scores = g.querySelectorAll('[data-testid="Scoreboard.GameScore"], .Scoreboard__GameScore');
    const status = g.querySelector('[data-testid="Scoreboard.GameStatus"], .Scoreboard__GameTime, .Scoreboard__GameStatus');
    const out = {
      away: teams[0]?.innerText?.trim(),
      home: teams[1]?.innerText?.trim(),
      away_score: scores[0]?.innerText?.trim(),
      home_score: scores[1]?.innerText?.trim(),
      status: status?.innerText?.trim(),
    };
    games.push(out);
  });
  return games;
})()
"""

# Goal.com (soccer live scores)
# Per-row structure: .fco-match-row__container > .fco-match-row > [
#   .fco-match-state (status text),
#   .fco-match-team-and-score__container > .fco-match-team-and-score > [
#     .fco-match-team-and-score__team-a  (away team name),
#     .fco-match-team-and-score__team-b  (home team name),
#     .fco-match-score__container > .fco-match-score x2 (away, home)
#   ]
GOAL_JS = """
(function(){
  const games = [];
  document.querySelectorAll('.fco-match-row__container').forEach(row => {
    const state = row.querySelector(':scope > .fco-match-row .fco-match-state, :scope > a.fco-match-state');
    const container = row.querySelector('.fco-match-team-and-score');
    const awayEl = row.querySelector('.fco-match-team-and-score__team-a');
    const homeEl = row.querySelector('.fco-match-team-and-score__team-b');
    const scoreEls = row.querySelectorAll('.fco-match-score__container .fco-match-score');
    games.push({
      away: awayEl?.innerText?.trim(),
      home: homeEl?.innerText?.trim(),
      away_score: scoreEls[0]?.innerText?.trim(),
      home_score: scoreEls[1]?.innerText?.trim(),
      status: state?.innerText?.trim(),
    });
  });
  return games;
})()
"""


class LiveScores:
    def __init__(self, clawplay: Optional[Clawplay] = None):
        self.cp = clawplay or Clawplay()

    def _extract(self, url: str, js: str, sport_label: str, timeout_ms: int = 25000) -> dict:
        r = self.cp.eval(url, js, timeout_ms=timeout_ms)
        if not r.get("ok"):
            return {
                "sport": sport_label,
                "url": url,
                "ok": False,
                "error": r.get("error"),
                "games": [],
            }
        try:
            games = json.loads(r["content"])
        except Exception:
            return {"sport": sport_label, "url": url, "ok": True, "raw": r["content"], "games": []}
        for g in games:
            if (
                "score" not in g
                and g.get("away_score") is not None
                and g.get("home_score") is not None
            ):
                g["score"] = f"{g['away_score']}-{g['home_score']}"
        return {"sport": sport_label, "url": url, "ok": True, "count": len(games), "games": games}

    # --- ESPN scoreboard fetchers ---
    def _espn(self, sport: str) -> dict:
        if sport not in SPORTS:
            return {
                "ok": False,
                "error": f"unknown sport: {sport}",
                "available": list(SPORTS.keys()),
            }
        return self._extract(SPORTS[sport], ESPN_JS, sport)

    def nfl_today(self):
        return self._espn("nfl")

    def nba_today(self):
        return self._espn("nba")

    def nhl_today(self):
        return self._espn("nhl")

    def mlb_today(self):
        return self._espn("mlb")

    def mls_today(self):
        return self._espn("mls")

    def cfb_today(self):
        return self._espn("cfb")

    def cbb_today(self):
        return self._espn("cbb")

    def wnba_today(self):
        return self._espn("wnba")

    # Soccer
    def epl_today(self):
        return self._espn("epl")

    def ucl_today(self):
        return self._espn("ucl")

    def laliga_today(self):
        return self._espn("laliga")

    def bundes_today(self):
        return self._espn("bundes")

    def seriea_today(self):
        return self._espn("seriea")

    def ligue1_today(self):
        return self._espn("ligue1")

    def worldcup_today(self):
        return self._espn("worldcup")

    def soccer_live(self):
        return self._extract(SPORTS["soccer_live"], GOAL_JS, "soccer_live")

    # Other
    def ufc_today(self):
        return self._espn("ufc")

    def f1_today(self):
        return self._extract(
            SPORTS["f1"], "(function(){return document.body.innerText.slice(0,3000)})()", "f1"
        )

    def tennis_today(self):
        return self._espn("tennis")

    def golf_today(self):
        return self._espn("golf")

    def cricket_today(self):
        return self._espn("cricket")

    def rugby_today(self):
        return self._espn("rugby")

    # --- Sport-agnostic find ---
    def find_game(self, query: str, sports: list = None) -> dict:
        sports = sports or ["nba", "nfl", "nhl", "mlb", "mls", "epl", "worldcup", "soccer_live"]
        q = query.lower()
        for s in sports:
            try:
                data = self._espn(s) if s != "soccer_live" else self.soccer_live()
                for g in data.get("games", []):
                    haystack = f"{g.get('home', '')} {g.get('away', '')} {g.get('home_score', '')} {g.get('away_score', '')} {g.get('score', '')}".lower()
                    if q in haystack:
                        return {"found_in": s, "game": g, "all_today": data}
            except Exception:
                continue
        return {"found_in": None, "error": "no match", "query": query}

    # --- All major US sports at once ---
    def all_us_today(self) -> list:
        out = []
        for s in ["nfl", "nba", "nhl", "mlb", "mls", "wnba", "cfb", "cbb"]:
            with contextlib.suppress(Exception):
                out.append(self._espn(s))
        return out

    def all_soccer_today(self) -> list:
        out = []
        for s in ["epl", "ucl", "laliga", "bundes", "seriea", "ligue1", "worldcup"]:
            with contextlib.suppress(Exception):
                out.append(self._espn(s))
        return out

    def all_today(self) -> dict:
        return {
            "us": self.all_us_today(),
            "soccer": self.all_soccer_today(),
            "soccer_live_any": self.soccer_live(),
        }


# Singleton + convenience
scores = LiveScores()


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: clawplay-live {health|nba|nfl|nhl|mlb|mls|epl|worldcup|soccer_live|f1|ufc|tennis|golf|cricket|all_us|all_soccer|all|find <query>}"
        )
        return
    cmd = sys.argv[1].lower()
    if cmd == "health":
        print(json.dumps(scores.cp.health(), indent=2))
    elif cmd == "soccer_live":
        print(json.dumps(scores.soccer_live(), indent=2))
    elif cmd == "all_us":
        print(json.dumps(scores.all_us_today(), indent=2))
    elif cmd == "all_soccer":
        print(json.dumps(scores.all_soccer_today(), indent=2))
    elif cmd == "all":
        print(json.dumps(scores.all_today(), indent=2))
    elif cmd == "find":
        query = " ".join(sys.argv[2:])
        print(json.dumps(scores.find_game(query), indent=2))
    elif hasattr(scores, cmd + "_today"):
        print(json.dumps(getattr(scores, cmd + "_today")(), indent=2))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
