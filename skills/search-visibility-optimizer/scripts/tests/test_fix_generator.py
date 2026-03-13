"""Tests for fix_generator.py — schema, llms.txt, robots.txt, meta, weak sections."""
import json
import pytest
from fix_generator import (
    generate_schema_fixes,
    generate_llms_txt,
    generate_robots_fixes,
    generate_meta_fixes,
    identify_weak_sections,
)


# ---------------------------------------------------------------------------
# Fixtures / sample data
# ---------------------------------------------------------------------------

EXTRACTION_FULL = {
    "url": "https://acme.com/blog/ai-tools",
    "meta": {
        "title": "Best AI Tools for Small Business Owners in 2026",
        "description": "A comprehensive guide to AI tools that help small business owners save time and grow revenue.",
    },
    "headings": {
        "h1": ["Best AI Tools for Small Business Owners in 2026"],
        "h2": ["What are AI Tools?", "Top 5 AI Tools", "How to Choose", "FAQ"],
        "h3": [],
    },
    "content": {
        "word_count": 1500,
        "faq_detected": True,
        "sections": [
            {
                "heading": "What are AI Tools?",
                "text": "AI tools are software applications that use artificial intelligence.",
                "word_count": 60,
                "has_stats": True,
                "has_citations": True,
                "has_quotes": True,
                "answer_first": True,
            },
            {
                "heading": "Top 5 AI Tools",
                "text": "Here is a list of the top five AI tools available today.",
                "word_count": 120,
                "has_stats": True,
                "has_citations": False,
                "has_quotes": False,
                "answer_first": False,
            },
            {
                "heading": "How to Choose",
                "text": "Choosing the right tool depends on your needs.",
                "word_count": 40,
                "has_stats": False,
                "has_citations": False,
                "has_quotes": False,
                "answer_first": False,
            },
            {
                "heading": "FAQ",
                "text": "What is the best AI tool? The best AI tool depends on your use case. How much do AI tools cost? Prices range from free to $500 per month.",
                "word_count": 80,
                "has_stats": True,
                "has_citations": False,
                "has_quotes": False,
                "answer_first": True,
            },
        ],
    },
    "authority": {
        "statistics_count": 5,
        "citation_count": 2,
        "quote_count": 1,
        "named_entities": ["ChatGPT", "Anthropic"],
        "vague_claims": [],
    },
    "technical": {
        "schema_types": ["Article"],
        "schema_missing": ["FAQPage", "Organization", "BreadcrumbList"],
        "ai_bots_blocked": [],
        "ai_bots_allowed": ["GPTBot", "ChatGPT-User"],
        "training_bots_blocked": [],
        "training_bots_allowed": ["GPTBot"],
        "citation_bots_blocked": [],
        "citation_bots_allowed": ["ChatGPT-User", "PerplexityBot"],
        "meta_tags_present": ["description", "og:title"],
        "meta_tags_missing": ["og:description", "og:image"],
        "is_ssr": True,
    },
    "eeat": {
        "author_bio_detected": True,
        "person_schema": {},
        "org_schema": {},
        "credentials_visible": False,
    },
}


# ---------------------------------------------------------------------------
# generate_schema_fixes
# ---------------------------------------------------------------------------

class TestGenerateSchemaFixes:
    def test_generates_faqpage_when_faq_detected(self):
        extraction = {
            "content": {
                "faq_detected": True,
                "sections": [
                    {
                        "heading": "FAQ",
                        "text": "What is SEO? SEO stands for search engine optimization. How long does SEO take? SEO typically takes 3-6 months to show results.",
                        "word_count": 30,
                        "has_stats": False,
                        "has_citations": False,
                        "has_quotes": False,
                    }
                ],
            },
            "technical": {"schema_types": ["Article"], "schema_missing": ["FAQPage"]},
            "eeat": {"author_bio_detected": False, "person_schema": {}, "org_schema": {}},
            "url": "https://example.com/seo-guide",
            "meta": {"title": "SEO Guide", "description": "A guide to SEO."},
        }
        fixes = generate_schema_fixes(extraction)
        faq_fixes = [f for f in fixes if f["schema_type"] == "FAQPage"]
        assert len(faq_fixes) == 1
        schema = faq_fixes[0]["schema"]
        assert schema["@type"] == "FAQPage"
        assert "mainEntity" in schema
        assert len(schema["mainEntity"]) >= 1
        assert schema["mainEntity"][0]["@type"] == "Question"

    def test_generates_organization_when_missing(self):
        extraction = {
            "content": {"faq_detected": False, "sections": []},
            "technical": {"schema_types": [], "schema_missing": ["Organization"]},
            "eeat": {"author_bio_detected": False, "person_schema": {}, "org_schema": {}},
            "url": "https://acme.com/about",
            "meta": {"title": "About Acme", "description": "About us."},
        }
        fixes = generate_schema_fixes(extraction)
        org_fixes = [f for f in fixes if f["schema_type"] == "Organization"]
        assert len(org_fixes) == 1
        schema = org_fixes[0]["schema"]
        assert schema["@type"] == "Organization"
        assert "name" in schema
        assert "url" in schema
        assert "sameAs" in schema

    def test_generates_person_when_author_bio_detected(self):
        extraction = {
            "content": {"faq_detected": False, "sections": []},
            "technical": {"schema_types": [], "schema_missing": ["Person"]},
            "eeat": {
                "author_bio_detected": True,
                "person_schema": {},
                "org_schema": {},
            },
            "url": "https://example.com/blog/post",
            "meta": {"title": "Blog Post", "description": "A post."},
        }
        fixes = generate_schema_fixes(extraction)
        person_fixes = [f for f in fixes if f["schema_type"] == "Person"]
        assert len(person_fixes) == 1
        schema = person_fixes[0]["schema"]
        assert schema["@type"] == "Person"
        assert "sameAs" in schema
        assert "knowsAbout" in schema

    def test_generates_article_when_missing(self):
        extraction = {
            "content": {"faq_detected": False, "sections": []},
            "technical": {"schema_types": [], "schema_missing": ["Article"]},
            "eeat": {"author_bio_detected": False, "person_schema": {}, "org_schema": {}},
            "url": "https://example.com/blog/post",
            "meta": {
                "title": "My Blog Post",
                "description": "A detailed blog post.",
                "published_date": "2026-01-15",
                "modified_date": "2026-02-01",
            },
        }
        fixes = generate_schema_fixes(extraction)
        article_fixes = [f for f in fixes if f["schema_type"] == "Article"]
        assert len(article_fixes) == 1
        schema = article_fixes[0]["schema"]
        assert schema["@type"] == "Article"
        assert "headline" in schema
        assert "datePublished" in schema
        assert "author" in schema

    def test_generates_breadcrumblist_from_url(self):
        extraction = {
            "content": {"faq_detected": False, "sections": []},
            "technical": {"schema_types": [], "schema_missing": ["BreadcrumbList"]},
            "eeat": {"author_bio_detected": False, "person_schema": {}, "org_schema": {}},
            "url": "https://acme.com/blog/category/my-post",
            "meta": {"title": "My Post", "description": "A post."},
        }
        fixes = generate_schema_fixes(extraction)
        bc_fixes = [f for f in fixes if f["schema_type"] == "BreadcrumbList"]
        assert len(bc_fixes) == 1
        schema = bc_fixes[0]["schema"]
        assert schema["@type"] == "BreadcrumbList"
        assert "itemListElement" in schema
        # Should have Home + blog + category + my-post = 4 items
        assert len(schema["itemListElement"]) == 4

    def test_no_fixes_when_all_present(self):
        extraction = {
            "content": {"faq_detected": False, "sections": []},
            "technical": {"schema_types": ["Article", "Organization", "BreadcrumbList"], "schema_missing": []},
            "eeat": {"author_bio_detected": False, "person_schema": {"name": "Jane"}, "org_schema": {}},
            "url": "https://example.com",
            "meta": {"title": "Example", "description": "Example."},
        }
        fixes = generate_schema_fixes(extraction)
        assert len(fixes) == 0

    def test_schema_fixes_return_correct_shape(self):
        fixes = generate_schema_fixes(EXTRACTION_FULL)
        for fix in fixes:
            assert "schema_type" in fix
            assert "schema" in fix
            assert "reason" in fix
            assert isinstance(fix["schema"], dict)
            assert "@context" in fix["schema"]
            assert "@type" in fix["schema"]


# ---------------------------------------------------------------------------
# generate_llms_txt
# ---------------------------------------------------------------------------

class TestGenerateLlmsTxt:
    def test_basic_output(self):
        extraction = {
            "url": "https://example.com/tools",
            "meta": {
                "title": "Our Tools",
                "description": "Best tools guide for business owners.",
            },
        }
        content = generate_llms_txt(extraction, [])
        assert content.startswith("# ")
        assert "example.com" in content
        assert "Our Tools" in content or "tools" in content.lower()

    def test_includes_sitemap_urls(self):
        extraction = {
            "url": "https://example.com",
            "meta": {"title": "Example Site", "description": "A great site."},
        }
        sitemap = [
            "https://example.com/about",
            "https://example.com/blog",
            "https://example.com/contact",
        ]
        content = generate_llms_txt(extraction, sitemap)
        assert "/about" in content
        assert "/blog" in content
        assert "/contact" in content

    def test_has_markdown_structure(self):
        extraction = {
            "url": "https://example.com",
            "meta": {"title": "My Site", "description": "The description."},
        }
        content = generate_llms_txt(extraction, [])
        lines = content.strip().split("\n")
        # First line should be a markdown header
        assert lines[0].startswith("# ")
        # Should have a description line starting with >
        desc_lines = [l for l in lines if l.startswith(">")]
        assert len(desc_lines) >= 1

    def test_empty_sitemap_still_includes_analyzed_url(self):
        extraction = {
            "url": "https://example.com/blog/post",
            "meta": {"title": "Blog Post", "description": "A blog post."},
        }
        content = generate_llms_txt(extraction, [])
        assert "example.com/blog/post" in content


# ---------------------------------------------------------------------------
# generate_robots_fixes
# ---------------------------------------------------------------------------

class TestGenerateRobotsFixes:
    def test_unblocks_citation_bots(self):
        extraction = {
            "technical": {
                "citation_bots_blocked": ["PerplexityBot", "ChatGPT-User"],
                "training_bots_blocked": [],
            },
        }
        result = generate_robots_fixes(extraction)
        assert "PerplexityBot" in result
        assert "ChatGPT-User" in result
        assert "Allow" in result

    def test_adds_comments_explaining_distinction(self):
        extraction = {
            "technical": {
                "citation_bots_blocked": ["PerplexityBot"],
                "training_bots_blocked": ["GPTBot"],
            },
        }
        result = generate_robots_fixes(extraction)
        # Should contain a comment about training vs citation
        assert "#" in result
        lower = result.lower()
        assert "citation" in lower or "training" in lower

    def test_returns_empty_when_no_bots_blocked(self):
        extraction = {
            "technical": {
                "citation_bots_blocked": [],
                "training_bots_blocked": [],
            },
        }
        result = generate_robots_fixes(extraction)
        assert result == ""

    def test_preserves_training_bot_blocks(self):
        extraction = {
            "technical": {
                "citation_bots_blocked": ["PerplexityBot"],
                "training_bots_blocked": ["GPTBot", "CCBot"],
            },
        }
        result = generate_robots_fixes(extraction)
        # Training bots should remain blocked
        assert "GPTBot" in result
        assert "Disallow" in result
        # Citation bots should be allowed
        assert "PerplexityBot" in result


# ---------------------------------------------------------------------------
# generate_meta_fixes
# ---------------------------------------------------------------------------

class TestGenerateMetaFixes:
    def test_flags_title_too_long(self):
        extraction = {
            "meta": {
                "title": "A" * 65 + " This Title Is Way Too Long For Search Engine Display",
                "description": "A perfectly fine description that is within limits for SEO.",
            },
            "technical": {
                "meta_tags_missing": [],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert fixes["title_fix"] is not None
        assert "long" in fixes["title_fix"].lower() or "shorten" in fixes["title_fix"].lower()

    def test_flags_title_too_short(self):
        extraction = {
            "meta": {
                "title": "Short",
                "description": "A perfectly fine meta description that meets the minimum length requirement and provides useful context to searchers browsing.",
            },
            "technical": {
                "meta_tags_missing": [],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert fixes["title_fix"] is not None
        assert str(len("Short")) in fixes["title_fix"]

    def test_flags_description_too_long(self):
        extraction = {
            "meta": {
                "title": "A Good Title That Is Proper Length For SEO",
                "description": "A" * 165 + " this description is too long",
            },
            "technical": {
                "meta_tags_missing": [],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert fixes["description_fix"] is not None

    def test_flags_description_too_short(self):
        extraction = {
            "meta": {
                "title": "A Good Title That Is Proper Length For SEO",
                "description": "Too short.",
            },
            "technical": {
                "meta_tags_missing": [],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert fixes["description_fix"] is not None

    def test_flags_missing_og_tags(self):
        extraction = {
            "meta": {
                "title": "A Good Title That Is Proper Length For SEO",
                "description": "A perfectly fine description that meets the minimum length requirement.",
            },
            "technical": {
                "meta_tags_missing": ["og:description", "og:image"],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert len(fixes["og_fixes"]) == 2
        assert "og:description" in fixes["og_fixes"]
        assert "og:image" in fixes["og_fixes"]

    def test_no_fixes_needed(self):
        extraction = {
            "meta": {
                "title": "A Good Title That Is the Proper Length for SEO",
                "description": "A perfectly fine meta description that meets the minimum length requirement and provides useful context to searchers browsing results.",
            },
            "technical": {
                "meta_tags_missing": [],
            },
        }
        fixes = generate_meta_fixes(extraction)
        assert fixes["title_fix"] is None
        assert fixes["description_fix"] is None
        assert fixes["og_fixes"] == []


# ---------------------------------------------------------------------------
# identify_weak_sections
# ---------------------------------------------------------------------------

class TestIdentifyWeakSections:
    def test_weakest_section_first(self):
        extraction = {
            "content": {
                "sections": [
                    {"heading": "Strong", "has_stats": True, "has_citations": True, "has_quotes": True, "word_count": 100, "answer_first": True},
                    {"heading": "Weak", "has_stats": False, "has_citations": False, "has_quotes": False, "word_count": 20, "answer_first": False},
                    {"heading": "Medium", "has_stats": True, "has_citations": False, "has_quotes": False, "word_count": 80, "answer_first": True},
                ],
            },
        }
        weak = identify_weak_sections(extraction)
        assert weak[0]["heading"] == "Weak"
        assert weak[0]["score"] < weak[-1]["score"]

    def test_returns_max_5(self):
        sections = []
        for i in range(10):
            sections.append({
                "heading": f"Section {i}",
                "has_stats": False,
                "has_citations": False,
                "has_quotes": False,
                "word_count": 30,
                "answer_first": False,
            })
        extraction = {"content": {"sections": sections}}
        weak = identify_weak_sections(extraction)
        assert len(weak) <= 5

    def test_returns_all_if_fewer_than_5(self):
        extraction = {
            "content": {
                "sections": [
                    {"heading": "Only One", "has_stats": False, "has_citations": False, "has_quotes": False, "word_count": 25, "answer_first": False},
                ],
            },
        }
        weak = identify_weak_sections(extraction)
        assert len(weak) == 1

    def test_scoring_logic(self):
        """Each signal adds 1 point; word_count >= 50 adds 1."""
        extraction = {
            "content": {
                "sections": [
                    {"heading": "All Signals", "has_stats": True, "has_citations": True, "has_quotes": True, "word_count": 100, "answer_first": True},
                    {"heading": "No Signals", "has_stats": False, "has_citations": False, "has_quotes": False, "word_count": 10, "answer_first": False},
                ],
            },
        }
        weak = identify_weak_sections(extraction)
        no_signals = [s for s in weak if s["heading"] == "No Signals"]
        all_signals = [s for s in weak if s["heading"] == "All Signals"]
        if no_signals:
            assert no_signals[0]["score"] == 0
        if all_signals:
            assert all_signals[0]["score"] == 5

    def test_empty_sections(self):
        extraction = {"content": {"sections": []}}
        weak = identify_weak_sections(extraction)
        assert weak == []

    def test_section_output_shape(self):
        extraction = {
            "content": {
                "sections": [
                    {"heading": "Test", "has_stats": False, "has_citations": False, "has_quotes": False, "word_count": 25, "answer_first": False},
                ],
            },
        }
        weak = identify_weak_sections(extraction)
        assert len(weak) == 1
        item = weak[0]
        assert "heading" in item
        assert "score" in item
        assert isinstance(item["score"], (int, float))


# ---------------------------------------------------------------------------
# Integration: full extraction through all generators
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_extraction_generates_all_fix_types(self):
        schema_fixes = generate_schema_fixes(EXTRACTION_FULL)
        assert len(schema_fixes) >= 1  # At least FAQPage since faq_detected

        llms_txt = generate_llms_txt(EXTRACTION_FULL, [])
        assert isinstance(llms_txt, str)
        assert len(llms_txt) > 0

        meta_fixes = generate_meta_fixes(EXTRACTION_FULL)
        assert isinstance(meta_fixes, dict)
        assert "title_fix" in meta_fixes
        assert "description_fix" in meta_fixes
        assert "og_fixes" in meta_fixes

        weak = identify_weak_sections(EXTRACTION_FULL)
        assert isinstance(weak, list)
        assert len(weak) >= 1

    def test_all_schema_fixes_are_valid_json_ld(self):
        fixes = generate_schema_fixes(EXTRACTION_FULL)
        for fix in fixes:
            schema = fix["schema"]
            # Must be serializable as JSON
            serialized = json.dumps(schema)
            parsed = json.loads(serialized)
            assert parsed["@context"] == "https://schema.org"
