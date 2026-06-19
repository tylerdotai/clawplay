"""Tests for clawplay.assets — Tailwind CSS build pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from clawplay.assets import CSS_HELP, _tailwind_binary, build_css, css_path


def test_css_path_is_under_templates_dist() -> None:
    p = css_path()
    assert p.name == "styles.css"
    assert "templates" in p.parts
    assert "dist" in p.parts


def test_input_css_exists() -> None:
    """The input CSS file ships with the package."""
    from clawplay.assets import INPUT_CSS

    assert INPUT_CSS.exists()
    assert "@tailwind base" in INPUT_CSS.read_text()


def test_tailwind_config_exists() -> None:
    from clawplay.assets import CONFIG_JS

    assert CONFIG_JS.exists()
    text = CONFIG_JS.read_text()
    assert "content" in text
    assert "theme" in text


@pytest.mark.skipif(
    _tailwind_binary().__class__.__name__ != "Path" or not _tailwind_binary().exists(),
    reason="Tailwind binary not downloaded yet — run `clawplay-build-assets` first",
)
def test_build_css_produces_file(tmp_path: Path) -> None:
    """End-to-end: build the CSS file."""
    out = build_css()
    assert out.exists()
    assert out.stat().st_size > 5_000  # At least a few KB of compiled Tailwind
    assert "body" in out.read_text() or "*" in out.read_text()


def test_css_help_text_mentions_clawplay() -> None:
    assert "clawplay" in CSS_HELP.lower() or "tailwind" in CSS_HELP.lower()
