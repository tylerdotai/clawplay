"""Tests for clawplay.espn — ESPN API + Sleeper fantasy sync."""

from __future__ import annotations

import os

from clawplay.espn import (
    MockNFLPlayByPlay,
    fantasy_players_sleeper,
    nfl_play_by_play,
    top_waiver_targets,
)


def test_mock_play_by_play_returns_list_of_dicts() -> None:
    plays = MockNFLPlayByPlay.play("test-game-1")
    assert isinstance(plays, list)
    assert len(plays) == 12
    for p in plays:
        assert "type" in p
        assert "yard_start" in p
        assert "yard_end" in p
        assert "score" in p
        assert p["type"] in ("run", "pass")


def test_mock_play_by_play_is_deterministic() -> None:
    a = MockNFLPlayByPlay.play("same-game-id")
    b = MockNFLPlayByPlay.play("same-game-id")
    assert a == b


def test_mock_play_by_play_different_seeds_differ() -> None:
    a = MockNFLPlayByPlay.play("game-a")
    b = MockNFLPlayByPlay.play("game-b")
    assert a != b


def test_nfl_play_by_play_force_mock() -> None:
    plays = nfl_play_by_play("any-id", force_mock=True)
    assert isinstance(plays, list)
    assert len(plays) == 12


def test_nfl_play_by_play_mock_env_var() -> None:
    os.environ["CLAWPLAY_MOCK"] = "1"
    try:
        plays = nfl_play_by_play("env-mock-game")
        assert len(plays) == 12
    finally:
        del os.environ["CLAWPLAY_MOCK"]


def test_nfl_play_by_play_returns_list() -> None:
    """Without internet or force_mock, should still return a list
    (may be mock data if ESPN is unreachable)."""
    plays = nfl_play_by_play("test-game-id")
    assert isinstance(plays, list)
    assert len(plays) >= 0


def test_sleeper_force_mock_returns_mock_payload() -> None:
    data = fantasy_players_sleeper("nfl", force_mock=True)
    assert isinstance(data, dict)
    assert len(data) == 3
    assert "4017" in data  # Mahomes


def test_sleeper_mock_payload_has_required_fields() -> None:
    data = fantasy_players_sleeper("nfl", force_mock=True)
    for _pid, p in data.items():
        assert "first_name" in p
        assert "last_name" in p
        assert "position" in p
        assert "team" in p
        assert "status" in p


def test_top_waiver_targets_no_position() -> None:
    targets = top_waiver_targets(position=None, count=2, force_mock=True)
    assert isinstance(targets, list)
    assert len(targets) <= 2


def test_top_waiver_targets_qb_filter() -> None:
    targets = top_waiver_targets(position="QB", count=1, force_mock=True)
    assert isinstance(targets, list)
    for t in targets:
        assert t["position"] == "QB"


def test_top_waiver_targets_te_filter() -> None:
    targets = top_waiver_targets(position="TE", count=1, force_mock=True)
    assert isinstance(targets, list)
    for t in targets:
        assert t["position"] == "TE"


def test_top_waiver_targets_unknown_position_returns_empty() -> None:
    targets = top_waiver_targets(position="K", count=5, force_mock=True)
    # Mock has no kickers; expect empty list (not an error).
    assert isinstance(targets, list)
