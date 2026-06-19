"""clawplay.palettes — Team and sport color palettes.

Every sport has a ``Palette`` (primary, secondary, accent, surface, text)
that drives the CSS custom-property block at the top of each template.

Two sources of palettes, in priority order:

1. ``src/clawplay/_palette_registry.yaml`` (canonical, machine-readable)
2. ``templates/designs/{sport}.md`` frontmatter (designer overrides)

Per-team overrides can be registered at runtime via
``register_team(sport, slug, palette)`` or added under a top-level
``teams:`` key in the YAML registry.

Usage::

    from clawplay.palettes import palette_for, palette_for_team, all_sport_palettes

    palette = palette_for("nfl")
    palette.css_vars()  # {'--palette-primary': '#013369', ...}

    team_pal = palette_for_team("nfl", "dallas_cowboys")
    team_pal.css_vars()

The ClawPlex DNA applies when a sport has no palette defined: dark
surfaces, brand blue + signal red, no orange anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass(frozen=True)
class Palette:
    """Color palette for a sport or team. All values are hex strings."""

    primary: str = "#1e40af"  # brand blue (ClawPlex default)
    secondary: str = "#dc2626"  # signal red
    accent: str = "#3b82f6"  # blue accent
    surface: str = "#131313"  # card surface
    raised: str = "#1a1a1a"  # raised surface
    background: str = "#0a0a0a"  # page bg
    text: str = "#fafafa"  # primary text
    muted: str = "#a3a3a3"  # muted text
    border: str = "#262626"  # borders

    def css_vars(self) -> Dict[str, str]:
        """Return CSS custom-property name → value mapping for templates."""
        return {
            "--palette-primary": self.primary,
            "--palette-secondary": self.secondary,
            "--palette-accent": self.accent,
            "--palette-surface": self.surface,
            "--palette-raised": self.raised,
            "--palette-background": self.background,
            "--palette-text": self.text,
            "--palette-muted": self.muted,
            "--palette-border": self.border,
        }


DEFAULT_PALETTE = Palette()

# In-memory caches.
_SPORT_PALETTES: Dict[str, Palette] = {}
_TEAM_PALETTES: Dict[Tuple[str, str], Palette] = {}
_REGISTRY_LOADED = False


def _package_dir() -> Path:
    """Return the package root directory (where _palette_registry.yaml lives)."""
    return Path(__file__).resolve().parent


def _designs_dir() -> Path:
    """Return the templates/designs directory."""
    return Path(__file__).resolve().parent.parent.parent / "templates" / "designs"


def _registry_path() -> Path:
    return _package_dir() / "_palette_registry.yaml"


def _parse_yaml_registry() -> Dict[str, Palette]:
    """Load _palette_registry.yaml from the package root."""
    if yaml is None:
        return {}
    path = _registry_path()
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    out: Dict[str, Palette] = {}
    teams: Dict[Tuple[str, str], Palette] = {}
    for sport, data in raw.items():
        if not isinstance(data, dict):
            continue
        # Split per-team overrides from sport-level colors.
        sport_colors = {k: v for k, v in data.items() if k != "teams"}
        team_colors = data.get("teams") or {}
        if sport_colors:
            out[sport] = Palette(
                **{k: v for k, v in sport_colors.items() if k in Palette.__dataclass_fields__}
            )
        for team_slug, team_data in team_colors.items():
            if not isinstance(team_data, dict):
                continue
            teams[(sport, team_slug)] = Palette(
                **{k: v for k, v in team_data.items() if k in Palette.__dataclass_fields__}
            )
    _TEAM_PALETTES.update(teams)
    return out


def _ensure_registry_loaded() -> None:
    global _REGISTRY_LOADED
    if _REGISTRY_LOADED:
        return
    sport_palettes = _parse_yaml_registry()
    _SPORT_PALETTES.update(sport_palettes)
    _REGISTRY_LOADED = True


def _parse_design_frontmatter(md_text: str) -> dict:
    """Parse a simple ``---\\nkey: value\\n---`` YAML-ish frontmatter block."""
    if not md_text.startswith("---"):
        return {}
    end = md_text.find("\n---", 3)
    if end == -1:
        return {}
    block = md_text[3:end].strip()
    out: dict = {}
    section: Optional[str] = None
    section_data: dict = {}
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("  ") and section:
            m = re.match(r"\s+([a-zA-Z_]+):\s*(.+)", line)
            if m:
                key, val = m.group(1).strip(), m.group(2).strip()
                section_data[key] = val.strip('"').strip("'")
            continue
        if section:
            out[section] = section_data
            section_data = {}
        m = re.match(r"([a-zA-Z_]+):\s*(.*)", line)
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        if not val:
            section = key
            section_data = {}
            continue
        section = None
        if val.startswith("[") and val.endswith("]"):
            out[key] = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
        else:
            out[key] = val.strip('"').strip("'")
    if section:
        out[section] = section_data
    return out


def palettes_from_design(sport: str, *, reload: bool = False) -> Palette:
    """Load a sport palette from ``templates/designs/{sport}.md`` frontmatter.

    Used as a fallback / override layer on top of the YAML registry.
    """
    if not reload and sport in _SPORT_PALETTES:
        return _SPORT_PALETTES[sport]
    md_path = _designs_dir() / f"{sport}.md"
    if not md_path.exists():
        return DEFAULT_PALETTE
    text = md_path.read_text(encoding="utf-8")
    fm = _parse_design_frontmatter(text)
    colors = fm.get("colors", {}) or {}
    if not isinstance(colors, dict) or not colors:
        return DEFAULT_PALETTE
    palette = Palette(
        primary=colors.get("primary", DEFAULT_PALETTE.primary),
        secondary=colors.get("secondary", DEFAULT_PALETTE.secondary),
        accent=colors.get("accent", DEFAULT_PALETTE.accent),
        surface=colors.get("surface", DEFAULT_PALETTE.surface),
        raised=colors.get("raised", DEFAULT_PALETTE.raised),
        background=colors.get("background", DEFAULT_PALETTE.background),
        text=colors.get("text", DEFAULT_PALETTE.text),
        muted=colors.get("muted", DEFAULT_PALETTE.muted),
        border=colors.get("border", DEFAULT_PALETTE.border),
    )
    _SPORT_PALETTES[sport] = palette
    return palette


def palette_for(sport: str) -> Palette:
    """Return the palette for a sport (loads from YAML registry)."""
    _ensure_registry_loaded()
    if sport in _SPORT_PALETTES:
        return _SPORT_PALETTES[sport]
    # Fall back to design.md frontmatter, then default.
    fm_palette = palettes_from_design(sport)
    if fm_palette != DEFAULT_PALETTE:
        return fm_palette
    return DEFAULT_PALETTE


def palette_for_team(sport: str, team_slug: str) -> Palette:
    """Return the palette for a specific team, falling back to sport defaults."""
    _ensure_registry_loaded()
    if (sport, team_slug) in _TEAM_PALETTES:
        return _TEAM_PALETTES[(sport, team_slug)]
    return palette_for(sport)


def register_team(sport: str, team_slug: str, palette: Palette) -> None:
    """Register a per-team palette override at runtime."""
    _TEAM_PALETTES[(sport, team_slug)] = palette


def all_sport_palettes(*, reload: bool = False) -> Dict[str, Palette]:
    """Return all registered sport palettes keyed by sport slug."""
    _ensure_registry_loaded()
    if reload:
        _SPORT_PALETTES.clear()
        _TEAM_PALETTES.clear()
        # pylint: disable=global-statement
        global _REGISTRY_LOADED
        _REGISTRY_LOADED = False
        _ensure_registry_loaded()
    return dict(_SPORT_PALETTES)


__all__ = [
    "Palette",
    "DEFAULT_PALETTE",
    "palettes_from_design",
    "palette_for",
    "palette_for_team",
    "register_team",
    "all_sport_palettes",
]


def _self_test() -> None:
    nfl = palette_for("nfl")
    print(f"OK nfl.primary = {nfl.primary} (expect #013369)")
    assert nfl.primary == "#013369", nfl
    worldcup = palette_for("worldcup")
    print(f"OK worldcup.primary = {worldcup.primary}")
    assert worldcup.primary == "#9b1b30", worldcup
    fallback = palette_for("does_not_exist")
    print(f"OK fallback = {fallback.primary}")
    assert fallback == DEFAULT_PALETTE
    all_p = all_sport_palettes()
    print(f"OK {len(all_p)} sport palettes loaded: {sorted(all_p)}")


if __name__ == "__main__":
    _self_test()
