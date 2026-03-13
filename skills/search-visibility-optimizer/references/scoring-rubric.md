# Search Visibility Scoring Rubric

Use this rubric to score each page from the `analyze_page.py` extraction JSON. Each category is 0-100. Apply the composite weights at the end.

## 1. Authority & Citability (Weight: 30%)

Score based on `authority` and `eeat` sections of extraction JSON. Combines Princeton GEO evidence density with E-E-A-T credibility signals.

### Sub-scores

**Evidence Density** (60% of category)

| Score Range | Criteria |
|---|---|
| 0-20 | 0 statistics, 0 citations, 0 quotes |
| 21-40 | 1-2 statistics OR 1 citation, no quotes |
| 41-60 | 3-5 statistics, 1-2 citations, 0-1 quotes |
| 61-80 | 6-10 statistics, 3-5 citations, 2+ quotes, some named entities |
| 81-100 | 10+ statistics with cited sources, 5+ citations, 3+ expert quotes, strong entity density |

**E-E-A-T Signals** (40% of category)

| Score Range | Criteria |
|---|---|
| 0-20 | No author bio, no Person schema, no credentials visible |
| 21-40 | Author name present but no bio or credentials |
| 41-60 | Author bio detected OR Person schema present (not both) |
| 61-80 | Author bio + Person schema with `sameAs` links, `knowsAbout` populated |
| 81-100 | Full Person schema (`sameAs`, `knowsAbout`, `honorificSuffix`, `alumniOf`), author bio with credentials, earned media indicators |

**Deductions:**
- -10 per vague claim ("research shows", "experts say") without a specific source nearby
- -5 if author bio detected but no Person schema to back it
- -5 if no `datePublished` on Article schema

## 2. Content Structure (Weight: 20%)

Score based on `headings`, `content`, and section-level extraction. Reflects GEO-16 finding that 32% of AI citations are listicle-format content.

| Score Range | Criteria |
|---|---|
| 0-20 | No headings or 1 heading, no lists/tables, no FAQ |
| 21-40 | Some H2s but no H3s, no lists or tables, paragraphs > 100 words avg |
| 41-60 | Valid H1-H2-H3 hierarchy, some lists/tables, avg paragraph < 100 words |
| 61-80 | Clean hierarchy, 2+ lists, 1+ table, FAQ detected, sections self-contained |
| 81-100 | Answer-first pattern in 50%+ of sections, comprehensive FAQ with schema, tables for comparisons, all sections extractable and self-contained |

### Sub-checks

- **Answer-first pattern:** First sentence of each section is a direct answer (under 30 words, ends with period, contains a factual claim). Target: 50%+ of sections.
- **Self-contained paragraphs:** Each paragraph makes a complete point extractable by AI chunking. No paragraphs that start with "This" or "It" referring to prior context.
- **Listicle format:** Ordered/unordered lists present. Tables for comparisons. Numbered steps for processes.
- **FAQ presence:** FAQ section detected AND backed by FAQPage schema.

**Deductions:**
- -15 if `hierarchy_valid` is false (missing H1 or multiple H1s)
- -10 if no lists or tables anywhere on page
- -5 per section with > 300 words without a subheading break

## 3. Entity Clarity (Weight: 15%)

Score based on `authority.named_entities`, `authority.vague_claims`, and schema entity definitions. GEO-16 identifies entity specificity as a primary citation predictor.

| Score Range | Criteria |
|---|---|
| 0-20 | 0-1 named entities, many vague claims |
| 21-40 | 2-4 named entities, some vague claims remain |
| 41-60 | 5-8 named entities, few vague claims, some sections still generic |
| 61-80 | 8-15 named entities, rare vague claims, most claims attributed |
| 81-100 | 15+ named entities (people, orgs, frameworks), zero vague claims, every factual statement attributed |

### Sub-checks

- **Brand entity:** Organization schema present with `sameAs` linking to LinkedIn, Wikidata, or other authoritative profiles.
- **Author entity:** Person schema with `sameAs`, `knowsAbout`, `honorificSuffix`, `alumniOf`.
- **Product/Service entities:** Named offerings explicitly referenced (not just generic terms).
- **Named entities ratio:** `named_entities / (named_entities + vague_claims)`. Target: >= 0.80.

**Deductions:**
- -10 if Organization schema missing entirely
- -5 if no `sameAs` links on any entity schema
- -5 per section where > 50% of claims are vague

## 4. Technical Foundation (Weight: 20%)

Score based on `technical` section and `technical_checker.py` output. Incorporates traditional SEO signals plus GEO-16 structured data requirements.

| Score Range | Criteria |
|---|---|
| 0 | `is_ssr` is false. STOP. Page is invisible to AI engines. |
| 1-20 | SSR true but no schema, missing meta tags, AI bots blocked |
| 21-40 | SSR true, has description meta, no schema markup, missing OG tags |
| 41-60 | SSR true, description + OG tags, 1 schema type, SSL valid |
| 61-80 | SSR true, all expected meta tags, 2+ schema types, semantic URL, SSL + redirects clean |
| 81-100 | SSR true, complete meta tags, 3+ schema types (including FAQPage), CWV all "good", SSL + HSTS, clean redirect chain, semantic URL 5-7 words |

### Sub-checks

- **SSR detection:** Show-stopper. Score 0 if false.
- **Core Web Vitals (2024 thresholds):**
  - LCP < 2.5s = good, 2.5-4s = needs improvement, > 4s = poor
  - INP < 200ms = good, 200-500ms = needs improvement, > 500ms = poor (replaces FID)
  - CLS < 0.1 = good, 0.1-0.25 = needs improvement, > 0.25 = poor
  - Source: Lighthouse MCP (measured) or `technical_checker.py` (heuristic). Report notes which.
- **SSL:** Valid certificate, HTTP-to-HTTPS redirect, no mixed content.
- **Redirect chain:** Max 1 redirect. Flag chains > 2.
- **Schema completeness:** Check for Article, FAQPage, Organization, BreadcrumbList, HowTo (when applicable).
- **Meta tags:** title (50-60 chars), description (150-160 chars), OG image, OG title, OG description, Twitter card, canonical URL.

**Deductions:**
- Score 0 if `is_ssr` is false (overrides all other signals)
- -15 if any CWV metric is "poor"
- -10 if no schema markup at all
- -5 if title or description outside recommended length
- -5 if missing canonical URL

## 5. AI Crawlability (Weight: 10%)

Score based on `technical` bot analysis, llms.txt detection, and X-Robots-Tag headers. New category reflecting the training-vs-citation bot distinction.

| Score Range | Criteria |
|---|---|
| 0-20 | Citation bots blocked, no llms.txt, no sitemap |
| 21-40 | Citation bots allowed but no llms.txt, no sitemap OR sitemap without lastmod |
| 41-60 | Citation bots allowed, sitemap present, no llms.txt |
| 61-80 | Citation bots allowed, llms.txt present, sitemap with lastmod, training bot policy intentional |
| 81-100 | All citation bots allowed, well-structured llms.txt (title + descriptions + URLs), sitemap with lastmod, X-Robots-Tag clean, intentional training bot policy documented |

### Sub-checks

- **Training bots** (`GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot`): Blocking is a business decision, not a penalty. Report status neutrally.
- **Citation bots** (`ChatGPT-User`, `PerplexityBot`, `Claude-Web`, `Amazonbot`, `Bytespider`): Blocking is almost always unintentional. Flag as high-priority fix.
- **llms.txt:** Present at `/llms.txt`. Well-structured = has title line, description, and URL entries with descriptions. Count entries.
- **X-Robots-Tag:** HTTP header check. Flag `noindex` or `nofollow` on pages that should be indexed.
- **Sitemap:** Accessible, valid XML, includes `<lastmod>` dates.

**Deductions:**
- -30 if any citation bot is blocked (high-priority fix)
- -10 if no llms.txt
- -5 if sitemap missing or lacks lastmod dates
- -5 if X-Robots-Tag contains noindex on indexable pages

## 6. Freshness (Weight: 5%)

Score based on date signals in schema, HTTP headers, and content.

| Score Range | Criteria |
|---|---|
| 0-20 | No dates detectable anywhere |
| 21-40 | Published date only, older than 12 months |
| 41-60 | Published date within 12 months, no modified date |
| 61-80 | Published within 6 months OR modified within 3 months, Last-Modified header present |
| 81-100 | Published or modified within 30 days, Last-Modified header + ETag present, clear recency signals in content |

### Sub-checks

- **Schema dates:** `datePublished` and `dateModified` in Article/WebPage schema.
- **HTTP headers:** `Last-Modified` header present. `ETag` header present (enables conditional requests).
- **Content signals:** Year references, "updated for [year]", recent event mentions.
- **Sitemap lastmod:** Matches actual content modification date.

**Deductions:**
- -10 if `datePublished` present but `dateModified` missing (suggests content is stale)
- -5 if Last-Modified header missing

## Composite Score

```
composite = (authority * 0.30) + (structure * 0.20) + (technical * 0.20) + (entity * 0.15) + (ai_crawlability * 0.10) + (freshness * 0.05)
```

## Score Interpretation

| Range | Label | Meaning |
|---|---|---|
| 0-25 | Critical | AI engines unlikely to cite this page. Major structural or technical gaps. |
| 26-50 | Weak | Some signals present but significant gaps in authority or technical foundation. |
| 51-75 | Competitive | Solid foundation. Targeted improvements in weakest categories move the needle. |
| 76-100 | Strong | Well-optimized. Maintain freshness, monitor competitors, and iterate on content. |

## Research Basis

- **Authority & Citability:** Princeton GEO (arxiv 2311.09735) — statistics +25.9%, citations +24.9%, quotations +27.8%
- **Content Structure:** GEO-16 (arxiv 2509.10762) — 32% of AI citations are listicle-format
- **Entity Clarity:** GEO-16 — entity specificity is a primary citation predictor
- **Technical Foundation:** GEO-16 — structured data is the strongest single predictor of citation
- **AI Crawlability:** Industry practice 2025 — training vs. citation bot distinction
- **Freshness:** GEO-16 — recency signals correlate with citation probability
- **E-E-A-T:** Qwairy 2025 — 82% of AI citations include structured data, 40% more citations with visible credentials
