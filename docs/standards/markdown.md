# Markdown Standard

Rules for all Markdown in CreatorOS (docs, standards, research, decisions). Documentation
is a product; treat it like one.

## Structure

- **Exactly one H1 (`#`) per file**, as the first line — the document title.
- Use ATX headings (`##`, `###`). Never skip a level (no `##` → `####`).
- Heading text in sentence case: "Design principles", not "Design Principles".
- Start every document with a one- or two-line statement of what it is and who it's for.

## Writing

- Short sentences. Active voice. Say the conclusion first, then support it.
- Prefer lists and tables over long paragraphs. Comparisons **must** be tables.
- One sentence per line OR hard-wrap at ~100 chars — pick one and be consistent within a
  file. This keeps diffs readable.
- No filler ("basically", "simply", "just", "in order to"). Cut words that carry no
  information.

## Formatting

- Fenced code blocks always declare a language (```python, ```bash, ```toml).
- Inline-code (`` ` ``) for filenames, commands, identifiers, and values.
- Links are Markdown links with real targets; use **relative paths** for in-repo links
  (`../decisions/0001-memory-architecture.md`). No bare URLs in prose.
- Dates are ISO 8601 (`2026-07-10`).

## Hygiene

- No trailing whitespace. End files with a single newline.
- Don't commit commented-out sections or "TODO: write this later" as content — either
  write it or track it in Next Actions / an issue.
