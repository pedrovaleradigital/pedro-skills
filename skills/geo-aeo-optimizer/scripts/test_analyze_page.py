"""Tests for analyze_page.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from analyze_page import analyze_html

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Best Project Management Tools for Small Teams | Acme PM</title>
    <meta name="description" content="Compare the top 5 project management tools for teams under 20 people.">
    <meta property="og:title" content="Best PM Tools for Small Teams">
    <meta property="og:description" content="Compare top 5 PM tools">
    <link rel="canonical" href="https://acme.com/pm-tools">
    <meta name="article:published_time" content="2026-01-15">
    <meta name="article:modified_time" content="2026-02-10">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Article", "headline": "Best PM Tools"}
    </script>
</head>
<body>
    <h1>Best Project Management Tools for Small Teams in 2026</h1>
    <p>Managing a small team is hard. According to a 2025 PMI study, 67% of small teams fail to deliver projects on time.</p>
    <h2>Why This Matters</h2>
    <p>Research shows that productivity tools matter.</p>
    <h2>Top 5 Tools Compared</h2>
    <table><tr><td>Tool</td><td>Price</td></tr></table>
    <ul><li>Asana</li><li>Monday.com</li></ul>
    <h3>1. Asana</h3>
    <p>"Asana transformed how our 12-person team collaborates," says Jane Smith, CEO of TechStartup Inc.</p>
    <p>Asana serves over 130,000 paying customers as of 2025.</p>
    <h3>2. Monday.com</h3>
    <p>Some people like Monday.com. Experts say it's good for visual learners.</p>
</body>
</html>"""


def test_meta_extraction():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    meta = result["meta"]
    assert meta["title"] == "Best Project Management Tools for Small Teams | Acme PM"
    assert "top 5 project management" in meta["description"].lower()
    assert meta["canonical"] == "https://acme.com/pm-tools"
    assert meta["published_date"] == "2026-01-15"
    assert meta["modified_date"] == "2026-02-10"
    assert meta["url_word_count"] == 2  # "pm" and "tools"
    assert meta["url_is_semantic"] is True


def test_heading_extraction():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    headings = result["headings"]
    assert len(headings["h1"]) == 1
    assert "Project Management" in headings["h1"][0]
    assert len(headings["h2"]) == 2
    assert len(headings["h3"]) == 2
    assert headings["hierarchy_valid"] is True


def test_content_extraction():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    content = result["content"]
    assert content["word_count"] > 50
    assert content["paragraph_count"] >= 4
    assert content["list_count"] >= 1
    assert content["table_count"] >= 1
    assert content["faq_detected"] is False
    assert len(content["sections"]) >= 2


def test_authority_extraction():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    auth = result["authority"]
    assert auth["statistics_count"] >= 2  # "67%", "130,000"
    assert auth["citation_count"] >= 1  # "2025 PMI study"
    assert auth["quote_count"] >= 1  # Jane Smith quote
    assert "PMI" in auth["named_entities"] or "TechStartup Inc" in auth["named_entities"]
    assert len(auth["vague_claims"]) >= 1  # "Research shows", "Experts say"


def test_section_level_signals():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    sections = result["content"]["sections"]
    # Find the section with "Why This Matters"
    why_section = [s for s in sections if "Why This Matters" in s["heading"]]
    assert len(why_section) == 1
    assert why_section[0]["has_stats"] is False
    assert why_section[0]["has_citations"] is False


def test_technical_extraction():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    tech = result["technical"]
    assert "Article" in tech["schema_types"]
    assert tech["meta_tags_present"]  # at least description, og:title
    assert "description" in tech["meta_tags_present"]


def test_anti_pattern_detection():
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    anti = result["anti_patterns"]
    assert isinstance(anti["keyword_density_flags"], list)
    assert isinstance(anti["thin_sections"], list)
    assert isinstance(anti["wall_of_text_sections"], list)
    assert isinstance(anti["unsourced_claims"], list)
    # "Research shows" and "Experts say" should be flagged
    assert len(anti["unsourced_claims"]) >= 1


def test_ssr_detection_with_content():
    """Page with real content should be detected as SSR."""
    result = analyze_html(SAMPLE_HTML, "https://acme.com/pm-tools")
    assert result["technical"]["is_ssr"] is True


def test_ssr_detection_empty_body():
    """Page with only a script tag should be detected as client-rendered."""
    empty_html = """<html><head><title>My App</title></head>
    <body><script src="app.js"></script></body></html>"""
    result = analyze_html(empty_html, "https://example.com")
    assert result["technical"]["is_ssr"] is False


COMPLEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>10 AI Tools Every Small Business Needs in 2026 | SmartBiz</title>
    <meta name="description" content="Comprehensive guide to the 10 best AI tools for small businesses in 2026, with pricing, features, and ROI data.">
    <meta property="og:title" content="10 AI Tools for Small Businesses">
    <meta property="og:description" content="Best AI tools guide 2026">
    <meta property="og:image" content="https://smartbiz.com/og-ai-tools.jpg">
    <link rel="canonical" href="https://smartbiz.com/ai-tools-2026">
    <meta name="article:published_time" content="2026-02-01">
    <meta name="article:modified_time" content="2026-02-20">
    <script type="application/ld+json">
    [
        {"@context": "https://schema.org", "@type": "Article", "headline": "10 AI Tools"},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
    ]
    </script>
</head>
<body>
    <h1>10 AI Tools Every Small Business Needs in 2026</h1>
    <p>Small businesses that adopt AI tools see an average 23% increase in productivity, according to a 2025 McKinsey Global Survey. Here are the tools that deliver the highest ROI.</p>
    <h2>Why AI Matters for Small Business</h2>
    <p>According to Gartner's 2025 SMB Technology Report, 64% of small businesses plan to increase AI spending in 2026. "The businesses that adopt AI early will have an insurmountable advantage in 3-5 years," says Dr. Sarah Mitchell, Director of AI Research at Stanford's HAI.</p>
    <h2>Top 10 Tools</h2>
    <table><tr><th>Tool</th><th>Price</th><th>Best For</th></tr>
    <tr><td>Claude</td><td>$20/mo</td><td>Writing &amp; Analysis</td></tr>
    <tr><td>Jasper</td><td>$49/mo</td><td>Marketing Content</td></tr></table>
    <h3>1. Claude by Anthropic</h3>
    <p>Anthropic's Claude processes 200K tokens of context, making it ideal for analyzing business documents. In our testing with 50 small businesses, Claude reduced report generation time by 67%.</p>
    <h3>2. Jasper</h3>
    <p>Jasper is a good tool. Many businesses use it. It's industry-leading in content generation.</p>
    <h2>Frequently Asked Questions</h2>
    <p><strong>Q: How much should a small business budget for AI tools?</strong></p>
    <p>A: Based on Forrester's 2025 analysis, small businesses should allocate 5-8% of their technology budget to AI tools, with an expected ROI of 150-300% within the first year.</p>
    <p><strong>Q: Do I need technical skills?</strong></p>
    <p>A: No. According to a 2025 Salesforce survey, 78% of AI tools now require zero coding knowledge.</p>
</body>
</html>"""


def test_full_pipeline_complex():
    """Integration test: full extraction on a realistic page."""
    result = analyze_html(COMPLEX_HTML, "https://smartbiz.com/ai-tools-2026")

    # Meta
    assert result["meta"]["url_is_semantic"] is True
    assert result["meta"]["published_date"] == "2026-02-01"

    # Content
    assert result["content"]["table_count"] >= 1
    assert result["content"]["faq_detected"] is True
    assert result["content"]["word_count"] > 150

    # Authority — should find multiple signals
    assert result["authority"]["statistics_count"] >= 4  # 23%, 64%, 67%, 200K, 50, 78%, 150-300%
    assert result["authority"]["citation_count"] >= 3  # McKinsey, Gartner, Forrester
    assert result["authority"]["quote_count"] >= 1  # Dr. Sarah Mitchell
    assert len(result["authority"]["named_entities"]) >= 3

    # Technical
    assert "Article" in result["technical"]["schema_types"]
    assert "FAQPage" in result["technical"]["schema_types"]
    assert result["technical"]["is_ssr"] is True

    # Anti-patterns: Jasper section has vague claims
    assert len(result["anti_patterns"]["unsourced_claims"]) >= 1

    # This page should score well overall (Claude does the scoring, but extraction should be rich)
    print(json.dumps(result, indent=2, default=str))


def test_cli_with_html_file(tmp_path):
    """Test CLI reads from HTML file."""
    html_file = tmp_path / "test.html"
    html_file.write_text(SAMPLE_HTML)
    result = subprocess.run(
        [sys.executable, "analyze_page.py", "--file", str(html_file)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "meta" in data
    assert "content" in data
    assert "authority" in data
