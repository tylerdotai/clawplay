"""
clawplay — minimal HTTP client for a headless-browser service.

Talks to any FastAPI + Playwright/CDP service that exposes:
    GET  /health        → service liveness
    POST /eval          → evaluate JS on a page and return JSON-serializable result
    POST /extract       → render page and return markdown / cleaned HTML
    POST /screenshot    → capture screenshot (PNG bytes or path)

Configure via $CLAWPLAY_URL (default http://localhost:9300).

This module is HTTP-only and works against any compatible backend. No
SSH, no docker-exec, no host-specific paths. Pull the Python deps and
point at any reachable service.
"""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urljoin

import requests

DEFAULT_URL = os.environ.get("CLAWPLAY_URL", "http://localhost:9300")
DEFAULT_TIMEOUT = 30


class ClawplayError(RuntimeError):
    """Raised for any non-OK clawplay response or transport error."""


class Clawplay:
    """Thin HTTP client for the headless-browser service."""

    def __init__(self, base_url: str = DEFAULT_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # -- low-level --------------------------------------------------------

    def _post(self, path: str, payload: dict, timeout: Optional[float] = None) -> dict:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        t = int(timeout) if timeout is not None else self.timeout
        try:
            r = self.session.post(url, json=payload, timeout=t)
        except (requests.RequestException, OSError) as e:
            return {"ok": False, "error": f"transport: {e}", "status": None}
        try:
            body = r.json()
        except ValueError:
            return {
                "ok": False,
                "error": f"non-json response (HTTP {r.status_code})",
                "raw": r.text[:400],
            }
        body.setdefault("status", r.status_code)
        return body

    def _get(self, path: str, timeout: Optional[float] = None) -> dict:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        t = int(timeout) if timeout is not None else self.timeout
        try:
            r = self.session.get(url, timeout=t)
        except (requests.RequestException, OSError) as e:
            return {"ok": False, "error": f"transport: {e}", "status": None}
        try:
            body = r.json()
        except ValueError:
            return {
                "ok": False,
                "error": f"non-json response (HTTP {r.status_code})",
                "raw": r.text[:400],
            }
        body.setdefault("status", r.status_code)
        return body

    # -- public API -------------------------------------------------------

    def health(self) -> dict:
        return self._get("/health", timeout=5)

    def eval(self, url: str, js: str, timeout_ms: int = 18000) -> dict:
        """Evaluate JS on a page. Returns {"ok": True, "content": <JSON result>, ...}."""
        return self._post(
            "/eval",
            {"url": url, "js": js, "timeoutMs": timeout_ms},
            timeout=max(timeout_ms / 1000 + 5, 10),
        )

    def extract(self, url: str, fmt: str = "markdown", timeout_ms: int = 20000) -> dict:
        return self._post(
            "/extract",
            {"url": url, "format": fmt, "timeoutMs": timeout_ms},
            timeout=max(timeout_ms / 1000 + 5, 10),
        )

    def screenshot(
        self,
        url: str,
        out_path: str,
        *,
        full_page: bool = True,
        viewport: tuple = (1280, 1800),
        wait_ms: int = 800,
    ) -> dict:
        return self._post(
            "/screenshot",
            {
                "url": url,
                "fullPage": full_page,
                "viewport": {"width": viewport[0], "height": viewport[1]},
                "waitMs": wait_ms,
                "outPath": out_path,
            },
            timeout=max(wait_ms / 1000 + 15, 20),
        )


def health() -> dict:
    """Quick health probe."""
    return Clawplay().health()
