import logging
from typing import List, Optional

from config.core_config import BrowserConfig
from core.browser import BrowserManager, HTTPClient
from transformers.datatransform import DataTransformer, CompanyModel

logger = logging.getLogger(__name__)

class BaseScraper:
    """
    Base Scraper Engine.
    Provides shared browser management and data transformation capabilities.
    """

    def __init__(self, cfg: BrowserConfig):
        self.cfg = cfg
        self.browser_manager = BrowserManager(self.cfg)
        self.transformer = DataTransformer(self.cfg)
        self.http_client = HTTPClient(self.cfg)
        
    async def run(self):
        """Main execution method to be implemented by child classes."""
        raise NotImplementedError("Child classes must implement run()")

