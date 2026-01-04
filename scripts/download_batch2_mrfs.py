#!/usr/bin/env python3
"""
Download MRF files from batch 2 hospitals (filtered working domains).
Run: python scripts/download_batch2_mrfs.py
"""

import csv
import requests
import hashlib
import time
import concurrent.futures
from pathlib import Path

# Configuration
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
TIMEOUT = 120  # seconds
WORKERS = 10

# Paths
BASE_DIR = Path(__file__).parent.parent
BATCH2_FILE = BASE_DIR / 'data/raw/pricevision/batch2_filtered.csv'
OUTPUT_DIR = BASE_DIR / 'data/raw/pricevision/mrfs'
LOG_FILE = BASE_DIR / 'data/raw/pricevision/batch2_crawl_log.csv'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Skip domains with 0% success rate
SKIP_DOMAINS = [
    'www.pennmedicine.org', 'www.slhn.org', 'www.wellspan.org',
    'www.lifebridgehealth.org', 'portalapprev.com', 'www.huntsvillehospital.org',
    'bhco.wpenginepowered.com', 'www.chghospitals.com', 'lhcgroup.com',
    'apps.scripps.org', 'hartfordhealthcare.org', 'www.mhs.net',
    'baptisthealth.net', 'www.northside.com', 'www.emoryhealthcare.org',
    'www.hshs.org', 'www.advocatehealth.com', 'memorial.health',
    'www.stlukesonline.org', 'media.franciscanhealth.org', 'medcenterhealth.org',
    'ochsnerlg.org'
]


def download_file(hospital):
    """Download MRF file for a hospital"""
    url = hospital['mrf_url']
    name = hospital['hospital_name']
    npi = hospital.get('npi', '').replace('.0', '')
    domain = hospital.get('domain', '')

    # Skip known bad domains
    if any(skip in domain for skip in SKIP_DOMAINS):
        return {
            'hospital': name,
            'status': 'skipped',
            'error': 'bad_domain',
            'size_mb': 0,
            'time': 0,
            'filepath': ''
        }

    try:
        start = time.time()
        resp = requests.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True)

        if resp.status_code != 200:
            return {
                'hospital': name,
                'status': 'failed',
                'error': f'HTTP {resp.status_code}',
                'size_mb': 0,
                'time': time.time() - start,
                'filepath': ''
            }

        # Check size from header
        content_length = int(resp.headers.get('Content-Length', 0))
        if content_length > MAX_FILE_SIZE:
            resp.close()
            return {
                'hospital': name,
                'status': 'too_large',
                'error': f'{content_length/(1024*1024):.0f} MB',
                'size_mb': content_length/(1024*1024),
                'time': time.time() - start,
                'filepath': ''
            }

        # Download content
        content = b''
        for chunk in resp.iter_content(chunk_size=1024*1024):
            content += chunk
            if len(content) > MAX_FILE_SIZE:
                resp.close()
                return {
                    'hospital': name,
                    'status': 'too_large',
                    'error': 'Exceeded limit during download',
                    'size_mb': len(content)/(1024*1024),
                    'time': time.time() - start,
                    'filepath': ''
                }

        # Check for HTML error pages
        if b'<html' in content[:500].lower() or b'<!doctype' in content[:500].lower():
            return {
                'hospital': name,
                'status': 'failed',
                'error': 'HTML error page',
                'size_mb': len(content)/(1024*1024),
                'time': time.time() - start,
                'filepath': ''
            }

        # Detect file type and save
        file_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        content_type = resp.headers.get('Content-Type', '')

        if 'json' in content_type or content[:1] in [b'{', b'[']:
            ext = 'json'
        elif 'csv' in content_type or (b',' in content[:1000] and b'\n' in content[:1000]):
            ext = 'csv'
        elif content[:4] == b'PK\x03\x04':  # ZIP/XLSX magic bytes
            ext = 'xlsx'
        else:
            ext = 'json'

        filename = f"{npi}_{file_hash}.{ext}" if npi else f"batch2_{file_hash}.{ext}"
        filepath = OUTPUT_DIR / filename

        with open(filepath, 'wb') as f:
            f.write(content)

        return {
            'hospital': name,
            'status': 'success',
            'error': '',
            'size_mb': len(content)/(1024*1024),
            'time': time.time() - start,
            'filepath': str(filepath)
        }

    except requests.exceptions.Timeout:
        return {'hospital': name, 'status': 'failed', 'error': 'timeout', 'size_mb': 0, 'time': TIMEOUT, 'filepath': ''}
    except requests.exceptions.ConnectionError:
        return {'hospital': name, 'status': 'failed', 'error': 'connection_error', 'size_mb': 0, 'time': 0, 'filepath': ''}
    except Exception as e:
        return {'hospital': name, 'status': 'failed', 'error': str(e)[:50], 'size_mb': 0, 'time': 0, 'filepath': ''}


def main():
    # Load hospitals
    hospitals = []
    with open(BATCH2_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hospitals.append(row)

    print("=" * 70)
    print("BATCH 2 HOSPITAL MRF DOWNLOADER")
    print("=" * 70)
    print(f"Hospitals to process: {len(hospitals)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Max file size: {MAX_FILE_SIZE/(1024*1024):.0f} MB")
    print(f"Workers: {WORKERS}")
    print(f"Skipping {len(SKIP_DOMAINS)} known bad domains")
    print("=" * 70)

    # Download with progress
    results = []
    success = 0
    failed = 0
    skipped = 0
    total_mb = 0
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(download_file, h): h for h in hospitals}

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

            if result['status'] == 'success':
                success += 1
                total_mb += result['size_mb']
                status_icon = "[OK]"
            elif result['status'] == 'skipped':
                skipped += 1
                status_icon = "[SKIP]"
            elif result['status'] == 'too_large':
                failed += 1
                status_icon = "[BIG]"
            else:
                failed += 1
                status_icon = "[FAIL]"

            done = success + failed + skipped
            elapsed = time.time() - start_time
            rate = total_mb / elapsed if elapsed > 0 else 0

            # Progress line
            if result['status'] != 'skipped':  # Don't spam skipped entries
                print(f"{status_icon} {done:>4}/{len(hospitals)} | {result['hospital'][:38]:<38} | "
                      f"{result['size_mb']:>6.1f} MB | {result['time']:>5.1f}s | "
                      f"Total: {total_mb:>7.0f} MB @ {rate:.1f} MB/s")
            elif done % 100 == 0:
                print(f"  Progress: {done}/{len(hospitals)} ({success} ok, {failed} fail, {skipped} skip)")

    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Time elapsed:      {elapsed/60:.1f} minutes")
    print(f"Total processed:   {len(results)}")
    print(f"Successful:        {success} ({success/len(results)*100:.1f}%)")
    print(f"Failed:            {failed}")
    print(f"Skipped (bad domain): {skipped}")
    print(f"Total downloaded:  {total_mb:.0f} MB ({total_mb/1024:.2f} GB)")
    if success > 0:
        print(f"Average file size: {total_mb/success:.1f} MB")
    if elapsed > 0:
        print(f"Average speed:     {total_mb/elapsed:.1f} MB/s")

    # Save log
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['hospital', 'status', 'error', 'size_mb', 'time', 'filepath'])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nLog saved to: {LOG_FILE}")


if __name__ == '__main__':
    main()
