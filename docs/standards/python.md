# Python Standard

Rules for Python code in CreatorOS. These are enforced, not suggested.

## Environment

- **uv** manages everything. Never call `pip`, `venv`, `poetry`, or `pipenv` directly.
  Add deps with `uv add`, run code with `uv run`. See
  [package-management](../package-management.md).
- **Python 3.13+** only (pinned in `.python-version`). Do not add code paths for older
  interpreters.
- Every dependency is committed to `uv.lock`. A new dependency requires an evaluation
  first (see [research](research.md) and `docs/decisions/`).

## Style & formatting

- **Ruff is the authority** for both linting and formatting. Code must pass
  `uv run ruff check .` and `uv run ruff format --check .` before it is committed. Do not
  hand-format around Ruff.
- Line length 88. Double quotes. Spaces, not tabs.
- Imports are sorted by Ruff (isort rules). No unused imports.

## Code rules

- **Type hints are required** on every function signature (arguments and return). Use
  modern syntax (`list[str]`, `X | None`), not `typing.List` / `Optional`.
- **Docstrings** on every public module, function, and class. One line minimum; say what
  it does, not how.
- Use `pathlib.Path`, never `os.path` string juggling.
- **No bare `except:`**. Catch specific exceptions. Never silence an error without a
  comment explaining why.
- No mutable default arguments. No wildcard imports. No dead code.
- Prefer the standard library. Reach for a dependency only when it clearly wins on
  maintenance, correctness, or speed — and only after it is evaluated.
- Functions do one thing. If you need "and" to describe it, split it.
- Secrets come from the environment, never literals. Nothing secret is committed.

## Layout

- Reusable tool code lives under `tools/<tool>/`. Runnable demos live under
  `examples/<tool>/`, never in `scripts/`. One-off operational scripts live in
  `scripts/`. See [folders](folders.md).

## Testing

- Tests live in `tests/`, named `test_*.py`. Run them with:
  ```bash
  uv run python -m unittest discover -s tests
  ```
- Use the **standard-library `unittest`** for the MVP — no test-framework dependency
  until one is justified by a written evaluation. Mock network/external calls
  (`unittest.mock`); tests must not hit the network.
- Every feature ships with tests (Definition of Done). Aim for a small number of
  high-value tests over exhaustive coverage.
