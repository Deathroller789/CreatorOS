# ADR-002: YouTube extraction stack (yt-dlp + youtube-transcript-api)

- **Status:** Accepted
- **Date:** 2026-07-10

## Context

Module 001 (YouTube Intelligence) needs to fetch channel/video metadata and transcripts.
Sprint 2 installs the first runtime dependencies for this. The choice was researched in
[research/technology/youtube_library_evaluation.md](../../research/technology/youtube_library_evaluation.md).

## Decision

Adopt **`yt-dlp`** for channel/video/playlist metadata (and later thumbnails, subtitles,
comments) and **`youtube-transcript-api`** for transcript text. Installed via `uv add`.

## Alternatives

- pytubefix / scrapetube — narrower or thinner; lose to yt-dlp on coverage + maintenance.
- YouTube Data API v3 — authoritative but needs an API key + quota; kept as a fallback for
  exact counts, not the default.
- (transcripts) yt-dlp `--write-auto-subs` — works, but youtube-transcript-api returns
  clean timed text directly and is simpler for our use.

## Tradeoffs

- **Gain:** widest coverage, no API key/quota, both actively maintained (yt-dlp ~daily).
- **Give up:** scraping can break on YouTube changes (mitigated by yt-dlp's fix velocity);
  heavy reliance on yt-dlp is a concentration risk — pin versions, keep the Data API path.

## Consequences

- `yt-dlp` and `youtube-transcript-api` become runtime dependencies in `pyproject.toml`.
- Comment extraction and authoritative-count needs may later require the Data API (its own
  decision when scoped).
