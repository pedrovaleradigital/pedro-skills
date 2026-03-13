---
name: search-visibility-optimizer
description: Audit any webpage for search engine and AI search visibility. Scores across 6 research-backed categories (Authority, Content Structure, Entity Clarity, Technical Foundation, AI Crawlability, Freshness), compares against competitors, and generates ready-to-use fixes (schema markup, llms.txt, robots.txt, content rewrites, Next.js metadata). Based on Princeton GEO (2024), GEO-16 (2025), and E-E-A-T research. Triggers on "SEO audit", "GEO", "AEO", "AI search optimization", "search visibility", "optimize for AI", "get cited by AI", "site audit", "page audit", or "search optimization".
---

# Search Visibility Optimizer

Audit any webpage for traditional search engine and AI search visibility. Score against 6 research-backed categories. Compare against competitors. Generate ready-to-use fixes. Deliver a prioritized action plan.

Based on Princeton GEO (KDD 2024), GEO-16 (2025), and E-E-A-T citation research (Qwairy 2025).

## Workflow

### Step 1: Collect Input

Ask the user for:

1. **Target URL** (primary) — or ask them to paste their page content as fallback.
2. **Competitor URLs** — "Provide 2-3 competitor URLs, OR I can discover your top AI competitors automatically (requires an OpenAI API key)."

If the user wants auto-discovery and provides an API key, run competitor discovery:

1. Use WebFetch to get the user's page HTML.
2. Save to a temp file and run extraction:
   ```bash
   python3 scripts/analyze_page.py --file /tmp/target_page.html --url {url}
   ```
3. Pipe extraction JSON to discover competitors:
   ```bash
   echo '{extraction_json}' | python3 scripts/discover_competitors.py --brand "User Brand" --api-key {KEY}
   ```
4. Present discovered competitors to the user for confirmation.
5. Report whether the user's brand was mentioned by AI at all.

### Step 2: Detect MCP Capabilities

Check your available tools for MCP integrations that enhance the audit:

**Lighthouse MCP** — Look for tools named like `run_audit`, `get_core_web_vitals`, `lighthouse_audit`, or similar performance audit tools. If found, these replace heuristic CWV estimates with measured LCP, INP, and CLS values.

**Google Search Console MCP** — Look for tools named like `search_analytics`, `get_search_performance`, `gsc_query`, or similar. If found, pull actual click/impression data and indexing status.

Report to the user what was detected:

- "Lighthouse MCP detected — I will use measured Core Web Vitals instead of heuristics."
- "Google Search Console MCP detected — I will pull actual search performance data."
- "No optional MCP servers detected — I will use heuristic analysis for CWV and skip search performance data. Results will note where measured data would improve accuracy."

### Step 3: Extract Data

For each URL (target + competitors), collect data from all available sources.

**3a. Fetch page assets**

Use WebFetch to retrieve:

1. The page HTML — save to `/tmp/{domain}_page.html`
2. `{scheme}://{domain}/robots.txt` — save to `/tmp/{domain}_robots.txt`
3. `{scheme}://{domain}/llms.txt` — this may 404, that is fine. If it exists, save to `/tmp/{domain}_llms.txt`

Note any relevant HTTP response headers (especially `X-Robots-Tag`). If headers are available, save them to `/tmp/{domain}_headers.json`.

**3b. Run page analyzer**

```bash
python3 scripts/analyze_page.py \
  --file /tmp/{domain}_page.html \
  --url {url} \
  --robots /tmp/{domain}_robots.txt \
  [--llms-txt /tmp/{domain}_llms.txt] \
  [--headers-json /tmp/{domain}_headers.json]
```

Omit `--llms-txt` if the llms.txt fetch returned 404. Omit `--headers-json` if no relevant headers were captured.

This outputs a JSON object with keys: `url`, `meta`, `headings`, `content`, `authority`, `technical`, `anti_patterns`, `eeat`, `llms_txt`, `x_robots_tag`.

**3c. Run technical checker**

```bash
python3 scripts/technical_checker.py {url}
```

This outputs a JSON object with keys: `ssl`, `redirects`, `security_headers`, `page_speed`, `sitemap`, `cwv_heuristic`.

**3d. Lighthouse MCP (if available)**

If Lighthouse MCP tools were detected in Step 2, run the audit tool for each URL. Extract:

- LCP (Largest Contentful Paint) in seconds
- INP (Interaction to Next Paint) in milliseconds
- CLS (Cumulative Layout Shift) score
- Performance score (0-100)

When Lighthouse data is available, use it instead of the `cwv_heuristic` values from `technical_checker.py`. Note `"source": "lighthouse"` instead of `"source": "heuristic"` in the results.

**3e. Google Search Console MCP (if available)**

If GSC MCP tools were detected in Step 2, pull for the target URL:

- Total clicks and impressions (last 28 days)
- Top queries driving traffic
- Indexing status

**3f. Merge results**

Combine `analyze_page.py` output, `technical_checker.py` output, and any MCP data into a single extraction JSON per page.

### Step 4: Score

Read `references/scoring-rubric.md` for the detailed rubric with score ranges, sub-checks, and deductions.

For each page, assign a 0-100 score per category:

| Category | Weight | Primary Data Source |
|---|---|---|
| Authority & Citability | 30% | `authority` + `eeat` sections |
| Content Structure | 20% | `headings` + `content` sections |
| Entity Clarity | 15% | `authority.named_entities` + `authority.vague_claims` + schema |
| Technical Foundation | 20% | `technical` section + `technical_checker.py` output |
| AI Crawlability | 10% | `technical` bot analysis + `llms_txt` + `x_robots_tag` |
| Freshness | 5% | `meta` dates + `eeat.article_dates` + `technical_checker` headers |

Calculate the composite score:

```
composite = (authority * 0.30) + (structure * 0.20) + (technical * 0.20) + (entity * 0.15) + (ai_crawlability * 0.10) + (freshness * 0.05)
```

**Critical check:** If `technical.is_ssr` is false for the target page, flag this immediately as a show-stopper. The page is invisible to AI crawlers and must be fixed before any content optimization matters. Set the Technical Foundation score to 0.

### Step 5: Report Card

Present a side-by-side comparison table:

```
                        Target   Comp1    Comp2    Comp3
Authority & Citability    32      71       65       58
Content Structure         55      68       72       61
Entity Clarity            28      64       59       53
Technical Foundation      70      85       80       75
AI Crawlability           45      80       70       65
Freshness                 60      80       70       65
──────────────────────────────────────────────────────────
COMPOSITE                 46      74       70       64
```

Below the table, provide a sub-score breakdown for each category on the target page. For each category where the target scores lower than the top competitor:

- State the gap with specific numbers from the extraction data (e.g., "You have 2 statistics, Competitor A has 14").
- Reference the research basis (e.g., "Princeton GEO found statistics addition improves visibility by 25.9%").
- Skip categories where the target is competitive (within 10 points of the leader).

**Flag show-stoppers** prominently:

- `is_ssr` is false — "SHOW-STOPPER: Page is not server-side rendered. AI crawlers see an empty page."
- Citation bots blocked — "SHOW-STOPPER: Citation bots (ChatGPT-User, PerplexityBot) are blocked in robots.txt. Your content cannot appear in AI search results."

Note data source quality: "CWV scores based on heuristic analysis" or "CWV scores based on Lighthouse MCP measurement" as applicable.

### Step 6: Generate Fixes

**6a. Run fix generator**

Pipe the target page's extraction JSON to the fix generator:

```bash
echo '{extraction_json}' | python3 scripts/fix_generator.py
```

This outputs a JSON object with keys: `schema_fixes`, `llms_txt`, `robots_fixes`, `meta_fixes`, `weak_sections`.

**6b. Present schema fixes**

For each entry in `schema_fixes`, present the ready-to-paste JSON-LD block:

```
**Missing: FAQPage Schema**
Reason: FAQ content detected on page but FAQPage schema is missing. 82% of AI citations include structured data.

Add this to your page's <head>:
```json
<script type="application/ld+json">
{ ... generated schema ... }
</script>
```

**6c. Present llms.txt**

If `llms_txt` content was generated, present it:

```
**Generated llms.txt**
Save this file at your domain root (e.g., https://example.com/llms.txt):

```markdown
# Site Title
> Site description

## Pages
- [Page Title](url): description
```

**6d. Present robots.txt fixes**

If `robots_fixes` content was generated, present the corrected rules with the training-vs-citation bot explanation:

```
**Robots.txt Fix**
Replace your current AI bot rules with:

# Training bots — blocked (content used for model training)
User-agent: GPTBot
Disallow: /

# Citation bots — allowed (these cite your content in AI answers)
User-agent: PerplexityBot
Allow: /
```

**6e. Present meta tag fixes**

If `meta_fixes` contains suggestions, present them. For Next.js projects, generate a TypeScript metadata export:

```typescript
export const metadata: Metadata = {
  title: "Optimized Title Here (50-60 chars)",
  description: "Optimized description here targeting 150-160 characters for best search visibility.",
  openGraph: {
    title: "Optimized Title Here",
    description: "Optimized description here.",
    images: ["/og-image.png"],
  },
};
```

**6f. Rewrite weak sections**

Read `references/princeton-techniques.md` for rewriting methods.

Using the `weak_sections` output, identify the 3-5 weakest sections. For each, apply the top 3 Princeton techniques (Statistics Addition, Citation Addition, Quotation Addition) and present as:

```
**Section: "Your Heading Here"**
Weakness: Missing statistics, citations, answer-first pattern

ORIGINAL:
> Many small businesses struggle with project management.

FIXED:
> According to a 2025 PMI survey, 67% of businesses with under 50 employees report missing project deadlines at least quarterly. "We saw a 34% reduction in missed deadlines after implementing structured project workflows," says [REPLACE: real customer name and title]. Research from McKinsey (2025) confirms that even basic project management tools reduce delivery delays by 28% for teams under 20 people.

WHY: Added specific statistic (67%), named citation (PMI survey, McKinsey), and expert quote placeholder. Princeton GEO research shows these three techniques combined improve AI citation probability by 30-40%.
```

Mark any placeholder data or quotes clearly with `[REPLACE: ...]` so the owner knows what to fill in with real information. Preserve the owner's voice and tone.

### Step 7: Action Plan

Produce a prioritized checklist grouped by impact level. Write instructions for non-technical people. Use plain language. If something requires a developer, say "Ask your developer to..."

**High Impact (this week):**
Actions based on the biggest scoring gaps and show-stoppers. Things that can be done immediately.

Examples:
- [ ] Fix robots.txt to allow citation bots (copy the rules from Step 6)
- [ ] Add the 3 rewritten sections to your page
- [ ] Add FAQPage schema markup (copy from Step 6)
- [ ] Add missing statistics and citations to thin sections

**Medium Impact (this month):**
Structural and technical changes that take more effort.

Examples:
- [ ] Ask your developer to add Person schema with your credentials
- [ ] Create an llms.txt file at your domain root (copy from Step 6)
- [ ] Fix heading hierarchy (ensure single H1, logical H2/H3 structure)
- [ ] Add OG image and missing meta tags

**Low Impact (when you get to it):**
Minor optimizations and maintenance items.

Examples:
- [ ] Break up sections longer than 300 words with subheadings
- [ ] Add a "last updated" date to the page and update Article schema
- [ ] Improve URL structure if not semantic
- [ ] Set up regular content freshness reviews

## Dependencies

Scripts require:

```bash
pip install beautifulsoup4 requests
```

Optional (for competitor discovery):

```bash
pip install openai
```
