# HealthGuard America - Data Sources Documentation

**Last Updated:** January 3, 2026
**Total Raw Data Size:** ~45 GB
**Data Collection Status:** Complete

---

## Table of Contents

1. [Overview](#overview)
2. [DrugWatch Module](#drugwatch-module)
3. [FoodScore Module](#foodscore-module)
4. [RuralAccess Module](#ruralaccess-module)
5. [PriceVision Module](#pricevision-module)
6. [Data Quality Notes](#data-quality-notes)
7. [Update Schedule](#update-schedule)

---

## Overview

HealthGuard America aggregates data from 16+ government and public sources to provide healthcare transparency across four modules:

| Module | Purpose | Primary Sources | Data Size |
|--------|---------|-----------------|-----------|
| DrugWatch | Drug price comparison (US vs international) | CMS, FDA, Health Canada, NHS, PBS | 6.7 GB |
| FoodScore | Food product health scoring | OpenFoodFacts, FDA | 1.2 GB |
| RuralAccess | Healthcare desert mapping | HRSA, CMS, Census | 1.3 GB |
| PriceVision | Hospital price transparency | CMS, Hospital MRFs (1,260 hospitals) | 36.4 GB |

---

## DrugWatch Module

### 1. Medicare Part D Spending by Drug (US)

| Attribute | Value |
|-----------|-------|
| **Source** | Centers for Medicare & Medicaid Services (CMS) |
| **URL** | https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug |
| **File** | `data/raw/drugwatch/us/part_d/.../DSD_PTD_RY25_P04_V10_DY23_BGM.csv` |
| **Size** | 5.1 MB |
| **Records** | 14,310 drugs |
| **Format** | CSV |
| **Update Frequency** | Annual (typically Q1) |
| **Years Covered** | 2019-2023 |
| **License** | Public Domain (US Government Work) |

**Key Fields:**
- `Brnd_Name` - Brand name of the drug
- `Gnrc_Name` - Generic name
- `Mftr_Name` - Manufacturer
- `Tot_Spndng_YYYY` - Total Medicare spending for year
- `Tot_Clms_YYYY` - Total claims
- `Tot_Benes_YYYY` - Total beneficiaries
- `Avg_Spnd_Per_Dsg_Unt_Wghtd_YYYY` - Average spending per dosage unit
- `Chg_Avg_Spnd_Per_Dsg_Unt_22_23` - Year-over-year change

**Use Case:** Calculate US drug prices for international comparison and MFN savings analysis.

---

### 2. FDA National Drug Code (NDC) Directory

| Attribute | Value |
|-----------|-------|
| **Source** | U.S. Food and Drug Administration |
| **URL** | https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory |
| **File** | `data/raw/drugwatch/us/ndc/product.txt`, `package.txt` |
| **Size** | 62 MB (extracted) |
| **Records** | ~200,000 NDC codes |
| **Format** | Tab-delimited text |
| **Update Frequency** | Weekly |
| **License** | Public Domain |

**Key Fields:**
- `PRODUCTID` - Unique product identifier
- `PRODUCTNDC` - NDC code (format: XXXXX-XXXX)
- `PROPRIETARYNAME` - Brand name
- `NONPROPRIETARYNAME` - Generic name
- `DOSAGEFORMNAME` - Dosage form (tablet, capsule, etc.)
- `ACTIVE_NUMERATOR_STRENGTH` - Drug strength
- `ACTIVE_INGRED_UNIT` - Unit of measure
- `PHARM_CLASSES` - Pharmacological classes
- `LABELERNAME` - Manufacturer/labeler

**Use Case:** Drug identification, cross-referencing with international databases, generic/brand mapping.

---

### 3. Canada Drug Product Database

| Attribute | Value |
|-----------|-------|
| **Source** | Health Canada |
| **URL** | https://health-products.canada.ca/api/drug/ |
| **File** | `data/raw/drugwatch/canada/drug_products.json` |
| **Size** | 15 MB |
| **Records** | ~30,000 drugs |
| **Format** | JSON |
| **Update Frequency** | Monthly |
| **License** | Open Government Licence - Canada |

**Key Fields:**
- `drug_code` - Health Canada drug code
- `brand_name` - Canadian brand name
- `descriptor` - Product description
- `company_name` - Manufacturer
- `active_ingredient_code` - Ingredient identifier
- `strength` - Drug strength
- `dosage_form` - Dosage form

**Use Case:** Canadian drug prices for international comparison.

---

### 4. UK NHS English Prescribing Data (EPD)

| Attribute | Value |
|-----------|-------|
| **Source** | NHS Business Services Authority |
| **URL** | https://opendata.nhsbsa.net/dataset/english-prescribing-data-epd |
| **File** | `data/raw/drugwatch/uk/epd_202401.csv` |
| **Size** | 6.5 GB |
| **Records** | ~100+ million prescriptions |
| **Format** | CSV |
| **Update Frequency** | Monthly |
| **License** | Open Government Licence v3.0 |

**Key Fields:**
- `YEAR_MONTH` - Prescribing period
- `PRACTICE_CODE` - GP practice identifier
- `BNF_CHEMICAL_SUBSTANCE` - Drug chemical name
- `BNF_CODE` - British National Formulary code
- `CHEMICAL_SUBSTANCE_BNF_DESCR` - Drug description
- `QUANTITY` - Quantity prescribed
- `ITEMS` - Number of prescription items
- `ACTUAL_COST` - Actual cost (GBP)
- `NIC` - Net Ingredient Cost

**Use Case:** UK drug prices and volumes for MFN calculations.

---

### 5. Australia Pharmaceutical Benefits Scheme (PBS)

| Attribute | Value |
|-----------|-------|
| **Source** | Australian Government Department of Health |
| **URL** | https://www.pbs.gov.au/info/browse/download |
| **File** | `data/raw/drugwatch/australia/pbs/tables_as_csv/items.csv` |
| **Size** | 47 MB (all tables) |
| **Records** | 14,598 drug items |
| **Format** | CSV |
| **Update Frequency** | Monthly (1st of each month) |
| **License** | Creative Commons Attribution 4.0 |

**Key Files:**
- `items.csv` - Drug listings with prices
- `amt-items.csv` - Australian Medicines Terminology mappings
- `fees.csv` - Dispensing fees by program
- `atc-codes.csv` - ATC classification codes

**Key Fields (items.csv):**
- `li_item_id` - Line item identifier
- `drug_name` - Drug name
- `brand_name` - Brand name
- `pbs_code` - PBS item code
- `claimed_price` - Price claimed (AUD)
- `determined_price` - Government determined price
- `pack_size` - Package size
- `maximum_quantity_units` - Max quantity per script

**Use Case:** Australian drug prices for international comparison.

---

## FoodScore Module

### 1. OpenFoodFacts Product Database

| Attribute | Value |
|-----------|-------|
| **Source** | Open Food Facts (Community Database) |
| **URL** | https://world.openfoodfacts.org/data |
| **File** | `data/raw/foodscore/openfoodfacts_us.csv.gz` |
| **Size** | 1.2 GB (compressed), ~10 GB uncompressed |
| **Records** | ~3 million products globally, ~500K US products |
| **Format** | Gzipped CSV |
| **Update Frequency** | Real-time (daily bulk export) |
| **License** | Open Database License (ODbL) |

**Key Fields:**
- `code` - Barcode (EAN/UPC)
- `product_name` - Product name
- `brands` - Brand name(s)
- `categories` - Product categories
- `ingredients_text` - Full ingredient list
- `allergens` - Allergen information
- `nova_group` - NOVA processing classification (1-4)
- `nutriscore_grade` - Nutri-Score (A-E)
- `energy_100g`, `fat_100g`, `sugars_100g`, `sodium_100g` - Nutrition values
- `countries_tags` - Countries where sold

**Use Case:** Product lookup by barcode, ingredient analysis, NOVA classification, MAHA scoring.

**Filtering Note:** Filter to US products using `countries_tags LIKE '%united-states%'`

---

### 2. Additive Risk Database (Curated)

| Attribute | Value |
|-----------|-------|
| **Source** | HealthGuard America (curated from multiple sources) |
| **Primary Sources** | CSPI Chemical Cuisine, FDA EAFUS, EU regulations |
| **File** | `data/raw/foodscore/additive_risks.csv` |
| **Size** | 5.1 KB |
| **Records** | 42 high-priority additives |
| **Format** | CSV |
| **Update Frequency** | As needed |
| **License** | Project-created |

**Key Fields:**
- `name` - Common name
- `aliases` - Alternative names (pipe-separated)
- `type` - Category (dye, preservative, sweetener, emulsifier, flavor, other)
- `risk_score` - Risk score 0-100 (higher = more concerning)
- `fda_status` - FDA approval status
- `eu_status` - EU status (approved, restricted, banned)
- `is_artificial` - Boolean
- `is_petroleum_based` - Boolean
- `notes` - Research summary

**Methodology:**
- Risk scores derived from CSPI Chemical Cuisine ratings
- EU regulatory status from European Food Safety Authority
- Research summaries from peer-reviewed literature

---

### 3. FDA Food Additives (Scraped)

| Attribute | Value |
|-----------|-------|
| **Source** | FDA Center for Food Safety and Applied Nutrition |
| **URL** | https://www.fda.gov/food/food-additives-petitions/food-additive-status-list |
| **File** | `data/raw/foodscore/fda_additives_scraped.csv` |
| **Size** | 3.6 KB |
| **Records** | 50 additives |
| **Format** | CSV |
| **Update Frequency** | As needed |
| **License** | Public Domain |

**Key Fields:**
- `name` - Additive name
- `function` - Primary function
- `status` - FDA regulatory status

---

## RuralAccess Module

### 1. HRSA Health Professional Shortage Areas (HPSA)

| Attribute | Value |
|-----------|-------|
| **Source** | Health Resources and Services Administration |
| **URL** | https://data.hrsa.gov/data/download |
| **File** | `data/raw/ruralaccess/hrsa_hpsa.csv` |
| **Size** | 43 MB |
| **Records** | 73,034 shortage area designations |
| **Format** | CSV |
| **Update Frequency** | Quarterly |
| **License** | Public Domain |

**Key Fields:**
- `HPSA_ID` - Unique identifier
- `HPSA_Name` - Designation name
- `HPSA_Type_Desc` - Type (Geographic, Population, Facility)
- `HPSA_Discipline_Class` - Discipline (Primary Care, Dental, Mental Health)
- `HPSA_Status` - Status (Designated, Proposed Withdrawal, etc.)
- `HPSA_Score` - Shortage severity score (0-26)
- `State_Abbr` - State
- `County_Name` - County
- `FIPS_State_County_Code` - FIPS code
- `Designation_Pop` - Population affected

**Use Case:** Identify healthcare shortage areas, calculate access scores.

---

### 2. CMS NPI Provider Registry

| Attribute | Value |
|-----------|-------|
| **Source** | Centers for Medicare & Medicaid Services (NPPES) |
| **URL** | https://download.cms.gov/nppes/NPI_Files.html |
| **File** | `data/raw/ruralaccess/npi_registry.zip` |
| **Size** | 988 MB (compressed), ~10 GB uncompressed |
| **Records** | ~7 million providers |
| **Format** | CSV (zipped) |
| **Update Frequency** | Monthly |
| **License** | Public Domain |

**Key Fields:**
- `NPI` - National Provider Identifier
- `Entity Type Code` - 1=Individual, 2=Organization
- `Provider Organization Name` - Organization name
- `Provider Last Name`, `First Name` - Individual name
- `Provider Business Practice Location Address` - Street address
- `Provider Business Practice Location Address City Name` - City
- `Provider Business Practice Location Address State Name` - State
- `Provider Business Practice Location Address Postal Code` - ZIP
- `Healthcare Provider Taxonomy Code_1` - Provider specialty

**Use Case:** Geocode provider locations, calculate provider density per county.

---

### 3. Census TIGER County Boundaries

| Attribute | Value |
|-----------|-------|
| **Source** | U.S. Census Bureau |
| **URL** | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html |
| **File** | `data/raw/ruralaccess/county_boundaries/tl_2023_us_county.shp` |
| **Size** | 127 MB (shapefile set) |
| **Records** | 3,234 counties/equivalents |
| **Format** | ESRI Shapefile |
| **Update Frequency** | Annual |
| **License** | Public Domain |

**Files Included:**
- `.shp` - Shape geometry
- `.dbf` - Attribute data
- `.shx` - Shape index
- `.prj` - Projection info

**Key Fields:**
- `STATEFP` - State FIPS code
- `COUNTYFP` - County FIPS code
- `GEOID` - Combined FIPS (state+county)
- `NAME` - County name
- `ALAND` - Land area (sq meters)
- `AWATER` - Water area

**Use Case:** Spatial analysis, choropleth mapping, provider-to-county assignment.

---

### 4. Census Population by County

| Attribute | Value |
|-----------|-------|
| **Source** | U.S. Census Bureau American Community Survey |
| **URL** | https://api.census.gov/data/2022/acs/acs5 |
| **File** | `data/raw/ruralaccess/county_population.json` |
| **Size** | 156 KB |
| **Records** | 3,221 counties |
| **Format** | JSON |
| **Update Frequency** | Annual |
| **License** | Public Domain |

**Key Fields:**
- `B01001_001E` - Total population
- `NAME` - County name, State
- `county` - County FIPS code
- `state` - State FIPS code

**Use Case:** Population denominators for provider density calculations.

---

## PriceVision Module

### 1. CMS Hospital General Information

| Attribute | Value |
|-----------|-------|
| **Source** | Centers for Medicare & Medicaid Services |
| **URL** | https://data.cms.gov/provider-data/dataset/hospital-general-information |
| **File** | `data/raw/pricevision/hospital_general_info.csv` |
| **Size** | 1.6 MB |
| **Records** | 5,422 hospitals |
| **Format** | CSV |
| **Update Frequency** | Quarterly |
| **License** | Public Domain |

**Key Fields:**
- `Facility ID` - CMS Certification Number (CCN)
- `Facility Name` - Hospital name
- `Address`, `City/Town`, `State`, `ZIP Code` - Location
- `County/Parish` - County name
- `Hospital Type` - Acute Care, Critical Access, etc.
- `Hospital Ownership` - Government, Non-profit, Proprietary
- `Emergency Services` - Yes/No
- `Hospital overall rating` - CMS star rating (1-5)

**Use Case:** Hospital master list for MRF crawling and price comparison.

---

### 2. Medicare Provider Utilization (Procedure Training Data)

| Attribute | Value |
|-----------|-------|
| **Source** | Centers for Medicare & Medicaid Services |
| **URL** | https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners |
| **File** | `data/raw/pricevision/provider_util/.../MUP_PHY_R25_P05_V20_D23_Prov_Svc.csv` |
| **Size** | 2.9 GB |
| **Records** | 9,660,648 procedure records |
| **Format** | CSV |
| **Update Frequency** | Annual |
| **License** | Public Domain |

**Key Fields:**
- `Rndrng_NPI` - Provider NPI
- `Rndrng_Prvdr_Last_Org_Name` - Provider name
- `Rndrng_Prvdr_Type` - Provider specialty
- `HCPCS_Cd` - HCPCS/CPT procedure code
- `HCPCS_Desc` - Procedure description (training data!)
- `HCPCS_Drug_Ind` - Is drug indicator
- `Place_Of_Srvc` - Facility (F) or Office (O)
- `Tot_Benes` - Total beneficiaries
- `Tot_Srvcs` - Total services
- `Avg_Sbmtd_Chrg` - Average submitted charge
- `Avg_Mdcr_Alowd_Amt` - Average Medicare allowed amount
- `Avg_Mdcr_Pymt_Amt` - Average Medicare payment

**Use Case:**
1. **Procedure name training:** Extract unique `HCPCS_Cd` + `HCPCS_Desc` pairs for BioClinicalBERT fine-tuning
2. **Reference pricing:** Use Medicare allowed amounts as benchmark prices

---

### 3. Hospital Machine-Readable Files (MRF) - COMPLETE

| Attribute | Value |
|-----------|-------|
| **Source** | Individual hospital websites (CMS mandated) |
| **Mandate** | Hospital Price Transparency Rule (CMS-1717-F2) |
| **File** | `data/raw/pricevision/mrfs/*` |
| **Total Files** | 1,084 hospital MRF files |
| **Total Size** | 33.51 GB |
| **Unique Hospitals** | 1,059 (by NPI) |
| **US Coverage** | 19.5% (target: 20%) |
| **Format** | CSV (767), JSON (343), XLSX (179) |
| **Update Frequency** | Annual (hospitals required to update) |
| **License** | Public (mandated by CMS) |

**Download Summary:**

| Batch | Hospitals | Success Rate | Size |
|-------|-----------|--------------|------|
| Priority (high-success domains) | 557 | 93.9% (523) | 18.5 GB |
| Batch 2 (filtered domains) | 2,273 | 37.0% (840) | 14.0 GB |
| After cleanup (20% target) | - | - | 33.5 GB |
| **Final** | **1,084** | **19.5% coverage** | **33.5 GB** |

**File Format Distribution:**

| Format | Files | Size | Avg Size |
|--------|-------|------|----------|
| CSV | 767 | 12.79 GB | 17.1 MB |
| JSON | 343 | 19.20 GB | 56.0 MB |
| XLSX | 179 | 1.54 GB | 8.8 MB |

**Crawler Scripts:**
- `scripts/download_priority_mrfs.py` - Priority hospital systems
- `scripts/download_batch2_mrfs.py` - Secondary batch with domain filtering

**Verified URL Source:**

| Attribute | Value |
|-----------|-------|
| **Sources** | TPAFS GitHub, cms-hpt.txt scraping, DoltHub |
| **File** | `data/raw/pricevision/hospital_mrf_urls.csv` |
| **Unique URLs** | 3,318 hospitals |
| **CMS Total** | 5,421 US hospitals |
| **Coverage** | 61.2% of US hospitals |

**Confirmed Data Fields (validated from downloaded files):**

| Field | Example Value |
|-------|---------------|
| CPT/HCPCS Code | 70450, 71046, 80053, 93306 |
| Description | "CT: Brain/Head W/O Contrast" |
| Code Type | CPT/HCPCS, CDM |
| Revenue Code | 301, 351, 483 |
| Gross Charge | $2,826.94 |
| Cash/Self-Pay Price | $1,413.47 (typically 50% of gross) |
| Min Negotiated Rate | $1,263.64 |
| Max Negotiated Rate | $2,544.25 |
| Payer-Specific Rates | Aetna, BCBS, Cigna, United, Humana, Coventry, Multiplan, etc. |

**Sample Pricing Data (AdventHealth Central Texas):**

| Procedure | CPT | Gross | Cash | BCBS PPO | United PPO |
|-----------|-----|-------|------|----------|------------|
| CT Head w/o Contrast | 70450 | $2,827 | $1,413 | $1,399 | $1,979 |
| Chest X-Ray 2 Views | 71046 | $760 | $380 | $376 | $532 |
| Metabolic Panel | 80053 | $379 | $189 | $187 | $265 |
| CBC w/ Differential | 85025 | $219 | $109 | $108 | $153 |
| Echocardiogram | 93306 | $1,360 | $680 | $673 | $952 |

**High-Success Hospital Domains:**
- `apps.para-hcfs.com` - 189/215 (87.9%)
- `core.secure.ehc.com` - 100/102 (98.0%)
- `hcah-p-001-delivery.stylelabs.cloud` - 55/55 (100%)
- `healthy.kaiserpermanente.org` - 32/32 (100%)
- `cdn.upmc.com` - 35/35 (100%)
- `www.dignityhealth.org` - 35/35 (100%)

**Crawl Configuration:**
- `MAX_FILE_SIZE`: 500 MB
- `WORKERS`: 10 concurrent downloads
- Auto-skip known bad domains (0% success rate)
- HTML error page detection and removal

**Crawl Logs:**
- `data/raw/pricevision/priority_crawl_log.csv`
- `data/raw/pricevision/batch2_crawl_log.csv`

---

## Data Quality Notes

### Known Issues

| Dataset | Issue | Mitigation |
|---------|-------|------------|
| OpenFoodFacts | ~40% missing NOVA classification | Train NOVA classifier to predict |
| Hospital MRFs | 1,289 files from 1,260 hospitals (~24% of US hospitals) | Covers major systems, expand over time |
| Hospital MRFs | 3 file formats (CSV, JSON, XLSX) | Normalize in processing pipeline |
| Hospital MRFs | ~6% files removed (HTML errors, empty) | Auto-cleanup in crawler |
| NPI Registry | Addresses need geocoding | Batch geocode with Census API |
| Part D | Excludes rebates | Note in methodology |
| UK EPD | Very large file | Stream processing required |

### Data Freshness

| Dataset | Data Date | Download Date |
|---------|-----------|---------------|
| Part D Spending | 2023 | Jan 2026 |
| FDA NDC | Jan 2025 | Jan 2026 |
| UK EPD | Jan 2024 | Jan 2026 |
| PBS | Jan 2026 | Jan 2026 |
| OpenFoodFacts | Rolling | Jan 2026 |
| HRSA HPSA | Q4 2025 | Jan 2026 |
| Census Counties | 2023 | Jan 2026 |
| Hospital MRFs | 2022-2025 | Jan 2026 |
| TPAFS Verified URLs | Dec 2025 | Jan 2026 |

---

## Update Schedule

| Dataset | Recommended Update Frequency | Method |
|---------|------------------------------|--------|
| Part D Spending | Annual (Q1) | Manual download |
| FDA NDC | Weekly | Automated script |
| OpenFoodFacts | Daily (incremental) | API sync |
| HRSA HPSA | Quarterly | Automated script |
| Hospital MRFs | Annual | Crawler script |
| Census Population | Annual | API call |

---

## File Structure

```
data/
├── raw/
│   ├── drugwatch/
│   │   ├── us/
│   │   │   ├── part_d/Medicare Part D Spending by Drug/2023/
│   │   │   │   └── DSD_PTD_RY25_P04_V10_DY23_BGM.csv
│   │   │   └── ndc/
│   │   │       ├── product.txt
│   │   │       └── package.txt
│   │   ├── canada/
│   │   │   └── drug_products.json
│   │   ├── uk/
│   │   │   └── epd_202401.csv
│   │   └── australia/
│   │       └── pbs/tables_as_csv/
│   │           ├── items.csv
│   │           ├── amt-items.csv
│   │           └── [other tables]
│   ├── foodscore/
│   │   ├── openfoodfacts_us.csv.gz
│   │   ├── additive_risks.csv
│   │   ├── additive_risks.json
│   │   └── fda_additives_scraped.csv
│   ├── ruralaccess/
│   │   ├── hrsa_hpsa.csv
│   │   ├── county_population.json
│   │   ├── county_boundaries/
│   │   │   └── tl_2023_us_county.[shp|dbf|shx|prj]
│   │   ├── npi_registry.zip
│   │   └── npi/[extracted headers]
│   └── pricevision/
│       ├── hospital_general_info.csv
│       ├── provider_util/Medicare Physician.../2023/
│       │   └── MUP_PHY_R25_P05_V20_D23_Prov_Svc.csv
│       ├── procedure_training_data.csv
│       ├── procedure_variations.json
│       ├── hospital_mrf_urls.csv          # 3,584 verified URLs from TPAFS
│       ├── priority_hospitals.csv         # 557 priority hospital list
│       ├── batch2_filtered.csv            # 2,273 batch 2 hospital list
│       ├── priority_crawl_log.csv         # Priority batch results (523 success)
│       ├── batch2_crawl_log.csv           # Batch 2 results (840 success)
│       └── mrfs/                          # 1,289 MRF files (33.54 GB)
│           ├── *.csv                      # 767 CSV files (12.79 GB)
│           ├── *.json                     # 343 JSON files (19.20 GB)
│           └── *.xlsx                     # 179 Excel files (1.54 GB)
├── processed/
│   └── [cleaned/filtered data]
└── models/
    └── [trained ML models]
```

---

## Legal & Attribution

All data used in HealthGuard America is from public sources:

- **US Government Data** (CMS, FDA, HRSA, Census): Public Domain
- **OpenFoodFacts**: Open Database License (ODbL) - requires attribution
- **NHS UK**: Open Government Licence v3.0
- **Health Canada**: Open Government Licence - Canada
- **Australia PBS**: Creative Commons Attribution 4.0

**Required Attribution:**
> "This product includes data from Open Food Facts (https://openfoodfacts.org), made available under the Open Database License."

---

*Document generated by HealthGuard America data collection pipeline.*
