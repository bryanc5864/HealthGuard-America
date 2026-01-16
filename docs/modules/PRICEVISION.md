# PriceVision Module Documentation

**Module:** Hospital Price Transparency
**Version:** 1.0
**Last Updated:** January 16, 2026

---

## Overview

PriceVision is HealthGuard's hospital price transparency module that aggregates, normalizes, and analyzes hospital pricing data from Machine-Readable Files (MRFs) mandated by CMS. It enables patients, insurers, and researchers to compare procedure costs across hospitals.

---

## Problem Statement

### Before PriceVision

1. **Price Opacity:** Patients had no way to know procedure costs before treatment
2. **Naming Inconsistency:** Same procedure listed under 50+ different names across hospitals
3. **Format Chaos:** Each hospital's MRF used different schemas, columns, and formats
4. **No Comparison:** Impossible to compare Hospital A vs Hospital B for the same procedure
5. **Surprise Bills:** Patients received bills 10-100x higher than expected

### After PriceVision

1. **Transparent Pricing:** Search any procedure, see prices at all hospitals
2. **ML Normalization:** Procedure Encoder matches different names (0.82+ accuracy)
3. **Unified Schema:** All hospitals normalized to standard format
4. **Easy Comparison:** Side-by-side price comparison with filters
5. **Informed Decisions:** Know costs before choosing where to get care

---

## Data Pipeline

### Data Sources

| Source | Description | Update Frequency |
|--------|-------------|------------------|
| Hospital MRFs | CMS-mandated price files | Annually |
| CMS Provider Data | Hospital metadata, NPI, address | Quarterly |
| CPT Code Database | Procedure code definitions | Annually |

### Pipeline Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Hospital MRF   │────▶│  MRF Parser     │────▶│  Normalizer     │
│  (JSON/CSV)     │     │  (Extract)      │     │  (Transform)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PostgreSQL     │◀────│  Procedure      │◀────│  Price          │
│  Database       │     │  Encoder (ML)   │     │  Validator      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Processing Steps

1. **Discovery:** Crawl CMS database for hospital MRF URLs
2. **Download:** Fetch MRF files (JSON, CSV, or proprietary formats)
3. **Parse:** Extract procedure descriptions, codes, and prices
4. **Normalize:** Standardize column names, price types, payer names
5. **Encode:** Use Procedure Encoder ML model to match to CPT codes
6. **Validate:** Check for outliers, missing data, invalid prices
7. **Load:** Insert into PostgreSQL with hospital foreign keys

---

## Database Schema

### Tables

```sql
-- Hospitals table
CREATE TABLE hospitals (
    id SERIAL PRIMARY KEY,
    npi VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    hospital_type VARCHAR(50),
    bed_count INTEGER,
    mrf_url TEXT,
    mrf_last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Procedures table (canonical)
CREATE TABLE procedures (
    id SERIAL PRIMARY KEY,
    cpt_code VARCHAR(10) UNIQUE,
    description VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    avg_national_price DECIMAL(12,2)
);

-- Hospital prices table
CREATE TABLE hospital_prices (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER REFERENCES hospitals(id),
    procedure_id INTEGER REFERENCES procedures(id),
    description_raw TEXT,
    gross_charge DECIMAL(12,2),
    cash_price DECIMAL(12,2),
    min_negotiated DECIMAL(12,2),
    max_negotiated DECIMAL(12,2),
    payer_name VARCHAR(255),
    plan_name VARCHAR(255),
    negotiated_rate DECIMAL(12,2),
    billing_code VARCHAR(50),
    revenue_code VARCHAR(10),
    setting VARCHAR(20),  -- inpatient/outpatient
    confidence_score FLOAT,  -- ML matching confidence
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_hospital_procedure (hospital_id, procedure_id),
    INDEX idx_cpt_code (billing_code),
    INDEX idx_payer (payer_name)
);
```

### Relationships

```
hospitals (1) ──────< (many) hospital_prices
procedures (1) ─────< (many) hospital_prices
```

---

## ML Integration: Procedure Encoder

### Purpose

Match free-text procedure descriptions to canonical CPT codes.

### How It Works

```python
from ml.procedure_encoder.model import ProcedureEncoder

# Load trained model
encoder = ProcedureEncoder.load("ml/weights/procedure_encoder.pt")

# Encode hospital's raw description
raw_description = "MRI BRAIN W/O CONTRAST 70551"
embedding = encoder.encode([raw_description])

# Compare to canonical procedure embeddings
similarities = cosine_similarity(embedding, canonical_embeddings)
best_match_idx = similarities.argmax()
confidence = similarities.max()

# Result
matched_cpt = "70551"  # MRI Brain without contrast
confidence = 0.88      # High confidence match
```

### Matching Thresholds

| Similarity | Action | Description |
|------------|--------|-------------|
| ≥ 0.80 | Auto-match | High confidence, assign CPT code |
| 0.65 - 0.80 | Review | Flag for manual review |
| < 0.65 | No match | Cannot determine procedure |

### Example Matches

| Hospital Description | Matched CPT | Similarity |
|---------------------|-------------|------------|
| "MRI BRAIN WITHOUT CONTRAST" | 70551 | 0.92 |
| "CT ABDOMEN PELVIS W CONTRAST" | 74177 | 0.87 |
| "COMPLETE BLOOD COUNT CBC" | 85025 | 0.85 |
| "KNEE REPLACEMENT TOTAL LEFT" | 27447 | 0.81 |

---

## API Reference

### Endpoints

#### List Hospitals

```http
GET /api/pricevision/hospitals
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| state | string | Filter by state (e.g., "CA") |
| has_mrf | boolean | Only hospitals with MRF data |
| limit | integer | Results per page (default: 50) |
| offset | integer | Pagination offset |

**Response:**
```json
{
  "total": 1002,
  "hospitals": [
    {
      "npi": "1234567890",
      "name": "General Hospital",
      "city": "Los Angeles",
      "state": "CA",
      "bed_count": 450,
      "mrf_available": true,
      "price_count": 15420
    }
  ]
}
```

#### Get Hospital Prices

```http
GET /api/pricevision/hospitals/{npi}/prices
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| cpt_code | string | Filter by CPT code |
| search | string | Search procedure description |
| payer | string | Filter by insurance payer |
| price_type | string | gross, cash, negotiated |
| min_price | float | Minimum price filter |
| max_price | float | Maximum price filter |

**Response:**
```json
{
  "hospital": {
    "npi": "1234567890",
    "name": "General Hospital"
  },
  "prices": [
    {
      "cpt_code": "70551",
      "description": "MRI Brain without contrast",
      "gross_charge": 3500.00,
      "cash_price": 850.00,
      "negotiated_rates": [
        {"payer": "Blue Cross", "rate": 1200.00},
        {"payer": "Aetna", "rate": 1150.00}
      ]
    }
  ]
}
```

#### Compare Prices

```http
GET /api/pricevision/compare
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| cpt_code | string | Procedure CPT code (required) |
| zip | string | Center point ZIP code |
| radius | integer | Search radius in miles |
| limit | integer | Max hospitals to return |

**Response:**
```json
{
  "procedure": {
    "cpt_code": "70551",
    "description": "MRI Brain without contrast"
  },
  "comparison": [
    {
      "hospital": "Hospital A",
      "distance_miles": 5.2,
      "cash_price": 450.00,
      "avg_negotiated": 850.00
    },
    {
      "hospital": "Hospital B",
      "distance_miles": 8.1,
      "cash_price": 1200.00,
      "avg_negotiated": 1500.00
    }
  ],
  "savings_potential": "$750 (62% savings at Hospital A)"
}
```

#### Match Procedure

```http
POST /api/pricevision/procedures/match
```

**Request Body:**
```json
{
  "description": "MRI HEAD W/O CONTRAST"
}
```

**Response:**
```json
{
  "matches": [
    {
      "cpt_code": "70551",
      "description": "MRI Brain without contrast",
      "similarity": 0.88,
      "confidence": "high"
    }
  ]
}
```

---

## Data Statistics

### Current Dataset

| Metric | Value |
|--------|-------|
| Total Price Records | 30,200,589 |
| Unique Hospitals | 1,002 |
| Unique Procedures | ~15,000 |
| Unique Payers | ~500 |
| Date Range | 2023-2024 |

### Price Distribution

| Price Type | Mean | Median | Min | Max |
|------------|------|--------|-----|-----|
| Gross Charge | $29,442 | $518 | $0.01 | $9.96M |
| Cash Price | $3,519 | $357 | $0.01 | $9.97M |
| Negotiated Rate | $1,288 | $171 | $0.01 | $8.21M |

### Top Payers by Record Count

| Payer | Records |
|-------|---------|
| CIGNA | 175,000 |
| UnitedHealth | 159,357 |
| Multiplan | 124,794 |
| Aetna | 123,662 |
| Humana | 98,421 |

---

## Use Cases

### 1. Patient Price Shopping

```
Scenario: Patient needs an MRI
1. Search "MRI Brain" in PriceVision
2. Filter by ZIP code (within 25 miles)
3. Compare cash prices across hospitals
4. Hospital A: $450, Hospital B: $1,200
5. Choose Hospital A, save $750
```

### 2. Employer Benefits Analysis

```
Scenario: HR selecting in-network hospitals
1. Query all hospitals in state
2. Compare average negotiated rates
3. Identify cost-effective providers
4. Negotiate network inclusion
5. Reduce employee healthcare costs
```

### 3. Policy Research

```
Scenario: Researcher studying price variation
1. Export all prices for CPT 27447 (knee replacement)
2. Analyze geographic variation
3. Correlate with hospital characteristics
4. Publish findings on price transparency
```

---

## Configuration

### Environment Variables

```bash
# Database
PRICEVISION_DB_HOST=localhost
PRICEVISION_DB_PORT=5432
PRICEVISION_DB_NAME=healthguard
PRICEVISION_DB_USER=postgres
PRICEVISION_DB_PASSWORD=secret

# ML Model
PROCEDURE_ENCODER_PATH=ml/weights/procedure_encoder.pt
PROCEDURE_MATCH_THRESHOLD=0.80

# MRF Processing
MRF_DOWNLOAD_DIR=/data/raw/pricevision/mrfs
MRF_MAX_FILE_SIZE_MB=500
MRF_PARSE_TIMEOUT_SEC=300
```

### Config File (ml/config.py)

```python
@dataclass
class ProcedureEncoderConfig:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    max_length: int = 128
    match_threshold: float = 0.80
    review_threshold: float = 0.65
    weights_path: str = "ml/weights/procedure_encoder.pt"
```

---

## File Structure

```
backend/pricevision/
├── __init__.py
├── api/
│   ├── __init__.py          # FastAPI router
│   ├── hospitals.py         # Hospital endpoints
│   ├── prices.py            # Price query endpoints
│   └── compare.py           # Price comparison endpoints
├── models/
│   ├── __init__.py
│   ├── hospital.py          # Hospital ORM model
│   ├── procedure.py         # Procedure ORM model
│   └── price.py             # HospitalPrice ORM model
├── services/
│   ├── __init__.py
│   ├── mrf_parser.py        # MRF file parsing
│   ├── price_normalizer.py  # Price standardization
│   └── procedure_matcher.py # ML matching integration
└── data/
    ├── __init__.py
    └── seed_procedures.py   # CPT code seeding

ml/procedure_encoder/
├── __init__.py
├── model.py                 # ProcedureEncoder class
├── dataset.py               # Training data loading
├── train.py                 # Training script
└── inference.py             # Batch inference

data/
├── raw/pricevision/
│   ├── mrfs/                # Downloaded MRF files
│   └── provider_util/       # CMS provider data
└── processed/pricevision/
    ├── normalized_prices.parquet
    └── procedure_embeddings.pt
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low match confidence | Unusual procedure description | Add to training data, retrain encoder |
| Missing prices | MRF format changed | Update parser for new format |
| Duplicate records | Same procedure, multiple rows | Deduplicate by hospital+CPT+payer |
| Outlier prices | Data entry errors | Apply statistical outlier detection |

### Logging

```python
import logging
logger = logging.getLogger("pricevision")

# Log levels
logger.debug("Parsing MRF file...")
logger.info("Loaded 15,000 prices from Hospital XYZ")
logger.warning("Low confidence match: 0.62 for 'MISC SUPPLY'")
logger.error("Failed to parse MRF: invalid JSON")
```

---

## Future Enhancements

1. **Real-time MRF Monitoring:** Detect when hospitals update prices
2. **Price Prediction:** ML model to predict fair prices
3. **Quality Integration:** Combine price with quality metrics
4. **Mobile App:** Barcode scanning for procedure lookup
5. **Insurance Integration:** Direct insurer API connections

---

*Documentation generated for HealthGuard PriceVision Module*
