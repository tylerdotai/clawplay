"""Render fresh screenshots of all four clawplay report templates.

Captures every template at:
  - Desktop (1440×900 viewport)  → examples/{name}.png
  - Print (816×1056 viewport, scales correctly) → examples/{name}_print.png
  - Hero crop (first 900px) for README hero → examples/{name}_hero.png

Usage:
    uv run --with playwright python scripts/render_screenshots.py

Requires `playwright install chromium` to have run at least once.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "templates"
OUT = REPO / "examples"

DESKTOP = {"width": 1440, "height": 900}
PRINT = {"width": 816, "height": 1056}

TASKS = [
    ("preview.html", "preview"),
    ("live.html", "live"),
    ("recap.html", "recap"),
    ("hub.html", "hub"),
]


def render() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport_name, viewport in (("desktop", DESKTOP), ("print", PRINT)):
            ctx = browser.new_context(viewport=viewport, device_scale_factor=2)
            page = ctx.new_page()
            for src, name in TASKS:
                url = (TEMPLATES / src).as_uri()
                page.goto(url, wait_until="networkidle")
                # Give Tailwind CDN a beat to apply utility classes after DOMContentLoaded
                page.wait_for_timeout(400)
                # Full-page screenshot for the main artifact
                full = OUT / f"{name}.png" if viewport_name == "desktop" else OUT / f"{name}_print.png"
                page.screenshot(path=str(full), full_page=True)
                print(f"  wrote {full.relative_to(REPO)} ({full.stat().st_size // 1024} KB)")
                # Hero crop (desktop only) — top 900px at full width
                if viewport_name == "desktop":
                    hero = OUT / f"{name}_hero.png"
                    page.screenshot(path=str(hero), full_page=False, clip={"x": 0, "y": 0, "width": viewport["width"], "height": 900})
                    print(f"  wrote {hero.relative_to(REPO)} ({hero.stat().st_size // 1024} KB)")
            ctx.close()
        browser.close()
    print("\nDone — 4 templates × 2 viewports + 4 hero crops = 12 screenshots")


if __name__ == "__main__":
    render()
