# YouTube Extraction Libraries — Evaluation

## Summary

**Evaluated 2026-07-10. Nothing was installed** — this is a decision-support report only.

For CreatorOS's YouTube tooling, two libraries win everything:

- **`yt-dlp`** — winner for **comments, channel metadata, playlist metadata, thumbnails,
  and subtitles** (5 of 6 categories).
- **`youtube-transcript-api`** — winner for **transcript extraction**.

The dominant result is deliberate: optimizing for maintenance, accuracy, speed, and
long-term reliability (and explicitly *ignoring popularity*) converges on the one project
that is maintained essentially daily and covers the widest surface. Standardizing on
`yt-dlp` means **one dependency to track** for most needs — a maintenance win — with a
single, well-understood risk (see Open Questions). Confidence: **High** for yt-dlp's
dominance; **Medium** for comments specifically (the most fragile area on all of YouTube).

## Evidence

### Winners by category

| Category | Winner | Why (maintenance / accuracy / speed / reliability) | Best alternative |
| --- | --- | --- | --- |
| Transcript extraction | **youtube-transcript-api** | Purpose-built; returns clean timed segments; handles auto-generated captions and translation; no API key, no headless browser; maintained (v1.2.4, Jan 2026). Faster and simpler than yt-dlp when you only want the text. | yt-dlp (`--write-auto-subs`) |
| Comment extraction | **yt-dlp** (`--write-comments` / `getcomments`) | No key, no quota; extracts comments **and replies** with sort/limit controls; fixed within days when YouTube changes. Beats the dedicated scrapers on maintenance. | Official **YouTube Data API v3** when authoritative counts/compliance matter |
| Channel metadata | **yt-dlp** (`--dump-single-json`, `--flat-playlist`) | Richest structured metadata without a key; actively maintained; accurate. | scrapetube for fast bulk video-ID enumeration on huge channels; Data API for authoritative subscriber stats |
| Playlist metadata | **yt-dlp** (`--flat-playlist --dump-json`) | Enumerates all entries with full metadata; handles very large playlists; maintained. | scrapetube (faster, thinner data) |
| Thumbnail downloading | **yt-dlp** (`--write-thumbnail`, `--list-thumbnails`) | Resolves the *best available* resolution/format per video and adapts when YouTube changes formats. | Direct URL (`https://i.ytimg.com/vi/<id>/maxresdefault.jpg`) — zero-dependency fast path, but maxres isn't always present |
| Subtitle downloading | **yt-dlp** (`--write-subs --write-auto-subs --sub-langs --convert-subs srt`) | Downloads real subtitle files (vtt/srt) incl. auto-captions across many languages; maintained. | youtube-transcript-api when you need text, not files |

### Libraries considered (maintenance status, 2026-07)

| Library | Maintained? | Notes |
| --- | --- | --- |
| **yt-dlp** | ✅ Daily (latest `2026.07.04`) | 1800+ sites; the reference tool. Scraping-based (breaks are possible but fixed fast). |
| **youtube-transcript-api** (jdepoix) | ✅ Active (v1.2.4, Jan 2026) | Transcripts only. No key, no browser. Python 3.8–3.14. |
| **scrapetube** (dermasmid) | ✅ Active (v2.6.0) | Channel/playlist/search enumeration, no key, no Selenium. Thin metadata. |
| **pytubefix** (JuanBindez) | ✅ Active (v10.x) | Maintained fork of pytube; dependency-free; streams/captions. Narrower than yt-dlp. |
| youtube-comment-downloader (egbertbouman) | ⚠️ Maintenance concerns | Fork `yt-comment-dl` exists; superseded by yt-dlp for our purposes. |
| pytube | ❌ Unmaintained | Breaks on YouTube changes; do not use. Use pytubefix if a pytube-style API is needed. |
| YouTube Data API v3 (google-api-python-client) | ✅ Official (Google) | Most authoritative/stable API, but needs an API key and has daily **quota**; large comment threads/channels can exhaust it. |

### The core tradeoff: scraping vs. official API

- **yt-dlp / transcript-api / scrapetube** read YouTube's public/internal endpoints — **no
  key, no quota**, but *we* carry the risk when YouTube changes (mitigated by yt-dlp's
  exceptional fix velocity).
- **YouTube Data API v3** is authoritative and contractually stable, but adds **key
  management + quota** and can't cheaply retrieve everything (e.g. all comments on a huge
  thread). For a local-first system, the scraping path wins on operational simplicity;
  keep the Data API as the escape hatch when accuracy/compliance is non-negotiable.

## Confidence

**High** that yt-dlp + youtube-transcript-api are the right backbone: both are the most
actively maintained, key-free, and accurate options, and standardizing minimizes
dependencies. **Medium** on comment extraction specifically — comments are the most
frequently-broken YouTube surface for every tool; if we hit reliability limits, the Data
API is the fallback. This report is a 2026-07-10 snapshot; library health should be
re-checked before adoption.

## Sources

- yt-dlp releases (latest 2026.07.04): <https://github.com/yt-dlp/yt-dlp/releases> (accessed 2026-07-10)
- youtube-transcript-api — PyPI: <https://pypi.org/project/youtube-transcript-api/> and GitHub: <https://github.com/jdepoix/youtube-transcript-api> (accessed 2026-07-10)
- scrapetube — GitHub: <https://github.com/dermasmid/scrapetube>, PyPI: <https://pypi.org/project/scrapetube/> (accessed 2026-07-10)
- pytubefix — GitHub: <https://github.com/JuanBindez/pytubefix> (accessed 2026-07-10)
- youtube-comment-downloader — GitHub: <https://github.com/egbertbouman/youtube-comment-downloader>; fork `yt-comment-dl`: <https://pypi.org/project/yt-comment-dl/> (accessed 2026-07-10)
- pytube (unmaintained reference) — GitHub: <https://github.com/pytube/pytube> (accessed 2026-07-10)
- YouTube Data API v3 — quota/limits context: <https://tubealfred.com/blog/youtube-data-api-alternatives/> (accessed 2026-07-10)

## Open Questions

- **Concentration risk:** relying on yt-dlp for 5 of 6 categories is a single point of
  failure. Mitigation: pin the yt-dlp version, update deliberately, and keep the Data API
  path documented as a fallback. Is that mitigation sufficient, or do we want a second
  independent path for the most critical data?
- Do we need authoritative statistics (exact subscriber/like counts) anywhere? If yes,
  the Data API is required there regardless of the above.
- Rate-limiting / IP-block behavior at our expected volume is untested. May require
  backoff, cookies, or proxies — not yet assessed.
- Legal/ToS posture of scraping vs. API for our use case — out of scope here, worth a
  deliberate check before shipping.

## Next Actions

- Do **not** install yet. When the YouTube tool is built, adopt `yt-dlp` +
  `youtube-transcript-api` via `uv add`, and record the adoption as a decision in
  `docs/decisions/` (this report is the required evaluation).
- Prototype comment extraction with `yt-dlp` against a large thread to confirm
  completeness and speed before committing to it over the Data API.
- Pin yt-dlp and define an update/verification cadence, given the concentration risk.
