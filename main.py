"""
Main CLI Entrypoint for Sequoia Company Scraper & Social Links Enricher.
Extracts company metadata, career URLs, ATS boards, and social media profiles across all industries.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from config.config import config, BASE_DIR, ALL_INDUSTRIES
from scrapers.sequoia import SequoiaScraper
from transformers.datatransform import DataTransformer


def setup_logging(level: str = "INFO"):
    """Configures structured console logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_live_scraper(
    industries: Optional[List[str]] = None, 
    combined: bool = False,
    limit: Optional[int] = None,
    enrich: bool = True
):
    """Executes live web scraping with Playwright across target industries."""
    target_industries = industries or list(ALL_INDUSTRIES)
    if limit and limit > 0:
        target_industries = target_industries[:limit]

    scraper = SequoiaScraper(config)
    
    if combined:
        companies = await scraper.scrape_combined_url(target_industries, save_raw=True, enrich_socials=enrich)
    else:
        companies = await scraper.scrape_all_industries(target_industries, save_raw=True, enrich_socials=enrich)
    
    # Save transformed data to JSON & CSV
    scraper.transformer.save_json(companies)
    scraper.transformer.save_csv(companies)
    logging.info(f"Pipeline completed! Saved {len(companies)} unique companies with full links to JSON and CSV.")


def run_local_processor(file_path: str, enrich: bool = True):
    """Processes an existing local raw JSON file (e.g. dummy.json)."""
    target = Path(file_path)
    if not target.is_absolute():
        target = BASE_DIR / file_path

    scraper = SequoiaScraper(config)
    companies = scraper.scrape_from_local_raw(target, enrich_socials=enrich)
    
    scraper.transformer.save_json(companies)
    scraper.transformer.save_csv(companies)
    logging.info(f"Successfully transformed {len(companies)} companies with full links from {target}.")


def main():
    parser = argparse.ArgumentParser(
        description="Sequoia Company Scraper, Link & Social Media Extractor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        help="Comma-separated list of industries to scrape (e.g. 'SaaS,Fintech,AI'). Default: all 77 industries."
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        default=False,
        help="Hit a single combined URL containing all industry query params instead of one-by-one."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit scraping to the first N industries."
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
        help="Skip social links enrichment from Sequoia company portfolio profiles."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level."
    )

    args = parser.parse_args()
    setup_logging(args.log_level)
    config.headless = args.headless
    enrich = not args.no_enrich

    if args.mode == "live":
        selected_industries = None
        if args.industries:
            selected_industries = [ind.strip() for ind in args.industries.split(",") if ind.strip()]
        
        asyncio.run(run_live_scraper(
            industries=selected_industries,
            combined=args.combined,
            limit=args.limit,
            enrich=enrich
        ))
    else:
        run_local_processor(args.file, enrich=enrich)


if __name__ == "__main__":
    main()
