<!-- Improved compatibility compatibility HTML5 doctype. -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>clawplay — Sports Aggregator with Handout-Quality HTML Reports</title>
  </head>
  <body>
    <h1>clawplay</h1>
    <blockquote>
      <p><strong>Sports aggregator with handout-quality HTML reports.</strong></p>
    </blockquote>
    <p><a href="https://github.com/tylerdotai/clawplay/blob/main/LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-blue.svg" /></a>
    <a href="#"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9+-blue.svg" /></a>
    <a href="#"><img alt="Sports 24+" src="https://img.shields.io/badge/sports-24+-blue.svg" /></a>
    <a href=".github/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/badge/CI-passing-blue.svg" /></a>
    <a href="#"><img alt="No API keys" src="https://img.shields.io/badge/API%20keys-not%20required-blue.svg" /></a></p>
    <p><a href="https://github.com/tylerdotai/clawplay">clawplay</a> pulls live scoreboards, match previews, recaps, and live trackers for 24+ sports. Everything renders to self-contained, dark-themed HTML — mobile-first by default, with handout-quality print sheets matching the ClawPlex design system.</p>
    <p>No API keys. No rate limits. No scraping detective work. Just <code>pip install -e .</code> and go.</p>
    <p><img src="examples/preview.png" alt="Preview report — handout-quality dark theme" />
    <em>Pre-game preview — Tale of the Tape, Vegas Lines, Narrative Stack, Injury Report, X-Factors, interactive Fan Poll. 8.5×11&quot; print sheet ready.</em></p>
    <hr />
    <h2>Contents</h2>
    <ul>
      <li><a href="#about">About</a></li>
      <li><a href="#built-with">Built With</a></li>
      <li><a href="#installation">Installation</a></li>
      <li><a href="#usage">Usage</a></li>
      <li><a href="#the-four-report-modes">The Four Report Modes</a></li>
      <li><a href="#screenshots">Screenshots</a></li>
      <li><a href="#roadmap">Roadmap</a></li>
      <li><a href="#contributing">Contributing</a></li>
      <li><a href="#license">License</a></li>
      <li><a href="#acknowledgments">Acknowledgments</a></li>
    </ul>
    <hr />
    <h2>About</h2>
    <p><strong>clawplay</strong> is a sports aggregator with four report modes:</p>
    <ol>
      <li><strong>PRE-GAME PREVIEW</strong> — Tale of the Tape, Vegas lines, narrative stack, injury report with impact scores, positional X-factor matchups, interactive fan poll. <em>Handout-quality print sheet (8.5×11&quot;).</em></li>
      <li><strong>LIVE TRACKER</strong> — Mega-scoreboard, live win-probability bar with sparkline timeline, side-by-side live stats, hot player spotlight, scrolling play-by-play feed with color-coded importance tags. <em>Pulsing neon live indicator.</em></li>
      <li><strong>POST-GAME RECAP</strong> — Final score hero with MVP card, AI-generated &quot;Verdict&quot; summary, interactive box score with team tabs, 3 game-changing moments with win-prob deltas, fan verdict slider. <em>Premium digital magazine layout.</em></li>
      <li><strong>FRANCHISE HUB</strong> — Live league standings with wild-card cutoff, trade &amp; rumor mill (verified/developing/speculation), fantasy waiver targets + lookahead betting lines, social buzz feed, prominent countdown to next game. <em>Midweek digest format.</em></li>
    </ol>
    <p>All four modes are <strong>single-file HTML</strong> with Tailwind CDN, native JavaScript, and realistic mock data — no API keys required. The Python package renders dark-themed, mobile-first scoreboards and pre-game / post-game match reports that aggregate from multiple sources (Goal.com, ESPN, BBC Sport, FMHY, Wikipedia).</p>
    <hr />
    <h2>Built With</h2>
    <ul>
      <li><a href="https://www.python.org/">Python 3.9+</a> — core language</li>
      <li><a href="https://playwright.dev/">Playwright</a> — headless browser via clawplay HTTP client</li>
      <li><a href="https://fastapi.tiangolo.com/">FastAPI</a> — optional: run your own browser service</li>
      <li><a href="https://tailwindcss.com/">Tailwind CSS</a> (CDN) — premium HTML templates</li>
      <li><a href="https://www.goal.com/">Goal.com</a>, <a href="https://www.espn.com/">ESPN</a>, <a href="www.bbc.com/sport">BBC Sport</a>, <a href="https://fmhy.net/">FMHY.net</a>, <a href="https://en.wikipedia.org/">Wikipedia</a> — data sources</li>
      <li><a href="https://pytest.org/">pytest</a> + <a href="https://github.com/astral-sh/ruff">ruff</a> — testing + linting</li>
    </ul>
    <p>The visual design language is the ClawPlex design system — dark, premium, no orange, Georgia display headlines + Karla body + JetBrains Mono labels, hard-offset colored shadows, radial-gradient page backgrounds, mono uppercase tracking labels. Inspired by the Spark Arlington 06/10 meetup handouts.</p>
    <hr />
    <h2>Installation</h2>
    <pre><code class="language-bash">git clone https://github.com/tylerdotai/clawplay.git
cd clawplay
pip install -e .

# Optional dev deps (tests, lint, server)
pip install -e &quot;.[dev]&quot;
</code></pre>
    <p>Set the browser service URL (default <code>http://localhost:9300</code>):</p>
    <pre><code class="language-bash">export CLAWPLAY_URL=&quot;http://localhost:9300&quot;
</code></pre>
    <p>Or run your own — any FastAPI + Playwright service that exposes <code>/health</code>, <code>/eval</code>, <code>/extract</code>, <code>/screenshot</code>.</p>
    <hr />
    <h2>Usage</h2>
    <h3>CLI — live scoreboards</h3>
    <pre><code class="language-bash"># Generate a live scoreboard for any sport
clawplay-report nba --output nba.html
clawplay-report worldcup --output wc.html
clawplay-report all --output today.html --group-by status

# Filter, customize, dump JSON
clawplay-report epl --find &quot;Arsenal&quot; --output arsenal.html --title &quot;Arsenal watch&quot;
clawplay-report nfl --group-by competition --json
</code></pre>
    <h3>CLI — match reports (preview / recap)</h3>
    <pre><code class="language-bash"># Pre-game preview for a specific game
clawplay-match &quot;USA Mexico&quot; --sport worldcup --output usa_mexico_preview.html

# Post-game recap
clawplay-match &quot;Mexico Korea Republic&quot; --sport worldcup --output mexico_korea_recap.html

# Skip live aggregation (faster, less rich)
clawplay-match &quot;USA Mexico&quot; --sport worldcup --no-aggregate --output preview_static.html
</code></pre>
    <h3>CLI — raw JSON to stdout</h3>
    <pre><code class="language-bash">clawplay-live nba           # all NBA games today, JSON
clawplay-live soccer_live   # all live soccer matches globally
clawplay-live all           # everything
clawplay-live find &quot;Lakers&quot;   # find a specific team
</code></pre>
    <h3>Python library</h3>
    <pre><code class="language-python">import clawplay

# Live scoreboards
nba = clawplay.scores.nba_today()
print(f&quot;{nba['count']} NBA games today&quot;)
clawplay.write_report(nba['games'], 'nba.html', title='NBA — Tonight')

# Find a specific game
result = clawplay.scores.find_game('Lakers')
if result['found_in']:
    print(f&quot;Found in {result['found_in']}: {result['game']}&quot;)

# Match reports with multi-source aggregation
from clawplay import MatchReport, Aggregator, write_match_report

match = MatchReport(
    'worldcup', 'USA', 'Mexico',
    kickoff='2026-06-21T20:00:00-05:00',
    status='SCHEDULED',
    competition='FIFA World Cup 2026',
    venue='SoFi Stadium, Inglewood',
)
Aggregator().aggregate_match(match)   # pulls from ESPN + BBC + FMHY + Wikipedia
write_match_report(match, 'usa_mexico.html')
</code></pre>
    <h3>Local timezone</h3>
    <p>All times render in <strong>CST/CDT (America/Chicago)</strong> by default. Override via env var:</p>
    <pre><code class="language-bash">export CLAWPLAY_TZ=&quot;America/New_York&quot;
</code></pre>
    <hr />
    <h2>The Four Report Modes</h2>
    <p>Located under <code>templates/</code>. Each is a single self-contained HTML file with Tailwind CDN + native JS. Open in any browser.</p>
    <table>
      <thead>
        <tr>
          <th>Mode</th>
          <th>File</th>
          <th>Use case</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>PREVIEW</strong></td>
          <td><a href="templates/preview.html"><code>preview.html</code></a></td>
          <td>Pre-game hype sheet · Tale of the Tape · Vegas odds · Fan poll</td>
        </tr>
        <tr>
          <td><strong>LIVE</strong></td>
          <td><a href="templates/live.html"><code>live.html</code></a></td>
          <td>Live tracker · Score · Win probability · Play-by-play</td>
        </tr>
        <tr>
          <td><strong>RECAP</strong></td>
          <td><a href="templates/recap.html"><code>recap.html</code></a></td>
          <td>Post-game analytics · MVP · Box score · Fan verdict</td>
        </tr>
        <tr>
          <td><strong>HUB</strong></td>
          <td><a href="templates/hub.html"><code>hub.html</code></a></td>
          <td>Midweek digest · Standings · Rumors · Fantasy · Countdown</td>
        </tr>
      </tbody>
    </table>
    <p>Open any of them locally — no build step:</p>
    <pre><code class="language-bash">open templates/preview.html   # macOS
</code></pre>
    <hr />
    <h2>Screenshots</h2>
    <h3>Pre-game preview</h3>
    <p><img src="examples/preview.png" alt="Preview report — handout-quality dark theme" />
    <em>Pre-game preview — Tale of the Tape, Vegas Lines, Narrative Stack, Injury Report, X-Factors, interactive Fan Poll. 8.5×11&quot; print sheet ready.</em></p>
    <h3>Live tracker</h3>
    <p><img src="examples/live.png" alt="Live tracker — pulsing mega-scoreboard, WP bars, play-by-play" />
    <em>Live tracker — pulsing mega-scoreboard, win-probability bars + sparkline, hot-player spotlight, color-tagged play-by-play feed.</em></p>
    <h3>Post-game recap</h3>
    <p><img src="examples/recap.png" alt="Post-game recap — MVP hero, AI verdict, box score, turning points" />
    <em>Post-game recap — MVP hero card, AI-generated Verdict, tabbed box score, 3 turning points with win-probability deltas, Fan Verdict sliders.</em></p>
    <h3>Franchise hub</h3>
    <p><img src="examples/hub.png" alt="Franchise hub — standings, rumor mill, fantasy, countdown" />
    <em>Franchise hub — NFC East standings, trade &amp; rumor mill (verified / developing / speculation), fantasy + lookahead betting lines, social buzz feed, prominent countdown.</em></p>
    <hr />
    <h2>Roadmap</h2>
    <ul>
      <li><input checked="" disabled="" type="checkbox" /> Multi-source aggregator (Goal.com + ESPN + BBC + FMHY + Wikipedia)</li>
      <li><input checked="" disabled="" type="checkbox" /> Handout-quality match reports (8.5×11 print sheet)</li>
      <li><input checked="" disabled="" type="checkbox" /> Four report templates (Preview · Live · Recap · Hub)</li>
      <li><input checked="" disabled="" type="checkbox" /> CST/DFW timezone formatting throughout</li>
      <li><input checked="" disabled="" type="checkbox" /> pytest TDD · ruff lint · GitHub Actions CI</li>
      <li><input checked="" disabled="" type="checkbox" /> MIT license, public on GitHub</li>
      <li><input disabled="" type="checkbox" /> Live data wired into all 4 HTML templates (currently mock)</li>
      <li><input disabled="" type="checkbox" /> Configurable team colors (currently ClawPlex palette)</li>
      <li><input disabled="" type="checkbox" /> Tailwind build pipeline (currently CDN)</li>
      <li><input disabled="" type="checkbox" /> Interactive SVG play diagrams (NFL)</li>
      <li><input disabled="" type="checkbox" /> xG-style charts for soccer</li>
      <li><input disabled="" type="checkbox" /> Push to Discord / iMessage / SMS</li>
      <li><input disabled="" type="checkbox" /> NFL play-by-play via ESPN API reverse-engineered</li>
      <li><input disabled="" type="checkbox" /> Self-hosted web UI (Flask/FastAPI)</li>
      <li><input disabled="" type="checkbox" /> Fantasy sync (Sleeper, Yahoo, ESPN)</li>
    </ul>
    <p>See <a href="https://github.com/tylerdotai/clawplay/issues">open issues</a> for the full backlog.</p>
    <hr />
    <h2>Contributing</h2>
    <p>PRs welcome. The flow:</p>
    <ol>
      <li>Fork &amp; branch from <code>main</code></li>
      <li><code>pip install -e &quot;.[dev]&quot;</code></li>
      <li>Add tests under <code>tests/</code></li>
      <li><code>pytest</code> · <code>ruff check src/ tests/</code></li>
      <li>Submit a PR — CI runs on every push</li>
    </ol>
    <p>For new sports:</p>
    <ol>
      <li>Find the official scoreboard URL</li>
      <li>Open it in Chrome, inspect the live-widget DOM</li>
      <li>Write a JS extraction pattern (see existing sports in <code>src/clawplay/live_scores.py</code>)</li>
      <li>Add to <code>SPORTS</code> and a <code>&lt;sport&gt;_today()</code> method to <code>LiveScores</code></li>
      <li>Add tests with mock <code>Clawplay</code></li>
    </ol>
    <p>For new templates, model the structure off <code>templates/preview.html</code> — Georgia display + mono labels + hard-offset colored shadows + radial-gradient bg are non-negotiable design tokens.</p>
    <hr />
    <h2>License</h2>
    <p>Distributed under the MIT License. See <a href="LICENSE">LICENSE</a> for the full text.</p>
    <hr />
    <h2>Acknowledgments</h2>
    <ul>
      <li><a href="https://playwright.dev/">Playwright</a> — headless browser engine</li>
      <li><a href="https://www.espn.com/">ESPN</a>, <a href="https://www.goal.com/">Goal.com</a>, <a href="https://www.bbc.com/sport">BBC Sport</a>, <a href="https://fmhy.net/">FMHY.net</a>, <a href="https://en.wikipedia.org/">Wikipedia</a> — data sources</li>
      <li><a href="https://github.com/othneildrew/Best-README-Template">othneildrew's Best-README-Template</a> — README structure</li>
      <li><a href="https://github.com/tylerdotai/clawplex">ClawPlex design system</a> — visual language (dark, premium, no orange)</li>
      <li>Spark Coworking · Arlington TX — June 10 meetup · inspiration for handout typography</li>
      <li>Built for sports fans who want their scores on their terms</li>
    </ul>
    <hr />
    <p align="center"><a href="https://github.com/tylerdotai/clawplay">github.com/tylerdotai/clawplay</a></p>
  </body>
</html>
