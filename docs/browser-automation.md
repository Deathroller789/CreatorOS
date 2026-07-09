# Browser Automation (Playwright)

CreatorOS uses **[Playwright](https://playwright.dev/python/)** (Python) for browser automation and scraping. It's a project dependency, managed via `uv`.

## Setup

Playwright itself installs with `uv sync`. The browser binaries are a separate download:

```bash
uv run playwright install chromium
```

Add `firefox` and/or `webkit` to that command if you need other engines.

### Browser install location

On this machine, browser binaries are stored on the **D drive** via the persistent user environment variable:

```
PLAYWRIGHT_BROWSERS_PATH=D:\Tools\playwright
```

Anyone cloning the repo elsewhere can omit this to use Playwright's default (`%LOCALAPPDATA%\ms-playwright` on Windows).

## Usage

A runnable example lives at [`examples/playwright/screenshot.py`](../examples/playwright/screenshot.py):

```bash
uv run python examples/playwright/screenshot.py https://example.com out.png
```

Minimal in-code usage:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()          # add headless=False to watch it
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

An async API (`playwright.async_api`) is also available for `asyncio` workflows.

## Notes

- After upgrading the `playwright` package, re-run `uv run playwright install` so the browser build matches the library version.
- Browser binaries are large and machine-specific — they are **not** committed to the repo.
