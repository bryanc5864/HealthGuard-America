#!/usr/bin/env python3
"""
HealthGuard America - Data Download Script

This script downloads raw data from public sources for all four modules:
- PriceVision: Hospital price transparency MRF files
- DrugWatch: Drug pricing data (US, Australia, Canada)
- FoodScore: OpenFoodFacts product database
- RuralAccess: HRSA healthcare shortage data

Usage:
    python download_data.py --all              # Download all data
    python download_data.py --pricevision      # Download only PriceVision
    python download_data.py --drugwatch        # Download only DrugWatch
    python download_data.py --foodscore        # Download only FoodScore
    python download_data.py --ruralaccess      # Download only RuralAccess

Requirements:
    pip install requests tqdm pandas
"""

import os
import sys
import json
import gzip
import shutil
import argparse
import zipfile
from pathlib import Path
from datetime import datetime

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Installing required packages...")
    os.system("pip install requests tqdm")
    import requests
    from tqdm import tqdm

# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"

# Ensure directories exist
for module in ["pricevision", "drugwatch", "foodscore", "ruralaccess"]:
    (DATA_RAW / module).mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest_path: Path, desc: str = None) -> bool:
    """Download a file with progress bar."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc or dest_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def download_drugwatch():
    """Download DrugWatch data from public sources."""
    print("\n" + "=" * 60)
    print("DOWNLOADING DRUGWATCH DATA")
    print("=" * 60)

    drugwatch_dir = DATA_RAW / "drugwatch"
    drugwatch_dir.mkdir(parents=True, exist_ok=True)

    # US Medicare Part D Data
    print("\n[1/3] US Medicare Part D Spending Data...")
    us_dir = drugwatch_dir / "us" / "part_d"
    us_dir.mkdir(parents=True, exist_ok=True)

    # CMS Medicare Part D Spending by Drug
    # Note: This URL may need to be updated for the latest year
    cms_url = "https://data.cms.gov/sites/default/files/2024-09/3030d74f-cf29-4c71-a8db-e9f0adb6d7fb/MUP_DPR_RY25_P04_V10_DY23_NBR.csv"
    cms_path = us_dir / "DSD_PTD_RY25_P04_V10_DY23_BGM.csv"

    if not cms_path.exists():
        print("  Downloading from CMS (this may take a few minutes)...")
        # Try alternative approach - direct download or API
        alt_url = "https://data.cms.gov/data-api/v1/dataset/3030d74f-cf29-4c71-a8db-e9f0adb6d7fb/data.csv"
        if not download_file(alt_url, cms_path, "Medicare Part D"):
            print("  Note: CMS data may require manual download from:")
            print("  https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug")
    else:
        print(f"  Already exists: {cms_path.name}")

    # Australia PBS Data
    print("\n[2/3] Australia PBS Data...")
    aus_dir = drugwatch_dir / "australia" / "pbs"
    aus_dir.mkdir(parents=True, exist_ok=True)

    pbs_url = "https://www.pbs.gov.au/downloads/drug-list.zip"
    pbs_zip = aus_dir / "pbs_data.zip"

    if not (aus_dir / "tables_as_csv").exists():
        print("  Downloading from PBS...")
        if download_file(pbs_url, pbs_zip, "PBS Data"):
            print("  Extracting...")
            with zipfile.ZipFile(pbs_zip, 'r') as zf:
                zf.extractall(aus_dir)
            pbs_zip.unlink()
        else:
            print("  Note: PBS data may require manual download from:")
            print("  https://www.pbs.gov.au/info/browse/download")
    else:
        print("  Already exists")

    # Canada Drug Product Database
    print("\n[3/3] Canada Drug Product Database...")
    can_dir = drugwatch_dir / "canada"
    can_dir.mkdir(parents=True, exist_ok=True)

    # Health Canada API
    can_url = "https://health-products.canada.ca/api/drug/drugproduct/?lang=en&type=json"
    can_path = can_dir / "drug_products.json"

    if not can_path.exists():
        print("  Downloading from Health Canada API...")
        try:
            response = requests.get(can_url, timeout=60)
            response.raise_for_status()
            with open(can_path, 'w', encoding='utf-8') as f:
                json.dump(response.json(), f)
            print(f"  Saved: {can_path.name}")
        except Exception as e:
            print(f"  Error: {e}")
            print("  Note: Canada data may require manual download from:")
            print("  https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database.html")
    else:
        print(f"  Already exists: {can_path.name}")

    print("\nDrugWatch download complete!")


def download_foodscore():
    """Download FoodScore data from OpenFoodFacts."""
    print("\n" + "=" * 60)
    print("DOWNLOADING FOODSCORE DATA")
    print("=" * 60)

    foodscore_dir = DATA_RAW / "foodscore"
    foodscore_dir.mkdir(parents=True, exist_ok=True)

    # OpenFoodFacts US extract
    print("\n[1/2] OpenFoodFacts US Products Database...")
    off_url = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
    off_path = foodscore_dir / "openfoodfacts_us.csv.gz"

    if not off_path.exists():
        print("  Downloading from OpenFoodFacts (this is a large file ~6GB compressed)...")
        print("  Note: This download may take 30+ minutes depending on connection speed.")
        if not download_file(off_url, off_path, "OpenFoodFacts"):
            print("  Alternative: Download manually from:")
            print("  https://world.openfoodfacts.org/data")
    else:
        print(f"  Already exists: {off_path.name}")

    # Additive risks database (custom)
    print("\n[2/2] Additive Risk Database...")
    additive_path = foodscore_dir / "additive_risks.csv"

    if not additive_path.exists():
        print("  Creating additive risk database...")
        # Create a basic additive risk database
        additives_data = """name,type,risk_score,fda_status,eu_status,is_artificial,aliases
red 40,color,80,approved,approved,true,allura red|e129|fd&c red 40
yellow 5,color,70,approved,approved,true,tartrazine|e102|fd&c yellow 5
yellow 6,color,70,approved,approved,true,sunset yellow|e110|fd&c yellow 6
blue 1,color,50,approved,approved,true,brilliant blue|e133|fd&c blue 1
blue 2,color,50,approved,approved,true,indigo carmine|e132|fd&c blue 2
aspartame,sweetener,60,approved,approved,true,e951|equal|nutrasweet
sucralose,sweetener,40,approved,approved,true,e955|splenda
saccharin,sweetener,50,approved,approved,true,e954|sweet'n low
acesulfame potassium,sweetener,50,approved,approved,true,ace-k|e950
high fructose corn syrup,sweetener,70,approved,approved,false,hfcs|corn sugar
sodium nitrite,preservative,85,approved,approved,false,e250
sodium nitrate,preservative,80,approved,approved,false,e251
bha,preservative,75,approved,restricted,true,butylated hydroxyanisole|e320
bht,preservative,70,approved,restricted,true,butylated hydroxytoluene|e321
tbhq,preservative,65,approved,approved,true,e319
propyl gallate,preservative,60,approved,approved,true,e310
sodium benzoate,preservative,55,approved,approved,false,e211
potassium sorbate,preservative,30,approved,approved,false,e202
msg,flavor,40,approved,approved,false,monosodium glutamate|e621
carrageenan,thickener,50,approved,approved,false,e407
polysorbate 80,emulsifier,45,approved,approved,true,e433
titanium dioxide,color,60,approved,banned,true,e171
caramel color,color,55,approved,approved,false,e150|caramel coloring
partially hydrogenated oil,fat,95,banned,banned,false,trans fat|pho
brominated vegetable oil,emulsifier,90,restricted,banned,true,bvo
potassium bromate,flour,85,restricted,banned,false,e924
azodicarbonamide,flour,70,approved,banned,true,e927a|ada"""

        with open(additive_path, 'w') as f:
            f.write(additives_data)
        print(f"  Created: {additive_path.name}")
    else:
        print(f"  Already exists: {additive_path.name}")

    print("\nFoodScore download complete!")


def download_ruralaccess():
    """Download RuralAccess data from HRSA."""
    print("\n" + "=" * 60)
    print("DOWNLOADING RURALACCESS DATA")
    print("=" * 60)

    rural_dir = DATA_RAW / "ruralaccess"
    rural_dir.mkdir(parents=True, exist_ok=True)

    # HRSA HPSA Data
    print("\n[1/2] HRSA Health Professional Shortage Areas (HPSA)...")
    hpsa_url = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
    hpsa_path = rural_dir / "hrsa_hpsa.csv"

    if not hpsa_path.exists():
        print("  Downloading from HRSA...")
        if not download_file(hpsa_url, hpsa_path, "HPSA Data"):
            # Try alternative URL
            alt_url = "https://data.hrsa.gov/data/download?data=hpsa"
            print("  Trying alternative source...")
            print("  Note: HPSA data may require manual download from:")
            print("  https://data.hrsa.gov/topics/health-workforce/shortage-areas")
    else:
        print(f"  Already exists: {hpsa_path.name}")

    # County Population Data (Census)
    print("\n[2/2] County Population Data...")
    pop_path = rural_dir / "county_population.json"

    if not pop_path.exists():
        print("  Fetching from Census API...")
        census_url = "https://api.census.gov/data/2023/pep/population?get=NAME,POP_2023&for=county:*"
        try:
            response = requests.get(census_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Convert to dict format
            pop_data = []
            headers = data[0]
            for row in data[1:]:
                pop_data.append(dict(zip(headers, row)))
            with open(pop_path, 'w') as f:
                json.dump(pop_data, f)
            print(f"  Saved: {pop_path.name}")
        except Exception as e:
            print(f"  Error: {e}")
            print("  Note: Census data may require manual download or API key")
    else:
        print(f"  Already exists: {pop_path.name}")

    print("\nRuralAccess download complete!")


def download_pricevision():
    """Download/setup PriceVision hospital MRF data."""
    print("\n" + "=" * 60)
    print("DOWNLOADING PRICEVISION DATA")
    print("=" * 60)

    pricevision_dir = DATA_RAW / "pricevision"
    mrfs_dir = pricevision_dir / "mrfs"
    pricevision_dir.mkdir(parents=True, exist_ok=True)
    mrfs_dir.mkdir(parents=True, exist_ok=True)

    print("""
    Hospital Machine-Readable Files (MRFs) require special handling.

    Due to the decentralized nature of hospital price transparency data,
    MRF files must be downloaded from one of these sources:

    OPTION 1: DoltHub Hospital Price Transparency Dataset (Recommended)
    ---------------------------------------------------------------
    - URL: https://www.dolthub.com/repositories/dolthub/hospital-price-transparency
    - Contains aggregated MRF files from 6,000+ hospitals
    - Free to download with Dolt CLI

    Commands:
        pip install dolt
        dolt clone dolthub/hospital-price-transparency
        # Copy CSV files to data/raw/pricevision/mrfs/

    OPTION 2: Turquoise Health
    --------------------------
    - URL: https://turquoise.health/
    - Commercial API with free tier available
    - Pre-processed and normalized data

    OPTION 3: CMS Hospital Price Transparency Data
    ----------------------------------------------
    - URL: https://data.cms.gov/provider-compliance
    - List of hospital MRF file URLs
    - Requires scraping individual hospital websites

    OPTION 4: Manual Collection
    ---------------------------
    - Visit individual hospital websites
    - Search for "price transparency" or "machine readable file"
    - Download CSV/JSON files to data/raw/pricevision/mrfs/

    File Naming Convention:
        {hospital_npi}_{hash}.{csv|json|xlsx}
        Example: 010018_b712a435.csv
    """)

    # Download hospital general info from CMS
    print("\nDownloading Hospital General Information...")
    hospital_info_url = "https://data.cms.gov/provider-data/sites/default/files/resources/092256becd267d9eeccf73bf7d16c46b_1704412913/Hospital_General_Information.csv"
    hospital_info_path = pricevision_dir / "hospital_general_info.csv"

    if not hospital_info_path.exists():
        if not download_file(hospital_info_url, hospital_info_path, "Hospital Info"):
            print("  Note: Hospital info available at:")
            print("  https://data.cms.gov/provider-data/dataset/xubh-q36u")
    else:
        print(f"  Already exists: {hospital_info_path.name}")

    # Check if MRF files exist
    existing_mrfs = list(mrfs_dir.glob("*.*"))
    if existing_mrfs:
        print(f"\nFound {len(existing_mrfs)} existing MRF files in {mrfs_dir}")
    else:
        print(f"\nNo MRF files found. Please download using one of the options above.")

    print("\nPriceVision setup complete!")


def main():
    parser = argparse.ArgumentParser(
        description='HealthGuard America - Data Download Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python download_data.py --all           # Download everything
    python download_data.py --drugwatch     # Just drug pricing data
    python download_data.py --foodscore     # Just food product data
        """
    )
    parser.add_argument('--all', action='store_true', help='Download all datasets')
    parser.add_argument('--pricevision', action='store_true', help='Setup PriceVision data')
    parser.add_argument('--drugwatch', action='store_true', help='Download DrugWatch data')
    parser.add_argument('--foodscore', action='store_true', help='Download FoodScore data')
    parser.add_argument('--ruralaccess', action='store_true', help='Download RuralAccess data')

    args = parser.parse_args()

    # Default to all if no specific option
    if not any([args.all, args.pricevision, args.drugwatch, args.foodscore, args.ruralaccess]):
        args.all = True

    print("=" * 60)
    print("HEALTHGUARD AMERICA - DATA DOWNLOAD")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Directory: {DATA_RAW}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.all or args.drugwatch:
        download_drugwatch()

    if args.all or args.foodscore:
        download_foodscore()

    if args.all or args.ruralaccess:
        download_ruralaccess()

    if args.all or args.pricevision:
        download_pricevision()

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"\nNext step: Run the data processing script:")
    print(f"  python scripts/process_data.py --all")


if __name__ == "__main__":
    main()
