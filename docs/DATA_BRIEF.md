# HealthGuard America - Data Brief

**Generated:** January 4, 2026
**Version:** 1.0
**Total Records Processed:** 31,068,502

---

## Executive Summary

HealthGuard America integrates four comprehensive healthcare datasets to provide unprecedented transparency into American healthcare costs, drug pricing, food safety, and access to care. This brief summarizes the processed data across all modules.

| Module | Records | Coverage |
|--------|---------|----------|
| PriceVision | 30,200,589 | 1,002 hospitals |
| DrugWatch | 75,854 | 3 countries (US, Australia, Canada) |
| FoodScore | 50,000 | US food products |
| RuralAccess | 14,631 | 59 states/territories |

---

## 1. PriceVision: Hospital Price Transparency

### Overview
- **Total Price Records:** 30,200,589
- **Unique Hospitals:** 1,002
- **Data Processing Success Rate:** 94.6% (1,026/1,084 files)

### Price Statistics

| Metric | Gross Charge | Cash Price | Min Negotiated | Max Negotiated | Negotiated Rate |
|--------|--------------|------------|----------------|----------------|-----------------|
| **Count** | 22,298,063 | 20,303,428 | 16,880,100 | 17,000,684 | 10,718,830 |
| **Mean** | $29,442 | $3,519 | $1,121 | $6,465 | $1,288 |
| **Median** | $518 | $357 | $63 | $436 | $171 |
| **25th Percentile** | $97 | $68 | $12 | $90 | $39 |
| **75th Percentile** | $2,826 | $1,980 | $355 | $2,591 | $780 |
| **95th Percentile** | $22,615 | $14,082 | $4,175 | $23,269 | $5,396 |
| **Maximum** | $9,960,013 | $9,965,976 | $4,887,658 | $8,835,750 | $8,207,066 |

### Key Findings
- **Price Variation:** Gross charges average 8.3x higher than cash prices
- **Negotiation Impact:** Maximum negotiated rates average 5.8x higher than minimum rates
- **Median Discount:** Cash prices are 31% lower than gross charges at the median

### Billing Code Distribution
| Code Type | Records | Percentage |
|-----------|---------|------------|
| CDM (Chargemaster) | 10,971,951 | 36.3% |
| HCPCS | 486,379 | 1.6% |
| Revenue Code | 250,000 | 0.8% |
| APR-DRG | 167,974 | 0.6% |
| CPT/HCPCS | 55,233 | 0.2% |

### Care Setting Distribution
| Setting | Records | Percentage |
|---------|---------|------------|
| Outpatient | 10,353,023 | 34.3% |
| Inpatient | 643,510 | 2.1% |
| Both | 1,056,766 | 3.5% |
| Unspecified | 18,145,110 | 60.1% |

### Top Insurance Payers (by record count)
1. **Cigna** - 279,520 records
2. **UnitedHealthcare** - 328,988 records
3. **Aetna** - 718,752 records
4. **Multiplan** - 183,533 records
5. **Anthem** - 63,047 records
6. **Humana** - 61,981 records
7. **Medi-Cal** - 61,669 records

---

## 2. DrugWatch: Pharmaceutical Pricing Analysis

### US Medicare Part D (2023)

- **Total Drugs Analyzed:** 3,598
- **Total Medicare Spending (2023):** $275,924,520,551 (~$276 billion)
- **Total Beneficiaries:** 478,580,886

#### Top 10 Drugs by Medicare Spending (2023)

| Rank | Brand Name | Generic Name | Total Spending |
|------|------------|--------------|----------------|
| 1 | **Eliquis** | Apixaban | $18.27 billion |
| 2 | **Ozempic** | Semaglutide | $9.19 billion |
| 3 | **Jardiance** | Empagliflozin | $8.84 billion |
| 4 | **Trulicity** | Dulaglutide | $7.36 billion |
| 5 | **Xarelto** | Rivaroxaban | $6.31 billion |
| 6 | **Trelegy Ellipta** | Fluticasone/Umeclidin/Vilanter | $4.46 billion |
| 7 | **Humira (Cf) Pen** | Adalimumab | $4.42 billion |
| 8 | **Farxiga** | Dapagliflozin | $4.34 billion |
| 9 | **Januvia** | Sitagliptin | $4.09 billion |
| 10 | **Revlimid** | Lenalidomide | $3.86 billion |

#### Price Per Unit Statistics
| Metric | Value |
|--------|-------|
| Mean | $563.02 |
| Median | $8.86 |
| Maximum | $239,746 |
| Minimum | $0.004 |

#### Most Expensive Drugs (Per Unit)
| Rank | Brand Name | Generic Name | Price/Unit |
|------|------------|--------------|------------|
| 1 | **Amvuttra** | Vutrisiran Sodium | $239,746 |
| 2 | **Vabysmo** | Faricimab-Svoa | $46,702 |
| 3 | **Givlaari** | Givosiran Sodium | $41,427 |
| 4 | **Beovu** | Brolucizumab-Dbll | $40,425 |
| 5 | **Eylea HD** | Aflibercept | $40,244 |

### Australia PBS Comparison
- **Total Drugs:** 14,598
- **Mean Price (USD):** $5,509
- **Median Price (USD):** $17.60

### Canada Drug Database
- **Total Drug Records:** 57,658
- **Data includes:** Drug identification numbers, brand names, company information

---

## 3. FoodScore: Food Safety & MAHA Scoring

### Overview
- **Total Products Analyzed:** 50,000 US food products
- **Products with Flagged Additives:** 25,105 (50.2%)
- **Average Additives per Product:** 3.63

### MAHA Score Distribution (0-100 scale, higher = healthier)

| Category | Score Range | Products | Percentage |
|----------|-------------|----------|------------|
| Excellent | 90-100 | 22,221 | 44.4% |
| Good | 75-90 | 5,526 | 11.1% |
| Moderate | 50-75 | 15,007 | 30.0% |
| Poor | 25-50 | 6,106 | 12.2% |
| Very Poor | 0-25 | 1,140 | 2.3% |

**Overall MAHA Score:**
- Mean: 76.6
- Median: 83.0
- Standard Deviation: 23.3

### NOVA Food Processing Classification

| NOVA Group | Description | Products | Percentage |
|------------|-------------|----------|------------|
| **NOVA 4** | Ultra-processed | 22,277 | 70.3% |
| **NOVA 3** | Processed foods | 4,825 | 15.2% |
| **NOVA 1** | Unprocessed/Minimally | 3,943 | 12.5% |
| **NOVA 2** | Culinary ingredients | 625 | 2.0% |

### Nutri-Score Distribution

| Grade | Products | Percentage |
|-------|----------|------------|
| A (Healthiest) | 5,370 | 10.7% |
| B | 2,760 | 5.5% |
| C | 4,656 | 9.3% |
| D | 6,295 | 12.6% |
| E (Least Healthy) | 9,107 | 18.2% |
| Unknown | 21,367 | 42.7% |

### Nutritional Averages (per 100g)

| Nutrient | Mean | Median |
|----------|------|--------|
| Sugars | 20.7g | 6.1g |
| Fat | 17.3g | 4.3g |
| Sodium | 920mg | 167mg |
| Energy | 429 kcal | 265 kcal |

### Top Food Categories
1. Snacks - 1,544 products
2. Condiments/Sauces - 1,044 products
3. Confectioneries - 883 products
4. Cheeses - 788 products
5. Frozen Foods - 719 products

### Top Brands Represented
1. Kroger - 4,550 products
2. Spartan - 1,340 products
3. Roundy's - 1,314 products
4. Private Selection - 1,077 products
5. Simple Truth - 762 products

---

## 4. RuralAccess: Healthcare Shortage Analysis

### Overview
- **Total HPSA Designations:** 14,631
- **States/Territories Affected:** 59
- **Unique Counties with Shortages:** 2,833
- **Discipline:** Primary Care

### Population Impact
- **Total Population in Shortage Areas:** 957,031,727
- **Average Population per HPSA:** 65,451

### HPSA Score Analysis (0-25 scale, higher = more severe shortage)
| Metric | Value |
|--------|-------|
| Mean | 15.1 |
| Median | 16.0 |
| Maximum | 25.0 |
| Minimum | 0.0 |

### Geographic Distribution (Rural vs Urban)

| Status | Designations | Percentage |
|--------|--------------|------------|
| Non-Rural (Urban) | 7,953 | 54.4% |
| Rural | 5,322 | 36.4% |
| Partially Rural | 1,232 | 8.4% |
| Unknown | 122 | 0.8% |

### Top 10 States by HPSA Designations

| Rank | State | Designations | % of Total |
|------|-------|--------------|------------|
| 1 | New York | 1,820 | 12.4% |
| 2 | California | 1,246 | 8.5% |
| 3 | Ohio | 1,071 | 7.3% |
| 4 | Arizona | 700 | 4.8% |
| 5 | Texas | 692 | 4.7% |
| 6 | Illinois | 530 | 3.6% |
| 7 | Wisconsin | 506 | 3.5% |
| 8 | Minnesota | 483 | 3.3% |
| 9 | Tennessee | 480 | 3.3% |
| 10 | Kentucky | 368 | 2.5% |

### Poverty Correlation
- **Mean Poverty Rate in HPSAs:** 23.6%
- **Median Poverty Rate:** 16.8%

---

## Data Sources

### PriceVision
- **Source:** Hospital Price Transparency Machine-Readable Files (MRF)
- **Mandate:** CMS Hospital Price Transparency Rule (45 CFR 180)
- **Format:** CSV, JSON, XLSX (standardized from 7+ formats)
- **Coverage:** 1,002 US hospitals
- **URL:** Individual hospital websites (aggregated)

### DrugWatch
- **US Data:** Medicare Part D Spending by Drug (CMS)
  - URL: https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug
  - Year: 2023

- **Australia Data:** Pharmaceutical Benefits Scheme (PBS)
  - URL: https://www.pbs.gov.au/info/browse/download
  - Exchange Rate: 1 AUD = 0.65 USD

- **Canada Data:** Health Canada Drug Product Database
  - URL: https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database.html

### FoodScore
- **Source:** Open Food Facts Database
  - URL: https://world.openfoodfacts.org/data
  - License: Open Database License (ODbL)

- **Additive Risk Database:** Custom compilation from:
  - FDA GRAS List
  - EFSA Food Additive Database
  - CSPI Chemical Cuisine ratings
  - IARC classifications

### RuralAccess
- **Source:** HRSA Health Professional Shortage Areas (HPSA)
  - URL: https://data.hrsa.gov/topics/health-workforce/shortage-areas
  - API: https://data.hrsa.gov/data/download

- **County Population:** US Census Bureau
  - URL: https://www.census.gov/data/tables/time-series/demo/popest/2020s-counties-total.html

---

## Technical Notes

### Data Processing
- **Processing Date:** January 4, 2026
- **Pipeline:** Python 3.x with pandas, pyarrow
- **Output Format:** Apache Parquet (compressed columnar storage)
- **Total Storage:** ~383 MB processed data

### Data Quality
- **PriceVision Success Rate:** 94.6% (58 files failed due to corrupt/unusual formats)
- **Price Outlier Handling:** Values >$10M filtered for statistics
- **Missing Data:** Handled with null values, not imputed

### Column Standardization
PriceVision data normalized from 50+ column name variants to 14 standard columns:
- description, procedure_code, revenue_code, code_type
- gross_charge, cash_price, min_price, max_price, negotiated_rate
- payer_name, plan_name, setting
- hospital_npi, source_file

---

## Appendix: File Inventory

```
data/processed/
├── pricevision/
│   ├── all_prices_normalized.parquet (375 MB)
│   └── processing_summary.json
├── drugwatch/
│   ├── us_drugs.parquet (199 KB)
│   ├── us_drugs.csv (371 KB)
│   ├── australia_drugs.parquet (303 KB)
│   ├── canada_drugs.parquet (2.0 MB)
│   └── processing_summary.json
├── foodscore/
│   ├── us_products_scored.parquet (4.8 MB)
│   ├── additive_lookup.parquet (5.4 KB)
│   └── processing_summary.json
├── ruralaccess/
│   ├── hpsa_designations.parquet (414 KB)
│   ├── county_shortage_summary.parquet (44 KB)
│   ├── county_population.parquet (65 KB)
│   └── processing_summary.json
└── data_analysis.json
```

---

*This data brief was automatically generated by the HealthGuard America data processing pipeline.*
