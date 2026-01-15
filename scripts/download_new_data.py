"""
Download and Process New Data Sources for HealthGuard

Downloads new data and integrates into existing processed datasets:
- FoodScore: USDA Branded Foods, FDA Recalls → products + recalls
- DrugWatch: NADAC, VA Prices → drug pricing comparisons
- RuralAccess: FQHC, Hospital Closures → healthcare access

Usage:
    python scripts/download_new_data.py --all
    python scripts/download_new_data.py --foodscore
    python scripts/download_new_data.py --drugwatch
    python scripts/download_new_data.py --ruralaccess
"""

import os
import sys
import json
import requests
import zipfile
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from io import BytesIO, StringIO
import time

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def download_file(url, dest_path, desc="file", timeout=300, verify_ssl=True):
    """Download a file with progress."""
    log(f"Downloading {desc}...")
    try:
        # Some government sites (va.gov, pbm.va.gov) have certificate issues
        # Allow bypassing for known problematic but trustworthy sites
        response = requests.get(url, stream=True, timeout=timeout, verify=verify_ssl)
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))

        with open(dest_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(f"\r  {downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB", end="")
            print()

        log(f"  Saved: {dest_path} ({dest_path.stat().st_size/1024/1024:.1f} MB)")
        return True
    except requests.exceptions.SSLError:
        if verify_ssl:
            log(f"  SSL error, retrying without verification...")
            return download_file(url, dest_path, desc, timeout, verify_ssl=False)
        log(f"  ERROR: SSL verification failed")
        return False
    except Exception as e:
        log(f"  ERROR: {e}")
        return False


def fetch_api(url, params=None, desc="API"):
    """Fetch from API with pagination."""
    log(f"Fetching {desc}...")
    all_results = []
    skip = 0
    limit = 1000

    while True:
        try:
            p = {**(params or {}), "limit": limit, "skip": skip}
            resp = requests.get(url, params=p, timeout=60)
            resp.raise_for_status()
            results = resp.json().get("results", [])

            if not results:
                break
            all_results.extend(results)
            log(f"  {len(all_results):,} records...")

            if len(results) < limit:
                break
            skip += limit
            time.sleep(0.3)
        except Exception as e:
            log(f"  Error: {e}")
            break

    return all_results


# =============================================================================
# FOODSCORE
# =============================================================================

def download_and_process_foodscore():
    """Download and integrate FoodScore data sources."""
    log("=" * 60)
    log("FOODSCORE DATA SOURCES")
    log("=" * 60)

    raw_dir = DATA_RAW / "foodscore"
    proc_dir = DATA_PROCESSED / "foodscore"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. FDA Food Recalls API
    # -------------------------------------------------------------------------
    log("\n[1/3] FDA FOOD RECALLS")

    recalls = fetch_api(
        "https://api.fda.gov/food/enforcement.json",
        params={"search": "status:Ongoing OR status:Completed"},
        desc="FDA Food Recalls"
    )

    if recalls:
        df_recalls = pd.DataFrame(recalls)

        # Select and clean columns
        cols = ['recall_number', 'product_description', 'reason_for_recall',
                'classification', 'recalling_firm', 'distribution_pattern',
                'recall_initiation_date', 'state', 'status', 'city',
                'voluntary_mandated', 'product_type']
        cols = [c for c in cols if c in df_recalls.columns]
        df_recalls = df_recalls[cols]

        # Add severity score (Class I = 3, Class II = 2, Class III = 1)
        severity_map = {'Class I': 3, 'Class II': 2, 'Class III': 1}
        df_recalls['severity_score'] = df_recalls['classification'].map(severity_map).fillna(0)

        # Save
        out_path = proc_dir / "fda_recalls.parquet"
        df_recalls.to_parquet(out_path, index=False)
        log(f"  Saved: {out_path} ({len(df_recalls):,} recalls)")

        # Stats
        log(f"  Class I (serious): {(df_recalls['classification'] == 'Class I').sum():,}")
        log(f"  Class II (moderate): {(df_recalls['classification'] == 'Class II').sum():,}")
        log(f"  Class III (minor): {(df_recalls['classification'] == 'Class III').sum():,}")

    # -------------------------------------------------------------------------
    # 2. openFDA Food Enforcement (Bulk Download - includes import refusals)
    # -------------------------------------------------------------------------
    log("\n[2/3] openFDA FOOD ENFORCEMENT (BULK)")

    enforcement_dir = raw_dir / "openfda_enforcement"
    enforcement_dir.mkdir(exist_ok=True)

    # openFDA bulk download (JSON format - no API key required)
    # Data from FDA Recall Enterprise System (RES), 2004-present, updated weekly
    openfda_url = "https://download.open.fda.gov/food/enforcement/food-enforcement-0001-of-0001.json.zip"
    enforcement_zip = enforcement_dir / "food-enforcement.json.zip"

    if download_file(openfda_url, enforcement_zip, "openFDA Food Enforcement Bulk"):
        try:
            # Extract and process JSON
            with zipfile.ZipFile(enforcement_zip, 'r') as zf:
                json_files = [f for f in zf.namelist() if f.endswith('.json')]
                if json_files:
                    with zf.open(json_files[0]) as jf:
                        data = json.load(jf)

            # Parse results
            results = data.get('results', [])
            if results:
                df_enforcement = pd.DataFrame(results)
                log(f"  Loaded: {len(df_enforcement):,} enforcement records")

                # Select key columns
                cols = ['recall_number', 'product_description', 'reason_for_recall',
                        'classification', 'recalling_firm', 'distribution_pattern',
                        'recall_initiation_date', 'state', 'status', 'city',
                        'voluntary_mandated', 'product_type', 'country']
                cols = [c for c in cols if c in df_enforcement.columns]
                df_enforcement = df_enforcement[cols]

                out_path = proc_dir / "openfda_food_enforcement.parquet"
                df_enforcement.to_parquet(out_path, index=False)
                log(f"  Saved: {out_path} ({len(df_enforcement):,} records)")

                # Stats by classification
                if 'classification' in df_enforcement.columns:
                    for cls in ['Class I', 'Class II', 'Class III']:
                        count = (df_enforcement['classification'] == cls).sum()
                        log(f"  {cls}: {count:,}")
        except Exception as e:
            log(f"  Error processing: {e}")
    else:
        log("  openFDA bulk download failed")
        log("  Manual: https://open.fda.gov/apis/food/enforcement/download/")

    # -------------------------------------------------------------------------
    # 3. USDA Branded Foods (large file - skip if exists)
    # -------------------------------------------------------------------------
    log("\n[3/3] USDA BRANDED FOODS")

    usda_dir = raw_dir / "usda_branded"
    usda_dir.mkdir(exist_ok=True)

    # Check if already downloaded
    existing_usda = list(usda_dir.glob("*.csv"))
    if existing_usda:
        log(f"  Already downloaded: {len(existing_usda)} files")
    else:
        log("  USDA Branded Foods requires manual download:")
        log("  1. Go to: https://fdc.nal.usda.gov/download-datasets.html")
        log("  2. Download 'Branded Foods' CSV (~2.5 GB)")
        log("  3. Extract to: data/raw/foodscore/usda_branded/")

    # Process if available
    for csv_file in usda_dir.glob("**/branded_food.csv"):
        log(f"  Processing: {csv_file.name}")

        # Read in chunks due to size
        chunks = []
        for chunk in pd.read_csv(csv_file, chunksize=100000, low_memory=False, dtype=str):
            # Select key columns
            cols = ['fdc_id', 'brand_owner', 'brand_name', 'subbrand_name',
                    'gtin_upc', 'ingredients', 'serving_size', 'serving_size_unit',
                    'branded_food_category']
            cols = [c for c in cols if c in chunk.columns]
            chunks.append(chunk[cols])

        if chunks:
            df_usda = pd.concat(chunks, ignore_index=True)
            # Convert numeric columns
            for col in ['fdc_id', 'serving_size']:
                if col in df_usda.columns:
                    df_usda[col] = pd.to_numeric(df_usda[col], errors='coerce')
            out_path = proc_dir / "usda_branded_foods.parquet"
            df_usda.to_parquet(out_path, index=False)
            log(f"  Saved: {out_path} ({len(df_usda):,} products)")
        break

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    log("\nFOODSCORE PROCESSED FILES:")
    for f in proc_dir.glob("*.parquet"):
        size = f.stat().st_size / 1024 / 1024
        df = pd.read_parquet(f)
        log(f"  {f.name}: {len(df):,} rows ({size:.1f} MB)")


# =============================================================================
# DRUGWATCH
# =============================================================================

def download_and_process_drugwatch():
    """Download and integrate DrugWatch data sources."""
    log("=" * 60)
    log("DRUGWATCH DATA SOURCES")
    log("=" * 60)

    raw_dir = DATA_RAW / "drugwatch"
    proc_dir = DATA_PROCESSED / "drugwatch"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Load existing US drugs for merging
    us_drugs_path = proc_dir / "us_drugs.parquet"
    if us_drugs_path.exists():
        df_us = pd.read_parquet(us_drugs_path)
        log(f"Existing US drugs: {len(df_us):,}")
    else:
        df_us = pd.DataFrame()

    # -------------------------------------------------------------------------
    # 1. Medicaid NADAC (National Average Drug Acquisition Cost)
    # -------------------------------------------------------------------------
    log("\n[1/2] MEDICAID NADAC PRICES")

    nadac_dir = raw_dir / "nadac"
    nadac_dir.mkdir(exist_ok=True)

    # Try multiple NADAC download URLs (2025 dataset)
    nadac_urls = [
        "https://data.medicaid.gov/api/1/datastore/query/f38d0706-1239-442c-a3cc-40ef1b686ac0/0/download?format=csv",
        "https://data.medicaid.gov/api/1/datastore/query/99315a95-37ac-4eee-946a-3c523b4c481e/0/download?format=csv",
    ]
    nadac_file = nadac_dir / "nadac.csv"
    downloaded = False

    for url in nadac_urls:
        if download_file(url, nadac_file, "NADAC Drug Prices", timeout=600):
            downloaded = True
            break

    if downloaded and nadac_file.exists():
        df_nadac = pd.read_csv(nadac_file, low_memory=False)
        log(f"  Loaded: {len(df_nadac):,} records")
        log(f"  Columns: {df_nadac.columns.tolist()[:6]}")

        # Rename columns (handle different column name formats)
        col_map = {
            'ndc_description': 'drug_name',
            'NDC Description': 'drug_name',
            'ndc': 'ndc',
            'NDC': 'ndc',
            'nadac_per_unit': 'nadac_price',
            'NADAC_Per_Unit': 'nadac_price',
            'effective_date': 'effective_date',
            'Effective_Date': 'effective_date',
            'pricing_unit': 'unit',
            'Pricing_Unit': 'unit',
        }
        df_nadac = df_nadac.rename(columns={k: v for k, v in col_map.items() if k in df_nadac.columns})

        # Get latest price per drug
        if 'effective_date' in df_nadac.columns:
            df_nadac['effective_date'] = pd.to_datetime(df_nadac['effective_date'], errors='coerce')
            df_nadac = df_nadac.sort_values('effective_date', ascending=False)
            if 'ndc' in df_nadac.columns:
                df_nadac = df_nadac.drop_duplicates(subset=['ndc'], keep='first')

        out_path = proc_dir / "nadac_prices.parquet"
        df_nadac.to_parquet(out_path, index=False)
        log(f"  Saved: {out_path} ({len(df_nadac):,} drugs)")
    else:
        log("  NADAC download failed")
        log("  Manual: https://data.medicaid.gov/dataset/f38d0706-1239-442c-a3cc-40ef1b686ac0")

    # -------------------------------------------------------------------------
    # 2. VA National Formulary & Drug Data (from VA PBM - Pharmacy Benefits)
    # Note: data.va.gov endpoints are broken, but PBM provides direct downloads
    # -------------------------------------------------------------------------
    log("\n[2/2] VA NATIONAL FORMULARY & DRUG DATA")

    va_dir = raw_dir / "va_formulary"
    va_dir.mkdir(exist_ok=True)

    # VA PBM direct download links (these work!)
    va_sources = [
        ("https://www.pbm.va.gov/PBM/nationalformulary/PharmacyProductSystem_NationalDrugCodeExtract.csv",
         "va_ndc_extract.csv", "VA NDC Drug Extract"),
        ("https://www.pbm.va.gov/PBM/nationalformulary/PPSN_Active_Products_Current_Copay_Tier.csv",
         "va_active_products.csv", "VA Active Products with Copay"),
    ]

    all_va_dfs = []
    for url, filename, desc in va_sources:
        va_file = va_dir / filename
        if download_file(url, va_file, desc):
            try:
                df_va = pd.read_csv(va_file, low_memory=False, dtype=str, encoding='latin-1')
                log(f"  Loaded: {len(df_va):,} records from {filename}")
                all_va_dfs.append(df_va)
            except Exception as e:
                log(f"  Error reading {filename}: {e}")

    if all_va_dfs:
        # Save the main NDC extract (usually the first and largest)
        df_main = all_va_dfs[0]
        log(f"  Columns: {df_main.columns.tolist()[:6]}")

        out_path = proc_dir / "va_drug_data.parquet"
        df_main.to_parquet(out_path, index=False)
        log(f"  Saved: {out_path} ({len(df_main):,} drugs)")
    else:
        log("  VA data download failed")
        log("  Manual: https://www.pbm.va.gov/nationalformulary.asp")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    log("\nDRUGWATCH PROCESSED FILES:")
    for f in proc_dir.glob("*.parquet"):
        size = f.stat().st_size / 1024 / 1024
        df = pd.read_parquet(f)
        log(f"  {f.name}: {len(df):,} rows ({size:.1f} MB)")


# =============================================================================
# RURALACCESS
# =============================================================================

def download_and_process_ruralaccess():
    """Download and integrate RuralAccess data sources."""
    log("=" * 60)
    log("RURALACCESS DATA SOURCES")
    log("=" * 60)

    raw_dir = DATA_RAW / "ruralaccess"
    proc_dir = DATA_PROCESSED / "ruralaccess"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. FQHC Health Center Locations
    # -------------------------------------------------------------------------
    log("\n[1/3] FQHC HEALTH CENTERS")

    fqhc_dir = raw_dir / "fqhc"
    fqhc_dir.mkdir(exist_ok=True)

    # Note: URL uses "LookAlike" not "Look-Alike"
    fqhc_urls = [
        "https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv",
        "https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_Sites.csv",
    ]
    fqhc_file = fqhc_dir / "fqhc_sites.csv"
    downloaded = False

    for fqhc_url in fqhc_urls:
        if download_file(fqhc_url, fqhc_file, "FQHC Health Centers"):
            downloaded = True
            break

    if not downloaded:
        log("  FQHC download failed")
        log("  Manual: https://data.hrsa.gov/data/download")

    if fqhc_file.exists():
        df_fqhc = pd.read_csv(fqhc_file, low_memory=False)
        log(f"  Loaded: {len(df_fqhc):,} sites")

        # Select key columns
        col_map = {
            'Health Center Name': 'health_center_name',
            'Site Name': 'site_name',
            'Site Address': 'address',
            'Site City': 'city',
            'Site State Abbreviation': 'state',
            'Site Postal Code': 'zip_code',
            'Site Telephone Number': 'phone',
            'Health Center Type': 'center_type',
            'Geocoding Artifact Address Primary X Coordinate': 'longitude',
            'Geocoding Artifact Address Primary Y Coordinate': 'latitude'
        }

        cols = [c for c in col_map.keys() if c in df_fqhc.columns]
        df_fqhc = df_fqhc[cols].rename(columns=col_map)

        # Save
        out_path = proc_dir / "fqhc_locations.parquet"
        df_fqhc.to_parquet(out_path, index=False)
        log(f"  Saved: {out_path} ({len(df_fqhc):,} centers)")
        log(f"  States covered: {df_fqhc['state'].nunique()}")

    # -------------------------------------------------------------------------
    # 2. Rural Hospital Closures
    # -------------------------------------------------------------------------
    log("\n[2/3] RURAL HOSPITAL CLOSURES")

    closures_dir = raw_dir / "hospital_closures"
    closures_dir.mkdir(exist_ok=True)

    # UNC Sheps Center tracks rural hospital closures
    closure_urls = [
        "https://www.shepscenter.unc.edu/download/11619/",
        "https://www.shepscenter.unc.edu/wp-content/uploads/2025/01/Rural-Hospital-Closures-January-2025.xlsx",
        "https://www.shepscenter.unc.edu/wp-content/uploads/2024/12/Rural-Hospital-Closures-December-2024.xlsx",
    ]

    closures_file = closures_dir / "rural_closures.xlsx"
    downloaded = False

    for url in closure_urls:
        if download_file(url, closures_file, "Rural Hospital Closures"):
            downloaded = True
            break

    if downloaded and closures_file.exists():
        try:
            # Read with dtype=str to avoid mixed type errors
            df_closures = pd.read_excel(closures_file, engine='openpyxl', dtype=str)
            log(f"  Loaded: {len(df_closures):,} closures")

            # Convert date columns after reading
            for col in df_closures.columns:
                if 'date' in col.lower() or 'year' in col.lower():
                    df_closures[col] = pd.to_datetime(df_closures[col], errors='coerce')

            out_path = proc_dir / "rural_hospital_closures.parquet"
            df_closures.to_parquet(out_path, index=False)
            log(f"  Saved: {out_path}")

            # Stats
            if 'State' in df_closures.columns:
                log(f"  States with closures: {df_closures['State'].nunique()}")
        except Exception as e:
            log(f"  Error: {e}")
    else:
        log("  Download failed - manual download required:")
        log("  https://www.shepscenter.unc.edu/programs-projects/rural-health/rural-hospital-closures/")

    # -------------------------------------------------------------------------
    # 3. CMS Hospital Quality Data
    # -------------------------------------------------------------------------
    log("\n[3/3] CMS HOSPITAL QUALITY")

    quality_dir = raw_dir / "hospital_quality"
    quality_dir.mkdir(exist_ok=True)

    # CMS Hospital General Information with star ratings
    quality_url = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv"
    quality_file = quality_dir / "hospital_quality.csv"

    if download_file(quality_url, quality_file, "CMS Hospital Quality"):
        df_quality = pd.read_csv(quality_file, low_memory=False)
        log(f"  Loaded: {len(df_quality):,} hospitals")

        # Save as parquet
        out_path = proc_dir / "hospital_quality.parquet"
        df_quality.to_parquet(out_path, index=False)
        log(f"  Saved: {out_path}")

        # Stats
        if 'Hospital overall rating' in df_quality.columns:
            ratings = df_quality['Hospital overall rating'].value_counts().sort_index()
            log("  Star ratings distribution:")
            for rating, count in ratings.items():
                log(f"    {rating} star: {count:,}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    log("\nRURALACCESS PROCESSED FILES:")
    for f in proc_dir.glob("*.parquet"):
        size = f.stat().st_size / 1024 / 1024
        df = pd.read_parquet(f)
        log(f"  {f.name}: {len(df):,} rows ({size:.1f} MB)")


# =============================================================================
# MAIN
# =============================================================================

def print_summary():
    """Print summary of all processed data."""
    log("\n" + "=" * 60)
    log("PROCESSED DATA SUMMARY")
    log("=" * 60)

    total_size = 0
    total_records = 0

    for module in ["foodscore", "drugwatch", "ruralaccess"]:
        log(f"\n{module.upper()}:")
        module_dir = DATA_PROCESSED / module

        if module_dir.exists():
            for f in sorted(module_dir.glob("*.parquet")):
                size = f.stat().st_size / 1024 / 1024
                df = pd.read_parquet(f)
                log(f"  {f.name}: {len(df):,} rows ({size:.1f} MB)")
                total_size += size
                total_records += len(df)

    log(f"\nTOTAL: {total_records:,} records, {total_size:.1f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and process HealthGuard data")
    parser.add_argument("--all", action="store_true", help="Download and process all")
    parser.add_argument("--foodscore", action="store_true", help="FoodScore data only")
    parser.add_argument("--drugwatch", action="store_true", help="DrugWatch data only")
    parser.add_argument("--ruralaccess", action="store_true", help="RuralAccess data only")
    parser.add_argument("--summary", action="store_true", help="Print summary only")

    args = parser.parse_args()

    if args.summary:
        print_summary()
    elif args.all:
        download_and_process_foodscore()
        download_and_process_drugwatch()
        download_and_process_ruralaccess()
        print_summary()
    elif args.foodscore:
        download_and_process_foodscore()
    elif args.drugwatch:
        download_and_process_drugwatch()
    elif args.ruralaccess:
        download_and_process_ruralaccess()
    else:
        parser.print_help()
        print("\nRun: python scripts/download_new_data.py --all")
