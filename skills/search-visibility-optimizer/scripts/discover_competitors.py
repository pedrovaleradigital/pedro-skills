#!/usr/bin/env python3
"""
GEO/AEO Competitor Discovery
Queries LLMs to find which brands AI recommends in your niche.
"""

import json
import os
import re
import sys
from collections import Counter


def generate_prompts(extraction: dict) -> list[str]:
    """Generate natural customer prompts from page extraction data."""
    title = extraction.get("meta", {}).get("title", "")
    desc = extraction.get("meta", {}).get("description", "")
    h1 = (extraction.get("headings", {}).get("h1", [None]) or [None])[0] or ""

    # Infer the niche from title + description + H1
    context = f"{title} {desc} {h1}".strip()

    # Build prompts that a customer would actually ask
    prompts = [
        f"What are the best alternatives for someone looking at {context[:80]}?",
        f"Can you recommend the top companies or tools for {desc[:80]}?",
        f"I need help choosing a solution for {h1[:80] if h1 else desc[:80]}. What should I consider?",
        f"Who are the market leaders in {desc[:60] if desc else title[:60]}?",
    ]

    # Add a specific recommendation prompt
    if h1:
        prompts.append(f"What would you recommend for {h1[:80]}?")

    return prompts[:5]


def parse_competitor_mentions(responses: list[str], user_brand: str) -> dict:
    """Parse LLM responses to extract mentioned brands and rank them."""
    # Extract capitalized brand-like names (2+ chars, not common words)
    stop_words = {"The", "This", "That", "These", "Those", "What", "When",
                  "Where", "Which", "While", "With", "Would", "Could", "Should",
                  "Here", "There", "They", "Their", "Also", "Some", "Many",
                  "Most", "More", "Best", "Good", "Great", "Free", "Other"}

    brand_counter = Counter()
    for response in responses:
        # Find capitalized words/phrases that look like brand names
        brands = re.findall(r"\b([A-Z][a-zA-Z]+(?:\.[a-zA-Z]+)?)\b", response)
        seen_in_response = set()
        for brand in brands:
            if brand not in stop_words and len(brand) > 2:
                if brand not in seen_in_response:
                    brand_counter[brand] += 1
                    seen_in_response.add(brand)

    # Check if user brand was mentioned
    user_mentioned = False
    user_count = 0
    user_lower = user_brand.lower()
    for response in responses:
        if user_lower in response.lower():
            user_mentioned = True
            user_count += 1

    # Build ranked competitor list (exclude user brand)
    competitors = [
        {"name": name, "url": "", "mentions": count}
        for name, count in brand_counter.most_common(10)
        if name.lower() != user_lower
    ][:3]

    return {
        "competitors": competitors,
        "user_mentioned": user_mentioned,
        "user_mention_count": user_count,
    }


def discover(extraction: dict, user_brand: str, api_key: str) -> dict:
    """Run full competitor discovery via OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai package not installed. Run: pip install openai"}

    client = OpenAI(api_key=api_key)
    prompts = generate_prompts(extraction)

    responses = []
    for prompt in prompts:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        responses.append(response.choices[0].message.content)

    result = parse_competitor_mentions(responses, user_brand)
    result["inferred_niche"] = extraction.get("meta", {}).get("description", "")
    result["prompts_used"] = prompts
    return result


def main():
    """CLI: reads extraction JSON from stdin, prints competitor JSON."""
    import argparse
    parser = argparse.ArgumentParser(description="GEO/AEO Competitor Discovery")
    parser.add_argument("--brand", required=True, help="Your brand name")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print(json.dumps({"error": "No API key provided"}))
        sys.exit(1)

    extraction = json.load(sys.stdin)
    result = discover(extraction, args.brand, api_key)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
