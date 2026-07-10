# Folder Standard

The canonical map of CreatorOS. Every file has one obvious home. If you are unsure where
something goes, this document decides — and if it can't, update this document.

## Top-level layout

| Path | Holds | Rules |
| --- | --- | --- |
| `docs/` | Human-facing documentation | Prose about the system, not code. |
| `docs/standards/` | Binding rules (this file, `python.md`, …) | Rules, never tutorials. |
| `docs/decisions/` | Architecture Decision Records (ADRs) | One ADR per important decision; `adr-NNN-*.md`. |
| `docs/modules/` | Per-module design documents | One file per module: `NNN-<module>.md`. Design, not code. |
| `research/` | Research reports | Categorized into subfolders (below). Must follow [research](research.md). |
| `research/technology/` | Technology, library & stack evaluations | One file per subject considered. |
| `research/market/` | Market research | |
| `research/competitors/` | Competitor research | |
| `research/experiments/` | Experiment write-ups | |
| `research/reports/` | General / one-off reports | |
| `tools/` | Reusable capability code | One subfolder per tool: `tools/<tool>/`. |
| `examples/` | Runnable demos | One subfolder per tool: `examples/<tool>/`. Demos live here, **not** in `scripts/`. |
| `scripts/` | One-off operational scripts | Not libraries, not demos. |
| `prompts/` | Reusable prompts | Versioned as files, named by purpose. |
| `database/` | SQLite database & schema | Source of truth for state (see `docs/decisions/`). |

## Root files

- `README.md` — entry point (when written).
- `PROJECT_VISION.md` — mission, philosophy, and how decisions are made.
- `CLAUDE.md` — assistant working notes. Owned by the human; leave it unless asked.
- `pyproject.toml`, `uv.lock`, `.python-version` — the Python project (uv).
- `.mcp.json` — project MCP servers.

## Rules

- **Code vs. docs never mix.** Explanations go in `docs/`; runnable things go in
  `tools/`, `examples/`, or `scripts/`.
- **One tool, one folder.** A tool named `youtube` owns `tools/youtube/` and, if it has
  demos, `examples/youtube/`. Its research lives in `research/`.
- **A research report never lives next to the code it's about.** Reports go in
  `research/`; the resulting decision goes in `docs/decisions/`.
- **Empty folders keep a `.gitkeep`** until they hold real files, then it's removed.
- Machine-specific data (browser binaries, caches) stays outside the repo. See
  [naming](naming.md) and `.gitignore`.
