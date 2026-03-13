# E-E-A-T Checklist for AI Search Visibility

Platform-specific E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals that influence AI citation probability. Based on Qwairy 2025 research.

## Key Statistics

- **82%** of AI-cited pages include structured data (schema markup)
- **40%** more citations for pages with visible author credentials
- Structured data is the strongest single predictor of AI citation across all platforms

## Platform-Specific Signals

### ChatGPT
- **Values:** Academic credentials, institutional affiliations, publication history
- **Checks:** `honorificSuffix` (PhD, CPA, etc.), `alumniOf`, `sameAs` linking to academic profiles
- **Behavior:** Tends to cite pages where the author's expertise is verifiable through schema

### Claude
- **Values:** Methodology transparency, reasoning clarity, source attribution
- **Checks:** Inline citations with named sources, explained methodology, logical argument structure
- **Behavior:** Favors content that shows its work — "according to [source]" over unsourced claims

### Perplexity
- **Values:** Freshness + credentials combination
- **Checks:** Recent `dateModified`, author credentials, source recency
- **Behavior:** Heavily weights recency. Stale pages with great credentials still lose to fresh pages with good credentials.

### Gemini
- **Values:** Google ecosystem signals — Search Console indexing, Knowledge Graph presence
- **Checks:** Organization `sameAs` to Google Business Profile, Knowledge Graph entity, indexed pages
- **Behavior:** Leverages existing Google Search ranking signals more than other AI engines

## Schema Properties to Verify

### Person Schema

```json
{
  "@type": "Person",
  "name": "Required — full name",
  "sameAs": ["LinkedIn URL", "Twitter URL", "personal site"],
  "knowsAbout": ["topic1", "topic2", "topic3"],
  "honorificSuffix": "PhD, CFA, CPA, etc.",
  "alumniOf": {
    "@type": "Organization",
    "name": "University or institution"
  },
  "jobTitle": "Current role",
  "worksFor": {
    "@type": "Organization",
    "name": "Company"
  }
}
```

**Priority fields by impact:**
1. `sameAs` — verifiable identity across platforms (highest impact)
2. `knowsAbout` — topical authority signal
3. `honorificSuffix` — credential visibility (40% citation lift)
4. `alumniOf` — institutional credibility

### Organization Schema

```json
{
  "@type": "Organization",
  "name": "Required",
  "sameAs": ["LinkedIn company page", "Wikidata entry", "Crunchbase"],
  "url": "https://example.com",
  "logo": "https://example.com/logo.png"
}
```

**Priority fields:**
1. `sameAs` — links to authoritative profiles (LinkedIn, Wikidata especially)
2. `url` — canonical site
3. `logo` — brand recognition in AI-generated results

### Article Schema

```json
{
  "@type": "Article",
  "headline": "Required",
  "author": { "@type": "Person", "name": "Required" },
  "datePublished": "ISO 8601 — required",
  "dateModified": "ISO 8601 — required for freshness",
  "publisher": { "@type": "Organization", "name": "Required" }
}
```

**Priority fields:**
1. `author` — must reference a Person with its own schema (not just a name string)
2. `datePublished` + `dateModified` — freshness signals
3. `publisher` — organizational authority

## Audit Checklist

Use during scoring to check each signal. Mark as present/absent.

### Author Signals
- [ ] Author name visible on page
- [ ] Author bio section present ("About the Author", "Written by", or similar)
- [ ] Credentials visible in bio (title, certifications, years of experience)
- [ ] Person schema in JSON-LD with `name`
- [ ] Person schema has `sameAs` with 1+ external profile URLs
- [ ] Person schema has `knowsAbout` with relevant topics
- [ ] Person schema has `honorificSuffix` (if applicable)
- [ ] Person schema has `alumniOf` (if applicable)
- [ ] `rel="author"` link present

### Organization Signals
- [ ] Organization schema in JSON-LD
- [ ] `sameAs` links to LinkedIn company page
- [ ] `sameAs` links to Wikidata/Wikipedia (if entity exists)
- [ ] Logo URL in schema

### Article Signals
- [ ] Article schema present
- [ ] `author` field references Person schema (not just string)
- [ ] `datePublished` in ISO 8601 format
- [ ] `dateModified` in ISO 8601 format
- [ ] `publisher` references Organization schema

### Content-Level Signals
- [ ] Claims attributed to named sources
- [ ] Statistics have inline citations
- [ ] Expert quotes include name and title
- [ ] Methodology explained where applicable
- [ ] No vague authority claims ("research shows", "experts agree")

## Scoring Impact

When scoring Authority & Citability (30% weight), split the category:
- **Evidence Density** (60% of category): statistics, citations, quotes — Princeton GEO signals
- **E-E-A-T Signals** (40% of category): schema properties, author bio, credentials — this checklist

A page with strong evidence but no E-E-A-T signals caps at ~60/100 for Authority.
A page with full E-E-A-T but no evidence caps at ~40/100 for Authority.
Both are needed for 80+.

## Source

Qwairy, "E-E-A-T and AI Citations: How Credentials Drive Generative Engine Visibility," 2025.
