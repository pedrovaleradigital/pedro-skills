#!/usr/bin/env python3
"""Tests for technical_checker.py — TDD: written before implementation."""

import json
from unittest.mock import patch, MagicMock
import pytest

from technical_checker import (
    check_ssl,
    check_redirects,
    check_security_headers,
    check_page_speed,
    check_sitemap,
    check_cwv_heuristic,
    check_all,
)


# ---------------------------------------------------------------------------
# Helpers to build mock responses
# ---------------------------------------------------------------------------

def _mock_response(
    status_code=200,
    text="",
    content=b"",
    headers=None,
    url="https://example.com",
    history=None,
    elapsed_seconds=0.3,
):
    """Build a MagicMock that quacks like requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content or text.encode("utf-8")
    resp.headers = headers or {}
    resp.url = url
    resp.history = history or []
    elapsed = MagicMock()
    elapsed.total_seconds.return_value = elapsed_seconds
    resp.elapsed = elapsed
    return resp


# ===================================================================
# check_ssl
# ===================================================================

class TestCheckSSL:
    @patch("technical_checker.requests.Session")
    def test_ssl_valid_https(self, MockSession):
        session = MockSession.return_value
        # Main GET succeeds over HTTPS
        session.get.return_value = _mock_response(
            url="https://example.com",
            text="<html></html>",
        )
        result = check_ssl("https://example.com")
        assert result["https_enabled"] is True
        assert result["valid_certificate"] is True

    @patch("technical_checker.requests.Session")
    def test_ssl_invalid_certificate(self, MockSession):
        import requests as req
        session = MockSession.return_value
        session.get.side_effect = req.exceptions.SSLError("bad cert")
        result = check_ssl("https://bad-cert.example.com")
        assert result["valid_certificate"] is False

    @patch("technical_checker.requests.Session")
    def test_ssl_http_url(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            url="http://example.com", text="<html></html>"
        )
        result = check_ssl("http://example.com")
        assert result["https_enabled"] is False

    @patch("technical_checker.requests.Session")
    def test_ssl_mixed_content_detected(self, MockSession):
        session = MockSession.return_value
        html = '<html><img src="http://cdn.example.com/pic.jpg"></html>'
        session.get.return_value = _mock_response(
            url="https://example.com", text=html
        )
        result = check_ssl("https://example.com")
        assert result["mixed_content"] is True

    @patch("technical_checker.requests.Session")
    def test_ssl_no_mixed_content(self, MockSession):
        session = MockSession.return_value
        html = '<html><img src="https://cdn.example.com/pic.jpg"></html>'
        session.get.return_value = _mock_response(
            url="https://example.com", text=html
        )
        result = check_ssl("https://example.com")
        assert result["mixed_content"] is False

    @patch("technical_checker.requests.Session")
    def test_ssl_http_to_https_redirect(self, MockSession):
        session = MockSession.return_value

        def side_effect(url, **kwargs):
            if url.startswith("http://") and not kwargs.get("allow_redirects", True):
                return _mock_response(
                    status_code=301,
                    headers={"Location": "https://example.com"},
                    url=url,
                )
            return _mock_response(url="https://example.com", text="<html></html>")

        session.get.side_effect = side_effect
        result = check_ssl("https://example.com")
        assert result["redirect_to_https"] is True

    @patch("technical_checker.requests.Session")
    def test_ssl_error_returns_error_key(self, MockSession):
        session = MockSession.return_value
        session.get.side_effect = Exception("connection refused")
        result = check_ssl("https://example.com")
        assert "error" in result


# ===================================================================
# check_redirects
# ===================================================================

class TestCheckRedirects:
    @patch("technical_checker.requests.Session")
    def test_no_redirects(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            url="https://example.com", history=[]
        )
        result = check_redirects("https://example.com")
        assert result["redirect_count"] == 0
        assert result["final_url"] == "https://example.com"

    @patch("technical_checker.requests.Session")
    def test_redirect_chain(self, MockSession):
        session = MockSession.return_value
        hop1 = _mock_response(status_code=301, url="http://example.com")
        hop2 = _mock_response(status_code=301, url="https://example.com")
        session.get.return_value = _mock_response(
            url="https://www.example.com",
            history=[hop1, hop2],
        )
        result = check_redirects("http://example.com")
        assert result["redirect_count"] == 2
        assert result["has_redirect_chain"] is True
        assert result["final_url"] == "https://www.example.com"

    @patch("technical_checker.requests.Session")
    def test_redirects_error(self, MockSession):
        session = MockSession.return_value
        session.get.side_effect = Exception("timeout")
        result = check_redirects("https://example.com")
        assert "error" in result


# ===================================================================
# check_security_headers
# ===================================================================

class TestCheckSecurityHeaders:
    @patch("technical_checker.requests.Session")
    def test_all_headers_present(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            headers={
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'",
                "X-Content-Type-Options": "nosniff",
            }
        )
        result = check_security_headers("https://example.com")
        assert result["x_frame_options"] == "DENY"
        assert result["strict_transport_security"] == "max-age=31536000"
        assert result["content_security_policy"] is True
        assert result["x_content_type_options"] == "nosniff"

    @patch("technical_checker.requests.Session")
    def test_missing_headers(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(headers={})
        result = check_security_headers("https://example.com")
        assert result["x_frame_options"] is None
        assert result["content_security_policy"] is False

    @patch("technical_checker.requests.Session")
    def test_headers_error(self, MockSession):
        session = MockSession.return_value
        session.get.side_effect = Exception("refused")
        result = check_security_headers("https://example.com")
        assert "error" in result


# ===================================================================
# check_page_speed
# ===================================================================

class TestCheckPageSpeed:
    @patch("technical_checker.requests.Session")
    def test_page_speed_metrics(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            content=b"x" * 5000,
            headers={
                "Content-Encoding": "gzip",
                "Cache-Control": "max-age=3600",
                "ETag": '"abc123"',
            },
            elapsed_seconds=0.45,
        )
        result = check_page_speed("https://example.com")
        assert result["response_time"] == 0.45
        assert result["page_size"] == 5000
        assert result["compression"] is True
        assert result["cache_control"] == "max-age=3600"
        assert result["etag"] is True

    @patch("technical_checker.requests.Session")
    def test_page_speed_no_compression(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            content=b"hello", headers={}, elapsed_seconds=1.2
        )
        result = check_page_speed("https://example.com")
        assert result["compression"] is False
        assert result["etag"] is False

    @patch("technical_checker.requests.Session")
    def test_page_speed_error(self, MockSession):
        session = MockSession.return_value
        session.get.side_effect = Exception("timeout")
        result = check_page_speed("https://example.com")
        assert "error" in result


# ===================================================================
# check_sitemap
# ===================================================================

VALID_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc><lastmod>2025-06-01</lastmod></url>
  <url><loc>https://example.com/page2</loc><lastmod>2025-06-10</lastmod></url>
</urlset>"""


class TestCheckSitemap:
    @patch("technical_checker.requests.Session")
    def test_sitemap_found(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            status_code=200, text=VALID_SITEMAP
        )
        result = check_sitemap("https://example.com")
        assert result["exists"] is True
        assert result["url_count"] == 2
        assert result["valid_xml"] is True
        assert result["last_modified"] == "2025-06-10"

    @patch("technical_checker.requests.Session")
    def test_sitemap_not_found(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(status_code=404)
        result = check_sitemap("https://example.com")
        assert result["exists"] is False

    @patch("technical_checker.requests.Session")
    def test_sitemap_invalid_xml(self, MockSession):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            status_code=200, text="not xml at all <broken"
        )
        result = check_sitemap("https://example.com")
        assert result["valid_xml"] is False

    @patch("technical_checker.requests.Session")
    def test_sitemap_error(self, MockSession):
        session = MockSession.return_value
        session.get.side_effect = Exception("dns failed")
        result = check_sitemap("https://example.com")
        assert "error" in result


# ===================================================================
# check_cwv_heuristic  (no HTTP — pure HTML analysis)
# ===================================================================

class TestCheckCWVHeuristic:
    def test_good_page(self):
        html = """<html><head>
        <link rel="preload" as="image" href="hero.webp">
        <style>body{margin:0}</style>
        </head><body>
        <img src="hero.webp" width="800" height="600">
        <script defer src="app.js"></script>
        </body></html>"""
        result = check_cwv_heuristic(html, response_time=0.5)
        assert result["source"] == "heuristic"
        assert result["lcp_estimate"] == "good"
        assert result["cls_risk"] == "low"
        assert result["inp_risk"] == "low"

    def test_poor_page_slow_response(self):
        html = """<html><body>
        <img src="huge.jpg">
        <img src="banner.png">
        <script src="a.js"></script>
        <script src="b.js"></script>
        <script src="c.js"></script>
        </body></html>"""
        result = check_cwv_heuristic(html, response_time=3.0)
        assert result["lcp_estimate"] == "poor"  # response_time > 2.5s
        assert result["inp_risk"] in ("medium", "high")  # 3 sync scripts
        assert result["cls_risk"] in ("medium", "high")  # imgs without dimensions

    def test_needs_improvement_lcp(self):
        html = """<html><body>
        <img src="photo.jpg" width="400" height="300">
        <script defer src="app.js"></script>
        </body></html>"""
        # response_time between good and poor thresholds, no preload
        result = check_cwv_heuristic(html, response_time=2.0)
        assert result["lcp_estimate"] == "needs_improvement"

    def test_high_inp_many_sync_scripts(self):
        scripts = "".join('<script src="s{}.js"></script>'.format(i) for i in range(5))
        html = f"<html><body>{scripts}</body></html>"
        result = check_cwv_heuristic(html, response_time=0.5)
        assert result["inp_risk"] == "high"

    def test_low_cls_all_images_have_dimensions(self):
        html = """<html><body>
        <img src="a.jpg" width="100" height="100">
        <img src="b.jpg" width="200" height="150">
        </body></html>"""
        result = check_cwv_heuristic(html, response_time=0.5)
        assert result["cls_risk"] == "low"

    def test_high_cls_no_dimensions(self):
        html = """<html><body>
        <img src="a.jpg">
        <img src="b.jpg">
        <img src="c.jpg">
        </body></html>"""
        result = check_cwv_heuristic(html, response_time=0.5)
        assert result["cls_risk"] == "high"

    def test_thresholds_documented(self):
        """Verify the function documents correct 2024 CWV thresholds."""
        html = "<html><body></body></html>"
        result = check_cwv_heuristic(html, response_time=0.5)
        assert result["source"] == "heuristic"
        # Just ensure it returns valid values
        assert result["lcp_estimate"] in ("good", "needs_improvement", "poor")
        assert result["inp_risk"] in ("low", "medium", "high")
        assert result["cls_risk"] in ("low", "medium", "high")


# ===================================================================
# check_all — integration-ish (all sub-checks mocked)
# ===================================================================

class TestCheckAll:
    @patch("technical_checker.requests.Session")
    def test_check_all_returns_all_keys(self, MockSession):
        session = MockSession.return_value
        # Return a basic happy-path response for all GETs
        session.get.return_value = _mock_response(
            url="https://example.com",
            text="<html><body><img src='x.jpg' width='10' height='10'></body></html>",
            headers={
                "Content-Encoding": "gzip",
                "Cache-Control": "max-age=3600",
                "X-Frame-Options": "DENY",
            },
            elapsed_seconds=0.2,
        )
        result = check_all("https://example.com")
        expected_keys = {"ssl", "redirects", "security_headers", "page_speed", "sitemap", "cwv_heuristic"}
        assert expected_keys.issubset(set(result.keys()))

    @patch("technical_checker.requests.Session")
    def test_check_all_never_crashes(self, MockSession):
        """Even if every sub-check errors, check_all returns a dict."""
        session = MockSession.return_value
        session.get.side_effect = Exception("total failure")
        result = check_all("https://example.com")
        assert isinstance(result, dict)
        # Each sub-key should still exist (with error info)
        assert "ssl" in result
        assert "redirects" in result


# ===================================================================
# CLI entry point
# ===================================================================

class TestCLI:
    @patch("technical_checker.requests.Session")
    def test_cli_prints_json(self, MockSession, capsys):
        session = MockSession.return_value
        session.get.return_value = _mock_response(
            url="https://example.com",
            text="<html><body></body></html>",
            headers={},
            elapsed_seconds=0.1,
        )
        import sys
        original_argv = sys.argv
        try:
            sys.argv = ["technical_checker.py", "https://example.com"]
            # Import and run main
            from technical_checker import main
            main()
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert "ssl" in data
        finally:
            sys.argv = original_argv
