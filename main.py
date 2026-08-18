"""
Main CLI Entrypoint for Company Scrapers.
Extracts company metadata, career URLs, ATS boards, and social media profiles.
Supports multiple targets (Sequoia, Khosla).
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from config.config import SequoiaConfig, KhoslaConfig, BASE_DIR, ALL_INDUSTRIES
from scrapers.sequoia import SequoiaScraper
from scrapers.khosla import KhoslaScraper
from scrapers.accel import AccelScraper


def setup_logging(level: str = "INFO"):
    """Configures structured console logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_live_scraper(
    target: str = "sequoia",
    industries: Optional[List[str]] = None, 
    combined: bool = False,
    limit: Optional[int] = None,
    enrich: bool = True,
    headless: bool = False
):
    """Executes live web scraping with Playwright."""
    if target == "khosla":
        cfg = KhoslaConfig()
        cfg.headless = headless
        scraper = KhoslaScraper(cfg)
        companies = await scraper.scrape(save_raw=True)
    elif target == "accel":
        scraper = AccelScraper()
        companies = await scraper.scrape(save_raw=True)
    else:
        # Default to Sequoia
        cfg = SequoiaConfig()
        cfg.headless = headless
        target_industries = industries or list(ALL_INDUSTRIES)
        if limit and limit > 0:
            target_industries = target_industries[:limit]

        scraper = SequoiaScraper(cfg)
        
        if combined:
            companies = await scraper.scrape_combined_url(target_industries, save_raw=True, enrich_socials=enrich)
        else:
            companies = await scraper.scrape_all_industries(target_industries, save_raw=True, enrich_socials=enrich)
    
    # Save transformed data to JSON & CSV
    scraper.transformer.save_json(companies)
    scraper.transformer.save_csv(companies)
    logging.info(f"Pipeline completed! Saved {len(companies)} unique companies to JSON and CSV.")


def run_local_processor(target: str, file_path: str, enrich: bool = True):
    """Processes an existing local raw JSON file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / file_path

    if target == "khosla":
        # Khosla local processing is not fully implemented yet in KhoslaScraper
        # But we could reuse sequoia's scrape_from_local_raw logic if we moved it to BaseScraper.
        # For now, print error
        logging.error("Local processing not yet fully implemented for Khosla target.")
        return
    else:
        cfg = SequoiaConfig()
        scraper = SequoiaScraper(cfg)
        companies = scraper.scrape_from_local_raw(path, enrich_socials=enrich)
        
        scraper.transformer.save_json(companies)
        scraper.transformer.save_csv(companies)
        logging.info(f"Successfully transformed {len(companies)} companies from {path}.")


def main():
    parser = argparse.ArgumentParser(
        description="Company Scraper & Data Extractor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=["sequoia", "khosla", "accel"],
        default="sequoia",
        help="Target VC to scrape (default: sequoia)"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "transform"],
        default="live",
        help="Operation mode: 'live' for browser scraping, 'transform' for processing existing local raw JSON."
    )
    parser.add_argument(
        "--industries",
        type=str,
        default=None,
        help="Comma-separated list of industries to scrape (e.g. 'SaaS,Fintech,AI'). For Sequoia only."
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        default=False,
        help="Hit a single combined URL instead of one-by-one. For Sequoia only."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit scraping to the first N industries. For Sequoia only."
    )
    parser.add_argument(
        "--file",
        type=str,
        default="dummy.json",
        help="Path to raw JSON file when using mode='transform'."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (background)."
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Open visible browser window (default for dev inspection)."
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        default=False,
        help="Skip social links enrichment (if applicable to target)."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level."
    )

    args = parser.parse_args()
    setup_logging(args.log_level)
    enrich = not args.no_enrich

    if args.mode == "live":
        selected_industries = None
        if args.industries:
            selected_industries = [ind.strip() for ind in args.industries.split(",") if ind.strip()]
        
        asyncio.run(run_live_scraper(
            target=args.target,
            industries=selected_industries,
            combined=args.combined,
            limit=args.limit,
            enrich=enrich,
            headless=args.headless
        ))
    else:
        run_local_processor(args.target, args.file, enrich=enrich)


if __name__ == "__main__":
    main()
