#!/usr/bin/env python3
"""
GEO/AEO Page Analyzer
Extracts structured data from HTML for AI search visibility scoring.
"""

import json
import re
import sys
from urllib.parse import urlparse
from bs4 import BeautifulSoup


# Regex patterns for detection
STAT_PATTERN = re.compile(
    r"\b\d[\d,]*\.?\d*\s*(%|percent|million|billion|thousand)\b|\b\d[\d,]{2,}\b",
    re.IGNORECASE,
)
QUOTE_PATTERN = re.compile(r'["\u201c][^"\u201d]{20,}["\u201d]')
CITATION_PATTERN = re.compile(
    r"(?:according to|per|cited by|reported by|published (?:in|by)|"
    r"\d{4}\s+\w+\s+(?:study|report|survey|research|analysis))",
    re.IGNORECASE,
)
VAGUE_PATTERN = re.compile(
    r"\b(?:research shows|studies show|experts say|industry-leading|"
    r"cutting-edge|world-class|best-in-class|state-of-the-art|"
    r"some people|many believe|it is said)\b",
    re.IGNORECASE,
)
ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"  # Multi-word proper nouns
    r"|\b(?:[A-Z]{2,})\b"  # Acronyms like PMI, CEO
)
FAQ_INDICATORS = re.compile(
    r"(?:frequently asked|faq|common questions|q\s*&\s*a|q:)", re.IGNORECASE
)

# Known AI crawler bot names
AI_BOTS = ["GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
           "PerplexityBot", "Google-Extended", "Amazonbot", "Bytespider", "CCBot"]

EXPECTED_META = ["description", "og:title", "og:description", "og:image"]
EXPECTED_SCHEMA = ["Article", "FAQPage", "HowTo", "BreadcrumbList",
                   "Organization", "WebPage", "Service"]


def analyze_html(html: str, url: str = "", robots_txt: str = "") -> dict:
    """Analyze HTML content and return structured extraction JSON."""
    soup = BeautifulSoup(html, "html.parser")
    # Make a copy for technical SSR check (which decomposes script/style tags)
    soup_tech = BeautifulSoup(html, "html.parser")
    content = extract_content(soup)
    result = {
        "url": url,
        "meta": extract_meta(soup, url),
        "headings": extract_headings(soup),
        "content": content,
        "authority": extract_authority(soup),
        "technical": extract_technical(soup_tech, robots_txt),
        "anti_patterns": extract_anti_patterns(soup, content),
    }
    return result


def extract_meta(soup: BeautifulSoup, url: str) -> dict:
    """Extract meta tags, title, dates, URL structure."""
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else ""

    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical = canonical_tag.get("href", "") if canonical_tag else ""

    pub_date = ""
    mod_date = ""
    for attr in ["article:published_time", "publication_date", "date"]:
        tag = soup.find("meta", attrs={"name": attr}) or soup.find("meta", attrs={"property": attr})
        if tag:
            pub_date = tag.get("content", "")
            break

    for attr in ["article:modified_time", "last-modified", "updated_time"]:
        tag = soup.find("meta", attrs={"name": attr}) or soup.find("meta", attrs={"property": attr})
        if tag:
            mod_date = tag.get("content", "")
            break

    # URL semantic analysis
    parsed = urlparse(url)
    path_words = [w for w in re.split(r"[/\-_.]", parsed.path) if w and not w.isdigit()]
    url_word_count = len(path_words)
    url_is_semantic = 1 <= url_word_count <= 7

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "published_date": pub_date,
        "modified_date": mod_date,
        "url_word_count": url_word_count,
        "url_is_semantic": url_is_semantic,
    }


def extract_headings(soup: BeautifulSoup) -> dict:
    """Extract heading hierarchy."""
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3s = [h.get_text(strip=True) for h in soup.find_all("h3")]

    # Check hierarchy: should have exactly 1 H1, H2s before H3s make sense
    hierarchy_valid = len(h1s) == 1

    return {
        "h1": h1s,
        "h2": h2s,
        "h3": h3s,
        "hierarchy_valid": hierarchy_valid,
    }


def extract_content(soup: BeautifulSoup) -> dict:
    """Extract content structure and per-section signals."""
    body = soup.find("body") or soup
    paragraphs = body.find_all("p")
    all_text = body.get_text(separator=" ", strip=True)
    words = all_text.split()

    lists = body.find_all(["ul", "ol"])
    tables = body.find_all("table")
    faq_detected = bool(FAQ_INDICATORS.search(all_text))

    # Build sections from headings
    sections = build_sections(body)

    return {
        "word_count": len(words),
        "paragraph_count": len(paragraphs),
        "avg_paragraph_length": (
            sum(len(p.get_text().split()) for p in paragraphs) // max(len(paragraphs), 1)
        ),
        "list_count": len(lists),
        "table_count": len(tables),
        "faq_detected": faq_detected,
        "sections": sections,
    }


def build_sections(body) -> list:
    """Split page into sections based on H2/H3 headings."""
    sections = []
    current_heading = "(intro)"
    current_text_parts = []

    for element in body.descendants:
        if element.name in ("h2", "h3"):
            if current_text_parts:
                text = " ".join(current_text_parts)
                sections.append(make_section(current_heading, text))
            current_heading = element.get_text(strip=True)
            current_text_parts = []
        elif element.name == "p":
            current_text_parts.append(element.get_text(strip=True))

    # Don't forget the last section
    if current_text_parts:
        text = " ".join(current_text_parts)
        sections.append(make_section(current_heading, text))

    return sections


def make_section(heading: str, text: str) -> dict:
    """Create a section dict with signal detection."""
    return {
        "heading": heading,
        "text": text,
        "word_count": len(text.split()),
        "has_stats": bool(STAT_PATTERN.search(text)),
        "has_citations": bool(CITATION_PATTERN.search(text)),
        "has_quotes": bool(QUOTE_PATTERN.search(text)),
    }


def extract_authority(soup: BeautifulSoup) -> dict:
    """Extract authority signals from page content."""
    body = soup.find("body") or soup
    text = body.get_text(separator=" ", strip=True)

    stats = STAT_PATTERN.findall(text)
    citations = CITATION_PATTERN.findall(text)
    quotes = QUOTE_PATTERN.findall(text)
    entities = list(set(ENTITY_PATTERN.findall(text)))
    vague = [m.group() for m in VAGUE_PATTERN.finditer(text)]

    return {
        "statistics_count": len(stats),
        "citation_count": len(citations),
        "quote_count": len(quotes),
        "named_entities": entities,
        "vague_claims": vague,
    }


def extract_technical(soup: BeautifulSoup, robots_txt: str = "") -> dict:
    """Extract technical crawlability signals."""
    # Schema markup
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    schema_types = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and "@type" in data:
                schema_types.append(data["@type"])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        schema_types.append(item["@type"])
        except (json.JSONDecodeError, TypeError):
            continue

    schema_missing = [s for s in EXPECTED_SCHEMA if s not in schema_types]

    # Meta tags present/missing
    meta_present = []
    if soup.find("meta", attrs={"name": "description"}):
        meta_present.append("description")
    for og in ["og:title", "og:description", "og:image"]:
        if soup.find("meta", attrs={"property": og}):
            meta_present.append(og)
    meta_missing = [m for m in EXPECTED_META if m not in meta_present]

    # AI bot access from robots.txt
    ai_bots_blocked = []
    ai_bots_allowed = []
    if robots_txt:
        for bot in AI_BOTS:
            if re.search(rf"User-agent:\s*{bot}.*?Disallow:\s*/\s*$", robots_txt,
                         re.MULTILINE | re.DOTALL):
                ai_bots_blocked.append(bot)
            else:
                ai_bots_allowed.append(bot)
    else:
        ai_bots_allowed = list(AI_BOTS)  # Assume allowed if no robots.txt provided

    # SSR detection: does the body have meaningful text content?
    body = soup.find("body") or soup
    # Strip out script/style content for word count
    for tag in body.find_all(["script", "style"]):
        tag.decompose()
    clean_text = body.get_text(separator=" ", strip=True)
    is_ssr = len(clean_text.split()) > 20

    return {
        "schema_types": schema_types,
        "schema_missing": schema_missing,
        "ai_bots_blocked": ai_bots_blocked,
        "ai_bots_allowed": ai_bots_allowed,
        "meta_tags_present": meta_present,
        "meta_tags_missing": meta_missing,
        "is_ssr": is_ssr,
    }


def extract_anti_patterns(soup: BeautifulSoup, content_data: dict) -> dict:
    """Detect GEO/AEO anti-patterns."""
    body = soup.find("body") or soup
    text = body.get_text(separator=" ", strip=True)

    # Keyword stuffing: any single word appearing > 3% of total words
    words = text.lower().split()
    total = max(len(words), 1)
    from collections import Counter
    word_counts = Counter(words)
    # Filter out common stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "and", "or", "but", "not", "that", "this", "it", "as", "if"}
    keyword_flags = [
        w for w, c in word_counts.items()
        if c / total > 0.03 and w not in stop_words and len(w) > 3
    ]

    # Thin sections (< 30 words under a heading)
    thin = [s["heading"] for s in content_data.get("sections", [])
            if s["word_count"] < 30 and s["heading"] != "(intro)"]

    # Wall of text sections (> 300 words with no sub-headings)
    walls = [s["heading"] for s in content_data.get("sections", [])
             if s["word_count"] > 300]

    # Unsourced claims
    unsourced = [m.group() for m in VAGUE_PATTERN.finditer(text)]

    return {
        "keyword_density_flags": keyword_flags,
        "thin_sections": thin,
        "wall_of_text_sections": walls,
        "unsourced_claims": unsourced,
    }


def main():
    """CLI entry point: analyze a local HTML file or URL."""
    import argparse
    parser = argparse.ArgumentParser(description="GEO/AEO Page Analyzer")
    parser.add_argument("--file", help="Path to local HTML file")
    parser.add_argument("--url", help="URL (expects HTML via stdin if no --file)")
    parser.add_argument("--robots", help="Path to robots.txt file", default="")
    args = parser.parse_args()

    robots_txt = ""
    if args.robots:
        with open(args.robots) as f:
            robots_txt = f.read()

    if args.file:
        with open(args.file) as f:
            html = f.read()
        url = args.url or ""
    else:
        html = sys.stdin.read()
        url = args.url or ""

    result = analyze_html(html, url, robots_txt)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
