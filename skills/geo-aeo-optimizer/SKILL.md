---
name: geo-aeo-optimizer
description: Audit any webpage for AI search visibility (GEO/AEO). Scores content across 6 research-backed categories, compares against competitors, rewrites weak sections, and delivers a prioritized action plan. Use when users want to optimize their website for AI citations in ChatGPT, Perplexity, Gemini, Google AI Overviews, or Claude. Triggers on "GEO", "AEO", "AI search optimization", "AI visibility", "get cited by AI", "optimize for ChatGPT", "AI search audit", or "generative engine optimization".
---

# GEO/AEO Optimizer

Audit webpages for AI search visibility. Score against 6 research-backed categories. Compare against competitors. Rewrite weak sections. Deliver a prioritized action plan.

Based on Princeton's GEO research (KDD 2024) which proved specific content techniques boost AI citation visibility by 30-40%.

## Workflow

### Step 1: Collect Input

Ask the user for:
1. **Their URL** (primary) — or ask them to paste their page content as fallback
2. **Competitor URLs** — "Provide 2-3 competitor URLs, OR I can discover your top AI competitors automatically (requires an OpenAI API key)."

If the user wants auto-discovery and provides an API key, run competitor discovery (Step 1b). Otherwise proceed to Step 2.

### Step 1b: Competitor Discovery (Optional)

Run `scripts/discover_competitors.py`:
1. Use WebFetch to get the user's page HTML
2. Pass the HTML to `scripts/analyze_page.py --file` to get extraction JSON
3. Pipe extraction JSON to `scripts/discover_competitors.py --brand "User Brand" --api-key KEY`
4. Present discovered competitors to the user for confirmation
5. Report whether the user's brand was mentioned by AI at all

### Step 2: Fetch and Analyze Pages

For each URL (user + competitors):
1. Use WebFetch to get page HTML
2. Use WebFetch to get `{domain}/robots.txt`
3. Save HTML to a temp file
4. Run: `python3 scripts/analyze_page.py --file /tmp/page.html --url {url} --robots /tmp/robots.txt`
5. Capture the JSON output

### Step 3: Score All Pages

Read `references/scoring-rubric.md` for the detailed rubric.

For each page's extraction JSON, assign a 0-100 score per category using the rubric thresholds. Calculate the composite score using the weights:
- Authority Signals: 30%
- Content Structure: 20%
- Entity Clarity: 20%
- Technical Crawlability: 15%
- Freshness: 10%
- Anti-patterns: 5%

**Critical check:** If `technical.is_ssr` is false for the user's page, flag this immediately as a show-stopper. The page is invisible to AI crawlers and must be fixed before any content optimization matters.

### Step 4: Generate Report Card

Present a side-by-side comparison table:

```
                    You     Comp1    Comp2    Comp3
Authority Signals   32      71       65       58
Content Structure   55      68       72       61
Entity Clarity      28      64       59       53
Tech Crawlability   70      85       80       75
Freshness           45      80       70       65
Anti-patterns       80      90       85       85
─────────────────────────────────────────────────
COMPOSITE           45      74       70       64
```

### Step 5: Generate Gap Analysis

For each category where the user scores lower than the top competitor:
- State the gap with specific numbers
- Reference specific extraction data (e.g., "You have 2 statistics, Competitor A has 14")
- Explain why this matters using the research basis

Skip categories where the user is competitive (within 10 points of the leader).

### Step 6: Rewrite Weakest Sections

Read `references/princeton-techniques.md` for rewriting methods.

1. Identify the 3-5 lowest-scoring sections from `content.sections`
2. For each section, apply the top 3 Princeton techniques:
   - Statistics Addition
   - Citation Addition
   - Quotation Addition
3. Present as: Original → Optimized → What Changed
4. Mark any placeholder data/quotes the owner needs to replace
5. Preserve the owner's voice and tone

### Step 7: Generate Action Plan

Produce a prioritized checklist grouped by impact:

**High Impact (this week):** Actions based on the biggest scoring gaps, things that can be done immediately (add statistics, add citations, add FAQ section).

**Medium Impact (this month):** Structural changes (add schema markup, fix heading hierarchy, improve meta tags).

**Low Impact (when you get to it):** Minor optimizations (break up long sections, improve URL structure).

Write instructions for non-technical people. Use plain language. If something requires a developer, say so.

## Dependencies

Scripts require: `pip install beautifulsoup4 requests`

Optional (for competitor discovery): `pip install openai`
