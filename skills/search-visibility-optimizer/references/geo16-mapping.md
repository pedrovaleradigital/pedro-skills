# GEO-16 Framework Mapping

Maps the GEO-16 pillars (arxiv 2509.10762, September 2025) to the search-visibility-optimizer scoring categories. Use this to understand why each scoring category exists and what research backs it.

## Key Findings

- **G >= 0.70 yields 4.2x citation improvement.** Pages scoring 0.70+ on the GEO-16 composite are cited 4.2x more than pages below that threshold.
- **Structured data is the single strongest predictor** of AI citation across all engines tested.
- **Metadata + semantic HTML + structured data** together predict citations better than content quality alone.

## By-Engine Citation Rates

| Engine | Citation Rate at G >= 0.70 | Notes |
|---|---|---|
| Brave Search AI | 78% | Most responsive to structured data |
| Google AI Overviews | 72% | Leverages existing Search index signals |
| Perplexity | 45% | Lower overall but rewards freshness heavily |

## The 6 Core GEO-16 Principles

### 1. People-First Answers
Content should directly answer questions, not gate answers behind preamble. Maps to answer-first pattern detection in Content Structure.

### 2. Structured Data
Schema markup (JSON-LD) enables engines to parse entities, relationships, and facts without inference. Maps to Technical Foundation (schema completeness) and Entity Clarity.

### 3. Provenance
Every claim should be traceable to a source. Named entities, citations, expert quotes. Maps to Authority & Citability and Entity Clarity.

### 4. Freshness
Recency signals — dates in schema, HTTP headers, content references to current events. Maps to Freshness category.

### 5. Risk Management
Control which bots access content. Distinguish training crawlers from citation crawlers. Maps to AI Crawlability.

### 6. RAG Fit
Content should be chunking-friendly — self-contained paragraphs, clear section boundaries, extractable answers. Maps to Content Structure.

## GEO-16 Pillar-to-Category Mapping

| GEO-16 Pillar | Our Category | Weight | What We Check |
|---|---|---|---|
| P1: Direct answers | Content Structure | 20% | Answer-first pattern per section |
| P2: Heading hierarchy | Content Structure | 20% | H1-H2-H3 validity, logical nesting |
| P3: FAQ markup | Content Structure + Technical | 20% + 20% | FAQ detected + FAQPage schema |
| P4: Schema.org entities | Technical Foundation | 20% | Article, Organization, Person, BreadcrumbList |
| P5: Named entities | Entity Clarity | 15% | Named entity count, vague claims ratio |
| P6: Author credentials | Authority & Citability | 30% | Person schema, author bio, sameAs links |
| P7: Source attribution | Authority & Citability | 30% | Citation count, named sources |
| P8: Statistical evidence | Authority & Citability | 30% | Statistics count, inline source attribution |
| P9: Expert quotations | Authority & Citability | 30% | Quote count, named + titled speakers |
| P10: Publication dates | Freshness | 5% | datePublished, dateModified in schema |
| P11: Content recency | Freshness | 5% | Last-Modified header, ETag, content signals |
| P12: Sitemap quality | AI Crawlability | 10% | Sitemap accessible, lastmod dates present |
| P13: Crawl permissions | AI Crawlability | 10% | Training vs. citation bot classification |
| P14: LLM-specific access | AI Crawlability | 10% | llms.txt, X-Robots-Tag |
| P15: Self-contained sections | Content Structure | 20% | Paragraph independence, no dangling references |
| P16: List/table formatting | Content Structure | 20% | Lists, tables, comparison formats |

## Applying the Threshold

When scoring, check if the composite score crosses the 70-point threshold (equivalent to G >= 0.70). Below 70, improvements yield disproportionate citation gains. Above 70, the page is in the high-citation tier and gains are incremental.

Flag in the report:
- **Below 70:** "This page is below the GEO-16 citation threshold. Improvements in [weakest categories] will have outsized impact."
- **Above 70:** "This page meets the GEO-16 citation threshold. Focus on maintaining freshness and monitoring competitor movement."

## Source

Aggarwal et al., "GEO-16: A Comprehensive Framework for Generative Engine Optimization," September 2025, arxiv 2509.10762.
