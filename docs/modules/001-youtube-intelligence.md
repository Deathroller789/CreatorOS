# Module 001: YouTube Intelligence — Ingestion Design

_System design document. No implementation code. Describes what CreatorOS collects for a
YouTube channel, why, from where, and how it is stored and refreshed. Tool choices follow
[research/technology/youtube_library_evaluation.md](../../research/technology/youtube_library_evaluation.md);
state is stored in SQLite per [0001](../decisions/0001-memory-architecture.md)._

## Purpose

Given a **YouTube channel URL**, build and maintain a local, queryable knowledge base of
everything about that channel and its videos — durable enough to power research, trend
analysis, and content decisions over time. This is the foundation the rest of the module
(analysis, reporting, search) builds on.

## Input

A channel URL in any of its forms: `youtube.com/@handle`, `/channel/UC…`, `/c/Custom`,
`/user/Legacy`. Stage 1 resolves all of these to the canonical **`channel_id`** (`UC…`),
which is the stable primary key everything else hangs off.

## Pipeline stages

1. **Resolve** — normalize the URL to a canonical `channel_id`.
2. **Enumerate** — list the channel's videos and playlists (IDs + light metadata).
3. **Fetch metadata** — full per-channel and per-video metadata.
4. **Fetch transcripts** — captions where available.
5. **Fetch comments** *(optional / later)* — top-level comments and replies.
6. **Fetch assets** — thumbnails, avatar, banner.
7. **Store** — write canonical facts and append time-series snapshots to SQLite.
8. **Report** — emit a structured summary.

Volatile metrics (counts) are captured as **append-only time-series snapshots** so growth
is measurable; canonical facts are stored once and updated only on change.

## Data catalog

Columns for every field: **Why it matters · Source · Tool · Store permanently? · Update
frequency · Confidence**. "Store permanently" = keep the canonical value; metrics marked
*time-series* are appended as dated snapshots rather than overwritten.

### Channel

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `channel_id` (UC…) | Stable primary key for everything | Channel page | yt-dlp | Yes | Never | High |
| `handle` (@name) | Human identity, URL building | Channel page | yt-dlp | Yes | Rare | High |
| `title` | Display name | Channel page | yt-dlp | Yes | Rare | High |
| `description` | Positioning, keywords, links | Channel page | yt-dlp | Yes | Low | High |
| `subscriber_count` | Audience size / growth | Channel page | yt-dlp (rounded); Data API (exact) | Yes — time-series | Daily–weekly | Medium (yt-dlp rounds) |
| `view_count` (channel total) | Cumulative reach | Channel page | yt-dlp / Data API | Yes — time-series | Weekly | Medium |
| `video_count` | Catalog size, triggers re-enumeration | Channel page | yt-dlp | Yes — time-series | On change | High |
| `country` | Localization, market | Channel page | yt-dlp / Data API | Yes | Rare | Medium |
| `joined_date` | Channel age, tenure | About tab | Data API (yt-dlp often omits) | Yes | Never | Medium |
| `avatar` / `banner` | Branding assets | Channel page | yt-dlp (thumbnails) | Yes — file | Rare | High |
| `external_links` | Cross-platform presence | Channel page | yt-dlp | Yes | Rare | Medium |
| `topic_categories` | Niche classification | Channel page | Data API | Optional | Rare | Low |

### Playlist

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `playlist_id` | Key; content organization | Channel playlists | yt-dlp | Yes | Never | High |
| `title` / `description` | How the creator groups content | Playlist page | yt-dlp | Yes | Low | High |
| `video_ids` (ordered) | Sequencing, series structure | Playlist page | yt-dlp (`--flat-playlist`) | Yes | On change | High |
| `video_count` | Playlist size | Playlist page | yt-dlp | Yes — time-series | On change | High |

### Video

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `video_id` | Primary key | Video page | yt-dlp | Yes | Never | High |
| `title` | Content, packaging, SEO | Video page | yt-dlp | Yes | Rare | High |
| `description` | Links, chapters, keywords | Video page | yt-dlp | Yes | Low | High |
| `upload_date` / `published_at` | Timeline, cadence analysis | Video page | yt-dlp | Yes | Never | High |
| `duration` | Format (short vs long), pacing | Video page | yt-dlp | Yes | Never | High |
| `view_count` | Performance signal | Video page | yt-dlp | Yes — time-series | Daily–weekly | High |
| `like_count` | Engagement signal | Video page | yt-dlp | Yes — time-series | Weekly | Medium (sometimes hidden) |
| `comment_count` | Engagement / discussion volume | Video page | yt-dlp | Yes — time-series | Weekly | Medium |
| `tags` | Creator's SEO intent | Video page | yt-dlp | Yes | Rare | Medium (often empty) |
| `category` | Classification | Video page | yt-dlp | Yes | Never | Medium |
| `chapters` | Structure, topic segmentation | Video page | yt-dlp | Yes | Never | Medium |
| `thumbnail` | Packaging; CTR analysis | Video page | yt-dlp | Yes — file | Rare | High |
| `is_short` | Format cohorting | Derived / URL | yt-dlp + rule | Yes | Never | Medium |
| `live_status` | Live/premiere vs VOD | Video page | yt-dlp | Yes | Never | Medium |
| `availability` | Public/unlisted/private/removed | Video page | yt-dlp | Yes | On change | High |
| `default_language` | Localization | Video page | yt-dlp | Optional | Never | Low |

### Transcript (per video)

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `segments` (text, start, duration) | The core content for search/analysis/summarization | Captions | youtube-transcript-api | Yes | Never (once fetched) | High *when captions exist* |
| `available_languages` | Localization, translation options | Captions | youtube-transcript-api | Yes | Rare | High |
| `is_generated` | Auto-caption vs human (quality) | Captions | youtube-transcript-api | Yes | Never | High |
| caption availability | Not all videos have captions | Captions | youtube-transcript-api | Yes (flag) | On change | Medium |
| subtitle files (vtt/srt) | When we need formatted files, not just text | Captions | yt-dlp (`--write-subs`) | Optional — file | Never | High |

### Comments (per video — optional, fetched deliberately)

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| `comment_id`, `parent_id` | Thread structure | Video page | yt-dlp (`getcomments`) | Selective | Snapshot | Medium |
| `text` | Audience sentiment, topics, questions | Video page | yt-dlp | Selective | Snapshot | Medium |
| `author`, `author_channel_id` | Who is engaging | Video page | yt-dlp | Selective | Snapshot | Medium |
| `like_count`, `reply_count` | Which comments resonate | Video page | yt-dlp | Selective — time-series | Snapshot | Medium |
| `published_at` | When discussion happened | Video page | yt-dlp | Selective | Snapshot | Medium |

Comments are the most fragile and highest-volume data on YouTube. They are **opt-in per
run**, stored selectively (e.g. top-N by likes), and the official Data API is the fallback
when authoritative/complete retrieval is required.

### Derived (computed by CreatorOS, not scraped)

| Field | Why it matters | Source | Tool | Permanent? | Update freq | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| engagement ratios (like/view, comment/view) | Normalized performance | Computed from stored metrics | CreatorOS | Yes | On ingest | High |
| upload cadence | Consistency, strategy | Computed from `upload_date` | CreatorOS | Yes | On ingest | High |
| growth deltas (subs/views over time) | Trajectory | Computed from time-series snapshots | CreatorOS | Yes | On ingest | High |

## Storage model (conceptual)

Single SQLite database (source of truth). Conceptual tables, not DDL:

- `channels` — one row per channel (canonical facts).
- `channel_stats` — append-only `(channel_id, captured_at, subscriber_count, view_count, video_count)`.
- `playlists` and `playlist_items` — playlists and their ordered membership.
- `videos` — one row per video (canonical facts), FK → `channels`.
- `video_stats` — append-only `(video_id, captured_at, view_count, like_count, comment_count)`.
- `transcripts` — one row per (video, language): flags + storage reference; segments either
  child rows in `transcript_segments` or a stored blob, TBD.
- `comments` — optional, FK → `videos`, self-referencing `parent_id`.
- `assets` — downloaded files (thumbnails, avatar, banner): type, `video_id`/`channel_id`,
  local path, source URL.

**Principle:** canonical facts are updated in place only on change; every volatile metric
is an append-only snapshot so history is never lost. Large binaries (thumbnails, subtitle
files) live on disk with paths recorded in the DB, not as blobs, keeping the DB lean.

## Refresh strategy

- **Static** fields fetched once.
- **Slow** fields re-checked occasionally; updated only on change.
- **Metrics** captured on a schedule (daily/weekly) as new snapshots.
- **Enumeration** re-run when `video_count` changes; only new/changed videos are deeply
  fetched (incremental, not full re-scrape).

## Confidence & risks

- **Structural data** (IDs, titles, dates, durations, transcripts): high confidence.
- **Exact counts** (subs, likes): medium via yt-dlp (rounding, hidden metrics) — use the
  Data API when exactness matters.
- **Comments**: medium and fragile; treat as best-effort unless the Data API is used.
- **Concentration risk**: yt-dlp powers most of this. Mitigation: pin the version, refresh
  deliberately, keep the Data API path documented. (See the library evaluation.)
- **ToS / rate-limiting / legal**: out of scope here; must be reviewed before scaled use.

## Sprint 2 scope (the executable milestone)

The first shippable capability, `creatoros analyze-channel <url>`, implements the minimum
end-to-end slice — ugly output is fine:

1. **Resolve** URL → `channel_id`.
2. **Fetch** channel metadata + enumerate videos (yt-dlp).
3. **Transcripts** for videos where available (youtube-transcript-api).
4. **Store** channels, videos, and transcripts in SQLite locally.
5. **Report** — a structured summary (channel overview, video list, transcript coverage).

Deferred past Sprint 2: comments, full asset downloading, scheduled metric snapshots,
derived analytics. Adopting `yt-dlp` and `youtube-transcript-api` (via `uv add`) gets an
ADR at that point — this design plus the library evaluation are the required inputs.

## Open questions

- Transcript storage: normalized segment rows vs. stored blob + offsets.
- Comment retention policy (all vs. top-N; refresh cadence).
- Where authoritative counts are mandatory enough to require the Data API (and a key).
- Backfill vs. incremental on first run for very large channels.
