#!/usr/bin/env python3
"""
Hospital Machine-Readable File (MRF) Crawler for HealthGuard America

This script crawls hospital price transparency files as required by the
Hospital Price Transparency Rule (CMS-1717-F2).

Since January 1, 2021, hospitals are required to post machine-readable files
containing their standard charges. This script attempts to discover and
download these files.

Usage:
    python crawl_hospital_mrfs.py [--test N] [--resume] [--workers N] [--priority-only]

Arguments:
    --test N         Only crawl first N hospitals (for testing)
    --resume         Skip hospitals that already have downloaded files
    --workers N      Number of concurrent workers (default: 3)
    --priority-only  Only crawl priority hospital systems (faster, higher success)

Output:
    - Downloaded MRF files in data/raw/pricevision/mrfs/
    - Crawl log in data/raw/pricevision/mrfs_crawl_log.csv
    - Summary statistics printed to console

Expected runtime: 8-12 hours for full crawl (~5,400 hospitals)
Expected success rate: 50-60% (many hospitals are non-compliant)

Author: HealthGuard America Team
Date: January 2026
"""

import os
import sys
import csv
import json
import time
import logging
import argparse
import hashlib
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Tuple, Set
import struct

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================================
# CONFIGURATION
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mrf_crawler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "raw" / "pricevision"
HOSPITAL_FILE = DATA_DIR / "hospital_general_info.csv"
HOSPITAL_MRF_URLS_FILE = DATA_DIR / "hospital_mrf_urls.csv"  # DoltHub verified URLs
MRF_DIR = DATA_DIR / "mrfs"
LOG_FILE = DATA_DIR / "mrfs_crawl_log.csv"

# Request settings
REQUEST_TIMEOUT = 45  # seconds for normal files
LARGE_FILE_TIMEOUT = 180  # seconds for large files
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
DELAY_BETWEEN_REQUESTS = 0.5  # seconds (faster with verified URLs)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB max per file
CHUNK_SIZE = 8192  # For streaming downloads
DEFAULT_WORKERS = 5  # Increased for verified URLs

USER_AGENT = (
    "HealthGuard-America-Research-Bot/1.0 "
    "(Healthcare Price Transparency Research Project; "
    "https://github.com/healthguard-america)"
)

# ============================================================================
# PRIORITY HOSPITAL SYSTEMS (Higher compliance, better formatted files)
# ============================================================================

PRIORITY_HOSPITAL_SYSTEMS = [
    # System Name patterns to match in facility names
    "HCA",
    "CommonSpirit",
    "Ascension",
    "Kaiser",
    "Cleveland Clinic",
    "Mayo Clinic",
    "UPMC",
    "Providence",
    "Intermountain",
    "Atrium",
    "Trinity Health",
    "AdventHealth",
    "Sutter Health",
    "Baylor Scott",
    "Northwell",
    "Mass General Brigham",
    "NYU Langone",
    "Mount Sinai",
    "Cedars-Sinai",
    "Stanford Health",
    "UCLA Health",
    "Duke Health",
    "Johns Hopkins",
    "Northwestern Medicine",
    "Emory Healthcare",
    "Houston Methodist",
    "Ochsner",
    "Geisinger",
    "Spectrum Health",
    "Advocate Aurora",
]

# Known third-party transparency platforms
THIRD_PARTY_PLATFORMS = {
    "turquoise": "https://turquoise.health",
    "clarify": "https://clarifyhealth.com",
}

# ============================================================================
# KNOWN HOSPITAL SYSTEM URLs (Verified working MRF locations)
# ============================================================================

KNOWN_HOSPITAL_URLS = {
    # HCA Healthcare (182 hospitals) - Uses centralized transparency site
    "HCA": {
        "base_url": "https://healthcaretransparency.hcahealthcare.com",
        "mrf_patterns": [
            "/machine-readable-files/{facility_id}",
            "/standard-charges/{facility_id}",
        ],
        "direct_download": "https://healthcaretransparency.hcahealthcare.com/api/v1/charges/{facility_id}",
    },

    # CommonSpirit Health (140 hospitals)
    "CommonSpirit": {
        "base_url": "https://www.commonspirit.org",
        "mrf_patterns": [
            "/patients-visitors/billing-insurance/pricing-transparency/machine-readable-file",
        ],
        "index_url": "https://www.commonspirit.org/patients-visitors/billing-insurance/pricing-transparency",
    },

    # Ascension (139 hospitals)
    "Ascension": {
        "base_url": "https://healthcare.ascension.org",
        "mrf_patterns": [
            "/patient-financial-services/cost-transparency",
        ],
        "index_url": "https://healthcare.ascension.org/patient-financial-services/cost-transparency",
    },

    # Kaiser Permanente (39 hospitals)
    "Kaiser": {
        "base_url": "https://healthy.kaiserpermanente.org",
        "mrf_patterns": [
            "/front-door/machine-readable",
        ],
        "index_url": "https://healthy.kaiserpermanente.org/front-door/machine-readable",
    },

    # Providence (51 hospitals)
    "Providence": {
        "base_url": "https://www.providence.org",
        "mrf_patterns": [
            "/patients-visitors/billing-pricing/pricing-transparency",
        ],
        "index_url": "https://www.providence.org/patients-visitors/billing-pricing/pricing-transparency",
    },

    # Tenet Healthcare (61 hospitals)
    "Tenet": {
        "base_url": "https://www.tenethealth.com",
        "mrf_patterns": [
            "/pricing-transparency",
        ],
        "index_url": "https://www.tenethealth.com/pricing-transparency",
    },

    # Universal Health Services (28 hospitals)
    "Universal Health": {
        "base_url": "https://www.uhsinc.com",
        "mrf_patterns": [
            "/pricing-transparency",
        ],
    },

    # Community Health Systems (79 hospitals)
    "Community Health": {
        "base_url": "https://www.chs.net",
        "mrf_patterns": [
            "/hospitals/pricing-transparency",
        ],
    },

    # AdventHealth (50 hospitals) - Uses centralized site
    "AdventHealth": {
        "base_url": "https://www.adventhealth.com",
        "mrf_patterns": [
            "/pricing-transparency",
            "/patient-financial-services/standard-charges",
        ],
        "index_url": "https://www.adventhealth.com/pricing-transparency",
    },

    # Trinity Health (88 hospitals)
    "Trinity Health": {
        "base_url": "https://www.trinity-health.org",
        "mrf_patterns": [
            "/patients/pricing-transparency",
        ],
    },

    # UPMC (40 hospitals)
    "UPMC": {
        "base_url": "https://www.upmc.com",
        "mrf_patterns": [
            "/patients-visitors/billing-payment/standard-charges",
        ],
        "index_url": "https://www.upmc.com/patients-visitors/billing-payment/standard-charges",
    },

    # Cleveland Clinic (19 hospitals)
    "Cleveland Clinic": {
        "base_url": "https://my.clevelandclinic.org",
        "mrf_patterns": [
            "/patients/billing-finance/pricing-information",
        ],
        "index_url": "https://my.clevelandclinic.org/patients/billing-finance/pricing-information",
    },

    # Mayo Clinic (5 hospitals)
    "Mayo Clinic": {
        "base_url": "https://www.mayoclinic.org",
        "mrf_patterns": [
            "/patient-visitor-guide/billing-insurance/price-estimates/chargemaster",
        ],
        "index_url": "https://www.mayoclinic.org/patient-visitor-guide/billing-insurance/price-estimates/chargemaster",
    },

    # Intermountain Healthcare (33 hospitals)
    "Intermountain": {
        "base_url": "https://intermountainhealthcare.org",
        "mrf_patterns": [
            "/patient-resources/billing-insurance/price-transparency",
        ],
    },

    # Atrium Health (38 hospitals)
    "Atrium": {
        "base_url": "https://atriumhealth.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-transparency",
        ],
    },

    # Sutter Health (24 hospitals)
    "Sutter Health": {
        "base_url": "https://www.sutterhealth.org",
        "mrf_patterns": [
            "/for-patients/billing/pricing-info",
        ],
    },

    # Baylor Scott & White (52 hospitals)
    "Baylor Scott": {
        "base_url": "https://www.bswhealth.com",
        "mrf_patterns": [
            "/patient-tools/billing-insurance/pricing-transparency",
        ],
    },

    # Northwell Health (23 hospitals)
    "Northwell": {
        "base_url": "https://www.northwell.edu",
        "mrf_patterns": [
            "/patient-resources/billing/price-transparency",
        ],
    },

    # NYU Langone (4 hospitals)
    "NYU Langone": {
        "base_url": "https://nyulangone.org",
        "mrf_patterns": [
            "/patient-visitor-guide/billing-insurance/standard-charges",
        ],
    },

    # Mount Sinai (8 hospitals)
    "Mount Sinai": {
        "base_url": "https://www.mountsinai.org",
        "mrf_patterns": [
            "/patient-care/pay-your-bill/pricing-transparency",
        ],
    },

    # Cedars-Sinai (2 hospitals)
    "Cedars-Sinai": {
        "base_url": "https://www.cedars-sinai.org",
        "mrf_patterns": [
            "/billing-insurance/hospital-pricing-information",
        ],
    },

    # Stanford Health Care (3 hospitals)
    "Stanford Health": {
        "base_url": "https://stanfordhealthcare.org",
        "mrf_patterns": [
            "/for-patients/billing/pricing-transparency",
        ],
    },

    # UCLA Health (4 hospitals)
    "UCLA Health": {
        "base_url": "https://www.uclahealth.org",
        "mrf_patterns": [
            "/patients/billing/pricing-transparency",
        ],
    },

    # Duke Health (3 hospitals)
    "Duke Health": {
        "base_url": "https://www.dukehealth.org",
        "mrf_patterns": [
            "/patients-visitors/billing-insurance/price-transparency",
        ],
    },

    # Johns Hopkins (6 hospitals)
    "Johns Hopkins": {
        "base_url": "https://www.hopkinsmedicine.org",
        "mrf_patterns": [
            "/patient-care/billing-insurance/estimate-costs",
        ],
    },

    # Northwestern Medicine (11 hospitals)
    "Northwestern Medicine": {
        "base_url": "https://www.nm.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-information",
        ],
    },

    # Emory Healthcare (11 hospitals)
    "Emory Healthcare": {
        "base_url": "https://www.emoryhealthcare.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-transparency",
        ],
    },

    # Houston Methodist (8 hospitals)
    "Houston Methodist": {
        "base_url": "https://www.houstonmethodist.org",
        "mrf_patterns": [
            "/for-patients/billing-insurance/pricing-transparency",
        ],
    },

    # Ochsner Health (40 hospitals)
    "Ochsner": {
        "base_url": "https://www.ochsner.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-information",
        ],
    },

    # Geisinger (10 hospitals)
    "Geisinger": {
        "base_url": "https://www.geisinger.org",
        "mrf_patterns": [
            "/patient/billing/price-transparency",
        ],
    },

    # Spectrum Health (14 hospitals)
    "Spectrum Health": {
        "base_url": "https://www.spectrumhealth.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-transparency",
        ],
    },

    # Advocate Aurora (27 hospitals)
    "Advocate Aurora": {
        "base_url": "https://www.advocateaurorahealth.org",
        "mrf_patterns": [
            "/patients-visitors/billing/pricing-transparency",
        ],
    },
}

# ============================================================================
# URL PATTERNS FOR MRF DISCOVERY
# ============================================================================

# Common paths where hospitals host MRF files
MRF_PATH_PATTERNS = [
    # Standard CMS-recommended paths
    "/chargemaster",
    "/standard-charges",
    "/price-transparency",
    "/pricing",
    "/machine-readable-file",
    "/mrf",
    "/hospital-charges",
    "/patient-pricing",
    "/pricing-transparency",
    "/cms-price-transparency",

    # Common file locations
    "/sites/default/files/standard-charges",
    "/sites/default/files/chargemaster",
    "/wp-content/uploads/standard-charges",
    "/wp-content/uploads/chargemaster",
    "/documents/standard-charges",
    "/documents/chargemaster",
    "/files/price-transparency",
    "/assets/pricing",

    # Direct file paths
    "/standard-charges.json",
    "/standard-charges.csv",
    "/chargemaster.json",
    "/chargemaster.csv",
    "/machine-readable.json",
    "/cdm.json",
    "/cdm.csv",
]

# File extensions we accept
VALID_EXTENSIONS = {'.csv', '.json', '.txt', '.xlsx', '.xls', '.xml', '.zip', '.gz'}

# HTTP status codes to retry
RETRY_STATUS_CODES = {500, 502, 503, 504, 429}

# HTTP status codes that indicate permanent failure (don't retry)
PERMANENT_FAILURE_CODES = {401, 403, 404, 410}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CrawlResult:
    """Result of crawling a single hospital."""
    facility_id: str
    facility_name: str
    state: str
    city: str
    hospital_type: str
    url_attempted: str
    final_url: str  # After redirects
    status: str  # 'success', 'failed', 'skipped', 'too_large'
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None  # 'json', 'csv', 'xlsx', etc.
    content_type: Optional[str] = None
    error_message: Optional[str] = None
    error_category: Optional[str] = None  # 'not_found', 'forbidden', 'timeout', etc.
    http_status: Optional[int] = None
    crawl_time_seconds: Optional[float] = None
    is_priority_system: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# FILE TYPE DETECTION
# ============================================================================

def detect_file_type(content: bytes, content_type: str, url: str) -> Tuple[str, str]:
    """
    Detect file type from content, headers, and URL.
    Returns (file_type, extension).
    """
    # Check URL extension first
    parsed = urlparse(url)
    url_ext = Path(parsed.path).suffix.lower()

    # Check content-type header
    ct = content_type.lower().split(';')[0].strip() if content_type else ''

    # Check magic bytes
    if len(content) >= 4:
        # JSON detection
        first_char = content.lstrip()[:1]
        if first_char in (b'{', b'['):
            return 'json', '.json'

        # XML detection
        if content.lstrip()[:5] == b'<?xml' or content.lstrip()[:1] == b'<':
            return 'xml', '.xml'

        # ZIP detection (PK signature)
        if content[:4] == b'PK\x03\x04':
            return 'zip', '.zip'

        # GZIP detection
        if content[:2] == b'\x1f\x8b':
            return 'gzip', '.gz'

        # Excel XLSX (also ZIP-based but with specific structure)
        if content[:4] == b'PK\x03\x04' and b'[Content_Types].xml' in content[:1000]:
            return 'xlsx', '.xlsx'

        # Excel XLS (OLE2)
        if content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            return 'xls', '.xls'

    # Content-type based detection
    ct_map = {
        'application/json': ('json', '.json'),
        'text/json': ('json', '.json'),
        'text/csv': ('csv', '.csv'),
        'application/csv': ('csv', '.csv'),
        'text/plain': ('txt', '.txt'),
        'application/xml': ('xml', '.xml'),
        'text/xml': ('xml', '.xml'),
        'application/vnd.ms-excel': ('xls', '.xls'),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('xlsx', '.xlsx'),
        'application/zip': ('zip', '.zip'),
        'application/gzip': ('gzip', '.gz'),
    }

    if ct in ct_map:
        return ct_map[ct]

    # URL extension fallback
    ext_map = {
        '.json': ('json', '.json'),
        '.csv': ('csv', '.csv'),
        '.xml': ('xml', '.xml'),
        '.xlsx': ('xlsx', '.xlsx'),
        '.xls': ('xls', '.xls'),
        '.zip': ('zip', '.zip'),
        '.gz': ('gzip', '.gz'),
        '.txt': ('txt', '.txt'),
    }

    if url_ext in ext_map:
        return ext_map[url_ext]

    # CSV heuristic: check for comma-separated structure
    if b',' in content[:1000] and b'\n' in content[:1000]:
        lines = content[:2000].split(b'\n')
        if len(lines) >= 2:
            comma_counts = [line.count(b',') for line in lines[:5] if line.strip()]
            if comma_counts and all(c == comma_counts[0] for c in comma_counts):
                return 'csv', '.csv'

    return 'unknown', '.dat'


def is_html_error_page(content: bytes) -> bool:
    """Check if content is an HTML error page rather than valid data."""
    if len(content) < 100:
        return True

    # Check first 500 bytes for HTML signatures
    start = content[:500].lower()

    html_indicators = [
        b'<!doctype html',
        b'<html',
        b'<head>',
        b'<body>',
    ]

    error_phrases = [
        b'page not found',
        b'404 error',
        b'404 not found',
        b'access denied',
        b'forbidden',
        b'not available',
        b'error page',
        b'coming soon',
        b'under construction',
        b'maintenance',
        b'login required',
        b'sign in',
        b'please wait',
    ]

    is_html = any(indicator in start for indicator in html_indicators)
    has_error = any(phrase in start for phrase in error_phrases)

    # If it's HTML but contains MRF-related terms, might be valid XML
    if is_html:
        mrf_terms = [b'standard', b'charge', b'price', b'procedure', b'billing']
        if any(term in start for term in mrf_terms):
            return False  # Might be valid XML/data
        return True

    if has_error:
        return True

    return False


# ============================================================================
# HOSPITAL MRF CRAWLER
# ============================================================================

class HospitalMRFCrawler:
    """Crawler for hospital machine-readable price transparency files."""

    def __init__(self, resume: bool = True, max_workers: int = 3, priority_only: bool = False):
        self.resume = resume
        self.max_workers = max_workers
        self.priority_only = priority_only
        self.session = self._create_session()
        self.results: List[CrawlResult] = []
        self.existing_files: Set[str] = set()

        # Statistics
        self.stats = {
            'attempted': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'too_large': 0,
            'total_bytes': 0,
        }

        # Create output directory
        MRF_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing files if resuming
        if resume:
            self._load_existing_files()

    def _create_session(self) -> requests.Session:
        """Create a requests session with smart retry logic."""
        session = requests.Session()

        # Configure retries - only for transient errors
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=list(RETRY_STATUS_CODES),
            allowed_methods=["HEAD", "GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json, text/csv, application/xml, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        })

        return session

    def _load_existing_files(self):
        """Load list of already-downloaded files."""
        if MRF_DIR.exists():
            for f in MRF_DIR.iterdir():
                if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS:
                    # Extract facility ID from filename (format: FACILITYID_hash.ext)
                    parts = f.stem.split('_')
                    if parts:
                        self.existing_files.add(parts[0])

        logger.info(f"Found {len(self.existing_files)} existing MRF files (will skip if resuming)")

    def load_hospitals(self) -> List[Dict]:
        """Load hospital data from unified verified URLs CSV."""
        hospitals = []

        if not HOSPITAL_MRF_URLS_FILE.exists():
            logger.error(f"No verified URLs file found at {HOSPITAL_MRF_URLS_FILE}")
            logger.error("Please run the data collection script first.")
            return []

        logger.info(f"Loading verified MRF URLs from {HOSPITAL_MRF_URLS_FILE}")
        with open(HOSPITAL_MRF_URLS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('mrf_url', '').strip()
                if not url:
                    continue

                hospital = {
                    'facility_id': row.get('npi', '').strip().replace('.0', ''),
                    'facility_name': row.get('hospital_name', '').strip(),
                    'address': '',
                    'city': row.get('city', '').strip(),
                    'state': row.get('state', '').strip(),
                    'zip_code': '',
                    'hospital_type': 'Acute Care',
                    'verified_url': url,
                    'source': row.get('source', ''),
                }

                # Check if priority hospital system
                hospital['is_priority'] = any(
                    system.lower() in hospital['facility_name'].lower()
                    for system in PRIORITY_HOSPITAL_SYSTEMS
                )

                hospitals.append(hospital)

        # Sort: priority hospitals first
        hospitals.sort(key=lambda h: (not h['is_priority'], h['facility_name']))

        priority_count = sum(1 for h in hospitals if h['is_priority'])
        logger.info(f"Loaded {len(hospitals)} hospitals with verified URLs ({priority_count} priority)")

        return hospitals

    def _generate_potential_urls(self, hospital: Dict) -> List[str]:
        """Get verified MRF URL for a hospital (no guessing)."""
        # ONLY use verified URLs - no fake URL guessing
        verified_url = hospital.get('verified_url')
        if verified_url:
            return [verified_url]

        # No verified URL = skip this hospital
        return []

    def _download_file(self, url: str, timeout: int = REQUEST_TIMEOUT) -> Tuple[Optional[bytes], Optional[str], Optional[int], Optional[str]]:
        """
        Download file from URL with streaming for large files.
        Returns: (content, content_type, status_code, final_url)
        """
        try:
            # First, do a HEAD request to check size and type
            head_resp = self.session.head(url, timeout=timeout, allow_redirects=True)

            if head_resp.status_code in PERMANENT_FAILURE_CODES:
                return None, None, head_resp.status_code, url

            if head_resp.status_code != 200:
                return None, None, head_resp.status_code, url

            content_length = int(head_resp.headers.get('Content-Length', 0))
            content_type = head_resp.headers.get('Content-Type', '')

            # Skip files that are too large
            if content_length > MAX_FILE_SIZE:
                logger.warning(f"File too large ({content_length / 1024 / 1024:.1f} MB): {url}")
                return None, content_type, -1, url  # -1 indicates too large

            # Use longer timeout for larger files
            if content_length > 50 * 1024 * 1024:  # > 50 MB
                timeout = LARGE_FILE_TIMEOUT

            # Download with streaming
            resp = self.session.get(url, timeout=timeout, allow_redirects=True, stream=True)

            if resp.status_code != 200:
                return None, content_type, resp.status_code, resp.url

            # Stream content
            chunks = []
            total_size = 0
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                chunks.append(chunk)
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    logger.warning(f"File exceeded max size during download: {url}")
                    return None, content_type, -1, resp.url

            content = b''.join(chunks)
            return content, resp.headers.get('Content-Type', ''), resp.status_code, resp.url

        except requests.exceptions.Timeout:
            return None, None, -2, url  # -2 indicates timeout
        except requests.exceptions.SSLError:
            return None, None, -3, url  # -3 indicates SSL error
        except requests.exceptions.ConnectionError:
            return None, None, -4, url  # -4 indicates connection error
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return None, None, -5, url  # -5 indicates other error

    def crawl_hospital(self, hospital: Dict) -> CrawlResult:
        """Attempt to download MRF for a single hospital."""
        facility_id = hospital['facility_id']
        facility_name = hospital['facility_name']
        state = hospital['state']
        city = hospital['city']
        hospital_type = hospital['hospital_type']
        is_priority = hospital['is_priority']

        start_time = time.time()

        # Skip if already downloaded and resuming
        if self.resume and facility_id in self.existing_files:
            return CrawlResult(
                facility_id=facility_id,
                facility_name=facility_name,
                state=state,
                city=city,
                hospital_type=hospital_type,
                url_attempted="",
                final_url="",
                status="skipped",
                error_message="Already downloaded",
                error_category="skipped",
                is_priority_system=is_priority,
            )

        # Generate URLs to try
        urls_to_try = self._generate_potential_urls(hospital)

        # Skip hospitals without verified URLs or known system patterns
        if not urls_to_try:
            return CrawlResult(
                facility_id=facility_id,
                facility_name=facility_name,
                state=state,
                city=city,
                hospital_type=hospital_type,
                url_attempted="",
                final_url="",
                status="skipped",
                error_message="No verified URL available",
                error_category="no_url",
                crawl_time_seconds=time.time() - start_time,
                is_priority_system=is_priority,
            )

        last_error = "No URLs generated"
        last_error_category = "no_urls"
        last_url = ""

        for url in urls_to_try:
            time.sleep(DELAY_BETWEEN_REQUESTS)

            content, content_type, status_code, final_url = self._download_file(url)
            last_url = url

            # Handle special status codes
            if status_code == -1:
                return CrawlResult(
                    facility_id=facility_id,
                    facility_name=facility_name,
                    state=state,
                    city=city,
                    hospital_type=hospital_type,
                    url_attempted=url,
                    final_url=final_url,
                    status="too_large",
                    error_message="File exceeds 500MB limit",
                    error_category="too_large",
                    http_status=200,
                    crawl_time_seconds=time.time() - start_time,
                    is_priority_system=is_priority,
                )

            if status_code == -2:
                last_error = "Connection timeout"
                last_error_category = "timeout"
                continue

            if status_code == -3:
                last_error = "SSL certificate error"
                last_error_category = "ssl_error"
                continue

            if status_code == -4:
                last_error = "Connection refused"
                last_error_category = "connection_error"
                continue

            if status_code == -5:
                last_error = "Unknown error"
                last_error_category = "unknown_error"
                continue

            if status_code in PERMANENT_FAILURE_CODES:
                if status_code == 404:
                    last_error = "Not found"
                    last_error_category = "not_found"
                elif status_code == 403:
                    last_error = "Forbidden"
                    last_error_category = "forbidden"
                elif status_code == 401:
                    last_error = "Unauthorized"
                    last_error_category = "unauthorized"
                continue

            if content is None:
                last_error = f"HTTP {status_code}"
                last_error_category = "http_error"
                continue

            # Check if it's an HTML error page
            if is_html_error_page(content):
                last_error = "HTML error page returned"
                last_error_category = "html_error_page"
                continue

            # Detect file type
            file_type, extension = detect_file_type(content, content_type, final_url)

            if file_type == 'unknown':
                last_error = "Unknown file type"
                last_error_category = "unknown_format"
                continue

            # Success! Save the file
            file_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{facility_id}_{file_hash}{extension}"
            filepath = MRF_DIR / filename

            with open(filepath, 'wb') as f:
                f.write(content)

            crawl_time = time.time() - start_time

            logger.info(
                f"SUCCESS: {facility_name} ({state}) - "
                f"{len(content)/1024:.1f}KB {file_type} - {crawl_time:.1f}s"
            )

            return CrawlResult(
                facility_id=facility_id,
                facility_name=facility_name,
                state=state,
                city=city,
                hospital_type=hospital_type,
                url_attempted=url,
                final_url=final_url,
                status="success",
                file_path=str(filepath),
                file_size=len(content),
                file_type=file_type,
                content_type=content_type,
                http_status=status_code,
                crawl_time_seconds=crawl_time,
                is_priority_system=is_priority,
            )

        # All attempts failed
        crawl_time = time.time() - start_time

        return CrawlResult(
            facility_id=facility_id,
            facility_name=facility_name,
            state=state,
            city=city,
            hospital_type=hospital_type,
            url_attempted=last_url,
            final_url="",
            status="failed",
            error_message=last_error,
            error_category=last_error_category,
            crawl_time_seconds=crawl_time,
            is_priority_system=is_priority,
        )

    def save_results(self):
        """Save crawl results to CSV log."""
        fieldnames = [
            'facility_id', 'facility_name', 'state', 'city', 'hospital_type',
            'url_attempted', 'final_url', 'status', 'file_path', 'file_size',
            'file_type', 'content_type', 'error_message', 'error_category',
            'http_status', 'crawl_time_seconds', 'is_priority_system', 'timestamp'
        ]

        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))

        logger.info(f"Saved {len(self.results)} results to {LOG_FILE}")

    def print_summary(self):
        """Print comprehensive crawl summary."""
        total = len(self.results)
        success = sum(1 for r in self.results if r.status == 'success')
        failed = sum(1 for r in self.results if r.status == 'failed')
        skipped = sum(1 for r in self.results if r.status == 'skipped')
        too_large = sum(1 for r in self.results if r.status == 'too_large')

        total_size = sum(r.file_size or 0 for r in self.results if r.status == 'success')

        # Error category breakdown
        error_categories = {}
        for r in self.results:
            if r.status == 'failed' and r.error_category:
                error_categories[r.error_category] = error_categories.get(r.error_category, 0) + 1

        # File type breakdown
        file_types = {}
        for r in self.results:
            if r.status == 'success' and r.file_type:
                file_types[r.file_type] = file_types.get(r.file_type, 0) + 1

        # Priority system stats
        priority_total = sum(1 for r in self.results if r.is_priority_system)
        priority_success = sum(1 for r in self.results if r.is_priority_system and r.status == 'success')

        print("\n" + "="*70)
        print("HOSPITAL MRF CRAWL SUMMARY")
        print("="*70)
        print(f"\nTotal hospitals processed: {total}")
        print(f"  [OK] Successful:         {success:>5} ({100*success/max(total,1):.1f}%)")
        print(f"  [X]  Failed:             {failed:>5} ({100*failed/max(total,1):.1f}%)")
        print(f"  [--] Skipped:            {skipped:>5}")
        print(f"  [!]  Too large (>500MB): {too_large:>5}")

        print(f"\nPriority hospital systems: {priority_success}/{priority_total} successful")

        print(f"\nTotal data downloaded: {total_size / (1024*1024):.1f} MB")

        if file_types:
            print("\nFile types downloaded:")
            for ft, count in sorted(file_types.items(), key=lambda x: -x[1]):
                print(f"  {ft:>8}: {count}")

        if error_categories:
            print("\nFailure reasons (top 5):")
            for cat, count in sorted(error_categories.items(), key=lambda x: -x[1])[:5]:
                print(f"  {cat:>20}: {count}")

        print(f"\nOutput files:")
        print(f"  Log:  {LOG_FILE}")
        print(f"  MRFs: {MRF_DIR}/")
        print("="*70)

    def run(self, limit: Optional[int] = None):
        """Run the crawler."""
        hospitals = self.load_hospitals()

        # Filter to priority only if requested
        if self.priority_only:
            hospitals = [h for h in hospitals if h['is_priority']]
            logger.info(f"Priority-only mode: {len(hospitals)} hospitals")

        if limit:
            hospitals = hospitals[:limit]
            logger.info(f"Limited to {limit} hospitals")

        total = len(hospitals)
        logger.info(f"Starting crawl of {total} hospitals with {self.max_workers} workers...")

        start_time = time.time()

        # Use thread pool for concurrent crawling
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.crawl_hospital, h): h for h in hospitals}

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                completed += 1

                # Progress update every 100 hospitals
                if completed % 100 == 0:
                    success_count = sum(1 for r in self.results if r.status == 'success')
                    elapsed = time.time() - start_time
                    rate = completed / elapsed * 3600  # hospitals per hour
                    eta = (total - completed) / (completed / elapsed) if completed > 0 else 0

                    logger.info(
                        f"Progress: {completed}/{total} ({100*completed/total:.1f}%) - "
                        f"{success_count} successful - "
                        f"Rate: {rate:.0f}/hr - ETA: {eta/60:.0f}min"
                    )

        # Save results and print summary
        self.save_results()
        self.print_summary()

        total_time = time.time() - start_time
        logger.info(f"Crawl completed in {total_time/60:.1f} minutes")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Crawl hospital machine-readable price transparency files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python crawl_hospital_mrfs.py --test 50          # Test with 50 hospitals
  python crawl_hospital_mrfs.py --priority-only    # Only priority systems
  python crawl_hospital_mrfs.py --workers 5        # Use 5 concurrent workers
  python crawl_hospital_mrfs.py --no-resume        # Re-crawl everything
        """
    )
    parser.add_argument(
        '--test', type=int, metavar='N',
        help='Only crawl first N hospitals (for testing)'
    )
    parser.add_argument(
        '--resume', action='store_true', default=True,
        help='Skip hospitals with existing downloads (default: True)'
    )
    parser.add_argument(
        '--no-resume', action='store_false', dest='resume',
        help='Re-crawl all hospitals, ignoring existing files'
    )
    parser.add_argument(
        '--workers', type=int, default=DEFAULT_WORKERS,
        help=f'Number of concurrent workers (default: {DEFAULT_WORKERS})'
    )
    parser.add_argument(
        '--priority-only', action='store_true',
        help='Only crawl priority hospital systems (faster, higher success rate)'
    )

    args = parser.parse_args()

    print("="*70)
    print("HEALTHGUARD AMERICA - Hospital MRF Crawler")
    print("="*70)
    print(f"Hospital file:    {HOSPITAL_FILE}")
    print(f"Output directory: {MRF_DIR}")
    print(f"Resume mode:      {args.resume}")
    print(f"Workers:          {args.workers}")
    print(f"Priority only:    {args.priority_only}")
    if args.test:
        print(f"TEST MODE:        {args.test} hospitals only")
    print("="*70 + "\n")

    # Confirm before full crawl
    if not args.test and not args.priority_only:
        print("WARNING: Full crawl will take 8-12 hours!")
        print("Consider using --test 100 or --priority-only first.\n")

    crawler = HospitalMRFCrawler(
        resume=args.resume,
        max_workers=args.workers,
        priority_only=args.priority_only
    )
    crawler.run(limit=args.test)


if __name__ == "__main__":
    main()
