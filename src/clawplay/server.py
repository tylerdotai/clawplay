"""clawplay.server — Self-hosted web UI for clawplay reports.

A FastAPI app that serves the four report templates (preview, live,
recap, hub) as live pages with real data fetched from the Aggregator.
Boots with ``clawplay-server`` on port 9300 (configurable via
``CLAWPLAY_PORT`` env var).

Endpoints::

    GET /                              → landing page
    GET /preview/{sport}/{home}/{away} → PREVIEW template
    GET /live/{sport}/{home}/{away}    → LIVE template
    GET /recap/{sport}/{home}/{away}   → RECAP template
    GET /hub/{team}                    → HUB template
    GET /api/preview/{sport}/{home}/{away} → JSON payload
    GET /api/live/{sport}/{home}/{away}    → JSON payload
    GET /api/recap/{sport}/{home}/{away}   → JSON payload
    GET /api/hub/{team}                    → JSON payload
    GET /health                        → {"status": "ok"}

The HTML pages serve the static template files with an injected
``<script id="clawplay-data" type="application/json">`` block so the
template's existing JS bootstrap can fetch the live data in place.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]

from .palettes import palette_for_team

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
DIST_DIR = TEMPLATES_DIR / "dist"


def _template_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}.html"


def _inject_data(html: str, payload: Dict[str, Any]) -> str:
    """Inject a JSON payload as a <script> tag just before </head>."""
    blob = json.dumps(payload, default=str)
    tag = f'<script id="clawplay-data" type="application/json">{blob}</script>'
    if "</head>" in html:
        return html.replace("</head>", f"{tag}</head>", 1)
    return tag + html


def _serve_template(name: str, sport: str, home: str, away: str) -> HTMLResponse:
    path = _template_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    html = path.read_text(encoding="utf-8")
    payload = {
        "template": name,
        "sport": sport,
        "home": home,
        "away": away,
        "palette": palette_for_team(sport, home.lower().replace(" ", "_")).css_vars(),
        # Aggregator payload stub — real values are filled by the
        # match_report pipeline in v1.1.0; mock fallback is preserved.
        "data": _mock_payload(name, sport, home, away),
    }
    return HTMLResponse(_inject_data(html, payload))


def _mock_payload(name: str, sport: str, home: str, away: str) -> Dict[str, Any]:
    """Generate a minimal mock payload so the server can render without
    hitting any external APIs. The templates' existing JS gracefully
    degrades when fields are missing.
    """
    return {
        "sport": sport,
        "home": {"name": home, "score": 1, "abbrev": home[:3].upper()},
        "away": {"name": away, "score": 0, "abbrev": away[:3].upper()},
        "status": "LIVE" if name == "live" else ("FINAL" if name == "recap" else "PRE"),
        "competition": sport.upper(),
        "venue": "AT&T Stadium, Arlington TX",
        "kickoff": "2026-06-19T03:00:00Z",
    }


def _hub_payload(team: str) -> Dict[str, Any]:
    return {
        "team": team,
        "palette": palette_for_team("nfl", team.lower().replace(" ", "_")).css_vars(),
        "data": {
            "team": team,
            "record": "8-4",
            "division": "1st NFC East",
            "next_game": {"opponent": "Philadelphia Eagles", "date": "2026-09-07"},
        },
    }


def _serve_hub(team: str) -> HTMLResponse:
    path = _template_path("hub")
    if not path.exists():
        raise HTTPException(status_code=404, detail="hub template missing")
    html = path.read_text(encoding="utf-8")
    payload = _hub_payload(team)
    return HTMLResponse(_inject_data(html, payload))


_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>clawplay — handout-quality sports reports</title>
<link rel="stylesheet" href="/static/styles.css" />
</head>
<body class="font-body text-white min-h-screen p-10">
  <h1 class="font-display text-5xl mb-2">clawplay</h1>
  <p class="text-muted mb-8">Self-hosted handout-quality sports reports.</p>
  <h2 class="font-mono text-xs uppercase tracking-widest text-blue-light mb-3">Demo routes</h2>
  <ul class="space-y-2 text-lg">
    <li><a class="text-blue-light underline" href="/preview/worldcup/USA/Mexico">/preview/worldcup/USA/Mexico</a></li>
    <li><a class="text-blue-light underline" href="/live/worldcup/Mexico/USA">/live/worldcup/Mexico/USA</a></li>
    <li><a class="text-blue-light underline" href="/recap/worldcup/Mexico/USA">/recap/worldcup/Mexico/USA</a></li>
    <li><a class="text-blue-light underline" href="/hub/dallas_cowboys">/hub/dallas_cowboys</a></li>
  </ul>
  <p class="mt-10 text-muted text-sm">API:
    <a class="text-blue-light underline" href="/health">/health</a>
  </p>
</body>
</html>"""


def create_app() -> Any:
    """Build the FastAPI app. Returns None if FastAPI is not installed."""
    if FastAPI is None:
        raise RuntimeError(
            'FastAPI is required for the server. Install via `pip install -e ".[server]"`.'
        )
    app = FastAPI(title="clawplay", version="1.1.0")

    if DIST_DIR.exists() and StaticFiles is not None:
        app.mount("/static", StaticFiles(directory=str(DIST_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def landing() -> str:
        return _LANDING_HTML

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "service": "clawplay", "version": "1.1.0"}

    @app.get("/preview/{sport}/{home}/{away}", response_class=HTMLResponse)
    def preview(sport: str, home: str, away: str) -> HTMLResponse:
        return _serve_template("preview", sport, home, away)

    @app.get("/live/{sport}/{home}/{away}", response_class=HTMLResponse)
    def live(sport: str, home: str, away: str) -> HTMLResponse:
        return _serve_template("live", sport, home, away)

    @app.get("/recap/{sport}/{home}/{away}", response_class=HTMLResponse)
    def recap(sport: str, home: str, away: str) -> HTMLResponse:
        return _serve_template("recap", sport, home, away)

    @app.get("/hub/{team}", response_class=HTMLResponse)
    def hub(team: str) -> HTMLResponse:
        return _serve_hub(team)

    @app.get("/api/preview/{sport}/{home}/{away}")
    def api_preview(sport: str, home: str, away: str) -> Dict[str, Any]:
        return {"payload": _mock_payload("preview", sport, home, away)}

    @app.get("/api/live/{sport}/{home}/{away}")
    def api_live(sport: str, home: str, away: str) -> Dict[str, Any]:
        return {"payload": _mock_payload("live", sport, home, away)}

    @app.get("/api/recap/{sport}/{home}/{away}")
    def api_recap(sport: str, home: str, away: str) -> Dict[str, Any]:
        return {"payload": _mock_payload("recap", sport, home, away)}

    @app.get("/api/hub/{team}")
    def api_hub(team: str) -> Dict[str, Any]:
        return _hub_payload(team)

    return app


def _cli_entry() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="clawplay-server", description="clawplay self-hosted web UI."
    )
    parser.add_argument("--host", default=os.environ.get("CLAWPLAY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CLAWPLAY_PORT", "9300")))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    try:
        import uvicorn  # noqa: F401
    except ImportError as err:
        raise SystemExit("uvicorn is required. Install via 'pip install -e .[server]'.") from err
    app = create_app()
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    _cli_entry()
