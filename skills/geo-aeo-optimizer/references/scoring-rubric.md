# GEO/AEO Scoring Rubric

Use this rubric to score each page from the `analyze_page.py` extraction JSON. Each category is 0-100. Apply the composite weights at the end.

## 1. Authority Signals (Weight: 30%)

Score based on `authority` section of extraction JSON.

| Score Range | Criteria |
|---|---|
| 0-20 | 0 statistics, 0 citations, 0 quotes |
| 21-40 | 1-2 statistics OR 1 citation, no quotes |
| 41-60 | 3-5 statistics, 1-2 citations, 0-1 quotes |
| 61-80 | 6-10 statistics, 3-5 citations, 2+ quotes, some named entities |
| 81-100 | 10+ statistics with cited sources, 5+ citations, 3+ expert quotes, strong entity density |

**Deductions:** -10 for each vague claim ("research shows", "experts say") without a specific source nearby.

## 2. Content Structure (Weight: 20%)

Score based on `headings` and `content` sections.

| Score Range | Criteria |
|---|---|
| 0-20 | No headings or 1 heading, no lists/tables, no FAQ |
| 21-40 | Some H2s but no H3s, no lists or tables, long paragraphs |
| 41-60 | Valid H1→H2→H3 hierarchy, some lists/tables, avg paragraph < 100 words |
| 61-80 | Clean hierarchy, 2+ lists, 1+ table, FAQ detected, sections self-contained |
| 81-100 | Answer-first pattern detected, comprehensive FAQ, tables for comparisons, all sections extractable and self-contained |

**Deductions:** -15 if `hierarchy_valid` is false (missing H1 or multiple H1s).

## 3. Entity Clarity (Weight: 20%)

Score based on `authority.named_entities` and `authority.vague_claims`.

| Score Range | Criteria |
|---|---|
| 0-20 | 0-1 named entities, many vague claims |
| 21-40 | 2-4 named entities, some vague claims remain |
| 41-60 | 5-8 named entities, few vague claims, some sections still generic |
| 61-80 | 8-15 named entities, rare vague claims, most claims attributed |
| 81-100 | 15+ named entities (people, orgs, frameworks), zero vague claims, every factual statement attributed |

**Key signal:** Ratio of named_entities to vague_claims. Higher is better.

## 4. Technical Crawlability (Weight: 15%)

Score based on `technical` section.

| Score Range | Criteria |
|---|---|
| 0 | `is_ssr` is false — STOP. Nothing else matters. Page is invisible to AI. |
| 1-20 | SSR true but no schema, missing meta tags, AI bots blocked |
| 21-40 | SSR true, has description meta, no schema markup |
| 41-60 | SSR true, description + OG tags, 1 schema type, no AI bots blocked |
| 61-80 | SSR true, all expected meta tags, 2+ schema types, semantic URL |
| 81-100 | SSR true, complete meta tags, 3+ schema types (including FAQPage), all AI bots allowed, semantic URL 5-7 words |

**Critical:** If `is_ssr` is false, this category scores 0 AND a prominent warning is added to the report.

## 5. Freshness (Weight: 10%)

Score based on `meta.published_date` and `meta.modified_date`.

| Score Range | Criteria |
|---|---|
| 0-20 | No dates detectable |
| 21-40 | Published date only, older than 12 months |
| 41-60 | Published date within 12 months, no modified date |
| 61-80 | Published within 6 months OR modified within 3 months |
| 81-100 | Published or modified within 30 days, clear recency signals in content |

## 6. Anti-patterns (Weight: 5%)

Score based on `anti_patterns` section. This is an inverted score — fewer anti-patterns = higher score.

| Score Range | Criteria |
|---|---|
| 0-20 | 3+ keyword density flags, 3+ wall-of-text sections, many unsourced claims |
| 21-40 | 2 keyword flags or 2+ walls of text |
| 41-60 | 1 keyword flag or 1-2 thin sections |
| 61-80 | No keyword flags, 0-1 thin sections, few unsourced claims |
| 81-100 | Zero flags across all anti-pattern categories |

## Composite Score

```
composite = (authority * 0.30) + (structure * 0.20) + (entity * 0.20) + (technical * 0.15) + (freshness * 0.10) + (anti_patterns * 0.05)
```

## Score Interpretation

| Range | Label | Meaning |
|---|---|---|
| 0-25 | Critical | AI engines unlikely to cite this page |
| 26-50 | Weak | Some signals present but major gaps |
| 51-75 | Competitive | Solid foundation, targeted improvements move the needle |
| 76-100 | Strong | Maintain freshness and monitor competitors |
