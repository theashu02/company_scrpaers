"""
Data Transformation, Enrichment & Normalization Pipeline.
Parses, deduplicates, cleans, validates, and serializes company records
along with all associated links (website, careers, socials, ATS, portfolio, logos).
"""

import csv
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from config.core_config import BrowserConfig
from config.config import config

logger = logging.getLogger(__name__)


@dataclass
class JobSource:
    """Represents an integrated career/job board for a company."""
    id: str
    label: str
    count: int = 0


@dataclass
class CompanyModel:
    """Standardized company data schema with comprehensive link and social tracking."""
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    careers_url: Optional[str] = None
    sequoia_jobs_url: Optional[str] = None
    sequoia_portfolio_url: Optional[str] = None
    
    # Social links
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    youtube_url: Optional[str] = None
    github_url: Optional[str] = None
    
    # ATS and Job information
    ats_platform: Optional[str] = None
    total_jobs: int = 0
    num_remote_jobs: int = 0
    job_sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # Media & Logo links
    logo_url: Optional[str] = None
    linkedin_logo_url: Optional[str] = None
    
    # Organization metadata
    description: Optional[str] = None
    email_domains: List[str] = field(default_factory=list)
    industries: List[str] = field(default_factory=list)
    markets: List[str] = field(default_factory=list)
    office_locations: List[str] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)
    staff_count: Optional[int] = None
    investors: List[str] = field(default_factory=list)
    investor_slugs: List[str] = field(default_factory=list)
    
    # Raw payload cache
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def get_all_social_links(self) -> List[str]:
        """Returns all non-empty social URLs as a list."""
        socials = [
            self.linkedin_url,
            self.twitter_url,
            self.github_url,
            self.facebook_url,
            self.instagram_url,
            self.youtube_url,
        ]
        return [s for s in socials if s]

    def get_all_links(self) -> List[str]:
        """Returns all discovered links for this company."""
        all_links = [
            self.website_url,
            self.careers_url,
            self.sequoia_jobs_url,
            self.sequoia_portfolio_url,
            self.logo_url,
            self.linkedin_logo_url,
        ] + self.get_all_social_links()
        return [l for l in all_links if l]

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        """Converts model to dictionary, optionally omitting the raw payload."""
        data = asdict(self)
        data["all_social_links"] = self.get_all_social_links()
        data["all_links"] = self.get_all_links()
        if not include_raw:
            data.pop("raw_payload", None)
        return data

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flattens nested structures for CSV tabular export."""
        return {
            "name": self.name,
            "domain": self.domain or "",
            "website_url": self.website_url or "",
            "careers_url": self.careers_url or "",
            "sequoia_jobs_url": self.sequoia_jobs_url or "",
            "sequoia_portfolio_url": self.sequoia_portfolio_url or "",
            "linkedin_url": self.linkedin_url or "",
            "twitter_url": self.twitter_url or "",
            "github_url": self.github_url or "",
            "facebook_url": self.facebook_url or "",
            "instagram_url": self.instagram_url or "",
            "youtube_url": self.youtube_url or "",
            "all_social_links": " | ".join(self.get_all_social_links()),
            "ats_platform": self.ats_platform or "",
            "total_jobs": self.total_jobs,
            "num_remote_jobs": self.num_remote_jobs,
            "logo_url": self.logo_url or "",
            "linkedin_logo_url": self.linkedin_logo_url or "",
            "industries": ", ".join(sorted(set(self.industries))),
            "markets": ", ".join(sorted(set(self.markets))),
            "office_locations": ", ".join(self.office_locations),
            "stages": ", ".join(self.stages),
            "staff_count": self.staff_count or "",
            "email_domains": ", ".join(self.email_domains),
            "investors": ", ".join(self.investors),
            "description": (self.description or "").replace("\n", " ").strip(),
            "slug": self.slug,
            "id": self.id,
        }

    def merge_with(self, other: "CompanyModel"):
        """Merges metadata and links from another instance of the same company."""
        # Merge lists
        self.industries = list(set(self.industries) | set(other.industries))
        self.markets = list(set(self.markets) | set(other.markets))
        self.office_locations = list(set(self.office_locations) | set(other.office_locations))
        self.stages = list(set(self.stages) | set(other.stages))
        self.email_domains = list(set(self.email_domains) | set(other.email_domains))
        self.investors = list(set(self.investors) | set(other.investors))
        self.investor_slugs = list(set(self.investor_slugs) | set(other.investor_slugs))

        # Update URLs if currently empty
        if not self.website_url and other.website_url:
            self.website_url = other.website_url
        if not self.domain and other.domain:
            self.domain = other.domain
        if not self.careers_url and other.careers_url:
            self.careers_url = other.careers_url
        if not self.linkedin_url and other.linkedin_url:
            self.linkedin_url = other.linkedin_url
        if not self.twitter_url and other.twitter_url:
            self.twitter_url = other.twitter_url
        if not self.github_url and other.github_url:
            self.github_url = other.github_url
        if not self.facebook_url and other.facebook_url:
            self.facebook_url = other.facebook_url
        if not self.instagram_url and other.instagram_url:
            self.instagram_url = other.instagram_url
        if not self.youtube_url and other.youtube_url:
            self.youtube_url = other.youtube_url
        if not self.logo_url and other.logo_url:
            self.logo_url = other.logo_url
        if not self.linkedin_logo_url and other.linkedin_logo_url:
            self.linkedin_logo_url = other.linkedin_logo_url
        if not self.description and other.description:
            self.description = other.description
        if not self.staff_count and other.staff_count:
            self.staff_count = other.staff_count
        if not self.ats_platform and other.ats_platform:
            self.ats_platform = other.ats_platform

        self.total_jobs = max(self.total_jobs, other.total_jobs)
        self.num_remote_jobs = max(self.num_remote_jobs, other.num_remote_jobs)

        # Merge job sources
        existing_sources = {js.get("id"): js for js in self.job_sources if isinstance(js, dict)}
        for js in other.job_sources:
            if isinstance(js, dict) and js.get("id") not in existing_sources:
                self.job_sources.append(js)


class DataTransformer:
    """
    Transforms raw JSON responses into standardized, deduplicated, link-enriched CompanyModel records.
    """

    def __init__(self, cfg: Optional[BrowserConfig] = None):
        self.cfg = cfg or config

    def transform_single(self, raw: Dict[str, Any], industry_tag: Optional[str] = None) -> CompanyModel:
        """Transforms a raw company dictionary into a normalized CompanyModel."""
        company_id = str(raw.get("id") or raw.get("name") or "").strip()
        name = raw.get("name") or raw.get("id") or "Unknown"
        slug = (raw.get("slug") or name.lower().replace(" ", "-")).strip()
        domain = raw.get("domain") or ""
        
        # Clean domain
        if domain:
            domain = domain.lower().replace("https://", "").replace("http://", "").strip("/")

        # Website URL resolution
        website_url = None
        if isinstance(raw.get("website"), dict):
            website_url = raw["website"].get("url")
        elif isinstance(raw.get("website"), str):
            website_url = raw.get("website")
        elif domain:
            website_url = f"https://{domain}"

        # Careers and job URLs
        sequoia_jobs_url = f"https://jobs.sequoiacap.com/companies/{slug}"
        sequoia_portfolio_url = f"https://www.sequoiacap.com/companies/{slug}/"
        
        careers_url = raw.get("careers_url") or raw.get("careersUrl")
        if not careers_url:
            careers_url = sequoia_jobs_url

        # Job sources & ATS info
        job_sources = raw.get("jobSources") or raw.get("job_sources") or []
        total_jobs = raw.get("numJobs") or sum(js.get("count", 0) for js in job_sources if isinstance(js, dict))
        num_remote_jobs = raw.get("numRemoteJobs") or 0
        ats_platform = ", ".join([js.get("label", js.get("id", "")) for js in job_sources if isinstance(js, dict)]) if job_sources else None

        # Social links directly from payload if available
        linkedin_url = raw.get("linkedinUrl") or raw.get("linkedin")
        twitter_url = raw.get("twitterUrl") or raw.get("twitter")
        github_url = raw.get("githubUrl") or raw.get("github")
        facebook_url = raw.get("facebookUrl") or raw.get("facebook")
        instagram_url = raw.get("instagramUrl") or raw.get("instagram")
        youtube_url = raw.get("youtubeUrl") or raw.get("youtube")

        # Logos
        logos = raw.get("logos") or {}
        logo_url = None
        linkedin_logo_url = None
        if isinstance(logos, dict):
            if "manual" in logos and isinstance(logos["manual"], dict):
                logo_url = logos["manual"].get("src")
            if "linkedin" in logos and isinstance(logos["linkedin"], dict):
                linkedin_logo_url = logos["linkedin"].get("src")
        elif isinstance(raw.get("logo"), str):
            logo_url = raw.get("logo")

        # Industries, markets, and locations
        industries_list: List[str] = []
        if isinstance(raw.get("industries"), list):
            industries_list.extend(raw["industries"])
        elif isinstance(raw.get("industry"), str) and raw.get("industry"):
            industries_list.append(raw["industry"])
        if industry_tag and industry_tag not in industries_list:
            industries_list.append(industry_tag)

        markets = raw.get("markets") or []
        office_locations = raw.get("officeLocations") or []
        stages = raw.get("stages") or []
        staff_count = raw.get("staffCount")

        description = raw.get("description") or raw.get("summary") or ""
        email_domains = raw.get("emailDomains") or raw.get("email_domains") or []
        investors = raw.get("investors") or []
        investor_slugs = raw.get("investorSlugs") or raw.get("investor_slugs") or []

        return CompanyModel(
            id=company_id,
            name=name,
            slug=slug,
            domain=domain,
            website_url=website_url,
            careers_url=careers_url,
            sequoia_jobs_url=sequoia_jobs_url,
            sequoia_portfolio_url=sequoia_portfolio_url,
            linkedin_url=linkedin_url,
            twitter_url=twitter_url,
            github_url=github_url,
            facebook_url=facebook_url,
            instagram_url=instagram_url,
            youtube_url=youtube_url,
            ats_platform=ats_platform,
            total_jobs=int(total_jobs),
            num_remote_jobs=int(num_remote_jobs),
            job_sources=job_sources,
            logo_url=logo_url,
            linkedin_logo_url=linkedin_logo_url,
            description=description,
            email_domains=list(set(email_domains)),
            industries=list(set(industries_list)),
            markets=list(set(markets)),
            office_locations=list(set(office_locations)),
            stages=list(set(stages)),
            staff_count=staff_count,
            investors=list(set(investors)),
            investor_slugs=list(set(investor_slugs)),
            raw_payload=raw
        )

    def transform_batch(
        self, 
        raw_items: Union[List[Dict[str, Any]], Dict[str, Any]], 
        industry_tag: Optional[str] = None
    ) -> List[CompanyModel]:
        """Transforms and deduplicates items into a list of CompanyModel objects."""
        items = []
        if isinstance(raw_items, dict):
            items = raw_items.get("companies", [])
        elif isinstance(raw_items, list):
            items = raw_items

        company_map: Dict[str, CompanyModel] = {}

        for item in items:
            try:
                model = self.transform_single(item, industry_tag=industry_tag)
                key = (model.slug or model.id or model.name).strip().lower()
                if not key:
                    continue

                if key in company_map:
                    company_map[key].merge_with(model)
                else:
                    company_map[key] = model
            except Exception as e:
                logger.warning(f"Error parsing raw company item: {e}")

        return list(company_map.values())

    def merge_datasets(self, company_lists: List[List[CompanyModel]]) -> List[CompanyModel]:
        """Merges multiple lists of CompanyModels with full deduplication."""
        merged: Dict[str, CompanyModel] = {}
        for c_list in company_lists:
            for comp in c_list:
                key = (comp.slug or comp.id or comp.name).strip().lower()
                if key in merged:
                    merged[key].merge_with(comp)
                else:
                    merged[key] = comp
        return list(merged.values())

    def save_json(self, companies: List[CompanyModel], output_path: Optional[Path] = None, include_raw: bool = False):
        """Saves transformed models with full link data to a JSON file."""
        target_path = output_path or self.cfg.processed_json_file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [c.to_dict(include_raw=include_raw) for c in companies]
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(companies)} unique companies to JSON at {target_path}")

    def save_csv(self, companies: List[CompanyModel], output_path: Optional[Path] = None):
        """Saves transformed models with all links and socials to a CSV file."""
        target_path = output_path or self.cfg.processed_csv_file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not companies:
            logger.warning("No companies to write to CSV.")
            return

        flat_records = [c.to_flat_dict() for c in companies]
        headers = list(flat_records[0].keys())

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(flat_records)
        logger.info(f"Saved {len(companies)} unique companies with full links & socials to CSV at {target_path}")
