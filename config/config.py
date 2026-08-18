"""
Configuration module for the Sequoia Company Scraper.
Centralizes endpoints, industries list, timeouts, stealth headers, and storage paths.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os


# Base Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure runtime directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Complete list of Sequoia industry filters
ALL_INDUSTRIES: List[str] = [
    "SaaS",
    "Fintech",
    "Enterprise Software",
    "Productivity",
    "AI",
    "Computer & Network Security",
    "Consumer",
    "ECommerce",
    "Developer Tools",
    "Financial Services",
    "Analytics",
    "Hospital & Health Care",
    "Consumer Services",
    "Blockchain",
    "Social Networking",
    "AI-Powered Applications",
    "Biotech/Pharma",
    "Transportation",
    "Hardware",
    "HR and Recruiting",
    "AI/ML",
    "Crypto",
    "Data & Analytics",
    "Health, Wellness and Fitness",
    "Infrastructure",
    "Marketing and Advertising",
    "Real Estate",
    "Security",
    "Cloud Services",
    "Video Games",
    "Telecommunications",
    "Renewables & Environment",
    "Manufacturing",
    "Legal Services",
    "Logistics and Supply Chain",
    "Delivery Services",
    "Virtual Reality",
    "Restaurants",
    "Healthcare",
    "SaaS Business App",
    "Sports",
    "IoT",
    "Higher Education",
    "Web3",
    "Wireless",
    "FinTech & Blockchain",
    "Payments",
    "NFT",
    "Retail",
    "Food & Beverages",
    "Agile Workplace",
    "Automation & Robotics",
    "IT and Services",
    "Apparel & Fashion",
    "Cybersecurity",
    "Insurance",
    "Banking",
    "Entertainment",
    "DeFi",
    "Investment Management",
    "Computer Networking",
    "Venture Capital & Private Equity",
    "Prediction Markets",
    "Environmental Services",
    "Online Media",
    "Sustainable Production and Consumption",
    "Marketplace",
    "Life Sciences",
    "Education Management",
    "Digital Health",
    "Defense & Space",
    "Cosmetics",
    "Consumer Electronics",
    "Autonomous Vehicles",
    "Aviation & Aerospace",
    "Business Services",
    "Capital Markets",
    "Computer Vision"
]


@dataclass
class ScraperConfig:
    """General configuration settings for scraper operations."""
    
    # Target URLs & Endpoints
    base_url: str = "https://jobs.sequoiacap.com"
    companies_page_url: str = "https://jobs.sequoiacap.com/companies"
    target_api_pattern: str = "api-boards/search-companies"
    
    # Industries to scrape
    industries: List[str] = field(default_factory=lambda: list(ALL_INDUSTRIES))
    
    # Browser & Request Settings
    headless: bool = False  # Set to False by default so user can see browser interactions if desired, or toggle via CLI
    timeout_ms: int = 40000
    page_load_timeout_ms: int = 60000
    scroll_delay_seconds: float = 1.2
    scroll_max_attempts: int = 50
    request_delay_seconds: float = 1.0
    max_retries: int = 3
    
    # User-Agent & Headers
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    custom_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    
    # Output file paths
    raw_output_file: Path = RAW_DATA_DIR / "search_companies_raw.json"
    processed_json_file: Path = PROCESSED_DATA_DIR / "sequoia_companies.json"
    processed_csv_file: Path = PROCESSED_DATA_DIR / "sequoia_companies.csv"
    
    # Logging
    log_level: str = "INFO"


# Default global instance
config = ScraperConfig()
