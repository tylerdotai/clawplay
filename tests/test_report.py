"""Tests for clawplay.report — scoreboard renderer."""

from clawplay.report import (
    BG_PAGE,
    FINAL_GREY,
    LIVE_RED,
    SIGNAL_RED,
    _normalize_game,
    _summary_counts,
    render_css,
    render_report,
    write_report,
)


class TestNormalizeGame:
    def test_basic(self):
        g = _normalize_game(
            {
                "home": "Mexico",
                "away": "Korea",
                "home_score": "1",
                "away_score": "0",
                "status": "FT",
                "sport": "worldcup",
            }
        )
        assert g["is_final"] is True
        assert g["status_label"] == "FINAL"
        assert g["status_color"] == FINAL_GREY
        assert g["home"]["score"] == "1"
        assert g["away"]["name"] == "Korea"

    def test_live_minute_marker(self):
        g = _normalize_game({"home": "A", "away": "B", "status": "77'"})
        assert g["is_live"] is True
        assert g["status_label"] == "LIVE"
        assert g["minute_or_clock"] == "77'"
        assert g["status_color"] == LIVE_RED

    def test_halftime(self):
        g = _normalize_game({"home": "A", "away": "B", "status": "HT"})
        assert g["is_live"] is True
        assert g["minute_or_clock"] == "Half"

    def test_upcoming_renders_local_kickoff(self):
        g = _normalize_game(
            {
                "home": "USA",
                "away": "Mexico",
                "status": "PRE",
                "kickoff": "2026-06-19T03:00:00Z",
            }
        )
        assert g["is_upcoming"] is True
        assert g["status_label"] == "PRE"
        # Should include "·" separator (local format string)
        assert "·" in g["minute_or_clock"]

    def test_quarter_live(self):
        g = _normalize_game({"home": "A", "away": "B", "status": "Q3", "clock": "4:12"})
        assert g["is_live"] is True
        assert g["minute_or_clock"] == "Q3 4:12"

    def test_dict_team_input(self):
        g = _normalize_game(
            {
                "home": {"name": "Lakers", "score": 98},
                "away": {"name": "Celtics", "score": 95},
                "status": "Q4",
            }
        )
        assert g["home"]["name"] == "Lakers"
        assert g["home"]["score"] == 98


class TestSummaryCounts:
    def test_counts(self):
        games = [
            _normalize_game({"home": "A", "away": "B", "status": "FT"}),
            _normalize_game({"home": "A", "away": "B", "status": "FT"}),
            # For live: must include the apostrophe marker so _normalize_game detects it
            _normalize_game({"home": "A", "away": "B", "status": "67'"}),
            _normalize_game(
                {"home": "A", "away": "B", "status": "NS", "kickoff": "2026-06-19T03:00:00Z"}
            ),
        ]
        c = _summary_counts(games)
        assert c["final"] == 2
        assert c["live"] == 1
        assert c["upcoming"] == 1


class TestRenderReport:
    def test_renders_html(self):
        games = [
            {
                "home": "Mexico",
                "away": "Korea",
                "home_score": "1",
                "away_score": "0",
                "status": "FT",
                "sport": "worldcup",
            }
        ]
        html = render_report(games, title="Test", subtitle="Subtitle")
        assert html.startswith("<!DOCTYPE html>")
        assert "Test" in html
        assert "Mexico" in html
        assert "Korea" in html

    def test_includes_clawplay_branding(self):
        games = []
        html = render_report(games, title="Empty")
        assert "Clawplay" in html or "clawplay" in html.lower()
        assert "CT" in html  # Central timezone marker

    def test_includes_design_tokens(self):
        games = [{"home": "A", "away": "B", "status": "FT"}]
        html = render_report(games)
        assert BG_PAGE in html
        assert SIGNAL_RED in html

    def test_includes_pulse_animation(self):
        games = [{"home": "A", "away": "B", "status": "67'"}]
        html = render_report(games)
        assert "pulse" in html or "@keyframes" in html

    def test_includes_hard_offset_shadows(self):
        games = [{"home": "A", "away": "B", "status": "FT"}]
        html = render_report(games)
        assert "box-shadow" in html

    def test_includes_sheet_class_for_print_mode(self):
        games = []
        html = render_report(games, sheet_mode=True)
        assert 'class="sheet"' in html
        assert "8.5in" in html or "@page" in html

    def test_local_timezone_appears(self):
        games = [{"home": "A", "away": "B", "status": "NS", "kickoff": "2026-06-19T03:00:00Z"}]
        html = render_report(games)
        # Should format kickoff in CST/CDT
        assert any(m in html for m in ["Jun", "PM", "AM"])

    def test_group_by_sport(self):
        games = [
            {"home": "A", "away": "B", "status": "FT", "sport": "nba"},
            {"home": "C", "away": "D", "status": "FT", "sport": "nfl"},
        ]
        html = render_report(games, group_by="sport")
        assert "NBA" in html.upper() or "nba" in html
        assert "NFL" in html.upper() or "nfl" in html

    def test_writes_to_file(self, tmp_path):
        games = [{"home": "A", "away": "B", "status": "FT"}]
        out = tmp_path / "test.html"
        path = write_report(games, out)
        assert path == str(out.resolve())
        content = out.read_text()
        assert "<!DOCTYPE html>" in content


class TestRenderCss:
    def test_combines_screen_and_print(self):
        css = render_css()
        # Screen mode
        assert ".container" in css
        assert "max-width" in css
        # Print / handout mode
        assert ".sheet" in css
        assert "@page" in css
        assert "8.5in" in css
        # Design tokens
        assert "--void" in css
        assert "Georgia" in css
        assert "Karla" in css
        assert "JetBrains Mono" in css or "monospace" in css
