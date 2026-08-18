"""
Core Configuration module.
Contains generic configuration settings for browser automation and HTTP clients.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# Base Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure runtime directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BrowserConfig:
    """General configuration settings for browser operations and HTTP clients."""
    
    # Browser & Request Settings
    headless: bool = False
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
    
    # Logging
    log_level: str = "INFO"
