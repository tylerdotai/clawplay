---
master_prompt: clawplay v1.1 — Complete the Roadmap
version: 1.1.0
created: 2026-06-19
owner: Tyler Delano (tylerdotai)
status: ACTIVE — execution in progress
---

# Clawplay v1.1 — Complete the Roadmap Master Prompt

> **For any AI agent or human taking over this build:** this is the
> authoritative starting point. It defines the goal, scope, constraints,
> procedure, and definition of done. **Read this entire file before
> touching anything.** No scope expansion. No improvising. Follow the
> procedure. Ship the definition of done.

---

## 0. Identity — Who You Are And What You're Shipping

You are the build agent for **clawplay v1.1.0**, the second major release
of a sports aggregator that produces handout-quality HTML reports
(pre-game previews, live trackers, post-game recaps, franchise hubs) for
20+ sports, dark-themed, print-ready, with zero API-key requirements.

This release closes the v1.0.0 roadmap. Every checked roadmap item
becomes a real shipped feature in v1.1.0. The repo lives at
**github.com/tylerdotai/clawplay** (public, MIT, Python 3.9+, tested on
3.10 / 3.11 / 3.12 via GitHub Actions).

The visual design system is the **ClawPlex** DNA — Georgia serif display
headlines, Karla body, JetBrains Mono uppercase tracking labels, radial-
gradient page backgrounds, hard-offset colored shadows (5–7px), no
orange anywhere (digital/print/video/wardrobe/props).

---

## 1. Scope — Exactly What To Ship

The roadmap has 16 items. **Ship all of them except push notifications.**
Push notifications (Discord/iMessage/SMS) are explicitly excluded by the
user.

### 1.1 Functional features (must work end-to-end)

1. **Live data wired into all 4 HTML templates.** Templates currently
   hardcode realistic mock data. v1.1.0 must replace the JSON-shaped
   data blocks with data delivered by the existing `Aggregator`
   pipeline (`src/clawplay/match_report.py`). Each template gets a
   small JS bootstrap that fetches `/api/templates/{name}/{sport}?home=X&away=Y`
   and re-renders the relevant sections. Mock data remains as the
   fallback when the API is unreachable or the sport has no live game.

2. **Configurable team colors.** Team palettes (USA = blue/red, Mexico =
   green/white, Cowboys = silver/navy, Lakers = purple/gold, etc.) come
   from a config layer (`src/clawplay/palettes.py`) backed by per-sport
   `templates/designs/*.md` frontmatter and a small `TEAMS` registry.
   The CSS custom-property block in each template reads from this layer
   instead of being baked into the `<style>` tag.

3. **Tailwind build pipeline.** Replace `<script src="https://cdn.tailwindcss.com">`
   with a compiled `templates/dist/styles.css` produced by Tailwind CLI
   during build. Templates keep working offline. The build is invoked
   via `clawplay-build-assets` (new CLI entry point) and runs as a
   pre-commit + CI step.

4. **Self-hosted web UI.** A FastAPI app under `src/clawplay/server.py`
   serves the templates as live pages:
   - `GET /` — landing page with sport picker + demo links
   - `GET /preview/{sport}/{home}/{away}` — live preview
   - `GET /live/{sport}/{home}/{away}` — live tracker
   - `GET /recap/{sport}/{home}/{away}` — post-game recap
   - `GET /hub/{team}` — franchise hub
   - `GET /api/{anything}` — JSON API mirroring the templates' data
   - `GET /health` — liveness
   Boots with `clawplay-server` (new CLI entry point, port 9300).

5. **xG chart for soccer.** Animated line chart of cumulative
   expected-goal differential over time, rendered as inline SVG. Pulls
   data from `Aggregator.xg_timeline(match)`. Used in PREVIEW (pre-game
   recent form) and RECAP (in-game shift). Backed by mock generator if
   no live xG data is available.

6. **SVG play diagrams for NFL.** Horizontal field diagram (110-yard
   yard-line grid) showing drive progress with play markers
   (run = triangle, pass = arrow, score = star). Used in RECAP's
   "Turning Points" section. Backed by `Aggregator.nfl_drive(game_id)`.

7. **NFL ESPN play-by-play extractor.** Reverse-engineer
   `site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={id}`
   to pull structured play-by-play for any NFL game. Add
   `Aggregator.nfl_play_by_play(game_id)` method. Falls back to mock
   play-by-play when API is unreachable or rate-limited. No API key
   required.

8. **Fantasy sync (Sleeper).** Public, unauthenticated Sleeper API
   (`api.sleeper.app/v1/players/nfl`) integration. Add
   `Aggregator.fantasy_players(platform='sleeper', sport='nfl')`. Cache
   to `~/.cache/clawplay/sleeper_players.json` with 24h TTL. Used in
   HUB's "Fantasy Waiver Targets" section.

### 1.2 Repo + docs features (must be in the final commit)

9. **Demo clips.** 4 short demonstration videos (~10–25s each) embedded
   in the README showing each of the four modes. Produced via headless
   Chromium navigation + Playwright + ffmpeg composition. Stored under
   `examples/clips/` and linked from README. Open-source production
   stack: Playwright + ffmpeg. No proprietary tools.

10. **README v1.1.0.** Full rewrite:
    - Hero: animated GIF or first-frame of preview demo clip (auto-loop)
    - 4 demo clips embedded under Screenshots section (one per mode)
    - "What's new in v1.1.0" section listing the shipped features
    - Updated Roadmap (the 8 done items checked, the 7 remaining moved
      to v1.2.0)
    - Updated About, Usage, and Contributing sections to reflect the
      web UI and asset pipeline
    - Production-quality screenshot integration using the verified
      PNGs in `examples/`

---

## 2. Non-Negotiable Constraints

### 2.1 Hard bans

- **No API keys anywhere.** No third-party paid APIs, no SerpAPI,
  no SportsDataIO, no Odds API. Sleeper and ESPN's public unauthenticated
  endpoints are fine.
- **No proprietary tooling for demo clips.** ffmpeg + Playwright only.
  No Camtasia, no ScreenFlow, no Descript.
- **No orange** in any output. Re-check palettes before committing.
- **No HTML scaffolding in the README.** Pure Markdown only (badges and
  centered `<p>` blocks for layout are the only allowed HTML).
- **No push notifications.** Discord / iMessage / SMS is out of scope.
- **No breaking changes to the v1.0.0 public API.** The Python package
  `import clawplay; clawplay.scores.nba_today()` still works exactly
  the same way.

### 2.2 Engineering standards

- **Python 3.9+ compatibility.** No `X | Y` syntax in type hints
  (use `Optional[X]` and `Union[X, Y]`). No match statements.
- **Type hints on every public function.** Internal helpers may be
  untyped.
- **Tests for every new feature.** pytest TDD. Aim for 100+ tests by
  v1.1.0.
- **ruff check + ruff format both pass.** No lint warnings, no format
  drift.
- **Single clean commit per logical feature**, or one squash commit at
  the end if features land atomically. The user prefers a tidy linear
  history — don't pile up 20 micro-commits.

### 2.3 Visual standards

- All templates must continue to render cleanly at 1440×900 desktop
  AND 816×1056 print sheet.
- All hero regions must have a single clear title hierarchy (no
  double-title, no overlap).
- All 22 sport palettes live in `templates/designs/{sport}.md` and are
  loaded dynamically. They don't share a colorway.
- Demo clips must be loopable (start-to-end matches end-to-start) and
  under 5MB each for fast GitHub README rendering.

---

## 3. Execution Procedure

Follow this sequence. **Do not skip steps. Do not reorder.**

### Step 1 — Master prompt + todos

Write this file (already done). Build the 12-item todo list. Mark
step 1 complete.

### Step 2 — Tailwind build pipeline

- Add `tailwindcss` (Node CLI) as a dev dependency via npm.
- Create `tailwind.config.js` reading from `templates/**/*.html` and
  `templates/dist/input.css` (input that includes the Tailwind
  directives).
- Add `npm run build:css` script that emits `templates/dist/styles.css`.
- Add `clawplay-build-assets` CLI entry point in `src/clawplay/assets.py`
  that shells out to the npm build (fallback: download standalone
  Tailwind CLI binary if Node isn't installed).
- Replace `<script src="https://cdn.tailwindcss.com"></script>` in all
  4 templates with `<link rel="stylesheet" href="dist/styles.css">`.
  For the templates to also work as standalone files when opened
  locally, add an inline `<style>` block fallback that contains the
  compiled utility classes for the offline case (or generate one HTML
  file per template via a `clawplay-bundle <name>` CLI).
- Add tests in `tests/test_assets.py` that verify the build emits a
  CSS file with the expected selectors.
- Run `ruff check` and `ruff format`. Confirm 60+ tests pass.

### Step 3 — Configurable team colors

- Add `src/clawplay/palettes.py` with a `Palette` dataclass
  (primary, secondary, accent, surface, text) and a `TEAMS` dict
  keyed by `(sport, team_slug)`.
- Add `palettes_from_design(sport: str)` that parses the YAML-ish
  frontmatter block at the top of `templates/designs/{sport}.md`.
- Update each template's `<style>` block to use CSS custom properties
  (`var(--team-primary)`) populated by a small JS bootstrap that
  reads the team's palette from the page's URL params or `<meta>`.
- Document the override mechanism in `README.md` so users can add
  custom teams.

### Step 4 — Self-hosted web UI

- Create `src/clawplay/server.py` with a FastAPI app:
  - `GET /` — HTML landing page (link to demo routes)
  - `GET /preview/{sport}/{home}/{away}` — serve preview.html with data
  - `GET /live/{sport}/{home}/{away}` — same for live.html
  - `GET /recap/{sport}/{home}/{away}` — same for recap.html
  - `GET /hub/{team}` — same for hub.html
  - `GET /api/preview/{sport}/{home}/{away}` — JSON payload
  - `GET /api/live/{sport}/{home}/{away}` — JSON payload
  - `GET /api/recap/{sport}/{home}/{away}` — JSON payload
  - `GET /api/hub/{team}` — JSON payload
  - `GET /health` — JSON `{status: 'ok'}`
- Wire `clawplay-server` as a CLI entry point on port 9300.
- Add `tests/test_server.py` with httpx-based tests.
- Confirm `pip install -e ".[server]"` boots the server and the demo
  routes render the templates with realistic data.

### Step 5 — Live data wiring

- Add a small JS bootstrap to each template that:
  1. Reads sport + teams from URL params or `<meta>` tags.
  2. Fetches `/api/{template}/{sport}/{home}/{away}`.
  3. Falls back to the embedded mock data block on network failure.
  4. Replaces the relevant sections in place (no full page reload).
- Update the Python aggregator (`match_report.py`) to expose
  `to_preview_data(match)`, `to_live_data(match)`, `to_recap_data(match)`,
  `to_hub_data(team)` methods that emit the JSON shapes each template
  expects.
- Add `tests/test_template_data.py` verifying each serializer produces
  a valid payload that matches the template's expected schema.

### Step 6 — xG chart

- Implement `xg_timeline(match)` in `Aggregator` — pulls cumulative xG
  per minute from underlying data sources, falls back to a procedural
  generator with realistic spikes around goals.
- Add a self-contained SVG chart component under
  `src/clawplay/charts/xg.py` that renders an inline `<svg>` with
  two colored lines (home/away), filled areas, and goal markers.
- Wire it into PREVIEW (recent form: last 5 matches xG) and RECAP
  (in-game xG timeline). Embed the rendered SVG via Jinja2 string
  substitution in the aggregator's serializer.

### Step 7 — SVG play diagrams for NFL

- Implement `nfl_drive(game_id)` returning a list of plays
  (yard_line_start, yard_line_end, play_type, yards_gained, score_flag).
- Add `src/clawplay/charts/drive.py` that renders an inline SVG:
  - 110-yard field with 10-yard line markers
  - Drive progression as a polyline from start to current yard
  - Play markers (run = triangle, pass = arrow, score = star) at each
    yard line
- Wire into RECAP's "Turning Points" section (3 biggest plays).

### Step 8 — NFL ESPN play-by-play

- Implement `Aggregator.nfl_play_by_play(game_id)`.
- Hit `https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={id}`
  with a 10s timeout and a polite `User-Agent`.
- Parse the `drives` -> `plays` JSON tree, mapping to the internal
  schema. Fall back to `MockNFLPlayByPlay.play(game_id)` on any error.
- Cache successful responses to `~/.cache/clawplay/nfl_pbp/{id}.json`
  with 24h TTL.
- Add tests with mocked HTTP responses.

### Step 9 — Sleeper fantasy sync

- Implement `Aggregator.fantasy_players(platform='sleeper', sport='nfl')`.
- Hit `https://api.sleeper.app/v1/players/nfl` (public, ~5MB, no auth).
- Cache to `~/.cache/clawplay/sleeper_players.json` with 24h TTL.
- Filter by sport/position, expose `top_waiver_targets(position, count)`.
- Wire into HUB's "Fantasy Waiver Targets" section.
- Add tests with mocked HTTP responses.

### Step 10 — Demo clips

- Create `scripts/render_demo_clips.py` using Playwright + ffmpeg.
- For each template, launch headless Chromium at 1440×900, navigate
  to the live URL, scroll through the page in timed segments, capture
  each segment as a PNG, then stitch into a 10–25s MP4 with ffmpeg's
  `image2` demuxer + libx264 encoder at 30fps.
- Embed each clip in the README via:
  `<img src="examples/clips/{name}.gif" alt="..." width="800">` (or
  MP4 via `<video autoplay loop muted playsinline>`).
- Verify all 4 clips are under 5MB and visually correct.

### Step 11 — README polish

- Rewrite `README.md` with the v1.1.0 feature set.
- Hero: animated GIF from the preview clip (loop, autoplay).
- "What's new in v1.1.0" callout block at the top.
- 4 demo clips under Screenshots section.
- Updated Roadmap (8 done, 7 deferred to v1.2.0).
- Updated About, Usage, Contributing sections.
- Verify with `curl https://raw.githubusercontent.com/.../README.md | grep -E "<title|<!DOCTYPE"` returning zero matches.

### Step 12 — Final verification + ship

- Run `uv run pytest tests/ -q` — confirm 100+ tests pass.
- Run `uv run ruff check src/ tests/` — clean.
- Run `uv run ruff format --check src/ tests/` — clean.
- Run `scripts/render_screenshots.py` and `scripts/render_demo_clips.py`
  — all artifacts present and under size limit.
- Commit with message
  `feat(v1.1.0): complete the roadmap — Tailwind build, team palettes, web UI, live data, xG charts, NFL play diagrams, Sleeper sync, demo clips`
- Push to `main`, wait for CI green on all 3 Python versions.
- Visually verify the README on github.com via the GitHub Markdown
  rendering API.

---

## 4. Definition of Done — Ship When ALL True

- [ ] `uv run pytest tests/ -q` returns **100+ passing tests**, 0 failures.
- [ ] `uv run ruff check src/ tests/` returns **All checks passed!**.
- [ ] `uv run ruff format --check src/ tests/` returns **clean**.
- [ ] `pip install -e ".[dev,server]"` completes without error.
- [ ] `clawplay-server` boots and `curl http://localhost:9300/health`
      returns `{"status":"ok"}`.
- [ ] `clawplay-build-assets` produces `templates/dist/styles.css`
      with the expected Tailwind classes.
- [ ] All 4 templates render at 1440×900 desktop AND 816×1056 print
      with no overlap, no double-title, correct visual hierarchy.
- [ ] All 4 demo clips exist, are < 5MB, and visually demonstrate
      the corresponding template mode.
- [ ] README on github.com has no raw HTML scaffolding (`<title>`,
      `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` all absent).
- [ ] All 22 per-sport design.md files remain in `templates/designs/`
      with no shared colorway.
- [ ] GitHub Actions CI is green on Python 3.10 / 3.11 / 3.12.
- [ ] The `clawplay` package on PyPI / GitHub has version `1.1.0`.

---

## 5. Out Of Scope (Explicitly)

- Push notifications to Discord / iMessage / SMS / email.
- Tailwind UI component library adoption (we hand-roll every component).
- Real-time WebSocket scoreboard updates (current polling is sufficient).
- User accounts, auth, saved preferences.
- Mobile native apps.
- Internationalization beyond English.
- Paid API integrations (no SportsDataIO, no Odds API, etc.).

---

## 6. Escalation Rules

If you hit a decision that isn't covered here:
1. Default to the **minimal change** that ships the feature.
2. Don't introduce a new dependency without a strong reason.
3. If you must diverge from this prompt, log the divergence in a
   "BUILD_NOTES.md" entry at the repo root so the user can review.
4. Never break the v1.0.0 public API surface.
5. Never mark an item done without verifying it (test, screenshot, or
   live curl response).

---

## 7. The User — Tyler Delano

- **Channel:** iMessage DM (this conversation). Discord for non-DM.
- **Communication style:** Casual, no corporate speak. Concise. Quick
  to hand off a new mission when context shifts.
- **Timezone:** CST/CDT (America/Chicago).
- **Decision-making:** Hands off quickly after greenlighting. Doesn't
  want to be re-asked "are you sure?" once he's said "go" or "build it".
- **Aesthetic bar:** Spark Coworking Arlington 06/10 meetup handouts.
  Handout-quality, magazine-quality, premium dark theme.

---

**End of master prompt. Begin execution from Step 2 (Tailwind build
pipeline) — Step 1 (this file) is complete.**
