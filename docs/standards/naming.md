# Naming Standard

Rules for naming things in CreatorOS. Consistent names make the system searchable and
predictable. When in doubt, favor clarity over brevity.

## General

- **Lowercase always** for files and directories, except the few deliberate all-caps
  root documents (`README.md`, `CLAUDE.md`, `PROJECT_VISION.md`, `ENGINEERING.md`).
- **No spaces** in any file or directory name, ever. Words are separated by `_` or `-`
  per the rules below.
- Names describe content, not format ("channel_metadata", not "data2").
- Dates in names use ISO 8601: `2026-07-10`.

## By type

| Thing | Convention | Example |
| --- | --- | --- |
| Python files & modules | `snake_case.py` | `transcript_extractor.py` |
| Python packages (dirs) | `snake_case` | `tools/youtube/` |
| Documentation files | `snake_case.md` | `technology/sqlite.md` |
| Decision records (ADRs) | `adr-NNN-kebab-title.md` | `adr-002-why-yt-dlp.md` |
| Module design docs | `NNN-kebab-title.md` | `001-youtube-intelligence.md` |
| Directories (general) | `snake_case` | `research/technology/` |
| Env variables | `UPPER_SNAKE_CASE` | `PLAYWRIGHT_BROWSERS_PATH` |
| SQLite tables/columns | `snake_case` | `channel_stats` |
| Branches | `kebab-case`, typed | `feat/youtube-transcripts` |

## Python identifiers

- `snake_case` for functions, methods, variables.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for module-level constants.
- Private helpers prefixed with a single underscore (`_build_url`).

## Rules

- One clear name per concept across the whole system. Do not call it `video_id` in one
  place and `vid` in another.
- No abbreviations unless they are universal (`id`, `url`, `api`). Never invent your own.
- No version numbers or "final"/"new"/"v2" in names. Git tracks versions.
