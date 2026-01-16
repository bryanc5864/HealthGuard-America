# DrugWatch Module Documentation

**Module:** Drug Price Comparison & Analysis
**Version:** 1.0
**Last Updated:** January 16, 2026

---

## Overview

DrugWatch is HealthGuard's pharmaceutical price transparency module that aggregates drug pricing data from multiple countries (US, Canada, Australia, UK) to enable cross-border price comparison, identify generic alternatives, and support drug affordability research.

---

## Problem Statement

### Before DrugWatch

1. **Price Opacity:** US drug prices among highest globally, but no easy comparison
2. **No Alternatives:** Patients unaware of generic or therapeutic alternatives
3. **Name Confusion:** Same drug has different brand names across countries
4. **Fragmented Data:** Pricing data scattered across government databases
5. **Policy Blind Spots:** No unified view for drug pricing policy analysis

### After DrugWatch

1. **Global Comparison:** See US price vs Canada, Australia, UK instantly
2. **Generic Finder:** Automatic identification of cheaper equivalents
3. **Unified Database:** All drugs matched by active ingredient
4. **Spending Analysis:** Medicare Part D spending transparency
5. **Policy Insights:** Data-driven drug pricing research

---

## Data Sources

### Primary Sources

| Source | Country | Data Type | Records | Update |
|--------|---------|-----------|---------|--------|
| Medicare Part D | USA | Spending, utilization | 3,598 drugs | Annual |
| NADAC | USA | Pharmacy acquisition cost | 25,000+ | Weekly |
| PBS Schedule | Australia | Subsidized drug prices | 14,598 drugs | Monthly |
| PMPRB | Canada | Patented drug prices | 57,658 records | Quarterly |
| NHS Drug Tariff | UK | NHS reimbursement prices | 12,000+ | Monthly |
| VA National Formulary | USA | VA contract prices | 8,000+ | Monthly |

### Data Fields

```
Common Fields (all sources):
├── drug_name (brand)
├── generic_name (active ingredient)
├── ndc/din/pbs_code (national identifier)
├── strength (e.g., "500mg")
├── form (tablet, capsule, injection)
├── manufacturer
├── price_per_unit
├── package_size
├── therapeutic_class
└── atc_code (WHO classification)

US-Specific:
├── total_spending
├── total_beneficiaries
├── total_claims
├── avg_beneficiary_cost
└── price_change_yoy

International:
├── local_currency_price
├── usd_equivalent
├── exchange_rate_date
└── subsidy_status
```

---

## Database Schema

### Tables

```sql
-- Drugs master table (canonical)
CREATE TABLE drugs (
    id SERIAL PRIMARY KEY,
    generic_name VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255),
    atc_code VARCHAR(10),
    therapeutic_class VARCHAR(100),
    form VARCHAR(50),
    strength VARCHAR(50),
    manufacturer VARCHAR(255),
    fda_approval_date DATE,
    patent_expiry DATE,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(generic_name, strength, form)
);

-- US Medicare Part D prices
CREATE TABLE drug_prices_us (
    id SERIAL PRIMARY KEY,
    drug_id INTEGER REFERENCES drugs(id),
    ndc VARCHAR(11),
    year INTEGER,
    total_spending DECIMAL(15,2),
    total_claims BIGINT,
    total_beneficiaries BIGINT,
    avg_price_per_unit DECIMAL(10,4),
    avg_beneficiary_cost DECIMAL(10,2),
    price_change_pct DECIMAL(5,2),
    source VARCHAR(50),  -- 'medicare_part_d', 'nadac', 'va'
    created_at TIMESTAMP DEFAULT NOW()
);

-- International prices
CREATE TABLE drug_prices_intl (
    id SERIAL PRIMARY KEY,
    drug_id INTEGER REFERENCES drugs(id),
    country VARCHAR(3),  -- 'CAN', 'AUS', 'GBR'
    local_code VARCHAR(20),  -- DIN, PBS code, etc.
    local_price DECIMAL(10,4),
    local_currency VARCHAR(3),
    usd_price DECIMAL(10,4),
    exchange_rate DECIMAL(10,6),
    exchange_rate_date DATE,
    subsidy_status VARCHAR(20),
    source VARCHAR(50),
    effective_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Price comparisons (materialized view)
CREATE MATERIALIZED VIEW drug_price_comparison AS
SELECT
    d.id AS drug_id,
    d.generic_name,
    d.brand_name,
    d.strength,
    us.avg_price_per_unit AS us_price,
    can.usd_price AS canada_price,
    aus.usd_price AS australia_price,
    gbr.usd_price AS uk_price,
    ROUND((us.avg_price_per_unit / NULLIF(can.usd_price, 0) - 1) * 100, 1) AS us_vs_canada_pct,
    ROUND((us.avg_price_per_unit / NULLIF(aus.usd_price, 0) - 1) * 100, 1) AS us_vs_australia_pct
FROM drugs d
LEFT JOIN drug_prices_us us ON d.id = us.drug_id
LEFT JOIN drug_prices_intl can ON d.id = can.drug_id AND can.country = 'CAN'
LEFT JOIN drug_prices_intl aus ON d.id = aus.drug_id AND aus.country = 'AUS'
LEFT JOIN drug_prices_intl gbr ON d.id = gbr.drug_id AND gbr.country = 'GBR';
```

---

## Data Processing Pipeline

### Pipeline Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Medicare D     │     │                 │     │                 │
│  NADAC          │────▶│  Drug Name      │────▶│  Price          │
│  PBS            │     │  Normalizer     │     │  Converter      │
│  PMPRB          │     │                 │     │  (USD)          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PostgreSQL     │◀────│  Drug           │◀────│  ATC Code       │
│  Database       │     │  Matcher        │     │  Classifier     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Processing Steps

1. **Ingest:** Download raw data from government sources
2. **Parse:** Extract drug names, prices, identifiers
3. **Normalize:** Standardize generic names (lowercase, remove salts)
4. **Match:** Link across sources by active ingredient + strength
5. **Convert:** Convert all prices to USD using daily exchange rates
6. **Classify:** Assign ATC therapeutic classification codes
7. **Load:** Insert into PostgreSQL, refresh materialized views

### Drug Name Normalization

```python
def normalize_drug_name(name: str) -> str:
    """
    Normalize drug names for matching across sources.

    Examples:
        "METFORMIN HCL 500MG" -> "metformin 500mg"
        "Lipitor (Atorvastatin)" -> "atorvastatin"
        "HUMIRA PEN 40MG/0.8ML" -> "adalimumab 40mg"
    """
    # Lowercase
    name = name.lower()

    # Remove salt forms
    salts = ['hcl', 'hydrochloride', 'sodium', 'potassium',
             'calcium', 'acetate', 'succinate', 'maleate']
    for salt in salts:
        name = name.replace(f' {salt}', '')

    # Extract generic from brand
    if '(' in name:
        generic = re.search(r'\(([^)]+)\)', name)
        if generic:
            name = generic.group(1)

    # Standardize strength format
    name = re.sub(r'(\d+)\s*(mg|mcg|ml|g)', r'\1\2', name)

    return name.strip()
```

---

## API Reference

### Endpoints

#### Search Drugs

```http
GET /api/drugwatch/drugs
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| q | string | Search by name (brand or generic) |
| atc_code | string | Filter by ATC classification |
| therapeutic_class | string | Filter by therapeutic class |
| has_generic | boolean | Only drugs with generic available |
| limit | integer | Results per page (default: 50) |

**Response:**
```json
{
  "total": 156,
  "drugs": [
    {
      "id": 1234,
      "generic_name": "atorvastatin",
      "brand_name": "Lipitor",
      "strength": "20mg",
      "form": "tablet",
      "therapeutic_class": "HMG-CoA Reductase Inhibitors",
      "atc_code": "C10AA05",
      "has_generic": true
    }
  ]
}
```

#### Get Drug Prices

```http
GET /api/drugwatch/drugs/{drug_id}/prices
```

**Response:**
```json
{
  "drug": {
    "generic_name": "atorvastatin",
    "brand_name": "Lipitor",
    "strength": "20mg"
  },
  "prices": {
    "us": {
      "price_per_unit": 12.50,
      "source": "medicare_part_d",
      "total_spending": 2400000000,
      "beneficiaries": 24500000
    },
    "canada": {
      "price_per_unit": 0.85,
      "local_price": 1.15,
      "local_currency": "CAD",
      "source": "pmprb"
    },
    "australia": {
      "price_per_unit": 0.42,
      "local_price": 0.65,
      "local_currency": "AUD",
      "source": "pbs"
    }
  },
  "comparison": {
    "us_vs_canada": "+1370%",
    "us_vs_australia": "+2876%",
    "potential_savings": "$11.65 per unit"
  }
}
```

#### Compare Prices

```http
GET /api/drugwatch/compare
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| drug_id | integer | Drug to compare |
| countries | string | Comma-separated country codes |

**Response:**
```json
{
  "drug": "atorvastatin 20mg",
  "comparison": [
    {"country": "USA", "price": 12.50, "index": 100},
    {"country": "Canada", "price": 0.85, "index": 6.8},
    {"country": "Australia", "price": 0.42, "index": 3.4},
    {"country": "UK", "price": 0.38, "index": 3.0}
  ],
  "chart_data": {
    "labels": ["USA", "Canada", "Australia", "UK"],
    "values": [12.50, 0.85, 0.42, 0.38]
  }
}
```

#### Find Alternatives

```http
GET /api/drugwatch/drugs/{drug_id}/alternatives
```

**Response:**
```json
{
  "drug": "Lipitor (atorvastatin) 20mg",
  "alternatives": {
    "generic": [
      {
        "name": "Atorvastatin 20mg",
        "price": 0.45,
        "savings": "96%"
      }
    ],
    "therapeutic": [
      {
        "name": "Simvastatin 40mg",
        "price": 0.12,
        "note": "Same drug class, different active ingredient"
      },
      {
        "name": "Rosuvastatin 10mg",
        "price": 0.35,
        "note": "Newer statin, may be more effective"
      }
    ]
  }
}
```

#### Top Spending

```http
GET /api/drugwatch/spending/top
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| year | integer | Year (default: latest) |
| limit | integer | Number of drugs (default: 10) |

**Response:**
```json
{
  "year": 2023,
  "total_spending": 275900000000,
  "top_drugs": [
    {
      "rank": 1,
      "drug": "Eliquis (apixaban)",
      "spending": 18300000000,
      "pct_of_total": 6.6,
      "beneficiaries": 4200000,
      "avg_cost_per_beneficiary": 4357
    },
    {
      "rank": 2,
      "drug": "Ozempic (semaglutide)",
      "spending": 9200000000,
      "pct_of_total": 3.3,
      "beneficiaries": 1100000,
      "avg_cost_per_beneficiary": 8364
    }
  ]
}
```

---

## Data Statistics

### US Medicare Part D (2023)

| Metric | Value |
|--------|-------|
| Total Drugs | 3,598 |
| Total Spending | $275.9 Billion |
| Total Beneficiaries | 478.6 Million |
| Mean Price/Unit | $563.02 |
| Median Price/Unit | $8.86 |
| Max Price/Unit | $239,746 (Amvuttra) |

### Top 10 Drugs by Spending

| Rank | Drug | Generic | Spending | % Total |
|------|------|---------|----------|---------|
| 1 | Eliquis | apixaban | $18.3B | 6.6% |
| 2 | Ozempic | semaglutide | $9.2B | 3.3% |
| 3 | Jardiance | empagliflozin | $8.8B | 3.2% |
| 4 | Trulicity | dulaglutide | $7.4B | 2.7% |
| 5 | Xarelto | rivaroxaban | $6.3B | 2.3% |
| 6 | Trelegy Ellipta | fluticasone combo | $4.5B | 1.6% |
| 7 | Humira Pen | adalimumab | $4.4B | 1.6% |
| 8 | Farxiga | dapagliflozin | $4.3B | 1.6% |
| 9 | Januvia | sitagliptin | $4.1B | 1.5% |
| 10 | Revlimid | lenalidomide | $3.9B | 1.4% |

### International Comparison

| Country | Records | Mean Price (USD) | Median Price (USD) |
|---------|---------|------------------|-------------------|
| USA | 3,598 | $563.02 | $8.86 |
| Australia | 14,598 | $5,509.44 | $17.60 |
| Canada | 57,658 | - | - |

---

## Use Cases

### 1. Patient Cost Savings

```
Scenario: Patient prescribed Lipitor 20mg
1. Search "Lipitor" in DrugWatch
2. See US price: $12.50/tablet
3. Find generic: Atorvastatin $0.45/tablet
4. Savings: $12.05/tablet = 96% savings
5. Annual savings: $4,400 (30 tablets/month)
```

### 2. Policy Analysis

```
Scenario: Researcher studying GLP-1 pricing
1. Query all GLP-1 drugs (semaglutide, dulaglutide, etc.)
2. Compare US vs international prices
3. Analyze spending growth year-over-year
4. Identify pricing outliers
5. Publish policy recommendations
```

### 3. Formulary Management

```
Scenario: PBM optimizing drug formulary
1. Export therapeutic class comparisons
2. Identify high-spend, high-margin drugs
3. Find therapeutic alternatives
4. Negotiate volume-based discounts
5. Update formulary tier placement
```

---

## Configuration

### Environment Variables

```bash
# Database
DRUGWATCH_DB_HOST=localhost
DRUGWATCH_DB_NAME=healthguard

# Data Sources
MEDICARE_PART_D_URL=https://data.cms.gov/...
NADAC_API_URL=https://data.medicaid.gov/...
PBS_SCHEDULE_URL=https://www.pbs.gov.au/...

# Exchange Rates
EXCHANGE_RATE_API_KEY=your_api_key
EXCHANGE_RATE_UPDATE_FREQUENCY=daily

# Processing
DRUG_MATCH_THRESHOLD=0.85
PRICE_OUTLIER_STDDEV=3.0
```

---

## File Structure

```
backend/drugwatch/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── drugs.py              # Drug search/lookup
│   ├── prices.py             # Price queries
│   ├── compare.py            # Cross-country comparison
│   └── spending.py           # Spending analysis
├── models/
│   ├── __init__.py
│   ├── drug.py               # Drug ORM model
│   ├── price_us.py           # US prices
│   └── price_intl.py         # International prices
├── services/
│   ├── __init__.py
│   ├── drug_normalizer.py    # Name standardization
│   ├── price_converter.py    # Currency conversion
│   └── alternative_finder.py # Generic/therapeutic alternatives
└── data/
    ├── __init__.py
    ├── medicare_loader.py    # Part D data loader
    ├── pbs_loader.py         # Australia PBS loader
    └── pmprb_loader.py       # Canada PMPRB loader

data/
├── raw/drugwatch/
│   ├── medicare_part_d_2023.csv
│   ├── nadac_prices.csv
│   ├── pbs_schedule.csv
│   └── pmprb_prices.csv
└── processed/drugwatch/
    ├── drugs_normalized.parquet
    └── price_comparison.parquet
```

---

## Future Enhancements

1. **Real-time Price Alerts:** Notify users of price changes
2. **Pharmacy Integration:** Add retail pharmacy prices
3. **Insurance Coverage:** Show formulary tier by insurer
4. **Import Assistance:** Legal drug importation guidance
5. **Biosimilar Tracking:** Monitor biosimilar market entry

---

*Documentation generated for HealthGuard DrugWatch Module*
