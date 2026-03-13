#!/usr/bin/env python3
"""
Technical SEO Checker — function-based
Checks SSL, redirects, security headers, page speed, sitemap, and CWV heuristics.

Usage:
    python3 technical_checker.py <url>
"""

import json
import re
import sys
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "SEO-Audit-Bot/1.0"})
    return session


# ---------------------------------------------------------------------------
# check_ssl
# ---------------------------------------------------------------------------

def check_ssl(url: str) -> dict:
    """Check HTTPS, certificate validity, HTTP->HTTPS redirect, mixed content."""
    url = _normalize_url(url)
    session = _make_session()
    try:
        response = session.get(url, timeout=10)
        https_enabled = url.startswith("https")

        # Check HTTP -> HTTPS redirect
        redirect_to_https = False
        if https_enabled:
            http_url = url.replace("https://", "http://", 1)
            try:
                redir_resp = session.get(http_url, allow_redirects=False, timeout=10)
                if redir_resp.status_code in (301, 302):
                    location = redir_resp.headers.get("Location", "")
                    redirect_to_https = location.startswith("https")
            except Exception:
                pass

        # Mixed content detection
        mixed_content = False
        if https_enabled:
            http_resources = re.findall(r'(src|href)=["\']http://', response.text)
            mixed_content = len(http_resources) > 0

        return {
            "https_enabled": https_enabled,
            "valid_certificate": True,
            "redirect_to_https": redirect_to_https,
            "mixed_content": mixed_content,
        }
    except requests.exceptions.SSLError:
        return {
            "https_enabled": url.startswith("https"),
            "valid_certificate": False,
            "error": "SSL certificate error",
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# check_redirects
# ---------------------------------------------------------------------------

def check_redirects(url: str) -> dict:
    """Check redirect chain depth and final URL."""
    url = _normalize_url(url)
    session = _make_session()
    try:
        response = session.get(url, allow_redirects=True, timeout=10)
        redirect_chain = [
            {"url": h.url, "status_code": h.status_code}
            for h in response.history
        ]
        return {
            "final_url": response.url,
            "redirect_count": len(response.history),
            "redirect_chain": redirect_chain,
            "has_redirect_chain": len(response.history) > 1,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# check_security_headers
# ---------------------------------------------------------------------------

def check_security_headers(url: str) -> dict:
    """Check X-Frame-Options, HSTS, CSP, X-Content-Type-Options."""
    url = _normalize_url(url)
    session = _make_session()
    try:
        response = session.get(url, timeout=10)
        headers = response.headers
        return {
            "x_frame_options": headers.get("X-Frame-Options"),
            "x_content_type_options": headers.get("X-Content-Type-Options"),
            "strict_transport_security": headers.get("Strict-Transport-Security"),
            "content_security_policy": headers.get("Content-Security-Policy") is not None,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# check_page_speed
# ---------------------------------------------------------------------------

def check_page_speed(url: str) -> dict:
    """Check response time, page size, compression, cache headers, ETag."""
    url = _normalize_url(url)
    session = _make_session()
    try:
        response = session.get(url, timeout=10)
        return {
            "response_time": response.elapsed.total_seconds(),
            "page_size": len(response.content),
            "compression": "gzip" in response.headers.get("Content-Encoding", ""),
            "cache_control": response.headers.get("Cache-Control"),
            "etag": response.headers.get("ETag") is not None,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# check_sitemap
# ---------------------------------------------------------------------------

def _validate_xml(content: str) -> bool:
    try:
        ElementTree.fromstring(content)
        return True
    except Exception:
        return False


def _get_sitemap_lastmod(content: str):
    lastmods = re.findall(r"<lastmod>([^<]+)</lastmod>", content)
    return max(lastmods) if lastmods else None


def check_sitemap(url: str) -> dict:
    """Check sitemap existence, URL count, valid XML, lastmod."""
    url = _normalize_url(url)
    session = _make_session()
    sitemap_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps/sitemap.xml",
    ]
    last_error = None
    try:
        for path in sitemap_paths:
            sitemap_url = urljoin(url + "/", path.lstrip("/"))
            try:
                response = session.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    return {
                        "exists": True,
                        "url": sitemap_url,
                        "valid_xml": _validate_xml(response.text),
                        "url_count": response.text.count("<url>"),
                        "last_modified": _get_sitemap_lastmod(response.text),
                    }
            except Exception as e:
                last_error = e
                continue
        if last_error:
            return {"exists": False, "error": str(last_error)}
        return {"exists": False, "checked_paths": sitemap_paths}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# check_cwv_heuristic  (no HTTP — works on raw HTML + response_time)
# ---------------------------------------------------------------------------

# 2024 Core Web Vitals thresholds:
#   LCP: <2.5s good, 2.5-4.0s needs improvement, >4.0s poor
#   INP: <200ms good, 200-500ms needs improvement, >500ms poor
#   CLS: <0.1 good, 0.1-0.25 needs improvement, >0.25 poor

def check_cwv_heuristic(html: str, response_time: float) -> dict:
    """Estimate Core Web Vitals from HTML when Lighthouse MCP is unavailable.

    Args:
        html: raw HTML string of the page
        response_time: server response time in seconds

    Returns:
        dict with lcp_estimate, inp_risk, cls_risk, source
    """
    soup = BeautifulSoup(html, "html.parser")

    # ----- LCP heuristic -----
    has_preload = bool(soup.find("link", attrs={"rel": "preload", "as": "image"}))
    has_critical_css = bool(soup.find("style"))

    if response_time > 2.5:
        lcp_estimate = "poor"
    elif response_time <= 1.5 and has_preload:
        lcp_estimate = "good"
    elif response_time <= 2.5 and (has_preload or has_critical_css):
        lcp_estimate = "good"
    else:
        lcp_estimate = "needs_improvement"

    # ----- INP heuristic -----
    all_scripts = soup.find_all("script", src=True)
    sync_scripts = [
        s for s in all_scripts
        if not s.get("defer") and not s.get("async") and s.get("defer") != ""
    ]
    sync_count = len(sync_scripts)

    if sync_count >= 4:
        inp_risk = "high"
    elif sync_count >= 3:
        inp_risk = "medium"
    else:
        inp_risk = "low"

    # ----- CLS heuristic -----
    images = soup.find_all("img")
    if images:
        imgs_without_dims = [
            img for img in images
            if not (img.get("width") and img.get("height"))
        ]
        ratio = len(imgs_without_dims) / len(images)
        if ratio > 0.5:
            cls_risk = "high"
        elif ratio > 0:
            cls_risk = "medium"
        else:
            cls_risk = "low"
    else:
        cls_risk = "low"

    return {
        "lcp_estimate": lcp_estimate,
        "inp_risk": inp_risk,
        "cls_risk": cls_risk,
        "source": "heuristic",
    }


# ---------------------------------------------------------------------------
# check_all
# ---------------------------------------------------------------------------

def check_all(url: str) -> dict:
    """Run all technical checks and return combined dict."""
    result = {}

    # Each sub-check is wrapped so one failure doesn't stop the rest
    for key, fn in [
        ("ssl", lambda: check_ssl(url)),
        ("redirects", lambda: check_redirects(url)),
        ("security_headers", lambda: check_security_headers(url)),
        ("page_speed", lambda: check_page_speed(url)),
        ("sitemap", lambda: check_sitemap(url)),
    ]:
        try:
            result[key] = fn()
        except Exception as e:
            result[key] = {"error": str(e)}

    # CWV heuristic needs HTML + response_time from page_speed
    page_speed = result.get("page_speed", {})
    response_time = page_speed.get("response_time", 1.0)

    # Fetch page HTML for CWV analysis
    try:
        session = _make_session()
        resp = session.get(_normalize_url(url), timeout=10)
        html = resp.text
    except Exception:
        html = ""

    try:
        result["cwv_heuristic"] = check_cwv_heuristic(html, response_time)
    except Exception as e:
        result["cwv_heuristic"] = {"error": str(e)}

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 technical_checker.py <url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    results = check_all(url)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
