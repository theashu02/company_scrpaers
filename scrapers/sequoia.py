"""
Sequoia Capital Company & Jobs Scraper.
Iterates over parameterized industry URLs, intercepts 'api-boards/search-companies' responses,
scrolls to the end of each page, and aggregates + enriches all company records with social links and URLs.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from config.config import ScraperConfig, config, ALL_INDUSTRIES
from core.browser import BrowserManager
from transformers.datatransform import DataTransformer, CompanyModel

logger = logging.getLogger(__name__)


class SequoiaScraper:
    """
    Main scraper engine for Sequoia Capital portfolio companies.
    Iterates through parameterized industry URLs, intercepts 'search-companies' API payloads,
    and enriches company records with verified website, career, and social profile links.
    """

    def __init__(self, cfg: Optional[ScraperConfig] = None):
        self.cfg = cfg or config
        self.browser_manager = BrowserManager(self.cfg)
        self.transformer = DataTransformer(self.cfg)

    def build_industry_url(self, industry: str) -> str:
        """Constructs parameterized URL for a single industry."""
        query = urlencode({"industries": industry})
        return f"{self.cfg.companies_page_url}?{query}"

    def build_combined_industries_url(self, industries: Optional[List[str]] = None) -> str:
        """Constructs a single URL containing all provided industries as query parameters."""
        ind_list = industries or self.cfg.industries
        query = urlencode([("industries", ind) for ind in ind_list])
        return f"{self.cfg.companies_page_url}?{query}"

    async def enrich_company_socials(self, company: CompanyModel, session: Optional[requests.Session] = None, semaphore: Optional[asyncio.Semaphore] = None):
        """
        Scrapes https://www.sequoiacap.com/companies/{slug}/ to collect official
        LinkedIn, Twitter/X, GitHub, Instagram, Facebook, and YouTube links.
        """
        if not company.slug:
            return

        url = f"https://www.sequoiacap.com/companies/{company.slug}/"
        headers = {
            "User-Agent": self.cfg.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        async def _fetch():
            loop = asyncio.get_event_loop()
            try:
                def _do_get():
                    s = session or requests
                    return s.get(url, headers=headers, timeout=6)
                
                resp = await loop.run_in_executor(None, _do_get)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if "linkedin.com/company" in href or "linkedin.com/in" in href:
                            if not company.linkedin_url:
                                company.linkedin_url = href
                        elif "twitter.com" in href or "x.com" in href:
                            if not company.twitter_url and "twitter.com/sequoia" not in href:
                                company.twitter_url = href
                        elif "github.com" in href:
                            if not company.github_url and "github.com/sequoia" not in href:
                                company.github_url = href
                        elif "facebook.com" in href:
                            if not company.facebook_url and "facebook.com/sequoia" not in href:
                                company.facebook_url = href
                        elif "instagram.com" in href:
                            if not company.instagram_url and "instagram.com/sequoia" not in href:
                                company.instagram_url = href
                        elif "youtube.com" in href:
                            if not company.youtube_url and "youtube.com/sequoia" not in href:
                                company.youtube_url = href
                        elif a.get("target") == "_blank" and not company.website_url:
                            if not any(k in href for k in ["sequoiacap", "schf.com", "partnerlogin"]):
                                company.website_url = href
            except Exception as e:
                logger.debug(f"Could not enrich social links for {company.name} ({url}): {e}")

        if semaphore:
            async with semaphore:
                await _fetch()
        else:
            await _fetch()

    async def enrich_all_companies(self, companies: List[CompanyModel], concurrency: int = 15):
        """
        Concurrently enriches all companies with social and website links.
        """
        logger.info(f"Enriching {len(companies)} companies with social links and official URLs...")
        semaphore = asyncio.Semaphore(concurrency)
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=concurrency + 5, pool_maxsize=concurrency + 5)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        tasks = [self.enrich_company_socials(c, session=session, semaphore=semaphore) for c in companies]
        await asyncio.gather(*tasks)
        session.close()
        logger.info("Social link enrichment completed.")

    async def scrape_industry(
        self, 
        page, 
        industry: str, 
        raw_responses: List[Dict[str, Any]],
        index: int = 1,
        total: int = 1
    ) -> List[CompanyModel]:
        """
        Navigates to a single parameterized industry URL, intercepts API responses,
        and scrolls to the bottom of the page.
        """
        url = self.build_industry_url(industry)
        logger.info(f"[{index}/{total}] Navigating to: {url}")
        
        industry_companies: List[Dict[str, Any]] = []

        async def handle_response(response):
            if self.cfg.target_api_pattern in response.url:
                try:
                    data = await response.json()
                    raw_responses.append({
                        "industry": industry,
                        "url": response.url,
                        "data": data
                    })
                    if isinstance(data, dict) and "companies" in data:
                        comps = data["companies"]
                        industry_companies.extend(comps)
                        logger.info(f"-> Intercepted {len(comps)} companies (Industry '{industry}' Total: {len(industry_companies)})")
                except Exception as err:
                    logger.debug(f"Could not parse JSON response from {response.url}: {err}")

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=self.cfg.page_load_timeout_ms)
            
            # Scroll until end of page / all paginated data captured
            scrolls = await self.browser_manager.scroll_till_end(
                page,
                get_current_count=lambda: len(industry_companies),
                max_scrolls=self.cfg.scroll_max_attempts,
                scroll_delay=self.cfg.scroll_delay_seconds
            )
            await asyncio.sleep(1.0)
            logger.info(f"Completed '{industry}' in {scrolls} scroll steps. Unique companies found: {len({c.get('id') for c in industry_companies if isinstance(c, dict)})}")
        except Exception as e:
            logger.error(f"Error scraping industry '{industry}': {e}")
        finally:
            page.remove_listener("response", handle_response)

        # Fallback to DOM parsing if no API responses arrived
        if not industry_companies:
            logger.info(f"No API response intercepted for '{industry}'. Checking DOM fallback...")
            try:
                content = await page.content()
                dom_items = self._parse_dom(content)
                industry_companies.extend(dom_items)
            except Exception as e:
                logger.debug(f"DOM fallback error: {e}")

        return self.transformer.transform_batch(industry_companies, industry_tag=industry)

    async def scrape_all_industries(
        self, 
        industries: Optional[List[str]] = None,
        save_raw: bool = True,
        enrich_socials: bool = True
    ) -> List[CompanyModel]:
        """
        Iterates sequentially through each parameterized industry URL, intercepts API responses,
        scrolls to the end of each page, deduplicates companies, and enriches all links.
        """
        target_industries = industries or self.cfg.industries
        total_targets = len(target_industries)
        logger.info(f"Starting sequential scrape across {total_targets} industries...")

        raw_responses: List[Dict[str, Any]] = []
        all_company_models: List[List[CompanyModel]] = []

        async with self.browser_manager as bm:
            page = await bm.new_page()

            for idx, ind in enumerate(target_industries, start=1):
                models = await self.scrape_industry(
                    page=page,
                    industry=ind,
                    raw_responses=raw_responses,
                    index=idx,
                    total=total_targets
                )
                all_company_models.append(models)
                await asyncio.sleep(self.cfg.request_delay_seconds)

        # Save all captured raw API payloads
        if save_raw and raw_responses:
            self._save_raw_data(raw_responses)

        # Merge and deduplicate all collected companies across all industries
        merged = self.transformer.merge_datasets(all_company_models)

        # Enrich all companies with social profiles and URLs
        if enrich_socials:
            await self.enrich_all_companies(merged)

        logger.info(f"Finished scraping! Total unique companies collected: {len(merged)}")
        return merged

    async def scrape_combined_url(
        self, 
        industries: Optional[List[str]] = None, 
        save_raw: bool = True,
        enrich_socials: bool = True
    ) -> List[CompanyModel]:
        """
        Alternative method: Hits a single combined URL with all industry parameters.
        """
        url = self.build_combined_industries_url(industries)
        logger.info(f"Scraping combined multi-parameter URL: {url}")
        
        raw_responses: List[Dict[str, Any]] = []
        intercepted_companies: List[Dict[str, Any]] = []

        async with self.browser_manager as bm:
            page = await bm.new_page()

            async def handle_response(response):
                if self.cfg.target_api_pattern in response.url:
                    try:
                        data = await response.json()
                        raw_responses.append({"url": response.url, "data": data})
                        if isinstance(data, dict) and "companies" in data:
                            comps = data["companies"]
                            intercepted_companies.extend(comps)
                            logger.info(f"Intercepted {len(comps)} companies (Total so far: {len(intercepted_companies)})")
                    except Exception as err:
                        logger.debug(f"JSON decode error: {err}")

            page.on("response", handle_response)
            await page.goto(url, wait_until="networkidle", timeout=self.cfg.page_load_timeout_ms)
            await bm.scroll_till_end(
                page, 
                get_current_count=lambda: len(intercepted_companies),
                scroll_delay=self.cfg.scroll_delay_seconds
            )
            await asyncio.sleep(1.5)

        if save_raw and raw_responses:
            self._save_raw_data(raw_responses)

        companies = self.transformer.transform_batch(intercepted_companies)
        if enrich_socials:
            await self.enrich_all_companies(companies)

        return companies

    def scrape_from_local_raw(self, filepath: Union[str, Path], enrich_socials: bool = True) -> List[CompanyModel]:
        """
        Loads and parses local raw JSON file(s) (e.g. dummy.json / cached dump).
        Handles single JSON objects as well as concatenated multi-JSON streams.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Raw data file not found: {path}")

        logger.info(f"Loading local raw data from {path}...")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        decoder = json.JSONDecoder()
        pos = 0
        all_companies: List[Dict[str, Any]] = []

        while pos < len(content):
            while pos < len(content) and content[pos].isspace():
                pos += 1
            if pos >= len(content):
                break
            try:
                obj, end_pos = decoder.raw_decode(content, idx=pos)
                pos = end_pos
                if isinstance(obj, dict):
                    if "companies" in obj:
                        all_companies.extend(obj["companies"])
                    elif "data" in obj and isinstance(obj["data"], dict) and "companies" in obj["data"]:
                        all_companies.extend(obj["data"]["companies"])
                    else:
                        all_companies.append(obj)
                elif isinstance(obj, list):
                    all_companies.extend(obj)
            except json.JSONDecodeError as e:
                logger.warning(f"Error decoding JSON segment at index {pos}: {e}")
                break

        companies = self.transformer.transform_batch(all_companies)
        if enrich_socials:
            asyncio.run(self.enrich_all_companies(companies))
        return companies

    def _parse_dom(self, html_content: str) -> List[Dict[str, Any]]:
        """Parses HTML content as fallback when network JSON is not present."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed. Skipping DOM parsing.")
            return []
        
        soup = BeautifulSoup(html_content, "html.parser")
        companies = []

        cards = soup.select(".company-card, [data-company], article, .portfolio-item, .item-card")
        for card in cards:
            name_elem = card.select_one("h2, h3, .company-name, [data-name]")
            name = name_elem.get_text(strip=True) if name_elem else "Unknown"
            
            link_elem = card.select_one("a[href]")
            link = link_elem["href"] if link_elem else ""
            
            desc_elem = card.select_one("p, .company-description, .bio")
            desc = desc_elem.get_text(strip=True) if desc_elem else ""
            
            img_elem = card.select_one("img[src]")
            logo = img_elem["src"] if img_elem else ""

            companies.append({
                "name": name,
                "id": name,
                "domain": link,
                "description": desc,
                "logo": logo
            })
        return companies

    def _save_raw_data(self, raw_data: List[Dict[str, Any]]):
        """Saves raw intercepted responses into data/raw/."""
        self.cfg.raw_output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg.raw_output_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Raw API responses saved to {self.cfg.raw_output_file}")
