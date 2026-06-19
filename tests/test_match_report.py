"""Tests for clawplay.match_report — match preview/recap generator."""

from unittest.mock import MagicMock

from clawplay.match_report import (
    SOURCE_URLS,
    Aggregator,
    MatchReport,
    extract_rich_content,
    find_match,
    render_match_report,
    write_match_report,
)


class TestMatchReport:
    def test_preview_status_detection(self):
        m = MatchReport("worldcup", "USA", "Mexico", status="PRE")
        assert m.is_preview is True
        assert m.is_final is False
        assert m.is_live is False
        assert m.match_type == "preview"

    def test_final_status_detection(self):
        for status in ["FT", "FINAL", "AET", "AP", "AFTER_OT"]:
            m = MatchReport("worldcup", "USA", "Mexico", status=status)
            assert m.is_final is True, status
            assert m.match_type == "recap", status

    def test_live_status_default(self):
        m = MatchReport("worldcup", "USA", "Mexico", status="1H")
        assert m.is_live is True
        assert m.match_type == "live"

    def test_to_dict(self):
        m = MatchReport("worldcup", "USA", "Mexico", kickoff="2026-06-19T03:00:00Z", status="PRE")
        d = m.to_dict()
        assert d["home"] == "USA"
        assert d["away"] == "Mexico"
        assert d["sport"] == "worldcup"
        assert d["match_type"] == "preview"
        assert d["sources"] == []

    def test_add_source_dedupes_notes(self):
        m = MatchReport("worldcup", "USA", "Mexico")
        m.add_note("test")
        m.add_note("test")
        m.add_note("test2")
        assert m.notes == ["test", "test2"]


class TestFindMatch:
    def test_finds_by_team(self):
        games = [
            {"home": "USA", "away": "Mexico", "sport": "worldcup", "status": "PRE"},
            {"home": "Brazil", "away": "Argentina", "sport": "worldcup", "status": "PRE"},
        ]
        match = find_match(games, "Mexico")
        assert match is not None
        assert match.away == "Mexico"

    def test_finds_by_competition(self):
        games = [
            {"home": "A", "away": "B", "competition": "World Cup Group Stage", "status": "PRE"},
        ]
        match = find_match(games, "World Cup")
        assert match is not None

    def test_no_match(self):
        games = [{"home": "A", "away": "B"}]
        result = find_match(games, "Zzzzz")
        assert result is None

    def test_propagates_sport_and_kickoff(self):
        games = [
            {
                "home": "USA",
                "away": "Mexico",
                "sport": "worldcup",
                "status": "PRE",
                "kickoff": "2026-06-19T03:00:00Z",
                "competition": "FIFA World Cup 2026",
                "venue": "SoFi Stadium",
            }
        ]
        m = find_match(games, "Mexico")
        assert m is not None
        assert m.sport == "worldcup"
        assert m.kickoff == "2026-06-19T03:00:00Z"
        assert m.competition == "FIFA World Cup 2026"
        assert m.venue == "SoFi Stadium"


class TestExtractRichContent:
    def test_fmhy_links(self):
        sources = [
            {
                "name": "fmhy",
                "url": "https://fmhy.net/video",
                "data": {"links": [{"text": "Cineby", "href": "https://cineby.app"}]},
            }
        ]
        out = extract_rich_content(sources)
        assert len(out["where_to_watch_links"]) == 1
        assert out["where_to_watch_links"][0]["text"] == "Cineby"

    def test_primary_structured(self):
        sources = [
            {
                "name": "primary",
                "url": "https://example.com",
                "data": [{"raw": "USA vs Mexico preview context"}],
            }
        ]
        out = extract_rich_content(sources)
        assert any("preview context" in s for s in out["form"])

    def test_empty_sources(self):
        assert extract_rich_content([])["form"] == []


class TestAggregator:
    def test_aggregates_from_mock_clawplay(self):
        mock_cp = MagicMock()
        mock_cp.eval.return_value = {
            "ok": True,
            "content": '[{"raw": "USA vs Mexico context", "numbers": []}]',
        }
        agg = Aggregator(clawplay=mock_cp)
        m = MatchReport("worldcup", "USA", "Mexico", status="PRE")
        agg.aggregate_match(m)
        assert len(m.sources) >= 1
        assert "aggregated_at" in m.metadata
        # Should have tried primary
        assert any(s["name"] == "primary" for s in m.sources)

    def test_aggregator_records_failure_notes(self):
        mock_cp = MagicMock()
        mock_cp.eval.return_value = {"ok": False, "error": "timeout"}
        agg = Aggregator(clawplay=mock_cp)
        m = MatchReport("worldcup", "USA", "Mexico", status="PRE")
        agg.aggregate_match(m)
        assert any("primary fetch failed" in n for n in m.notes)

    def test_source_urls_built_for_all_sports(self):
        # Every SPORTS key should have at least a 'primary' source URL
        from clawplay.live_scores import SPORTS

        for sport in SPORTS:
            assert sport in SOURCE_URLS, f"missing source urls for {sport}"
            assert "primary" in SOURCE_URLS[sport]


class TestRenderMatchReport:
    def _match_with_sources(self, status="PRE"):
        m = MatchReport(
            "worldcup",
            "USA",
            "Mexico",
            kickoff="2026-06-19T03:00:00Z",
            status=status,
            competition="FIFA World Cup 2026",
            venue="SoFi Stadium",
        )
        if status in ("FT", "FINAL") or status == "1H":
            m.home_score, m.away_score = "0", "1"
        m.add_source("primary", "https://example.com", [{"raw": "context", "numbers": []}])
        m.add_source(
            "fmhy",
            "https://fmhy.net/video",
            {
                "links": [{"text": "Cineby", "href": "https://cineby.app"}],
                "raw": "Live Sports section",
            },
        )
        m.add_note("aggregated from 2 sources")
        return m

    def test_preview_renders_handout(self):
        m = self._match_with_sources("PRE")
        html = render_match_report(m)
        assert 'class="sheet"' in html
        assert "USA" in html
        assert "Mexico" in html
        assert "PREVIEW" in html
        assert "SoFi Stadium" in html

    def test_preview_includes_countdown(self):
        m = self._match_with_sources("PRE")
        html = render_match_report(m)
        # Countdown is rendered as "Xd Yh" or "Yh Zm" or "Zm"
        import re

        assert re.search(r"\d+[dhm]", html) or "KICKOFF" in html or "TBD" in html

    def test_recap_renders_handout(self):
        m = self._match_with_sources("FT")
        html = render_match_report(m)
        assert "FULL TIME" in html
        assert "1" in html and "0" in html  # scores
        assert "SoFi Stadium" in html

    def test_live_renders_handout(self):
        m = self._match_with_sources("1H")
        html = render_match_report(m)
        assert "LIVE" in html

    def test_includes_fmhy_chips(self):
        m = self._match_with_sources("PRE")
        html = render_match_report(m)
        assert "Cineby" in html
        assert "fmhy.net" in html

    def test_includes_spark_handout_features(self):
        m = self._match_with_sources("PRE")
        html = render_match_report(m)
        # Spark handout DNA
        assert "8.5in" in html or "@page" in html  # letter sheet
        assert "Georgia" in html  # serif display
        assert "box-shadow" in html  # hard-offset shadows
        assert "radial-gradient" in html  # page bg gradient
        assert "speaker-card" in html  # speaker cards
        assert "thesis" in html  # big headline block
        assert "tag-row" in html or "tags" in html  # tag row
        assert "cta" in html  # CTA footer
        assert "topline" in html  # top-line rule
        assert "bottomline" in html  # bottom-line rule

    def test_includes_sources(self):
        m = self._match_with_sources("PRE")
        html = render_match_report(m)
        assert "PRIMARY" in html.upper()
        assert "FMHY" in html.upper()

    def test_writes_file(self, tmp_path):
        m = self._match_with_sources("FT")
        out = tmp_path / "match.html"
        path = write_match_report(m, out)
        assert path == str(out.resolve())
        assert "<!DOCTYPE html>" in out.read_text()
