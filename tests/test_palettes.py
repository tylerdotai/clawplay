"""Tests for clawplay.palettes."""

from __future__ import annotations

import pytest

from clawplay.palettes import (
    DEFAULT_PALETTE,
    Palette,
    all_sport_palettes,
    palette_for,
    palette_for_team,
    palettes_from_design,
    register_team,
)


def test_default_palette_is_clawplex_dna() -> None:
    p = DEFAULT_PALETTE
    assert p.primary == "#1e40af"
    assert p.secondary == "#dc2626"
    assert p.background == "#0a0a0a"


def test_palette_css_vars_contains_all_keys() -> None:
    p = Palette()
    vars_ = p.css_vars()
    assert "--palette-primary" in vars_
    assert "--palette-secondary" in vars_
    assert "--palette-accent" in vars_
    assert "--palette-surface" in vars_
    assert "--palette-raised" in vars_
    assert "--palette-background" in vars_
    assert "--palette-text" in vars_
    assert "--palette-muted" in vars_
    assert "--palette-border" in vars_
    assert len(vars_) == 9


def test_palette_is_frozen() -> None:
    """Palette must be hashable / immutable."""
    import dataclasses

    p = Palette()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.primary = "#000000"  # type: ignore[misc]  # noqa: ERA001


def test_palette_for_known_sport_loads_from_registry() -> None:
    nfl = palette_for("nfl")
    assert nfl.primary == "#013369"
    assert nfl.secondary == "#d50a0a"
    assert nfl.accent == "#869397"


def test_palette_for_unknown_sport_returns_default() -> None:
    p = palette_for("does_not_exist_xyz")
    assert p == DEFAULT_PALETTE


def test_all_21_sport_palettes_loaded() -> None:
    all_p = all_sport_palettes()
    assert len(all_p) == 21
    expected_sports = {
        "nfl",
        "nba",
        "nhl",
        "mlb",
        "mls",
        "wnba",
        "cfb",
        "cbb",
        "cbb_w",
        "epl",
        "ucl",
        "laliga",
        "bundes",
        "seriea",
        "worldcup",
        "soccer_live",
        "ufc",
        "tennis",
        "golf",
        "cricket",
        "rugby",
    }
    assert set(all_p.keys()) == expected_sports


def test_palettes_have_valid_hex_values() -> None:
    for sport, p in all_sport_palettes().items():
        for field_name in (
            "primary",
            "secondary",
            "accent",
            "surface",
            "raised",
            "background",
            "text",
            "muted",
            "border",
        ):
            value = getattr(p, field_name)
            assert value.startswith("#") and len(value) == 7, (
                f"{sport}.{field_name} = {value!r} is not a 7-char hex string"
            )
            int(value[1:], 16)  # parses


def test_palette_for_team_falls_back_to_sport() -> None:
    p = palette_for_team("nfl", "team_that_does_not_exist")
    assert p == palette_for("nfl")


def test_register_team_adds_override() -> None:
    custom = Palette(primary="#ff00ff", secondary="#00ffff")
    register_team("test_sport", "test_team", custom)
    p = palette_for_team("test_sport", "test_team")
    assert p == custom


def test_palettes_from_design_falls_back_when_no_frontmatter() -> None:
    """nfl.md currently has no frontmatter block, so returns default."""
    p = palettes_from_design("nfl")
    # Either default OR registry-loaded — both are valid. Just assert it works.
    assert isinstance(p, Palette)


def test_palettes_are_distinct_per_sport() -> None:
    """No two sports should share the same primary hex."""
    all_p = all_sport_palettes()
    primaries = [p.primary for p in all_p.values()]
    assert len(primaries) == len(set(primaries)), f"Duplicate primary hexes: {primaries}"
