#!/usr/bin/env python3
"""
Discover additional hospital MRF URLs from multiple sources.
Combines: TPAFS, DoltHub, cms-hpt.txt scraping, and hospital website deduction.

Run: python scripts/discover_mrf_urls.py
"""

import csv
import json
import requests
import re
import concurrent.futures
from pathlib import Path
from urllib.parse import urlparse, urljoin
from collections import defaultdict
import time

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data/raw/pricevision'

# Existing files
EXISTING_URLS_FILE = DATA_DIR / 'hospital_mrf_urls.csv'
HOSPITAL_INFO_FILE = DATA_DIR / 'hospital_general_info.csv'
OUTPUT_FILE = DATA_DIR / 'all_mrf_urls.csv'

# Common hospital system URL patterns
HOSPITAL_SYSTEM_PATTERNS = {
    'hca': 'https://www.hcahealthcare.com/pricing-transparency/',
    'ascension': 'https://healthcare.ascension.org/Standard-Charges',
    'commonspirit': 'https://www.commonspirit.org/pricing-transparency',
    'providence': 'https://www.providence.org/obp/standard-charges',
    'tenet': 'https://www.tenethealth.com/pricing-transparency',
    'universal': 'https://www.uhsinc.com/patients/pricing-transparency/',
    'community': 'https://www.communityhealth.com/pricing-transparency',
    'lifepoint': 'https://www.lifepointhealth.net/price-transparency',
    'steward': 'https://content.steward.org/machine-readable-files',
}


def load_existing_urls():
    """Load URLs we already have"""
    urls = set()
    if EXISTING_URLS_FILE.exists():
        with open(EXISTING_URLS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('mrf_url', '').strip()
                if url:
                    urls.add(url)
    print(f"Loaded {len(urls)} existing URLs")
    return urls


def load_hospital_info():
    """Load CMS hospital general info"""
    hospitals = []
    if HOSPITAL_INFO_FILE.exists():
        with open(HOSPITAL_INFO_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hospitals.append({
                    'ccn': row.get('Facility ID', ''),
                    'name': row.get('Facility Name', ''),
                    'city': row.get('City/Town', ''),
                    'state': row.get('State', ''),
                    'zip': row.get('ZIP Code', ''),
                    'type': row.get('Hospital Type', ''),
                })
    print(f"Loaded {len(hospitals)} hospitals from CMS")
    return hospitals


def fetch_dolthub_urls():
    """Fetch URLs from DoltHub standard-charge-files"""
    print("\nFetching DoltHub URLs...")
    urls = []

    # DoltHub SQL API endpoint
    api_url = "https://www.dolthub.com/api/v1alpha1/dolthub/hospital-price-transparency/master"

    try:
        # Query the links table
        query = "SELECT hospital_name, state, url, file_type FROM links LIMIT 10000"
        resp = requests.get(
            f"{api_url}",
            params={'q': query},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            rows = data.get('rows', [])
            for row in rows:
                if row.get('url'):
                    urls.append({
                        'hospital_name': row.get('hospital_name', ''),
                        'state': row.get('state', ''),
                        'mrf_url': row.get('url', ''),
                        'source': 'dolthub'
                    })
            print(f"  Found {len(urls)} URLs from DoltHub")
    except Exception as e:
        print(f"  DoltHub fetch error: {e}")

    return urls


def scrape_cms_hpt_txt(domain):
    """Scrape cms-hpt.txt from a hospital domain"""
    txt_url = f"https://{domain}/cms-hpt.txt"

    try:
        resp = requests.get(txt_url, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            content = resp.text

            # Parse the txt file for MRF URLs
            # Format typically: hospital-location: <name>
            #                   source-page-url: <url>
            #                   mrf-url: <url>

            mrf_urls = []
            lines = content.split('\n')
            current_hospital = None

            for line in lines:
                line = line.strip()
                if line.startswith('hospital-location:'):
                    current_hospital = line.split(':', 1)[1].strip()
                elif 'mrf-url:' in line.lower() or 'mrf_url:' in line.lower():
                    url = line.split(':', 1)[1].strip() if ':' in line else ''
                    # Handle URLs that might be on the next line
                    if url.startswith('http'):
                        mrf_urls.append({
                            'hospital': current_hospital or domain,
                            'url': url
                        })
                elif line.startswith('http') and ('standardcharge' in line.lower() or 'mrf' in line.lower() or 'price' in line.lower()):
                    mrf_urls.append({
                        'hospital': current_hospital or domain,
                        'url': line
                    })

            return mrf_urls
    except:
        pass

    return []


def discover_from_hospital_websites(hospitals, existing_urls, max_workers=20):
    """Try to discover MRF URLs from hospital websites via cms-hpt.txt"""
    print("\nDiscovering URLs from cms-hpt.txt files...")

    # Generate potential domains from hospital names
    domains_to_check = set()

    for h in hospitals:
        name = h['name'].lower()
        # Clean up name for domain guessing
        name = re.sub(r'[^a-z0-9\s]', '', name)
        words = name.split()

        # Common patterns
        patterns = [
            f"www.{words[0]}.com",
            f"www.{words[0]}hospital.com",
            f"www.{words[0]}health.com",
            f"www.{''.join(words[:2])}.com",
            f"www.{''.join(words[:2])}hospital.com",
        ]

        for p in patterns:
            if len(p) < 50:  # Reasonable length
                domains_to_check.add(p)

    # Also check known hospital system domains
    known_domains = [
        'www.hcahealthcare.com', 'healthcare.ascension.org', 'www.commonspirit.org',
        'www.providence.org', 'www.dignityhealth.org', 'www.ssmhealth.com',
        'www.ochsner.org', 'www.piedmont.org', 'www.baptisthealth.com',
        'www.northwell.edu', 'www.mountsinai.org', 'nyulangone.org',
        'www.pennmedicine.org', 'www.uchealth.org', 'www.froedtert.com',
        'www.rush.edu', 'www.nm.org', 'www.uchicagomedicine.org',
        'my.clevelandclinic.org', 'www.mayoclinic.org', 'www.massgeneral.org',
        'www.hopkinsmedicine.org', 'stanfordhealthcare.org', 'www.uclahealth.org',
        'www.cedars-sinai.org', 'www.scripps.org', 'www.sharp.com',
        'www.adventhealth.com', 'www.mercy.com', 'www.bswhealth.com',
        'www.texashealth.org', 'www.mdanderson.org', 'www.houstonmethodist.org',
    ]

    domains_to_check.update(known_domains)
    print(f"  Checking {len(domains_to_check)} potential domains...")

    discovered = []
    checked = 0

    def check_domain(domain):
        return domain, scrape_cms_hpt_txt(domain)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_domain, d): d for d in list(domains_to_check)[:500]}  # Limit to 500 for speed

        for future in concurrent.futures.as_completed(futures):
            domain, urls = future.result()
            checked += 1

            if urls:
                for u in urls:
                    if u['url'] not in existing_urls:
                        discovered.append({
                            'hospital_name': u['hospital'],
                            'mrf_url': u['url'],
                            'source': f'cms-hpt.txt:{domain}'
                        })

            if checked % 100 == 0:
                print(f"    Checked {checked} domains, found {len(discovered)} new URLs")

    print(f"  Discovered {len(discovered)} new URLs from cms-hpt.txt")
    return discovered


def fetch_from_gigasheet():
    """Fetch from Gigasheet sample data if available"""
    print("\nChecking Gigasheet sample data...")
    urls = []

    # Try to fetch the sample data
    gigasheet_url = "https://www.gigasheet.com/sample-data/hospital-price-transparency-machine-readable-links"

    try:
        # This typically requires authentication, so we'll just note it
        print("  Gigasheet requires account access - skipping")
    except:
        pass

    return urls


def fetch_additional_github_sources():
    """Fetch from additional GitHub sources"""
    print("\nFetching from additional GitHub sources...")
    urls = []

    # Try to get updated TPAFS data
    tpafs_url = "https://raw.githubusercontent.com/TPAFS/transparency-data/main/price_transparency/hospitals/machine_readable_links.csv"

    try:
        resp = requests.get(tpafs_url, timeout=30)
        if resp.status_code == 200:
            lines = resp.text.split('\n')
            reader = csv.DictReader(lines)
            for row in reader:
                url = row.get('mrf_url', row.get('url', '')).strip()
                if url and url.startswith('http'):
                    urls.append({
                        'hospital_name': row.get('name', row.get('hospital_name', '')),
                        'state': row.get('state', ''),
                        'mrf_url': url,
                        'npi': row.get('npi', ''),
                        'source': 'tpafs_github'
                    })
            print(f"  Found {len(urls)} URLs from TPAFS GitHub")
    except Exception as e:
        print(f"  TPAFS fetch error: {e}")

    return urls


def merge_and_deduplicate(all_sources, existing_urls):
    """Merge all sources and remove duplicates"""
    print("\nMerging and deduplicating...")

    # Use URL as key for deduplication
    url_to_record = {}

    for record in all_sources:
        url = record.get('mrf_url', '').strip()
        if not url or not url.startswith('http'):
            continue

        # Normalize URL
        url = url.split('?')[0]  # Remove query params for dedup

        if url in existing_urls:
            continue

        if url not in url_to_record:
            url_to_record[url] = record

    print(f"  {len(url_to_record)} new unique URLs found")
    return list(url_to_record.values())


def save_combined_urls(existing_file, new_records, output_file):
    """Save combined URL list"""
    all_records = []

    # Load existing
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_records.append(row)

    # Add new
    for record in new_records:
        all_records.append({
            'hospital_name': record.get('hospital_name', ''),
            'mrf_url': record.get('mrf_url', ''),
            'city': record.get('city', ''),
            'state': record.get('state', ''),
            'npi': record.get('npi', ''),
            'source': record.get('source', 'discovered')
        })

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['hospital_name', 'mrf_url', 'city', 'state', 'npi', 'source'])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nSaved {len(all_records)} total URLs to {output_file}")
    return len(all_records)


def main():
    print("="*70)
    print("MRF URL DISCOVERY")
    print("="*70)

    # Load existing data
    existing_urls = load_existing_urls()
    hospitals = load_hospital_info()

    # Collect from all sources
    all_new_urls = []

    # 1. Refresh TPAFS GitHub
    tpafs_urls = fetch_additional_github_sources()
    all_new_urls.extend(tpafs_urls)

    # 2. Try DoltHub
    dolthub_urls = fetch_dolthub_urls()
    all_new_urls.extend(dolthub_urls)

    # 3. Scrape cms-hpt.txt files
    cms_hpt_urls = discover_from_hospital_websites(hospitals, existing_urls)
    all_new_urls.extend(cms_hpt_urls)

    # Merge and deduplicate
    new_unique = merge_and_deduplicate(all_new_urls, existing_urls)

    # Save combined file
    total = save_combined_urls(EXISTING_URLS_FILE, new_unique, OUTPUT_FILE)

    print("\n" + "="*70)
    print("DISCOVERY COMPLETE")
    print("="*70)
    print(f"Previously had: {len(existing_urls)} URLs")
    print(f"New discovered: {len(new_unique)} URLs")
    print(f"Total now:      {total} URLs")


if __name__ == '__main__':
    main()
