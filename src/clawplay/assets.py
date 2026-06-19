"""clawplay.assets — Tailwind CSS build pipeline.

Compiles ``templates/dist/input.css`` into ``templates/dist/styles.css``
via the standalone Tailwind CLI binary (downloaded on first use) or a
local npm install. Replaces the previous `<script src="cdn.tailwindcss.com">`
hot-link in the HTML templates, so reports render offline.

Usage::

    from clawplay.assets import build_css, css_path
    build_css()                    # produces templates/dist/styles.css
    print(css_path())              # absolute path

CLI::

    clawplay-build-assets          # build CSS once
    clawplay-build-assets --watch  # rebuild on template change
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import tempfile
import urllib.request
from pathlib import Path

# Tailwind CSS CLI v3 standalone binary — released under MIT, free to
# redistribute. ~6MB, works on macOS / Linux / Windows without Node.
_TAILWIND_VERSION = "3.4.17"
_DOWNLOAD_URLS = {
    (
        "Darwin",
        "x86_64",
    ): f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{_TAILWIND_VERSION}/tailwindcss-macos-x64",
    (
        "Darwin",
        "arm64",
    ): f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{_TAILWIND_VERSION}/tailwindcss-macos-arm64",
    (
        "Linux",
        "x86_64",
    ): f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{_TAILWIND_VERSION}/tailwindcss-linux-x64",
    (
        "Linux",
        "aarch64",
    ): f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{_TAILWIND_VERSION}/tailwindcss-linux-arm64",
    (
        "Linux",
        "armv7l",
    ): f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{_TAILWIND_VERSION}/tailwindcss-linux-armv7",
}

CACHE_DIR = Path.home() / ".cache" / "clawplay" / "bin"
INPUT_CSS = Path(__file__).resolve().parent.parent.parent / "templates" / "dist" / "input.css"
OUTPUT_CSS = INPUT_CSS.parent / "styles.css"
CONFIG_JS = INPUT_CSS.parent.parent.parent / "tailwind.config.js"

CSS_HELP = "Compile clawplay Tailwind utility CSS to templates/dist/styles.css."


def _tailwind_binary() -> Path:
    """Return absolute path to the tailwindcss CLI binary, downloading on demand."""
    system = platform.system()
    machine = platform.machine()
    key = (system, machine)
    if key not in _DOWNLOAD_URLS:
        raise RuntimeError(
            f"No Tailwind CLI binary for {system}/{machine}. "
            "Install Node + npm and run `npm install -D tailwindcss`."
        )
    bin_path = CACHE_DIR / f"tailwindcss-{system}-{machine}"
    if bin_path.exists() and bin_path.stat().st_size > 1_000_000:
        return bin_path
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = _DOWNLOAD_URLS[key]
    print(f"Downloading Tailwind CLI from {url} ...")
    with (
        urllib.request.urlopen(url, timeout=60) as r,
        tempfile.NamedTemporaryFile(delete=False) as tmp,
    ):
        shutil.copyfileobj(r, tmp)
        tmp_path = Path(tmp.name)
    bin_path.write_bytes(tmp_path.read_bytes())
    tmp_path.unlink()
    bin_path.chmod(bin_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return bin_path


def build_css(*, minify: bool = True, watch: bool = False) -> Path:
    """Compile templates/dist/input.css → templates/dist/styles.css.

    Returns the absolute path to the output file.
    """
    if not INPUT_CSS.exists():
        raise FileNotFoundError(f"Input CSS not found: {INPUT_CSS}")
    if not CONFIG_JS.exists():
        raise FileNotFoundError(f"tailwind.config.js not found: {CONFIG_JS}")
    OUTPUT_CSS.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(_tailwind_binary()),
        "-c",
        str(CONFIG_JS),
        "-i",
        str(INPUT_CSS),
        "-o",
        str(OUTPUT_CSS),
    ]
    if minify:
        cmd.append("--minify")
    if watch:
        cmd.append("--watch")
    env = os.environ.copy()
    env["NODE_ENV"] = "production" if not watch else "development"
    subprocess.run(cmd, check=True, env=env)
    return OUTPUT_CSS


def css_path() -> Path:
    """Absolute path to the compiled CSS file (may not exist yet)."""
    return OUTPUT_CSS


def _cli_entry() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="clawplay-build-assets", description="Compile clawplay Tailwind CSS."
    )
    parser.add_argument("--watch", action="store_true", help="rebuild on template change")
    parser.add_argument("--no-minify", action="store_true", help="emit unminified CSS")
    args = parser.parse_args()
    out = build_css(minify=not args.no_minify, watch=args.watch)
    print(f"OK → {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    _cli_entry()
