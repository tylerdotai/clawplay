"""Tests for clawplay.clawplay — HTTP client."""

from unittest.mock import MagicMock

from clawplay.clawplay import Clawplay


class TestClawplayInit:
    def test_default_url_from_env(self, monkeypatch):
        monkeypatch.setenv("CLAWPLAY_URL", "http://example:1234")
        # Re-evaluate the module-level default URL after env change
        import importlib

        from clawplay import clawplay as cp_mod

        importlib.reload(cp_mod)
        c = cp_mod.Clawplay()
        assert c.base_url == "http://example:1234"

    def test_strips_trailing_slash(self):
        c = Clawplay(base_url="http://localhost:9300/")
        assert c.base_url == "http://localhost:9300"


class TestClawplayEval:
    def test_eval_posts_to_eval_endpoint(self):
        c = Clawplay("http://localhost:9300")
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "content": "[]"}
        mock_session.post.return_value = mock_resp
        c.session = mock_session

        result = c.eval("https://example.com", "return 1;")
        assert result["ok"] is True
        mock_session.post.assert_called_once()
        url_arg = mock_session.post.call_args[0][0]
        assert url_arg.endswith("/eval")

    def test_eval_handles_transport_error(self):
        c = Clawplay("http://localhost:9300")
        mock_session = MagicMock()
        mock_session.post.side_effect = OSError("connection refused")
        c.session = mock_session
        result = c.eval("https://example.com", "return 1;")
        assert result["ok"] is False
        assert (
            "transport" in result["error"]
            or "connection refused" in result["error"]
            or "OSError" in result["error"]
            or result["error"]
        )  # any error string


class TestClawplayHealth:
    def test_health_get(self):
        c = Clawplay("http://localhost:9300")
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "status": "ready"}
        mock_session.get.return_value = mock_resp
        c.session = mock_session
        result = c.health()
        assert result["ok"] is True
        mock_session.get.assert_called_once()
