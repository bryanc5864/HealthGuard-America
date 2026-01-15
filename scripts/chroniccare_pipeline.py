#!/usr/bin/env python3
"""
ChronicCare Data Pipeline - Download and Preprocessing

Downloads and processes data from:
1. CDC PLACES - County-level chronic disease prevalence
2. CMS Geographic Variation - Medicare spending by county
3. USDA Food Environment Atlas - Food access metrics

Usage:
    python scripts/chroniccare_pipeline.py --download      # Download raw data only
    python scripts/chroniccare_pipeline.py --process       # Process existing data only
    python scripts/chroniccare_pipeline.py --all           # Download and process (default)

Output:
    data/raw/chroniccare/          - Raw downloaded files
    data/processed/chroniccare/    - Processed parquet files
"""

import os
import sys
import json
import logging
import argparse
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

try:
    import requests
    import pandas as pd
    from tqdm import tqdm
except ImportError:
    print("Installing required packages...")
    os.system("pip install requests pandas tqdm pyarrow openpyxl")
    import requests
    import pandas as pd
    from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chroniccare_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "chroniccare"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed" / "chroniccare"

# Ensure directories exist
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA SOURCE URLs
# =============================================================================

DATA_SOURCES = {
    "cdc_places": {
        "name": "CDC PLACES County Data",
        "description": "County-level chronic disease prevalence estimates",
        # PLACES 2023 Release - County Level Data
        "url": "https://data.cdc.gov/api/views/swc5-untb/rows.csv?accessType=DOWNLOAD",
        "backup_url": "https://chronicdata.cdc.gov/api/views/swc5-untb/rows.csv?accessType=DOWNLOAD",
        "filename": "cdc_places_county_2023.csv",
        "records_expected": "~3,200 counties",
    },
    "cms_geographic": {
        "name": "CMS Medicare Geographic Variation",
        "description": "Medicare spending and utilization by county",
        # CMS County Health Data - using County Health Rankings as alternative
        # Original CMS data requires JavaScript portal access
        "url": "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2024.csv",
        "backup_url": "https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation",
        "filename": "county_health_rankings_2024.csv",
        "records_expected": "~3,200 counties",
        "note": "Using County Health Rankings as proxy - includes Medicare data and health outcomes",
    },
    "usda_food_atlas": {
        "name": "USDA Food Environment Atlas",
        "description": "Food access, stores, restaurants, and food assistance by county",
        # Updated URL - July 2025 version
        "url": "https://www.ers.usda.gov/media/5569/food-environment-atlas-data-download.xlsx",
        "backup_url": "https://www.ers.usda.gov/media/5570/food-environment-atlas-csv-files.zip",
        "filename": "food_environment_atlas.xlsx",
        "records_expected": "~3,200 counties",
    },
}


# =============================================================================
# DOWNLOAD FUNCTIONS
# =============================================================================

def download_file(url: str, dest_path: Path, desc: str = None, timeout: int = 120) -> bool:
    """Download a file with progress bar."""
    try:
        logger.info(f"Downloading: {url}")
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc or dest_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        file_size = dest_path.stat().st_size
        logger.info(f"Downloaded: {dest_path.name} ({file_size:,} bytes)")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading {url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


def download_cdc_places() -> Tuple[bool, Optional[Path]]:
    """
    Download CDC PLACES county-level chronic disease data.

    Source: https://data.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-County-Data-20/swc5-untb
    """
    logger.info("=" * 60)
    logger.info("DOWNLOADING CDC PLACES DATA")
    logger.info("=" * 60)

    source = DATA_SOURCES["cdc_places"]
    dest_path = DATA_RAW / source["filename"]

    if dest_path.exists():
        logger.info(f"File already exists: {dest_path.name}")
        return True, dest_path

    # Try primary URL
    success = download_file(source["url"], dest_path, "CDC PLACES")

    if not success and source.get("backup_url"):
        logger.info("Trying backup URL...")
        success = download_file(source["backup_url"], dest_path, "CDC PLACES (backup)")

    if not success:
        logger.error("Failed to download CDC PLACES data.")
        logger.info("Manual download available at:")
        logger.info("  https://data.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-County-Data-20/swc5-untb")
        return False, None

    return True, dest_path


def download_cms_geographic() -> Tuple[bool, Optional[Path]]:
    """
    Download County Health Rankings data (includes Medicare-relevant health spending data).

    Note: CMS direct data requires JavaScript portal. Using County Health Rankings
    which provides similar county-level health and spending metrics.

    Source: https://www.countyhealthrankings.org/
    """
    logger.info("=" * 60)
    logger.info("DOWNLOADING COUNTY HEALTH RANKINGS DATA")
    logger.info("=" * 60)
    logger.info("(Alternative to CMS data which requires JavaScript portal)")

    source = DATA_SOURCES["cms_geographic"]
    dest_path = DATA_RAW / source["filename"]

    if dest_path.exists():
        logger.info(f"File already exists: {dest_path.name}")
        return True, dest_path

    success = download_file(source["url"], dest_path, "County Health Rankings", timeout=180)

    if not success:
        # Try previous year
        logger.info("Trying 2023 data...")
        alt_url = "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2023.csv"
        dest_path_2023 = DATA_RAW / "county_health_rankings_2023.csv"
        success = download_file(alt_url, dest_path_2023, "County Health Rankings 2023", timeout=180)

        if success:
            dest_path = dest_path_2023

    if not success:
        logger.error("Failed to download County Health Rankings data.")
        logger.info("Manual download available at:")
        logger.info("  https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation")
        logger.info("")
        logger.info("For CMS Medicare Geographic Variation data (requires browser):")
        logger.info("  https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county")
        return False, None

    return True, dest_path


def download_usda_food_atlas() -> Tuple[bool, Optional[Path]]:
    """
    Download USDA Food Environment Atlas.

    Source: https://www.ers.usda.gov/data-products/food-environment-atlas/
    """
    logger.info("=" * 60)
    logger.info("DOWNLOADING USDA FOOD ENVIRONMENT ATLAS")
    logger.info("=" * 60)

    source = DATA_SOURCES["usda_food_atlas"]
    dest_path = DATA_RAW / source["filename"]

    if dest_path.exists():
        logger.info(f"File already exists: {dest_path.name}")
        return True, dest_path

    # Try primary URL (xlsx)
    success = download_file(source["url"], dest_path, "USDA Food Atlas", timeout=180)

    if not success:
        # Try backup URL (zip of CSVs)
        logger.info("Trying backup URL (CSV zip)...")
        zip_path = DATA_RAW / "food_environment_atlas_csv.zip"
        success = download_file(source["backup_url"], zip_path, "USDA Food Atlas CSV", timeout=180)

        if success:
            # Extract the zip
            try:
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(DATA_RAW)
                logger.info("Extracted CSV files from zip")
                # Find the main data file
                csv_files = list(DATA_RAW.glob("*.csv"))
                if csv_files:
                    # Rename the first CSV to our expected name
                    dest_path = dest_path.with_suffix('.csv')
                    source["filename"] = dest_path.name
            except Exception as e:
                logger.error(f"Failed to extract zip: {e}")
                success = False

    if not success:
        logger.error("Failed to download USDA Food Environment Atlas.")
        logger.info("Manual download available at:")
        logger.info("  https://www.ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads/")
        return False, None

    return True, dest_path


def download_all() -> Dict[str, bool]:
    """Download all ChronicCare data sources."""
    results = {}

    results["cdc_places"], _ = download_cdc_places()
    results["cms_geographic"], _ = download_cms_geographic()
    results["usda_food_atlas"], _ = download_usda_food_atlas()

    return results


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def process_cdc_places() -> Optional[pd.DataFrame]:
    """
    Process CDC PLACES county data.

    Extracts key chronic disease prevalence measures and standardizes format.
    """
    logger.info("=" * 60)
    logger.info("PROCESSING CDC PLACES DATA")
    logger.info("=" * 60)

    source_file = DATA_RAW / DATA_SOURCES["cdc_places"]["filename"]

    if not source_file.exists():
        logger.error(f"Source file not found: {source_file}")
        return None

    logger.info(f"Reading: {source_file.name}")
    df = pd.read_csv(source_file, low_memory=False)
    logger.info(f"Loaded {len(df):,} rows")

    # CDC PLACES has one row per measure per location
    # We need to pivot to get one row per county with all measures as columns

    # Key measures we want (CDC PLACES measure IDs)
    measures_of_interest = {
        'DIABETES': 'diabetes_prevalence',
        'OBESITY': 'obesity_prevalence',
        'CHD': 'heart_disease_prevalence',  # Coronary Heart Disease
        'STROKE': 'stroke_prevalence',
        'BPHIGH': 'high_bp_prevalence',  # High Blood Pressure
        'HIGHCHOL': 'high_cholesterol_prevalence',
        'KIDNEY': 'kidney_disease_prevalence',
        'CANCER': 'cancer_prevalence',
        'COPD': 'copd_prevalence',
        'DEPRESSION': 'depression_prevalence',
        'LPA': 'physical_inactivity_prevalence',  # Lack of Physical Activity
        'CSMOKING': 'smoking_prevalence',  # Current Smoking
        'BINGE': 'binge_drinking_prevalence',
    }

    # Filter to county-level data and measures of interest
    # The column names may vary - check actual data
    logger.info(f"Columns in data: {df.columns.tolist()[:20]}...")

    # Try to identify key columns
    location_col = None
    measure_col = None
    value_col = None
    state_col = None
    county_col = None

    for col in df.columns:
        col_lower = col.lower()
        if 'locationid' in col_lower or 'countyfips' in col_lower or col_lower == 'fips':
            location_col = col
        elif 'measureid' in col_lower or 'measure' in col_lower == col_lower:
            measure_col = col
        elif 'data_value' in col_lower or 'value' in col_lower:
            value_col = col
        elif 'stateabbr' in col_lower or col_lower == 'state':
            state_col = col
        elif 'county' in col_lower and 'fips' not in col_lower:
            county_col = col

    # Handle different possible CDC PLACES formats
    if 'MeasureId' in df.columns or 'Measure' in df.columns:
        # Long format - need to pivot
        measure_col = 'MeasureId' if 'MeasureId' in df.columns else 'Measure'
        value_col = 'Data_Value' if 'Data_Value' in df.columns else 'DataValue'
        location_col = 'LocationID' if 'LocationID' in df.columns else 'CountyFIPS'

        if measure_col not in df.columns:
            logger.warning("Could not find measure column, trying alternative approach")
            # Check for Short_Question_Text which contains measure names
            if 'Short_Question_Text' in df.columns:
                measure_col = 'Short_Question_Text'

        logger.info(f"Using columns: location={location_col}, measure={measure_col}, value={value_col}")

        # Filter to county level (5-digit FIPS)
        if 'LocationType' in df.columns:
            df = df[df['LocationType'] == 'County'].copy()

        # Filter to measures of interest
        if measure_col in df.columns:
            available_measures = df[measure_col].unique()
            logger.info(f"Available measures (first 20): {list(available_measures)[:20]}")

            # Map actual measure names to our standard names
            measure_mapping = {}
            for m in available_measures:
                m_upper = str(m).upper()
                for key, val in measures_of_interest.items():
                    if key in m_upper or key.lower() in str(m).lower():
                        measure_mapping[m] = val
                        break

            logger.info(f"Mapped {len(measure_mapping)} measures")

            # Filter and rename
            df_filtered = df[df[measure_col].isin(measure_mapping.keys())].copy()
            df_filtered['measure_name'] = df_filtered[measure_col].map(measure_mapping)

            # Pivot to wide format
            pivot_cols = [location_col]
            if 'StateAbbr' in df.columns:
                pivot_cols.append('StateAbbr')
            if 'LocationName' in df.columns:
                pivot_cols.append('LocationName')

            df_wide = df_filtered.pivot_table(
                index=pivot_cols,
                columns='measure_name',
                values=value_col,
                aggfunc='first'
            ).reset_index()

            df = df_wide

    # Standardize column names
    rename_map = {
        'LocationID': 'fips',
        'CountyFIPS': 'fips',
        'StateAbbr': 'state_abbr',
        'LocationName': 'county_name',
        'TotalPopulation': 'total_population',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Ensure FIPS is string with leading zeros
    if 'fips' in df.columns:
        df['fips'] = df['fips'].astype(str).str.zfill(5)
        df['state_fips'] = df['fips'].str[:2]

    # Calculate chronic disease burden score (average of key conditions)
    disease_cols = ['diabetes_prevalence', 'obesity_prevalence', 'heart_disease_prevalence', 'high_bp_prevalence']
    available_disease_cols = [c for c in disease_cols if c in df.columns]
    if available_disease_cols:
        df['chronic_disease_burden_score'] = df[available_disease_cols].mean(axis=1)

    logger.info(f"Processed {len(df):,} counties")
    logger.info(f"Columns: {df.columns.tolist()}")

    # Save processed data
    output_path = DATA_PROCESSED / "cdc_places_county.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    # Also save CSV for inspection
    csv_path = DATA_PROCESSED / "cdc_places_county.csv"
    df.to_csv(csv_path, index=False)

    return df


def process_cms_geographic() -> Optional[pd.DataFrame]:
    """
    Process County Health Rankings data (alternative to CMS Medicare data).

    Extracts health outcomes, spending indicators, and quality metrics by county.
    County Health Rankings uses coded variable names (v001, v002, etc.)
    """
    logger.info("=" * 60)
    logger.info("PROCESSING COUNTY HEALTH RANKINGS DATA")
    logger.info("=" * 60)

    # Try to find the data file
    source_file = None
    for filename in ["county_health_rankings_2024.csv", "county_health_rankings_2023.csv"]:
        potential_file = DATA_RAW / filename
        if potential_file.exists():
            source_file = potential_file
            break

    if source_file is None:
        logger.error("No County Health Rankings file found")
        return None

    logger.info(f"Reading: {source_file.name}")

    try:
        df = pd.read_csv(source_file, low_memory=False, encoding='latin-1')
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return None

    logger.info(f"Loaded {len(df):,} rows")
    logger.info(f"Columns (first 30): {df.columns.tolist()[:30]}...")

    # County Health Rankings 2024 uses descriptive column names
    # Map the actual column names to our standard names

    # Core identifier columns - handle both formats
    core_rename = {
        'fipscode': 'fips',
        '5-digit FIPS Code': 'fips',
        'state': 'state_abbr',
        'State Abbreviation': 'state_abbr',
        'county': 'county_name',
        'Name': 'county_name',
        'Release Year': 'year',
    }

    # Variable mappings - use the descriptive "raw value" column names
    var_rename = {
        'Premature Death raw value': 'premature_death_rate',
        'Poor or Fair Health raw value': 'pct_fair_poor_health',
        'Poor Physical Health Days raw value': 'avg_physically_unhealthy_days',
        'Poor Mental Health Days raw value': 'avg_mentally_unhealthy_days',
        'Adult Obesity raw value': 'obesity_prevalence',
        'Physical Inactivity raw value': 'physical_inactivity_prevalence',
        'Excessive Drinking raw value': 'excessive_drinking_prevalence',
        'Adult Smoking raw value': 'smoking_prevalence',
        'Diabetes Prevalence raw value': 'diabetes_prevalence',
        'Uninsured raw value': 'pct_uninsured',
        'Primary Care Physicians raw value': 'pcp_rate',
        'Preventable Hospital Stays raw value': 'preventable_hospitalizations',
        'High School Graduation raw value': 'high_school_graduation_rate',
        'Some College raw value': 'pct_some_college',
        'Median Household Income raw value': 'median_household_income',
        'Children in Poverty raw value': 'child_poverty_rate',
        'Food Insecurity raw value': 'food_insecurity_rate',
        'Limited Access to Healthy Foods raw value': 'pct_limited_food_access',
        'Insufficient Sleep raw value': 'pct_insufficient_sleep',
        'Low Birthweight raw value': 'pct_low_birthweight',
        'Teen Births raw value': 'teen_birth_rate',
        'Mental Health Providers raw value': 'mental_health_provider_rate',
        'Food Environment Index raw value': 'food_environment_index',
        'Access to Exercise Opportunities raw value': 'pct_access_exercise',
        'Income Inequality raw value': 'income_inequality_ratio',
        'Social Associations raw value': 'social_association_rate',
        'Severe Housing Problems raw value': 'pct_severe_housing_problems',
        '% 65 and older raw value': 'pct_65_and_older',
        '% below 18 years of age raw value': 'pct_under_18',
        '% Rural raw value': 'pct_rural',
    }

    # Apply core renames first
    df = df.rename(columns=core_rename)

    # Apply variable renames for columns that exist
    existing_var_cols = {k: v for k, v in var_rename.items() if k in df.columns}
    df = df.rename(columns=existing_var_cols)
    logger.info(f"Mapped {len(existing_var_cols)} health measures")

    # Keep only the columns we renamed plus a few extras
    keep_cols = ['fips', 'state_abbr', 'county_name', 'year'] + list(existing_var_cols.values())
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].copy()

    # Ensure FIPS is string with leading zeros
    if 'fips' in df.columns:
        df['fips'] = df['fips'].astype(str).str.zfill(5)
        # Filter out state-level rows (FIPS ending in 000)
        df = df[~df['fips'].str.endswith('000')].copy()

    # Convert numeric columns
    numeric_cols = [c for c in df.columns if c not in ['fips', 'state_abbr', 'county_name', 'year']]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate spending estimates based on health outcomes
    if 'preventable_hospitalizations' in df.columns:
        # Estimate cost: ~$15,000 per preventable hospitalization per 100k pop
        df['preventable_cost_estimate'] = df['preventable_hospitalizations'] * 15

    # Create a diet-related disease score from obesity and diabetes
    diet_factors = []
    if 'obesity_prevalence' in df.columns:
        diet_factors.append(df['obesity_prevalence'])
    if 'diabetes_prevalence' in df.columns:
        diet_factors.append(df['diabetes_prevalence'])

    if diet_factors:
        df['diet_disease_score'] = sum(diet_factors) / len(diet_factors)

    # Create overall health burden score
    health_cols = ['pct_fair_poor_health', 'obesity_prevalence', 'diabetes_prevalence',
                   'physical_inactivity_prevalence', 'smoking_prevalence']
    available_health = [c for c in health_cols if c in df.columns]
    if available_health:
        df['health_burden_score'] = df[available_health].mean(axis=1)

    logger.info(f"Processed {len(df):,} county records")
    logger.info(f"Final columns: {df.columns.tolist()}")

    # Save processed data
    output_path = DATA_PROCESSED / "county_health_rankings.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    csv_path = DATA_PROCESSED / "county_health_rankings.csv"
    df.to_csv(csv_path, index=False)

    return df


def process_usda_food_atlas() -> Optional[pd.DataFrame]:
    """
    Process USDA Food Environment Atlas.

    Extracts food access, store density, and food assistance metrics.
    """
    logger.info("=" * 60)
    logger.info("PROCESSING USDA FOOD ENVIRONMENT ATLAS")
    logger.info("=" * 60)

    # Try to find the data file (xlsx or xls)
    source_file = None
    for filename in ["food_environment_atlas.xlsx", "food_environment_atlas.xls",
                     "food-environment-atlas-data-download.xlsx"]:
        potential_file = DATA_RAW / filename
        if potential_file.exists():
            source_file = potential_file
            break

    # Also check for extracted CSV files
    if source_file is None:
        csv_files = list(DATA_RAW.glob("*food*atlas*.csv"))
        if csv_files:
            source_file = csv_files[0]

    if source_file is None:
        logger.error("No USDA Food Environment Atlas file found")
        return None

    logger.info(f"Reading: {source_file.name}")

    # The Food Environment Atlas is an Excel file with multiple sheets
    # Each sheet has header rows that need to be handled
    try:
        xl = pd.ExcelFile(source_file)
        logger.info(f"Sheets in Excel file: {xl.sheet_names}")

        # Key sheets to combine (skip Read_Me and Variable List)
        data_sheets = ['ACCESS', 'STORES', 'RESTAURANTS', 'ASSISTANCE',
                       'INSECURITY', 'HEALTH', 'SOCIOECONOMIC']

        dataframes = {}
        for sheet in xl.sheet_names:
            if sheet.strip() in data_sheets:
                try:
                    # First, peek at the sheet to find header row
                    # USDA Food Atlas has sheet name in row 0, headers in row 1
                    sheet_df = pd.read_excel(xl, sheet_name=sheet, header=1)  # Skip title row

                    # Verify we got real column names
                    first_col = str(sheet_df.columns[0]).upper()
                    if 'FIPS' in first_col or 'STATE' in first_col:
                        dataframes[sheet.strip()] = sheet_df
                        logger.info(f"  Sheet '{sheet}': {len(sheet_df):,} rows, cols: {sheet_df.columns.tolist()[:5]}")
                    else:
                        # Try header=0 as fallback
                        sheet_df = pd.read_excel(xl, sheet_name=sheet, header=0)
                        dataframes[sheet.strip()] = sheet_df
                        logger.info(f"  Sheet '{sheet}' (alt): {len(sheet_df):,} rows, cols: {sheet_df.columns.tolist()[:5]}")
                except Exception as e:
                    logger.warning(f"  Could not read sheet '{sheet}': {e}")

        if not dataframes:
            logger.error("No data sheets found")
            return None

        # Use ACCESS as the base sheet (has FIPS and core identifiers)
        if 'ACCESS' in dataframes:
            main_df = dataframes['ACCESS'].copy()
            base_sheet = 'ACCESS'
        else:
            base_sheet = list(dataframes.keys())[0]
            main_df = dataframes[base_sheet].copy()
        logger.info(f"Using '{base_sheet}' as base sheet")

        # Find FIPS column
        fips_col = None
        for col in main_df.columns:
            col_str = str(col).upper()
            if 'FIPS' in col_str:
                fips_col = col
                break

        if fips_col is None:
            logger.error("Could not find FIPS column in base sheet")
            logger.info(f"Available columns: {main_df.columns.tolist()[:20]}")
            return None

        logger.info(f"FIPS column: {fips_col}")

        # Standardize FIPS
        main_df['fips'] = main_df[fips_col].astype(str).str.zfill(5)

        # Drop original FIPS column to avoid duplicates later
        if fips_col != 'fips' and fips_col in main_df.columns:
            main_df = main_df.drop(columns=[fips_col])

        # Merge other sheets on FIPS
        for sheet_name, sheet_df in dataframes.items():
            if sheet_name == base_sheet:
                continue

            # Find FIPS column in this sheet
            sheet_fips = None
            for col in sheet_df.columns:
                if 'FIPS' in str(col).upper():
                    sheet_fips = col
                    break

            if sheet_fips:
                # Create temp fips column for merge
                sheet_df = sheet_df.copy()
                sheet_df['_merge_fips'] = sheet_df[sheet_fips].astype(str).str.zfill(5)

                # Get new columns only (exclude FIPS and State/County which are duplicates)
                existing_cols = set(main_df.columns)
                skip_cols = {sheet_fips, 'State', 'County', 'fips', '_merge_fips'}
                new_cols = [c for c in sheet_df.columns
                            if c not in existing_cols and c not in skip_cols]

                if new_cols:
                    # Add merge key
                    cols_to_merge = ['_merge_fips'] + new_cols
                    main_df = main_df.merge(
                        sheet_df[cols_to_merge],
                        left_on='fips',
                        right_on='_merge_fips',
                        how='left'
                    )
                    # Drop the temp merge column
                    if '_merge_fips' in main_df.columns:
                        main_df = main_df.drop(columns=['_merge_fips'])
                    logger.info(f"  Merged {len(new_cols)} columns from '{sheet_name}'")

        df = main_df

    except Exception as e:
        logger.error(f"Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Log available columns for debugging
    logger.info(f"Available columns after merge: {df.columns.tolist()[:30]}...")

    # Standardize column names - updated for 2024 data format
    # Note: FIPS is handled separately during merge to avoid duplicates
    rename_map = {
        'State': 'state_abbr',
        'County': 'county_name',
        # Store counts (2020 data)
        'GROC20': 'grocery_stores',
        'GROCPTH20': 'grocery_stores_per_1000',
        'SUPERC20': 'supercenters',
        'SUPERCPTH20': 'supercenters_per_1000',
        'CONVS20': 'convenience_stores',
        'CONVSPTH20': 'convenience_stores_per_1000',
        # Restaurant counts (2020 data)
        'FFR20': 'fast_food_restaurants',
        'FFRPTH20': 'fast_food_restaurants_per_1000',
        'FSR20': 'full_service_restaurants',
        'FSRPTH20': 'full_service_restaurants_per_1000',
        # Food access (2019 data)
        'LACCESS_POP19': 'low_access_pop',
        'PCT_LACCESS_POP19': 'pct_low_access_pop',
        'LACCESS_LOWI19': 'low_access_low_income',
        'PCT_LACCESS_LOWI19': 'pct_low_access_low_income',
        'LACCESS_CHILD19': 'low_access_children',
        'PCT_LACCESS_CHILD19': 'pct_low_access_children',
        'LACCESS_SENIORS19': 'low_access_seniors',
        'PCT_LACCESS_SENIORS19': 'pct_low_access_seniors',
        # Food insecurity (2021-2023 data)
        'FOODINSEC_21_23': 'food_insecurity_rate',
        'FOODINSEC_18_20': 'food_insecurity_rate_prev',
        # SNAP
        'SNAP_PART_RATE23': 'snap_participation_rate',
        'PCT_SNAP23': 'pct_snap',
        # Socioeconomic
        'POVRATE20': 'poverty_rate',
        'MEDHHINC20': 'median_household_income',
        # Health measures
        'PCT_DIABETES_ADULTS19': 'diabetes_prevalence',
        'PCT_OBESE_ADULTS20': 'obesity_prevalence',
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    logger.info(f"Columns after rename: {df.columns.tolist()[:20]}...")

    # Reset index to avoid duplicate label issues
    df = df.reset_index(drop=True)

    # Convert numeric columns
    numeric_cols = [c for c in df.columns if c not in ['fips', 'state_abbr', 'county_name']]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate food environment score
    # Higher score = better food environment
    score_components = 0
    df['food_environment_score'] = 0.0

    # Check for grocery store columns (try multiple possible names)
    grocery_col = None
    for col_name in ['grocery_stores_per_1000', 'GROCPTH20', 'GROCPTH16']:
        if col_name in df.columns:
            grocery_col = col_name
            break

    if grocery_col:
        # More grocery stores = better
        ranked = df[grocery_col].rank(pct=True).fillna(0.5)
        df['food_environment_score'] = df['food_environment_score'] + (ranked * 25)
        score_components += 1

    # Check for fast food columns
    ff_col = None
    for col_name in ['fast_food_restaurants_per_1000', 'FFRPTH20', 'FFRPTH16']:
        if col_name in df.columns:
            ff_col = col_name
            break

    if ff_col:
        # Fewer fast food = better (inverse)
        ranked = df[ff_col].rank(pct=True).fillna(0.5)
        df['food_environment_score'] = df['food_environment_score'] + ((1 - ranked) * 25)
        score_components += 1

    # Check for low access columns
    access_col = None
    for col_name in ['pct_low_access_pop', 'PCT_LACCESS_POP19', 'LACCESS_POP19']:
        if col_name in df.columns:
            access_col = col_name
            break

    if access_col:
        # Lower % low access = better (inverse)
        ranked = df[access_col].rank(pct=True).fillna(0.5)
        df['food_environment_score'] = df['food_environment_score'] + ((1 - ranked) * 25)
        score_components += 1

    # Check for food insecurity columns
    insec_col = None
    for col_name in ['food_insecurity_rate', 'FOODINSEC_21_23', 'FOODINSEC_18_20']:
        if col_name in df.columns:
            insec_col = col_name
            break

    if insec_col:
        # Lower food insecurity = better (inverse)
        ranked = df[insec_col].rank(pct=True).fillna(0.5)
        df['food_environment_score'] = df['food_environment_score'] + ((1 - ranked) * 25)
        score_components += 1

    # Normalize score if we didn't get all 4 components
    if score_components > 0 and score_components < 4:
        df['food_environment_score'] = df['food_environment_score'] * (4 / score_components)

    df['food_environment_score'] = df['food_environment_score'].clip(0, 100)
    logger.info(f"Food environment score calculated using {score_components} components")

    # Calculate fast food to full service ratio
    ff_ratio_col = ff_col  # Use the column we found earlier
    fs_col = None
    for col_name in ['full_service_restaurants_per_1000', 'FSRPTH20', 'FSRPTH16']:
        if col_name in df.columns:
            fs_col = col_name
            break

    if ff_ratio_col and fs_col:
        df['fast_food_to_full_service_ratio'] = (
            df[ff_ratio_col] / df[fs_col].replace(0, 0.001)
        )

    logger.info(f"Processed {len(df):,} counties")
    logger.info(f"Columns: {df.columns.tolist()[:20]}...")

    # Save processed data
    output_path = DATA_PROCESSED / "usda_food_environment.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    csv_path = DATA_PROCESSED / "usda_food_environment.csv"
    df.to_csv(csv_path, index=False)

    return df


def merge_datasets() -> Optional[pd.DataFrame]:
    """
    Merge all three datasets on county FIPS code.

    Creates the final integrated ChronicCare dataset linking:
    - Chronic disease burden (CDC PLACES)
    - Health outcomes/spending (County Health Rankings)
    - Food environment (USDA)
    """
    logger.info("=" * 60)
    logger.info("MERGING DATASETS")
    logger.info("=" * 60)

    # Load processed datasets - try multiple possible filenames
    cdc_path = DATA_PROCESSED / "cdc_places_county.parquet"
    chr_path = DATA_PROCESSED / "county_health_rankings.parquet"
    usda_path = DATA_PROCESSED / "usda_food_environment.parquet"

    dfs = {}

    for name, path in [("cdc", cdc_path), ("chr", chr_path), ("usda", usda_path)]:
        if path.exists():
            dfs[name] = pd.read_parquet(path)
            logger.info(f"Loaded {name}: {len(dfs[name]):,} rows")
        else:
            logger.warning(f"Missing: {path}")

    if not dfs:
        logger.error("No datasets to merge")
        return None

    # Start with CDC as base (has most complete county coverage)
    if "cdc" in dfs:
        merged = dfs["cdc"].copy()
        base_name = "cdc"
    elif "usda" in dfs:
        merged = dfs["usda"].copy()
        base_name = "usda"
    else:
        merged = dfs["cms"].copy()
        base_name = "cms"

    logger.info(f"Using {base_name} as base ({len(merged):,} rows)")

    # Ensure fips column exists and is standardized
    if 'fips' not in merged.columns:
        logger.error("No FIPS column in base dataset")
        return None

    merged['fips'] = merged['fips'].astype(str).str.zfill(5)

    # Merge other datasets
    for name, df in dfs.items():
        if name == base_name:
            continue

        if 'fips' in df.columns:
            df['fips'] = df['fips'].astype(str).str.zfill(5)

            # Identify columns to add (avoid duplicates except fips)
            existing_cols = set(merged.columns)
            new_cols = ['fips'] + [c for c in df.columns if c not in existing_cols]

            if len(new_cols) > 1:
                merged = merged.merge(
                    df[new_cols],
                    on='fips',
                    how='left'
                )
                logger.info(f"Merged {name}: added {len(new_cols)-1} columns")

    # Calculate MAHA intervention priority score
    # Higher score = higher priority for intervention
    priority_factors = []

    if 'chronic_disease_burden_score' in merged.columns:
        # Higher disease burden = higher priority
        priority_factors.append(merged['chronic_disease_burden_score'].rank(pct=True) * 30)

    if 'food_environment_score' in merged.columns:
        # Worse food environment = higher priority (inverse)
        priority_factors.append((1 - merged['food_environment_score'].rank(pct=True)) * 30)

    if 'per_capita_spending' in merged.columns:
        # Higher spending = higher priority
        priority_factors.append(merged['per_capita_spending'].rank(pct=True) * 20)

    if 'poverty_rate' in merged.columns:
        # Higher poverty = higher priority
        priority_factors.append(merged['poverty_rate'].rank(pct=True) * 20)

    if priority_factors:
        merged['maha_priority_score'] = sum(priority_factors)
        merged['maha_priority_score'] = merged['maha_priority_score'].clip(0, 100)

        # Assign intervention tiers
        merged['maha_intervention_tier'] = pd.cut(
            merged['maha_priority_score'],
            bins=[0, 25, 50, 75, 100],
            labels=['low', 'medium', 'high', 'critical']
        )

    # Calculate potential savings (if 10% disease reduction)
    if 'diet_related_spending_estimate' in merged.columns:
        merged['potential_savings_10pct_reduction'] = merged['diet_related_spending_estimate'] * 0.10

    logger.info(f"Final merged dataset: {len(merged):,} rows, {len(merged.columns)} columns")

    # Save merged dataset
    output_path = DATA_PROCESSED / "chroniccare_merged.parquet"
    merged.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    csv_path = DATA_PROCESSED / "chroniccare_merged.csv"
    merged.to_csv(csv_path, index=False)
    logger.info(f"Saved: {csv_path}")

    return merged


def generate_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate summary statistics for the merged dataset."""
    stats = {
        "total_counties": len(df),
        "timestamp": datetime.now().isoformat(),
    }

    # Disease prevalence stats
    for col in ['diabetes_prevalence', 'obesity_prevalence', 'heart_disease_prevalence']:
        if col in df.columns:
            stats[f"{col}_mean"] = round(df[col].mean(), 2)
            stats[f"{col}_median"] = round(df[col].median(), 2)
            stats[f"{col}_max"] = round(df[col].max(), 2)

    # Spending stats
    if 'per_capita_spending' in df.columns:
        stats["avg_per_capita_medicare_spending"] = round(df['per_capita_spending'].mean(), 2)
        stats["total_medicare_spending"] = round(df['total_spending'].sum(), 2) if 'total_spending' in df.columns else None

    if 'diet_related_spending_estimate' in df.columns:
        stats["total_diet_related_spending"] = round(df['diet_related_spending_estimate'].sum(), 2)

    if 'potential_savings_10pct_reduction' in df.columns:
        stats["potential_savings_10pct_reduction"] = round(df['potential_savings_10pct_reduction'].sum(), 2)

    # Food environment stats
    if 'food_environment_score' in df.columns:
        stats["avg_food_environment_score"] = round(df['food_environment_score'].mean(), 2)

    if 'pct_low_access_pop' in df.columns:
        stats["pct_population_low_food_access"] = round(df['pct_low_access_pop'].mean(), 2)

    # MAHA intervention stats
    if 'maha_intervention_tier' in df.columns:
        tier_counts = df['maha_intervention_tier'].value_counts().to_dict()
        stats["intervention_tiers"] = {str(k): v for k, v in tier_counts.items()}

    return stats


def process_all() -> Dict[str, bool]:
    """Process all downloaded data."""
    results = {}

    # Process each dataset
    cdc_df = process_cdc_places()
    results["cdc_places"] = cdc_df is not None

    cms_df = process_cms_geographic()
    results["cms_geographic"] = cms_df is not None

    usda_df = process_usda_food_atlas()
    results["usda_food_atlas"] = usda_df is not None

    # Merge datasets
    if any(results.values()):
        merged_df = merge_datasets()
        results["merged"] = merged_df is not None

        if merged_df is not None:
            # Generate and save summary stats
            stats = generate_summary_stats(merged_df)
            stats_path = DATA_PROCESSED / "chroniccare_stats.json"
            with open(stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Saved statistics: {stats_path}")

            # Print summary
            print("\n" + "=" * 60)
            print("CHRONICCARE SUMMARY STATISTICS")
            print("=" * 60)
            for key, value in stats.items():
                if value is not None:
                    print(f"  {key}: {value}")

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ChronicCare Data Pipeline - Download and Process',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/chroniccare_pipeline.py --all         # Download and process everything
    python scripts/chroniccare_pipeline.py --download    # Download only
    python scripts/chroniccare_pipeline.py --process     # Process existing data only
        """
    )
    parser.add_argument('--all', action='store_true', help='Download and process all data (default)')
    parser.add_argument('--download', action='store_true', help='Download raw data only')
    parser.add_argument('--process', action='store_true', help='Process existing data only')

    args = parser.parse_args()

    # Default to --all if no option specified
    if not any([args.all, args.download, args.process]):
        args.all = True

    print("=" * 60)
    print("CHRONICCARE DATA PIPELINE")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Raw Data: {DATA_RAW}")
    print(f"Processed Data: {DATA_PROCESSED}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    download_results = {}
    process_results = {}

    # Download phase
    if args.all or args.download:
        print("\n>>> DOWNLOAD PHASE <<<\n")
        download_results = download_all()

        print("\nDownload Results:")
        for source, success in download_results.items():
            status = "OK" if success else "FAILED"
            print(f"  {source}: {status}")

    # Process phase
    if args.all or args.process:
        print("\n>>> PROCESSING PHASE <<<\n")
        process_results = process_all()

        print("\nProcessing Results:")
        for source, success in process_results.items():
            status = "OK" if success else "FAILED"
            print(f"  {source}: {status}")

    # Final summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    # List output files
    print("\nOutput Files:")
    for f in sorted(DATA_PROCESSED.glob("*")):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
