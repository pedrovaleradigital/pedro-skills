#!/usr/bin/env python3
"""
Search Visibility Page Analyzer
Extracts structured data from HTML for AI search visibility scoring.
Expanded from geo-aeo-optimizer with E-E-A-T, llms.txt, AI crawler
classification, answer-first detection, and X-Robots-Tag support.
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

# AI crawler bot classifications
TRAINING_BOTS = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot"]
CITATION_BOTS = ["ChatGPT-User", "PerplexityBot", "Claude-Web", "Amazonbot", "Bytespider"]
# Combined list for backward compatibility
AI_BOTS = TRAINING_BOTS + CITATION_BOTS

# Author bio detection patterns
AUTHOR_BIO_PATTERNS = re.compile(
    r"(?:about the author|written by|authored by)", re.IGNORECASE
)

EXPECTED_META = ["description", "og:title", "og:description", "og:image"]
EXPECTED_SCHEMA = ["Article", "FAQPage", "HowTo", "BreadcrumbList",
                   "Organization", "WebPage", "Service"]


def analyze_html(html: str, url: str = "", robots_txt: str = "",
                 llms_txt: str = "", headers_json: dict = None) -> dict:
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
        "eeat": extract_eeat(BeautifulSoup(html, "html.parser")),
        "llms_txt": parse_llms_txt(llms_txt),
        "x_robots_tag": extract_x_robots_tag(headers_json),
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
    """Create a section dict with signal detection and answer-first check."""
    return {
        "heading": heading,
        "text": text,
        "word_count": len(text.split()),
        "has_stats": bool(STAT_PATTERN.search(text)),
        "has_citations": bool(CITATION_PATTERN.search(text)),
        "has_quotes": bool(QUOTE_PATTERN.search(text)),
        "answer_first": _is_answer_first(text),
    }


def _is_answer_first(text: str) -> bool:
    """Check if the first sentence is a direct answer.

    Criteria:
    - Ends with a period
    - Under 30 words
    - Contains a number or named entity (multi-word capitalized or acronym)
    """
    if not text:
        return False
    # Extract first sentence (up to first period followed by space or end)
    match = re.match(r"^(.+?\.)\s", text)
    if not match:
        # Try the whole text if it's a single sentence ending with period
        if text.endswith("."):
            first_sentence = text
        else:
            return False
    else:
        first_sentence = match.group(1)

    words = first_sentence.split()
    if len(words) > 30:
        return False

    # Check for a number
    has_number = bool(re.search(r"\d", first_sentence))
    # Check for named entity (multi-word capitalized phrase or acronym 2+ chars)
    has_entity = bool(ENTITY_PATTERN.search(first_sentence))

    return has_number or has_entity


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
    """Extract technical crawlability signals with AI crawler classification."""
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

    # AI bot access from robots.txt — classify into training vs citation
    ai_bots_blocked = []
    ai_bots_allowed = []
    training_bots_blocked = []
    training_bots_allowed = []
    citation_bots_blocked = []
    citation_bots_allowed = []

    if robots_txt:
        for bot in TRAINING_BOTS:
            if _is_bot_blocked(bot, robots_txt):
                training_bots_blocked.append(bot)
                ai_bots_blocked.append(bot)
            else:
                training_bots_allowed.append(bot)
                ai_bots_allowed.append(bot)
        for bot in CITATION_BOTS:
            if _is_bot_blocked(bot, robots_txt):
                citation_bots_blocked.append(bot)
                ai_bots_blocked.append(bot)
            else:
                citation_bots_allowed.append(bot)
                ai_bots_allowed.append(bot)
    else:
        training_bots_allowed = list(TRAINING_BOTS)
        citation_bots_allowed = list(CITATION_BOTS)
        ai_bots_allowed = list(AI_BOTS)

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
        "training_bots_blocked": training_bots_blocked,
        "training_bots_allowed": training_bots_allowed,
        "citation_bots_blocked": citation_bots_blocked,
        "citation_bots_allowed": citation_bots_allowed,
        "meta_tags_present": meta_present,
        "meta_tags_missing": meta_missing,
        "is_ssr": is_ssr,
    }


def _is_bot_blocked(bot_name: str, robots_txt: str) -> bool:
    """Check if a specific bot is blocked in robots.txt."""
    return bool(re.search(
        rf"User-agent:\s*{bot_name}.*?Disallow:\s*/\s*$",
        robots_txt, re.MULTILINE | re.DOTALL
    ))


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


def extract_eeat(soup: BeautifulSoup) -> dict:
    """Extract E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals."""
    body = soup.find("body") or soup
    text = body.get_text(separator=" ", strip=True)

    # 1. Author bio detection
    author_bio_detected = False
    # Check text patterns
    if AUTHOR_BIO_PATTERNS.search(text):
        author_bio_detected = True
    # Check headings
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        if AUTHOR_BIO_PATTERNS.search(heading.get_text()):
            author_bio_detected = True
            break
    # Check rel="author" links
    if soup.find("a", attrs={"rel": "author"}):
        author_bio_detected = True

    # 2. Parse JSON-LD for Person, Organization, Article schemas
    person_schema = {
        "name": None,
        "sameAs": [],
        "knowsAbout": [],
        "honorificSuffix": None,
        "alumniOf": None,
    }
    org_schema = {"sameAs_count": 0}
    article_dates = {"datePublished": None, "dateModified": None}

    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                schema_type = item.get("@type", "")

                if schema_type == "Person":
                    person_schema["name"] = item.get("name")
                    person_schema["sameAs"] = item.get("sameAs", [])
                    if isinstance(person_schema["sameAs"], str):
                        person_schema["sameAs"] = [person_schema["sameAs"]]
                    person_schema["knowsAbout"] = item.get("knowsAbout", [])
                    if isinstance(person_schema["knowsAbout"], str):
                        person_schema["knowsAbout"] = [person_schema["knowsAbout"]]
                    person_schema["honorificSuffix"] = item.get("honorificSuffix")
                    person_schema["alumniOf"] = item.get("alumniOf")

                elif schema_type == "Organization":
                    same_as = item.get("sameAs", [])
                    if isinstance(same_as, str):
                        same_as = [same_as]
                    org_schema["sameAs_count"] = len(same_as)

                elif schema_type == "Article":
                    article_dates["datePublished"] = item.get("datePublished")
                    article_dates["dateModified"] = item.get("dateModified")

        except (json.JSONDecodeError, TypeError):
            continue

    # 3. Credentials visible if Person schema has honorificSuffix or knowsAbout
    credentials_visible = bool(
        person_schema["honorificSuffix"]
        or person_schema["knowsAbout"]
    )

    return {
        "author_bio_detected": author_bio_detected,
        "person_schema": person_schema,
        "org_schema": org_schema,
        "article_dates": article_dates,
        "credentials_visible": credentials_visible,
    }


def parse_llms_txt(llms_txt: str) -> dict:
    """Parse llms.txt content for entries and structure."""
    if not llms_txt:
        return {"exists": False, "entries": 0, "has_descriptions": False}

    # Count entries: lines starting with "- ["
    entry_pattern = re.compile(r"^-\s+\[", re.MULTILINE)
    entries = entry_pattern.findall(llms_txt)

    # Check for descriptions: entries with ): after the URL closing paren
    desc_pattern = re.compile(r"^-\s+\[.*?\]\(.*?\):\s+\S", re.MULTILINE)
    has_descriptions = bool(desc_pattern.search(llms_txt))

    return {
        "exists": True,
        "entries": len(entries),
        "has_descriptions": has_descriptions,
    }


def extract_x_robots_tag(headers_json: dict = None) -> str:
    """Extract X-Robots-Tag from HTTP response headers."""
    if not headers_json:
        return None
    # Case-insensitive header lookup
    for key, value in headers_json.items():
        if key.lower() == "x-robots-tag":
            return value
    return None


def main():
    """CLI entry point: analyze a local HTML file or URL."""
    import argparse
    parser = argparse.ArgumentParser(description="Search Visibility Page Analyzer")
    parser.add_argument("--file", help="Path to local HTML file")
    parser.add_argument("--url", help="URL (expects HTML via stdin if no --file)")
    parser.add_argument("--robots", help="Path to robots.txt file", default="")
    parser.add_argument("--llms-txt", help="Path to llms.txt file", default="")
    parser.add_argument("--headers-json", help="Path to JSON file with HTTP response headers", default="")
    args = parser.parse_args()

    robots_txt = ""
    if args.robots:
        with open(args.robots) as f:
            robots_txt = f.read()

    llms_txt = ""
    if args.llms_txt:
        with open(args.llms_txt) as f:
            llms_txt = f.read()

    headers_json = None
    if args.headers_json:
        with open(args.headers_json) as f:
            headers_json = json.load(f)

    if args.file:
        with open(args.file) as f:
            html = f.read()
        url = args.url or ""
    else:
        html = sys.stdin.read()
        url = args.url or ""

    result = analyze_html(html, url, robots_txt, llms_txt=llms_txt, headers_json=headers_json)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
