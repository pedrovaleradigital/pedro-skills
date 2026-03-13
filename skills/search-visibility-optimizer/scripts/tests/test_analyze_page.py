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


# ===========================================================================
# Existing tests (from geo-aeo-optimizer — must all still pass)
# ===========================================================================

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
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "meta" in data
    assert "content" in data
    assert "authority" in data


# ===========================================================================
# NEW: E-E-A-T extraction tests
# ===========================================================================

def test_eeat_person_schema_detected():
    """Person JSON-LD schema should be extracted with sameAs, knowsAbout."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Person",
     "name": "Jane Smith",
     "sameAs": ["https://linkedin.com/in/janesmith"],
     "knowsAbout": ["AI", "Business"],
     "honorificSuffix": "PhD",
     "alumniOf": "MIT"}
    </script>
    </head><body>
    <h1>Article Title</h1>
    <p>Some content about AI and business trends that matters.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    eeat = result["eeat"]
    assert eeat["person_schema"]["name"] == "Jane Smith"
    assert len(eeat["person_schema"]["sameAs"]) == 1
    assert "AI" in eeat["person_schema"]["knowsAbout"]
    assert eeat["person_schema"]["honorificSuffix"] == "PhD"
    assert eeat["person_schema"]["alumniOf"] == "MIT"


def test_eeat_author_bio_detected():
    """Author bio patterns like 'About the Author' should be detected."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Article Title</h1>
    <p>Main content here about important topics and how they affect business.</p>
    <h2>About the Author</h2>
    <p>Jane Smith is a certified business coach with 15 years of experience.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    assert result["eeat"]["author_bio_detected"] is True


def test_eeat_written_by_detected():
    """'Written by' pattern should be detected as author bio."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Article Title</h1>
    <p>Written by Dr. John Doe, a leading expert in cybersecurity.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    assert result["eeat"]["author_bio_detected"] is True


def test_eeat_rel_author_detected():
    """rel='author' link should be detected."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Article Title</h1>
    <p>Some content about business strategies and growth hacking techniques.</p>
    <a rel="author" href="/authors/jane">Jane Smith</a>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    assert result["eeat"]["author_bio_detected"] is True


def test_eeat_no_signals():
    """Page with no E-E-A-T signals should return empty/false values."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Article Title</h1>
    <p>Just some generic content without any author information or schema.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    eeat = result["eeat"]
    assert eeat["author_bio_detected"] is False
    assert eeat["person_schema"]["name"] is None
    assert eeat["credentials_visible"] is False


def test_eeat_org_schema():
    """Organization schema sameAs links should be extracted."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization",
     "name": "Acme Inc",
     "sameAs": ["https://twitter.com/acme", "https://linkedin.com/company/acme"]}
    </script>
    </head><body>
    <h1>About Acme</h1>
    <p>Acme Inc is a technology company that builds software solutions.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    assert result["eeat"]["org_schema"]["sameAs_count"] == 2


def test_eeat_article_dates_in_schema():
    """datePublished and dateModified in Article JSON-LD should be detected."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Article",
     "headline": "Test Article",
     "datePublished": "2026-01-15",
     "dateModified": "2026-02-10"}
    </script>
    </head><body>
    <h1>Test Article</h1>
    <p>Content about testing and software development best practices today.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    eeat = result["eeat"]
    assert eeat["article_dates"]["datePublished"] == "2026-01-15"
    assert eeat["article_dates"]["dateModified"] == "2026-02-10"


def test_eeat_credentials_visible():
    """Person schema with honorificSuffix or knowsAbout should set credentials_visible."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Person",
     "name": "Dr. Jane Smith",
     "honorificSuffix": "PhD",
     "knowsAbout": ["Machine Learning"]}
    </script>
    </head><body>
    <h1>About Dr. Smith</h1>
    <p>Dr. Jane Smith is an expert in machine learning and artificial intelligence research.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    assert result["eeat"]["credentials_visible"] is True


# ===========================================================================
# NEW: llms.txt parsing tests
# ===========================================================================

def test_llms_txt_parsing():
    """llms.txt content should be parsed for entries and descriptions."""
    llms_content = (
        "# My Site\n"
        "> A great site about technology\n"
        "\n"
        "- [Page 1](https://example.com/page1): A useful page\n"
        "- [Page 2](https://example.com/page2): Another page\n"
    )
    result = analyze_html(SAMPLE_HTML, "https://example.com", llms_txt=llms_content)
    assert result["llms_txt"]["exists"] is True
    assert result["llms_txt"]["entries"] == 2
    assert result["llms_txt"]["has_descriptions"] is True


def test_llms_txt_no_descriptions():
    """llms.txt entries without descriptions (no colon after URL)."""
    llms_content = (
        "# My Site\n"
        "\n"
        "- [Page 1](https://example.com/page1)\n"
        "- [Page 2](https://example.com/page2)\n"
    )
    result = analyze_html(SAMPLE_HTML, "https://example.com", llms_txt=llms_content)
    assert result["llms_txt"]["exists"] is True
    assert result["llms_txt"]["entries"] == 2
    assert result["llms_txt"]["has_descriptions"] is False


def test_llms_txt_empty():
    """Empty llms_txt string should show as not existing."""
    result = analyze_html(SAMPLE_HTML, "https://example.com", llms_txt="")
    assert result["llms_txt"]["exists"] is False
    assert result["llms_txt"]["entries"] == 0


def test_llms_txt_none():
    """No llms_txt parameter should show as not existing."""
    result = analyze_html(SAMPLE_HTML, "https://example.com")
    assert result["llms_txt"]["exists"] is False


# ===========================================================================
# NEW: AI crawler classification tests
# ===========================================================================

def test_ai_crawler_classification_training_blocked():
    """Training bots should be classified separately from citation bots."""
    robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: ChatGPT-User\nAllow: /"
    result = analyze_html(SAMPLE_HTML, "https://example.com", robots_txt=robots)
    tech = result["technical"]
    assert "GPTBot" in tech["training_bots_blocked"]
    assert "GPTBot" not in tech["training_bots_allowed"]
    assert "ChatGPT-User" in tech["citation_bots_allowed"]
    assert "ChatGPT-User" not in tech["citation_bots_blocked"]


def test_ai_crawler_classification_citation_blocked():
    """Citation bots blocked should appear in citation_bots_blocked."""
    robots = "User-agent: PerplexityBot\nDisallow: /\n\nUser-agent: Claude-Web\nDisallow: /"
    result = analyze_html(SAMPLE_HTML, "https://example.com", robots_txt=robots)
    tech = result["technical"]
    assert "PerplexityBot" in tech["citation_bots_blocked"]
    assert "Claude-Web" in tech["citation_bots_blocked"]


def test_ai_crawler_backward_compat():
    """Old ai_bots_blocked/ai_bots_allowed keys should still be present."""
    robots = "User-agent: GPTBot\nDisallow: /"
    result = analyze_html(SAMPLE_HTML, "https://example.com", robots_txt=robots)
    tech = result["technical"]
    # Backward compat keys must still exist
    assert "ai_bots_blocked" in tech
    assert "ai_bots_allowed" in tech
    assert "GPTBot" in tech["ai_bots_blocked"]


def test_ai_crawler_no_robots():
    """No robots.txt means all bots allowed."""
    result = analyze_html(SAMPLE_HTML, "https://example.com")
    tech = result["technical"]
    assert len(tech["training_bots_blocked"]) == 0
    assert len(tech["citation_bots_blocked"]) == 0
    assert len(tech["training_bots_allowed"]) > 0
    assert len(tech["citation_bots_allowed"]) > 0


# ===========================================================================
# NEW: Answer-first detection tests
# ===========================================================================

def test_answer_first_detection_true():
    """Section starting with a direct answer (number, under 30 words, period) should be detected."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>AI Tools Guide</h1>
    <p>Introduction paragraph about technology tools and modern business approaches.</p>
    <h2>What is GEO?</h2>
    <p>GEO is a set of 16 techniques that increase AI citation probability by 37%.</p>
    <p>Additional context about GEO and its importance in search optimization.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    sections = result["content"]["sections"]
    geo_section = [s for s in sections if "GEO" in s["heading"]]
    assert len(geo_section) == 1
    assert geo_section[0]["answer_first"] is True


def test_answer_first_detection_false_no_number():
    """Section starting with vague text (no number/entity) should not be answer-first."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Guide to Tools</h1>
    <p>Introduction paragraph about various topics and their relevance to business today.</p>
    <h2>Why This Matters</h2>
    <p>Research shows that productivity tools matter a lot for teams.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    sections = result["content"]["sections"]
    why_section = [s for s in sections if "Why This Matters" in s["heading"]]
    assert len(why_section) == 1
    assert why_section[0]["answer_first"] is False


def test_answer_first_detection_false_too_long():
    """Section starting with a very long sentence should not be answer-first."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Long Guide Title</h1>
    <p>Introduction about the guide and what readers will learn about business.</p>
    <h2>Complex Topic</h2>
    <p>This is a really long sentence that goes on and on about many different topics and subtopics and includes a lot of words that make it unsuitable as a direct answer to any specific question because it tries to cover too much ground at once and fails to be concise in any meaningful way which is problematic.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    sections = result["content"]["sections"]
    complex_section = [s for s in sections if "Complex Topic" in s["heading"]]
    assert len(complex_section) == 1
    assert complex_section[0]["answer_first"] is False


def test_answer_first_with_named_entity():
    """Section starting with a named entity (capitalized multi-word) should be answer-first."""
    html = """<!DOCTYPE html><html><head><title>Test</title></head><body>
    <h1>Business Software Guide</h1>
    <p>Introduction about software and how it affects small business operations.</p>
    <h2>Who Created Asana?</h2>
    <p>Dustin Moskovitz founded Asana in 2008 to help teams coordinate work.</p>
    </body></html>"""
    result = analyze_html(html, "https://example.com")
    sections = result["content"]["sections"]
    who_section = [s for s in sections if "Asana" in s["heading"]]
    assert len(who_section) == 1
    assert who_section[0]["answer_first"] is True


# ===========================================================================
# NEW: X-Robots-Tag tests
# ===========================================================================

def test_x_robots_tag_noindex():
    """X-Robots-Tag with noindex should be captured."""
    headers = {"X-Robots-Tag": "noindex, nofollow"}
    result = analyze_html(SAMPLE_HTML, "https://example.com", headers_json=headers)
    assert result["x_robots_tag"] == "noindex, nofollow"


def test_x_robots_tag_absent():
    """No X-Robots-Tag should return None."""
    result = analyze_html(SAMPLE_HTML, "https://example.com")
    assert result["x_robots_tag"] is None


def test_x_robots_tag_empty_headers():
    """Empty headers dict should result in no X-Robots-Tag."""
    result = analyze_html(SAMPLE_HTML, "https://example.com", headers_json={})
    assert result["x_robots_tag"] is None


def test_x_robots_tag_nofollow_only():
    """X-Robots-Tag with only nofollow."""
    headers = {"X-Robots-Tag": "nofollow"}
    result = analyze_html(SAMPLE_HTML, "https://example.com", headers_json=headers)
    assert result["x_robots_tag"] == "nofollow"


# ===========================================================================
# NEW: CLI tests for new arguments
# ===========================================================================

def test_cli_with_llms_txt(tmp_path):
    """CLI --llms-txt flag should parse llms.txt file."""
    html_file = tmp_path / "test.html"
    html_file.write_text(SAMPLE_HTML)
    llms_file = tmp_path / "llms.txt"
    llms_file.write_text("# My Site\n\n- [Page 1](https://example.com/p1): Desc\n")
    result = subprocess.run(
        [sys.executable, "analyze_page.py", "--file", str(html_file),
         "--llms-txt", str(llms_file)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["llms_txt"]["exists"] is True
    assert data["llms_txt"]["entries"] == 1


def test_cli_with_headers_json(tmp_path):
    """CLI --headers-json flag should parse HTTP response headers."""
    html_file = tmp_path / "test.html"
    html_file.write_text(SAMPLE_HTML)
    headers_file = tmp_path / "headers.json"
    headers_file.write_text(json.dumps({"X-Robots-Tag": "noindex"}))
    result = subprocess.run(
        [sys.executable, "analyze_page.py", "--file", str(html_file),
         "--headers-json", str(headers_file)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["x_robots_tag"] == "noindex"
