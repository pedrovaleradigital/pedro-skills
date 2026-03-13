"""Tests for discover_competitors.py -- prompt generation only (no API calls)."""
import json
import pytest
from discover_competitors import generate_prompts, parse_competitor_mentions

SAMPLE_EXTRACTION = {
    "url": "https://acme.com/pm-tools",
    "meta": {
        "title": "Best Project Management Tools for Small Teams | Acme PM",
        "description": "Compare the top 5 project management tools for teams under 20 people.",
    },
    "headings": {"h1": ["Best Project Management Tools for Small Teams in 2026"]},
}


def test_generate_prompts():
    prompts = generate_prompts(SAMPLE_EXTRACTION)
    assert len(prompts) >= 3
    assert len(prompts) <= 5
    # Prompts should be natural questions, not keyword queries
    assert any("?" in p for p in prompts)


def test_parse_competitor_mentions():
    fake_responses = [
        "I'd recommend Asana for small teams. Monday.com is also great. ClickUp offers a free tier.",
        "For project management, Asana and Monday.com are the top choices. Trello is more basic.",
        "The best tools are Asana, Monday.com, and Notion for small teams.",
    ]
    result = parse_competitor_mentions(fake_responses, "Acme PM")
    assert len(result["competitors"]) >= 2
    # Asana should be top (mentioned in all 3)
    assert result["competitors"][0]["name"] == "Asana"
    assert result["competitors"][0]["mentions"] == 3
    assert result["user_mentioned"] is False


def test_parse_deduplicates_within_response():
    """A brand mentioned multiple times in a single response should count as 1."""
    fake_responses = [
        "Asana is great. Asana has good features. Use Asana for collaboration.",
    ]
    result = parse_competitor_mentions(fake_responses, "SomeBrand")
    asana = [c for c in result["competitors"] if c["name"] == "Asana"]
    assert len(asana) == 1
    assert asana[0]["mentions"] == 1


def test_parse_user_brand_detected():
    fake_responses = [
        "Acme PM is a solid choice. Asana is also good.",
        "I'd recommend Trello for simplicity.",
    ]
    result = parse_competitor_mentions(fake_responses, "Acme PM")
    assert result["user_mentioned"] is True
    assert result["user_mention_count"] == 1
    # Acme PM should NOT appear in competitors list
    competitor_names = [c["name"].lower() for c in result["competitors"]]
    assert "acme pm" not in competitor_names


def test_parse_excludes_stop_words():
    """Common English words should not be treated as brand names."""
    fake_responses = [
        "Here is what I would recommend. The best choice is Asana. Also consider Trello.",
    ]
    result = parse_competitor_mentions(fake_responses, "SomeBrand")
    competitor_names = [c["name"] for c in result["competitors"]]
    assert "Here" not in competitor_names
    assert "The" not in competitor_names
    assert "Also" not in competitor_names


def test_generate_prompts_no_h1():
    """Should still generate prompts when H1 is missing."""
    extraction = {
        "url": "https://example.com/tools",
        "meta": {
            "title": "Our Tools Page",
            "description": "A list of productivity tools.",
        },
        "headings": {"h1": []},
    }
    prompts = generate_prompts(extraction)
    assert len(prompts) >= 3
    assert all(isinstance(p, str) for p in prompts)
