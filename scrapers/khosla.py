"""
Khosla Ventures Company Scraper.
Intercepts 'api.getro.com' responses and clicks the "Load more" button to collect all companies.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from config.config import KhoslaConfig
from core.base_scraper import BaseScraper
from transformers.datatransform import CompanyModel

logger = logging.getLogger(__name__)


class KhoslaScraper(BaseScraper):
    """
    Scraper for Khosla Ventures portfolio companies.
    """

    def __init__(self, cfg: Optional[KhoslaConfig] = None):
        super().__init__(cfg or KhoslaConfig())

    async def scrape(self, save_raw: bool = True) -> List[CompanyModel]:
        """
        Navigates to the Khosla companies page, intercepts API responses,
        and clicks 'Load more' until all companies are loaded.
        """
        url = self.cfg.companies_page_url
        logger.info(f"Starting Khosla Ventures scrape: {url}")

        raw_responses: List[Dict[str, Any]] = []
        intercepted_companies: List[Dict[str, Any]] = []
        has_more_data = True

        async with self.browser_manager as bm:
            page = await bm.new_page()

            async def handle_response(response):
                nonlocal has_more_data
                if self.cfg.target_api_pattern in response.url:
                    try:
                        data = await response.json()
                        raw_responses.append({"url": response.url, "data": data})
                        
                        # The payload structure is typically {"results": {"companies": [...]}}
                        # based on the dummyresponse.json structure provided by the user.
                        if isinstance(data, dict):
                            if "results" in data and "companies" in data["results"]:
                                comps = data["results"]["companies"]
                                if len(comps) == 0:
                                    has_more_data = False
                                    logger.info("Received empty companies array. End of data reached.")
                                intercepted_companies.extend(comps)
                                logger.info(f"Intercepted {len(comps)} companies (Total so far: {len(intercepted_companies)})")
                            elif "companies" in data:
                                comps = data["companies"]
                                if len(comps) == 0:
                                    has_more_data = False
                                    logger.info("Received empty companies array. End of data reached.")
                                intercepted_companies.extend(comps)
                                logger.info(f"Intercepted {len(comps)} companies (Total so far: {len(intercepted_companies)})")
                            elif "data" in data and "companies" in data["data"]:
                                comps = data["data"]["companies"]
                                if len(comps) == 0:
                                    has_more_data = False
                                    logger.info("Received empty companies array. End of data reached.")
                                intercepted_companies.extend(comps)
                                logger.info(f"Intercepted {len(comps)} companies (Total so far: {len(intercepted_companies)})")
                    except Exception as err:
                        logger.debug(f"JSON decode error for {response.url}: {err}")

            page.on("response", handle_response)
            
            logger.info("Navigating to page and waiting for network idle...")
            await page.goto(url, wait_until="networkidle", timeout=self.cfg.page_load_timeout_ms)
            
            logger.info("Clicking 'Load More' button until exhausted...")
            clicks = await bm.click_load_more_and_scroll(
                page, 
                button_selector='button[data-testid="load-more"]',
                get_current_count=lambda: len(intercepted_companies),
                click_delay=2.0,
                api_pattern=self.cfg.target_api_pattern,
                max_scrolls=100,
                continue_condition=lambda: has_more_data
            )
            logger.info(f"Finished pagination after {clicks} clicks.")
            
            await asyncio.sleep(1.5)

        if save_raw and raw_responses:
            self._save_raw_data(raw_responses)

        # Transform using the generic data transformer
        companies = self.transformer.transform_batch(intercepted_companies)
        logger.info(f"Transformed {len(companies)} unique companies.")
        return companies

    def _save_raw_data(self, raw_data: List[Dict[str, Any]]):
        """Saves raw intercepted responses into data/raw/."""
        self.cfg.raw_output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg.raw_output_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Raw API responses saved to {self.cfg.raw_output_file}")
