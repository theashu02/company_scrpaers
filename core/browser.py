"""
Browser & Network Automation Manager.
Handles Playwright browser lifecycle, stealth configuration, and dynamic scrolling.
"""

import asyncio
import logging
from typing import Callable, Optional
from config.config import ScraperConfig, config

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages Playwright browser lifecycle, context, and page interactions.
    Provides async context management and helper functions for scraping.
    """

    def __init__(self, cfg: Optional[ScraperConfig] = None):
        self.cfg = cfg or config
        self._playwright = None
        self._browser = None
        self._context = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Launches the Playwright browser with configured arguments."""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.cfg.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--start-maximized"
                ]
            )
            viewport_config = None if not self.cfg.headless else {"width": 1920, "height": 1080}
            self._context = await self._browser.new_context(
                user_agent=self.cfg.user_agent,
                viewport=viewport_config,
                no_viewport=True if not self.cfg.headless else False,
            )
            logger.info(f"Browser launched successfully (headless={self.cfg.headless}).")
        except ImportError:
            logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
            raise

    async def new_page(self):
        """Creates and returns a new configured page instance."""
        if not self._context:
            await self.start()
        page = await self._context.new_page()
        page.set_default_timeout(self.cfg.timeout_ms)
        page.set_default_navigation_timeout(self.cfg.page_load_timeout_ms)
        return page

    async def scroll_till_end(
        self,
        page,
        get_current_count: Optional[Callable[[], int]] = None,
        max_scrolls: int = 35,
        scroll_delay: float = 1.3
    ) -> int:
        """
        Continuously scrolls down until all items have been fetched or bottom is reached.
        Uses back-and-forth micro-scrolling to trigger lazy intersection observers.
        """
        last_count = get_current_count() if get_current_count else 0
        no_change_iterations = 0
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Scroll to the bottom
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(scroll_delay)
            scroll_count += 1

            current_count = get_current_count() if get_current_count else scroll_count

            if current_count == last_count and scroll_count > 2:
                # Trigger intersection observer by slight upward scroll
                await page.evaluate("() => window.scrollBy(0, -400)")
                await asyncio.sleep(0.4)
                await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(scroll_delay)

                current_count = get_current_count() if get_current_count else scroll_count
                if current_count == last_count:
                    no_change_iterations += 1
                    if no_change_iterations >= 2:
                        logger.debug(f"Finished scrolling after {scroll_count} iterations.")
                        break
                else:
                    no_change_iterations = 0
            else:
                no_change_iterations = 0

            last_count = current_count

        return scroll_count

    async def close(self):
        """Closes open pages, context, and browser instances."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser session closed.")


class HTTPClient:
    """
    Lightweight resilient HTTP client using requests for direct API queries.
    """

    def __init__(self, cfg: Optional[ScraperConfig] = None):
        self.cfg = cfg or config

    def fetch_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Synchronously fetches JSON data with retry mechanism."""
        import requests
        headers = self.cfg.custom_headers.copy()
        headers["User-Agent"] = self.cfg.user_agent

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.cfg.timeout_ms / 1000)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.cfg.max_retries} failed for {url}: {e}")
                if attempt == self.cfg.max_retries:
                    raise
        return None

