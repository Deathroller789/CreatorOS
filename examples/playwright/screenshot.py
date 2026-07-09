"""Minimal Playwright example: capture a screenshot of a page.

Run with:
    uv run python examples/playwright/screenshot.py https://example.com out.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def capture(url: str, out_path: Path) -> None:
    """Open ``url`` in headless Chromium and save a full-page screenshot."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("screenshot.png")
    capture(url, out_path)
    print(f"Saved screenshot of {url} to {out_path.resolve()}")


if __name__ == "__main__":
    main()
