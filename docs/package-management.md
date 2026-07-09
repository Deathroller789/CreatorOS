# Package Management

CreatorOS uses **[uv](https://docs.astral.sh/uv/)** as its default Python package manager and project/environment manager. Do not use bare `pip`, `venv`, `poetry`, or `pipenv` for this repo — use `uv` so the environment stays reproducible from `uv.lock`.

## Prerequisites

- Python 3.13+ (the interpreter is pinned in `.python-version`).
- uv installed. Install with:
  ```powershell
  irm https://astral.sh/uv/install.ps1 | iex
  ```

## Common commands

| Task | Command |
| --- | --- |
| Install/sync the environment from the lockfile | `uv sync` |
| Add a dependency | `uv add <package>` |
| Add a dev-only dependency | `uv add --dev <package>` |
| Remove a dependency | `uv remove <package>` |
| Run a command in the project env | `uv run <cmd>` (e.g. `uv run python scripts/foo.py`) |
| Update the lockfile | `uv lock` |
| Upgrade a package | `uv lock --upgrade-package <package>` |

## Notes

- `pyproject.toml` holds project metadata and dependencies; `uv` manages it — prefer `uv add`/`uv remove` over hand-editing the `dependencies` list.
- `uv.lock` **is committed** to the repo for reproducible installs. Don't add it to `.gitignore`.
- The virtual environment lives in `.venv/` (git-ignored) and is created/managed automatically by `uv`.
