"""Render demo clips for clawplay report templates.

For each of the four report templates, navigate to a live URL on the
running ``clawplay-server`` with headless Chromium, scroll through the
page in timed segments, capture each segment as a PNG, then stitch
into an MP4 with ffmpeg + libx264.

Output: ``examples/clips/{preview,live,recap,hub}.mp4`` (~2–5 MB each).

Production stack: Playwright (Python) + ffmpeg + libx264. All open-source.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "examples" / "clips"
SCREENSHOTS_DIR = REPO / "examples" / "clip_frames"

VIEWPORT = {"width": 1440, "height": 900}
FPS = 30
SEGMENT_SECONDS = 3.5  # each segment captures this many seconds of scrolling
FRAMES_PER_SEGMENT = int(SEGMENT_SECONDS * FPS)
COMPRESSION = "crf 23"  # good balance of size vs quality for h264


DEMO_TARGETS: List[Tuple[str, str, str, str]] = [
    # (output_name, url_path, sport_slug, label)
    ("preview", "/preview/worldcup/USA/Mexico", "worldcup", "USA vs Mexico preview"),
    ("live", "/live/worldcup/Mexico/USA", "worldcup", "Mexico vs USA live"),
    ("recap", "/recap/worldcup/Mexico/USA", "worldcup", "Mexico 1-0 USA recap"),
    ("hub", "/hub/dallas_cowboys", "nfl", "Dallas Cowboys hub"),
]


def _ensure_server_running(host: str = "127.0.0.1", port: int = 9300) -> bool:
    """Quick TCP probe to see if clawplay-server is up."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False


def _ensure_server_started(host: str, port: int) -> subprocess.Popen:
    """Start the server in a subprocess and wait for it to be ready."""
    import urllib.request

    env = os.environ.copy()
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "clawplay-server",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=0.5) as r:
                if r.status == 200:
                    return proc
        except Exception:
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError(f"clawplay-server did not start on {host}:{port}")


def _capture_frames(page, base_url: str, segments: int = 4) -> List[Path]:
    """Capture scroll-segment frames."""
    frames: List[Path] = []
    page.goto(base_url, wait_until="networkidle")
    # Let Tailwind CDN + initial JS settle.
    page.wait_for_timeout(800)

    # Capture the first viewport as segment 1 (hero, fully visible).
    seg_dir = SCREENSHOTS_DIR / base_url.split("/")[-1].replace("/", "_")
    seg_dir.mkdir(parents=True, exist_ok=True)
    for i in range(segments):
        # Slight scroll on later segments to reveal more content.
        scroll_y = i * 700
        page.evaluate(f"window.scrollTo(0, {scroll_y})")
        page.wait_for_timeout(450)  # let any in-page animations settle
        # Capture N frames at 30fps in this scroll position to create motion.
        for j in range(FRAMES_PER_SEGMENT):
            # Interpolate a tiny vertical pan for a "Ken Burns" effect.
            micro_scroll = (j / FRAMES_PER_SEGMENT) * 50
            page.evaluate(f"window.scrollTo(0, {scroll_y + micro_scroll})")
            frame_path = seg_dir / f"seg{i:02d}_frame{j:04d}.png"
            page.screenshot(path=str(frame_path), full_page=False)
            frames.append(frame_path)
    return frames


def _stitch_mp4(frames: List[Path], output_path: Path) -> Path:
    """Stitch frames into an MP4 using ffmpeg + libx264."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH — install with `brew install ffmpeg`")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use the first frame's directory + a concat demuxer for reliability.
    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    with concat_file.open("w") as f:
        for fr in frames:
            f.write(f"file '{fr.resolve()}'\n")
            f.write(f"duration {1 / FPS:.6f}\n")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vf",
        f"fps={FPS}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "26",
        "-preset",
        "veryfast",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    concat_file.unlink(missing_ok=True)
    return output_path


def _make_gif(mp4_path: Path, gif_path: Path, fps: int = 12, width: int = 720) -> Path:
    """Derive a small GIF from the MP4 for README embedding."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-vf",
        f"fps={fps},scale={width}:-1:flags=lanczos",
        "-loop",
        "0",
        str(gif_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return gif_path


def render_all(host: str = "127.0.0.1", port: int = 9300) -> List[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    server_proc = None
    if not _ensure_server_running(host, port):
        print(f"Starting clawplay-server on {host}:{port} ...")
        server_proc = _ensure_server_started(host, port)
    else:
        print(f"clawplay-server already running on {host}:{port}")

    try:
        outputs: List[Path] = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
            page = ctx.new_page()
            for name, url_path, _sport, _label in DEMO_TARGETS:
                base_url = f"http://{host}:{port}{url_path}"
                print(f"  capturing {name} from {base_url} ...")
                frames = _capture_frames(page, base_url, segments=4)
                mp4 = OUT_DIR / f"{name}.mp4"
                _stitch_mp4(frames, mp4)
                print(f"    wrote {mp4.relative_to(REPO)} ({mp4.stat().st_size // 1024} KB)")
                # Also derive a small GIF for README.
                gif = OUT_DIR / f"{name}.gif"
                _make_gif(mp4, gif)
                print(f"    wrote {gif.relative_to(REPO)} ({gif.stat().st_size // 1024} KB)")
                outputs.append(mp4)
            ctx.close()
            browser.close()
        return outputs
    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()


def main() -> None:
    print(f"Rendering {len(DEMO_TARGETS)} demo clips ...")
    outputs = render_all()
    print(f"\nDone — {len(outputs)} clips in {OUT_DIR.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
