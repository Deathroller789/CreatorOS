# Competitive reuse audit — who already does CreatorOS's job

## Summary

**Surveyed 2026-07-13 (GitHub + web).**
No existing project — open-source or commercial — does what CreatorOS does: ingest *public*
YouTube data and turn it into age-normalized, ranking-based, confidence-bounded intelligence behind
an immutable findings contract with deterministic renderers.
The closest open-source neighbour (`mlorentedev/yt-metrics-cli`) is a young engagement-rate reporter
that needs an official API key and has none of the age-normalization, outlier ranking, cadence,
confidence discipline, or immutable-findings design.
The category is otherwise split into narrow single-idea scripts (outlier finders), heavy
dashboard/ETL stacks (Airflow/Kafka/PowerBI), and LLM-wrapper repos — none overlapping our design.
Commercial SaaS (VidIQ, 1of10, ViewStats, OutlierKit) validates the *problem* but is deliberately
predictive/prescriptive where CreatorOS is descriptive.
Recommendation: keep the current infrastructure reuse (yt-dlp + youtube-transcript-api + SQLite),
which is correct, and keep building only the intelligence layer, which is genuinely differentiated
and not available off the shelf.
Confidence: **Medium** — the analysis is solid; individual star counts and young-repo details are
2026-07-13 snapshots and move fast.

## Evidence

### Existing projects — open-source software that overlaps the job

No single OSS project covers CreatorOS's pipeline. The overlap falls into five categories.

**1. Official-API SDKs** — different data model (owner OAuth, authoritative counts, no derived
intelligence).

| Project | License | What it is | Distance from CreatorOS |
|---------|---------|------------|-------------------------|
| `parafoxia/analytix` | BSD | YouTube Analytics API via OAuth; owner-only reporting | Different source (owner OAuth vs public scrape); no intelligence layer |
| `gojiplus/tubern` (R) | — | R wrapper over YouTube APIs | Language + API-key model; no derived analysis |

CreatorOS uses yt-dlp public data with no OAuth and no key, so it can analyze *any* channel, not
only one the user owns.

**2. CLI tools — the closest neighbour.**

`mlorentedev/yt-metrics-cli` (MIT) is the nearest thing to CreatorOS: channels → engagement rates
plus transcripts → CSV/text reports, with CI and tests.
But it needs a Data API key, centres on engagement-rate plus "viral detection," and offers
multi-channel benchmarking — and it has **no** age-normalization, outlier ranking, cadence analysis,
confidence discipline, or immutable findings contract.
It is young and small.
Its engagement-rate metric and multi-channel benchmarking are borrowable *ideas*, not code to adopt.

**3. Outlier finders — single-idea overlap with our Q1.**

`zahidjavali/youtube-outlier-tool`, `georgewangyu/youtubebot`, and `peruvian-bull23/ideate-app` each
implement just the "outlier video" idea that CreatorOS's `performance_index` ranking covers.
All are experimental (0–1 stars), some unlicensed, none age-normalize or express confidence.

**4. Dashboards / ETL — opposite philosophy.**

| Project | Stack | Why it is not CreatorOS |
|---------|-------|-------------------------|
| `JensBender/youtube-channel-analytics` | Airflow + Docker + PowerBI | Heavy infra; dashboard + predictive orientation |
| `madEffort/youtube-trend-dashboard` | Web dashboard | Trend/dashboard focus, not a findings contract |
| `airscholar/YoutubeAnalytics` | Kafka streaming | Streaming-ETL infra; opposite of stdlib-first, descriptive |

These optimize for live dashboards, prediction, and sentiment — the maintainability and
infrastructure profile CreatorOS deliberately rejects.

**5. "Content intelligence" repos — mostly hollow.**

`Rahul-1052/Stratify`, `hex-yt-intel`, and roughly eight identically-named
`youtube-content-intelligence` repos are mostly thin LLM wrappers, near-empty, or AI-generated, with
0 stars.
They share CreatorOS's *name space* but not its design.

Notebooks and portfolio EDA (dozens exist) are analyses, not reusable software.

### Existing tools — commercial, closed-source (validates the problem)

VidIQ, 1of10, ViewStats, OutlierKit, TubeBuddy, and Spotter Studio all sell YouTube analytics as a
service.
1of10's headline — outliers performing "6×–100× vs channel size" — is essentially CreatorOS's
`performance_index`, which confirms the metric matters.
But every one of these is predictive or prescriptive SaaS ("do this next," "this will go viral"),
closed-source, and account-bound.
CreatorOS is deliberately descriptive, open, and public-data — a different product on purpose, not a
worse version of the same one.

### Existing gaps — what nobody ships

- **Public-data intelligence.** Serious tools use the official Data API (key + quota + owner scope);
  the descriptive intelligence layer on top of *public* scraped data is unoccupied.
- **Age-normalization as a first-class principle.** Outlier repos rank raw views; none normalize by
  upload age before ranking, so young and old videos are compared unfairly.
- **Confidence and sample-size discipline.** No surveyed project reports confidence, sample size, or
  refuses to overclaim on thin data.
- **An immutable findings contract.** None separate a canonical, serializable findings object from
  its rendered reports; all conflate computation with presentation.
- **Descriptive-by-charter.** Every commercial tool drifts toward prediction; none commit to
  "descriptive, not predictive" as a stated boundary.

### CreatorOS differentiation

The differentiator is the *shape* of the pipeline, not any single metric:

- public-data ingestion (yt-dlp, no key, any channel) →
- age-normalized, ranking-based, confidence-bounded metrics and intelligence →
- an immutable canonical **findings** contract →
- deterministic renderers that serialize only (never compute, infer, or reorder).

Layered on a stdlib-first, maintainability-first codebase with no frameworks, no ORM, and no
dashboard infrastructure.
That combination is not available off the shelf, open-source or commercial.

### What CreatorOS intentionally refuses to rebuild

Two kinds of refusal, both deliberate.

**Refuses to rebuild — reuse existing software instead** (per the reuse-first charter and
`research/technology/reuse_audit.md`):

- extraction → **yt-dlp** (not a hand-rolled scraper)
- transcripts → **youtube-transcript-api**
- storage / source of truth → **stdlib `sqlite3`**
- browser automation (future) → **Playwright** library
- LLM access (future) → **Anthropic SDK**, not a framework

**Refuses to build at all — out of scope by philosophy**, even though competitors sell it:

- prediction and prophecy ("this will get N views," "post at 5pm") — CreatorOS is descriptive
- prescriptive coaching / next-video recommendations
- sentiment and ML pipelines, trend-forecasting models
- live dashboards and BI infrastructure (a future read-only `serve` is the *only* opening, ADR-007)
- owner-only OAuth analytics — the public-data model is the point

Refusing these is what keeps the codebase small and the intelligence honest; they are the features
that would pull CreatorOS toward the dashboard/predictive category it deliberately avoids.

### Things CreatorOS deliberately does NOT compete on

The surveyed tools bundle a creator-workflow suite around their analytics.
CreatorOS competes on none of it.
It is an intelligence engine, not a creator studio — the whole product is *understanding a channel*,
not *operating one*.

| Not competing on | Whose product it is | Why it is out of scope |
|------------------|---------------------|------------------------|
| Real-time dashboards | VidIQ, ViewStats, BI stacks | Live UI + infrastructure; CreatorOS emits point-in-time findings, not a live surface |
| Scheduling / publishing | TubeBuddy, Buffer-likes | Operating a channel, not analyzing one |
| Team collaboration | TubeBuddy, Spotter | Multi-user workflow product, orthogonal to intelligence |
| AI script generation | VidIQ, Spotter Studio | Generative and prescriptive; CreatorOS is descriptive, not a content author |
| Video editing | Descript, CapCut, etc. | A different tool category entirely |
| Thumbnail generation | 1of10, VidIQ, design tools | Creative production, not measurement |

This is the sharper edge of the differentiation section: CreatorOS is deliberately narrow.
It answers "what is true about this channel, and how confident can we be?" and stops there —
everything above is somebody else's product, and building it would dilute the one thing CreatorOS
does that nobody else does.

### Remaining reuse opportunities

Borrowable *ideas* (evaluate later, do not adopt now):

- **Engagement-rate metrics** and **multi-channel benchmarking** from `yt-metrics-cli` — additive
  metric ideas that would fit the existing metric engine as new pure functions.
- **Multi-format export** precedent from `analytix` — corroborates ADR-007's export surface; nothing
  to adopt, just a design confirmation.

No new dependency is implied by any of these; each would be new intelligence code, not new plumbing.

## Confidence

**Medium.**
The structural conclusion — that no project matches CreatorOS's public-data → age-normalized →
confidence-bounded → immutable-findings pipeline — is robust and unlikely to be wrong.
The uncertainty is granular and time-bound: star counts, "young/small" judgements, and the exact
feature sets of fast-moving 0–1-star repos are 2026-07-13 snapshots.
This would be wrong only if a mature project exists that the GitHub/web survey missed under
different terminology — possible, not likely, and cheaply re-checked before any build decision.

## Sources

- `parafoxia/analytix` — <https://github.com/parafoxia/analytix> (accessed 2026-07-13)
- `mlorentedev/yt-metrics-cli` — <https://github.com/mlorentedev/yt-metrics-cli> (accessed 2026-07-13)
- `JensBender/youtube-channel-analytics` — <https://github.com/JensBender/youtube-channel-analytics> (accessed 2026-07-13)
- OutlierKit — <https://outlierkit.com> (accessed 2026-07-13)
- 1of10 / Overseeros — <https://overseeros.com> (accessed 2026-07-13)

## Open Questions

- Exact current star counts / activity of the young repos are snapshots; not re-verified per the
  "don't re-run the survey" directive. Re-check before acting on any single competitor.
- Whether a mature project exists under different terminology (e.g. "channel benchmarking",
  "content forensics") that this survey's search terms missed.
- Whether the public-data (yt-dlp) vs official-Data-API choice — the one axis every serious
  competitor decides differently from us — warrants its own ADR, given the maintainability priority
  and the fragility of scraping. Deliberately deferred to a future decision, not resolved here.

## Next Actions

- No build and no dependency from this audit — it is research only.
- File a future ADR candidate: **Data-API-vs-yt-dlp fallback strategy** (public-data flexibility vs
  scraping fragility), the one place CreatorOS's choice diverges from every serious competitor.
- Revisit `yt-metrics-cli`'s engagement-rate and multi-channel-benchmark ideas as additive metrics
  *after* the real-channel exercise phase, not before.
- Re-run a targeted competitor check before any decision to build a feature a competitor already
  ships, to confirm nothing mature emerged since 2026-07-13.
