"""
Configuration module for the Sequoia Company Scraper.
Centralizes endpoints, industries list, timeouts, stealth headers, and storage paths.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os

from config.core_config import BrowserConfig, RAW_DATA_DIR, PROCESSED_DATA_DIR, BASE_DIR

# Complete list of Sequoia industry filters
ALL_INDUSTRIES: List[str] = [
    "SaaS", "Fintech", "Enterprise Software", "Productivity", "AI",
    "Computer & Network Security", "Consumer", "ECommerce", "Developer Tools",
    "Financial Services", "Analytics", "Hospital & Health Care", "Consumer Services",
    "Blockchain", "Social Networking", "AI-Powered Applications", "Biotech/Pharma",
    "Transportation", "Hardware", "HR and Recruiting", "AI/ML", "Crypto",
    "Data & Analytics", "Health, Wellness and Fitness", "Infrastructure",
    "Marketing and Advertising", "Real Estate", "Security", "Cloud Services",
    "Video Games", "Telecommunications", "Renewables & Environment", "Manufacturing",
    "Legal Services", "Logistics and Supply Chain", "Delivery Services", "Virtual Reality",
    "Restaurants", "Healthcare", "SaaS Business App", "Sports", "IoT", "Higher Education",
    "Web3", "Wireless", "FinTech & Blockchain", "Payments", "NFT", "Retail",
    "Food & Beverages", "Agile Workplace", "Automation & Robotics", "IT and Services",
    "Apparel & Fashion", "Cybersecurity", "Insurance", "Banking", "Entertainment",
    "DeFi", "Investment Management", "Computer Networking", "Venture Capital & Private Equity",
    "Prediction Markets", "Environmental Services", "Online Media",
    "Sustainable Production and Consumption", "Marketplace", "Life Sciences",
    "Education Management", "Digital Health", "Defense & Space", "Cosmetics",
    "Consumer Electronics", "Autonomous Vehicles", "Aviation & Aerospace",
    "Business Services", "Capital Markets", "Computer Vision"
]


@dataclass
class SequoiaConfig(BrowserConfig):
    """Configuration settings specific to Sequoia Capital scraper operations."""
    
    # Target URLs & Endpoints
    base_url: str = "https://jobs.sequoiacap.com"
    companies_page_url: str = "https://jobs.sequoiacap.com/companies"
    target_api_pattern: str = "api-boards/search-companies"
    
    # Industries to scrape
    industries: List[str] = field(default_factory=lambda: list(ALL_INDUSTRIES))
    
    # Output file paths
    raw_output_file: Path = RAW_DATA_DIR / "sequoia_raw.json"
    processed_json_file: Path = PROCESSED_DATA_DIR / "sequoia_companies.json"
    processed_csv_file: Path = PROCESSED_DATA_DIR / "sequoia_companies.csv"


@dataclass
class KhoslaConfig(BrowserConfig):
    """Configuration settings specific to Khosla Ventures scraper operations."""
    
    # Target URLs & Endpoints
    base_url: str = "https://jobs.khoslaventures.com"
    companies_page_url: str = "https://jobs.khoslaventures.com/companies"
    target_api_pattern: str = "api/v2/collections/257/search/companies"
    
    # Output file paths
    raw_output_file: Path = RAW_DATA_DIR / "khosla_raw.json"
    processed_json_file: Path = PROCESSED_DATA_DIR / "khosla_companies.json"
    processed_csv_file: Path = PROCESSED_DATA_DIR / "khosla_companies.csv"

# Default instance (for backward compatibility / quick access, usually replaced dynamically)
config = SequoiaConfig()
