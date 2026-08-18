"""
Browser & Network Automation Manager.
Handles Playwright browser lifecycle, stealth configuration, and dynamic scrolling.
"""

import asyncio
import logging
from typing import Callable, Optional
from config.core_config import BrowserConfig
from config.config import config

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages Playwright browser lifecycle, context, and page interactions.
    Provides async context management and helper functions for scraping.
    """

    def __init__(self, cfg: Optional[BrowserConfig] = None):
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
        scroll_delay: float = 1.3,
        api_pattern: Optional[str] = None,
        slow_scroll: bool = False,
        continue_condition: Optional[Callable[[], bool]] = None
    ) -> int:
        """
        Continuously scrolls down until all items have been fetched or bottom is reached.
        Uses back-and-forth micro-scrolling to trigger lazy intersection observers.
        """
        last_count = get_current_count() if get_current_count else 0
        no_change_iterations = 0
        scroll_count = 0

        while scroll_count < max_scrolls:
            if continue_condition is not None and not continue_condition():
                logger.debug("Continue condition evaluated to False. Stopping scroll.")
                break
                
            # Scroll to the bottom or slowly
            scroll_script = "() => window.scrollBy(0, window.innerHeight)" if slow_scroll else "() => window.scrollTo(0, document.body.scrollHeight)"
            
            if api_pattern:
                try:
                    async with page.expect_response(lambda r: api_pattern in r.url and r.status == 200, timeout=10000):
                        await page.evaluate(scroll_script)
                except Exception as e:
                    logger.debug(f"Timeout waiting for response matching '{api_pattern}' during scroll.")
                    # If it times out, we still executed the scroll but no API fired, which might be fine if we reached the end
            else:
                await page.evaluate(scroll_script)
                
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

    async def click_load_more_and_scroll(
        self,
        page,
        button_selector: str,
        get_current_count: Optional[Callable[[], int]] = None,
        max_clicks: int = 50,
        click_delay: float = 2.0,
        api_pattern: Optional[str] = None,
        max_scrolls: int = 10,
        continue_condition: Optional[Callable[[], bool]] = None
    ) -> int:
        """
        Continuously clicks a 'Load More' button until it disappears, becomes disabled,
        or max_clicks is reached.
        """
        click_count = 0
        while click_count < max_clicks:
            try:
                # Wait a tiny bit for the button to be visible/enabled
                button = await page.wait_for_selector(button_selector, state="visible", timeout=5000)
                if not button:
                    break
                    
                is_disabled = await button.get_attribute("disabled")
                if is_disabled is not None:
                    break
                    
                # The Khosla button has data-loading="false", maybe we should wait if it's true
                # For safety, let's just click it
                await button.scroll_into_view_if_needed()
                
                if api_pattern:
                    try:
                        async with page.expect_response(lambda r: api_pattern in r.url and r.status == 200, timeout=15000):
                            await button.click()
                    except Exception as e:
                        logger.warning(f"Timeout waiting for response matching '{api_pattern}': {e}")
                else:
                    await button.click()
                    
                click_count += 1
                logger.info(f"Clicked 'Load More' button (Click #{click_count})")
                await asyncio.sleep(click_delay)
                
            except Exception as e:
                logger.info(f"Finished clicking 'Load More'. Button not found or clickable: {e}")
                break
                
        # After clicking load more, we do a scroll till end to make sure all images/lazy-loading finishes
        await self.scroll_till_end(
            page, 
            get_current_count, 
            max_scrolls=max_scrolls, 
            scroll_delay=1.0, 
            api_pattern=api_pattern,
            slow_scroll=True,
            continue_condition=continue_condition
        )
        
        return click_count

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

    def __init__(self, cfg: Optional[BrowserConfig] = None):
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

