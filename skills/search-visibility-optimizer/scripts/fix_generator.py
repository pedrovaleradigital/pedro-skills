#!/usr/bin/env python3
"""
Fix Generator for search-visibility-optimizer.
Takes extraction JSON from analyze_page.py and generates ready-to-use fixes:
schema JSON-LD, llms.txt, robots.txt corrections, meta tag fixes, weak sections.
"""

import json
import re
import sys
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# 1. Schema fixes
# ---------------------------------------------------------------------------

def generate_schema_fixes(extraction: dict) -> list:
    """Generate missing JSON-LD schema objects based on extraction data.

    Returns a list of dicts: {"schema_type": str, "schema": dict, "reason": str}
    """
    fixes = []
    technical = extraction.get("technical", {})
    content = extraction.get("content", {})
    eeat = extraction.get("eeat", {})
    meta = extraction.get("meta", {})
    url = extraction.get("url", "")
    schema_types = technical.get("schema_types", [])
    schema_missing = technical.get("schema_missing", [])

    # FAQPage — if FAQ content detected but schema missing
    if "FAQPage" in schema_missing and content.get("faq_detected"):
        faq_schema = _build_faq_schema(content.get("sections", []))
        if faq_schema["mainEntity"]:
            fixes.append({
                "schema_type": "FAQPage",
                "schema": faq_schema,
                "reason": "FAQ content detected on page but FAQPage schema is missing. "
                          "82% of AI citations include structured data (Qwairy 2025).",
            })

    # Organization — if missing
    if "Organization" in schema_missing:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        fixes.append({
            "schema_type": "Organization",
            "schema": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "PLACEHOLDER_ORG_NAME",
                "url": f"{parsed.scheme}://{domain}" if parsed.scheme else url,
                "sameAs": [
                    "PLACEHOLDER_LINKEDIN_URL",
                    "PLACEHOLDER_TWITTER_URL",
                ],
            },
            "reason": "Organization schema missing. Helps AI engines identify your brand entity "
                      "and improves E-E-A-T signals.",
        })

    # Person — if author bio detected but Person schema missing
    if eeat.get("author_bio_detected") and not eeat.get("person_schema"):
        fixes.append({
            "schema_type": "Person",
            "schema": {
                "@context": "https://schema.org",
                "@type": "Person",
                "name": "PLACEHOLDER_AUTHOR_NAME",
                "sameAs": [
                    "PLACEHOLDER_LINKEDIN_URL",
                ],
                "knowsAbout": [
                    "PLACEHOLDER_TOPIC_1",
                    "PLACEHOLDER_TOPIC_2",
                ],
                "jobTitle": "PLACEHOLDER_JOB_TITLE",
            },
            "reason": "Author bio detected but Person schema is missing. "
                      "40% more AI citations with visible credentials (Qwairy 2025).",
        })

    # Article — if missing
    if "Article" in schema_missing:
        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta.get("title", "PLACEHOLDER_HEADLINE"),
            "description": meta.get("description", ""),
            "datePublished": meta.get("published_date", "PLACEHOLDER_DATE"),
            "dateModified": meta.get("modified_date", meta.get("published_date", "PLACEHOLDER_DATE")),
            "author": {
                "@type": "Person",
                "name": "PLACEHOLDER_AUTHOR_NAME",
            },
        }
        fixes.append({
            "schema_type": "Article",
            "schema": article_schema,
            "reason": "Article schema missing. Required for proper indexing in AI search "
                      "and Google Discover.",
        })

    # BreadcrumbList — if missing, generate from URL path
    if "BreadcrumbList" in schema_missing and url:
        bc_schema = _build_breadcrumb_schema(url)
        if bc_schema["itemListElement"]:
            fixes.append({
                "schema_type": "BreadcrumbList",
                "schema": bc_schema,
                "reason": "BreadcrumbList schema missing. Helps search engines understand "
                          "site hierarchy and improves navigation in SERPs.",
            })

    return fixes


def _build_faq_schema(sections: list) -> dict:
    """Build FAQPage JSON-LD from sections that look like Q&A content."""
    questions = []
    for section in sections:
        text = section.get("text", "")
        heading = section.get("heading", "")

        # Try to extract Q&A pairs from the text
        # Pattern 1: "Question? Answer sentence."
        qa_pairs = re.findall(
            r"([^.?!]*\?)\s*([^?]+?)(?=\s*[A-Z][^.?!]*\?|\s*$)",
            text,
        )
        for question, answer in qa_pairs:
            question = question.strip()
            answer = answer.strip().rstrip(".")
            if question and answer:
                questions.append({
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": answer,
                    },
                })

        # Pattern 2: If the heading itself is a question
        if heading.endswith("?") and text and not qa_pairs:
            questions.append({
                "@type": "Question",
                "name": heading,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": text.split(".")[0].strip() + "." if "." in text else text.strip(),
                },
            })

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": questions,
    }


def _build_breadcrumb_schema(url: str) -> dict:
    """Build BreadcrumbList JSON-LD from URL path segments."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    segments = [s for s in parsed.path.split("/") if s]

    items = [{
        "@type": "ListItem",
        "position": 1,
        "name": "Home",
        "item": base + "/",
    }]

    accumulated = ""
    for i, segment in enumerate(segments):
        accumulated += f"/{segment}"
        name = segment.replace("-", " ").replace("_", " ").title()
        items.append({
            "@type": "ListItem",
            "position": i + 2,
            "name": name,
            "item": base + accumulated,
        })

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


# ---------------------------------------------------------------------------
# 2. llms.txt generation
# ---------------------------------------------------------------------------

def generate_llms_txt(extraction: dict, sitemap_urls: list = None) -> str:
    """Generate llms.txt content in markdown format.

    Format:
        # Site Title
        > Site description

        ## Pages
        - [Title](url): description
    """
    if sitemap_urls is None:
        sitemap_urls = []

    meta = extraction.get("meta", {})
    url = extraction.get("url", "")
    parsed = urlparse(url)
    domain = parsed.netloc or "example.com"

    title = meta.get("title", domain)
    description = meta.get("description", "")

    lines = [
        f"# {title}",
        f"> {description}",
        "",
    ]

    # Build page list
    pages = []
    if url:
        pages.append((url, title, description))

    for surl in sitemap_urls:
        if surl != url:
            # Derive a title from the URL path
            s_parsed = urlparse(surl)
            path_segments = [s for s in s_parsed.path.split("/") if s]
            page_title = (
                path_segments[-1].replace("-", " ").replace("_", " ").title()
                if path_segments
                else domain
            )
            pages.append((surl, page_title, ""))

    if pages:
        lines.append("## Pages")
        for page_url, page_title, page_desc in pages:
            if page_desc:
                lines.append(f"- [{page_title}]({page_url}): {page_desc}")
            else:
                lines.append(f"- [{page_title}]({page_url})")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Robots.txt fixes
# ---------------------------------------------------------------------------

def generate_robots_fixes(extraction: dict) -> str:
    """Generate corrected robots.txt rules for AI bots.

    Unblocks citation bots while preserving training bot blocks.
    Returns empty string if no fixes needed.
    """
    technical = extraction.get("technical", {})
    citation_blocked = technical.get("citation_bots_blocked", [])
    training_blocked = technical.get("training_bots_blocked", [])

    if not citation_blocked and not training_blocked:
        return ""

    lines = [
        "# AI Bot Access Rules",
        "# IMPORTANT: Training bots scrape content for model training.",
        "# Citation bots retrieve content to cite in AI-generated answers.",
        "# Blocking citation bots prevents your site from appearing in AI search results.",
        "",
    ]

    # Keep training bots blocked if they were blocked
    if training_blocked:
        lines.append("# Training bots — blocked (content used for model training)")
        for bot in training_blocked:
            lines.append(f"User-agent: {bot}")
            lines.append("Disallow: /")
            lines.append("")

    # Unblock citation bots
    if citation_blocked:
        lines.append("# Citation bots — allowed (these cite your content in AI answers)")
        for bot in citation_blocked:
            lines.append(f"User-agent: {bot}")
            lines.append("Allow: /")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Meta tag fixes
# ---------------------------------------------------------------------------

TITLE_MAX = 60
TITLE_MIN = 30
DESC_MAX = 160
DESC_MIN = 120


def generate_meta_fixes(extraction: dict) -> dict:
    """Analyze meta tags and suggest fixes.

    Returns {"title_fix": str|None, "description_fix": str|None, "og_fixes": list}
    """
    meta = extraction.get("meta", {})
    technical = extraction.get("technical", {})

    title = meta.get("title", "")
    description = meta.get("description", "")
    missing_tags = technical.get("meta_tags_missing", [])

    title_fix = None
    description_fix = None

    # Title checks
    if len(title) > TITLE_MAX:
        title_fix = (
            f"Title is {len(title)} characters (max recommended: {TITLE_MAX}). "
            f"Shorten to under {TITLE_MAX} characters to avoid truncation in search results."
        )
    elif len(title) < TITLE_MIN:
        title_fix = (
            f"Title is only {len(title)} characters (min recommended: {TITLE_MIN}). "
            f"Expand to {TITLE_MIN}-{TITLE_MAX} characters for better search visibility."
        )

    # Description checks
    if len(description) > DESC_MAX:
        description_fix = (
            f"Description is {len(description)} characters (max recommended: {DESC_MAX}). "
            f"Shorten to {DESC_MIN}-{DESC_MAX} characters."
        )
    elif len(description) < DESC_MIN:
        description_fix = (
            f"Description is only {len(description)} characters (min recommended: {DESC_MIN}). "
            f"Expand to {DESC_MIN}-{DESC_MAX} characters for better click-through rates."
        )

    # OG tag checks
    og_fixes = [tag for tag in missing_tags if tag.startswith("og:")]

    return {
        "title_fix": title_fix,
        "description_fix": description_fix,
        "og_fixes": og_fixes,
    }


# ---------------------------------------------------------------------------
# 5. Weak section identification
# ---------------------------------------------------------------------------

def identify_weak_sections(extraction: dict) -> list:
    """Score each section and return the bottom 5 (or fewer) sorted by weakness.

    Scoring: +1 for has_stats, +1 for has_citations, +1 for has_quotes,
             +1 for answer_first, +1 if word_count >= 50.
    Lower score = weaker.
    """
    sections = extraction.get("content", {}).get("sections", [])
    if not sections:
        return []

    scored = []
    for section in sections:
        score = 0
        if section.get("has_stats"):
            score += 1
        if section.get("has_citations"):
            score += 1
        if section.get("has_quotes"):
            score += 1
        if section.get("answer_first"):
            score += 1
        if section.get("word_count", 0) >= 50:
            score += 1

        scored.append({
            "heading": section["heading"],
            "score": score,
            "word_count": section.get("word_count", 0),
            "missing": _list_missing_signals(section),
        })

    # Sort by score ascending (weakest first)
    scored.sort(key=lambda s: s["score"])

    return scored[:5]


def _list_missing_signals(section: dict) -> list:
    """List which signals are missing from a section."""
    missing = []
    if not section.get("has_stats"):
        missing.append("statistics")
    if not section.get("has_citations"):
        missing.append("citations")
    if not section.get("has_quotes"):
        missing.append("quotes")
    if not section.get("answer_first"):
        missing.append("answer_first")
    if section.get("word_count", 0) < 50:
        missing.append("thin_content")
    return missing


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Read extraction JSON from stdin, output fixes JSON to stdout."""
    extraction = json.loads(sys.stdin.read())

    result = {
        "schema_fixes": generate_schema_fixes(extraction),
        "llms_txt": generate_llms_txt(extraction),
        "robots_fixes": generate_robots_fixes(extraction),
        "meta_fixes": generate_meta_fixes(extraction),
        "weak_sections": identify_weak_sections(extraction),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
