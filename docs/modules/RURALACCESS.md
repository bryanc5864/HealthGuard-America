# RuralAccess Module Documentation

**Module:** Healthcare Access & Shortage Mapping
**Version:** 1.0
**Last Updated:** January 16, 2026

---

## Overview

RuralAccess is HealthGuard's healthcare access module that maps Health Professional Shortage Areas (HPSAs), identifies healthcare deserts, and provides county-level analysis of provider availability. It supports policy makers, healthcare organizations, and communities in addressing healthcare access disparities.

---

## Problem Statement

### Before RuralAccess

1. **Fragmented Data:** HPSA, provider, and demographic data in separate systems
2. **No Unified View:** Can't see the complete healthcare access picture
3. **Invisible Deserts:** Healthcare deserts not easily identifiable
4. **Grant Challenges:** Rural communities struggle to quantify needs for funding
5. **Provider Placement:** Medical schools lack data for residency placement

### After RuralAccess

1. **Unified Database:** All access metrics in one place
2. **County Dashboards:** Complete healthcare profile per county
3. **Desert Mapping:** Visual identification of underserved areas
4. **Grant Support:** Data-backed applications for federal funding
5. **Strategic Placement:** Guide provider recruitment to high-need areas

---

## Key Concepts

### Health Professional Shortage Area (HPSA)

HPSAs are designated by HRSA (Health Resources and Services Administration) to identify areas with shortages of:

| HPSA Type | Description | Metric |
|-----------|-------------|--------|
| Primary Care | General/family medicine | Population per PCP |
| Dental | Oral health services | Population per dentist |
| Mental Health | Behavioral health | Population per mental health provider |

### HPSA Designation Types

| Type | Description |
|------|-------------|
| Geographic | Entire county or service area |
| Population | Specific underserved population group |
| Facility | Single facility (FQHC, prison, etc.) |

### HPSA Score

HPSA scores range from 0-25 (primary care/dental) or 0-26 (mental health), with higher scores indicating greater shortage severity.

| Score Range | Severity |
|-------------|----------|
| 0-7 | Low shortage |
| 8-14 | Moderate shortage |
| 15-19 | High shortage |
| 20-25/26 | Severe shortage |

---

## Data Sources

### Primary Sources

| Source | Description | Records | Update |
|--------|-------------|---------|--------|
| HRSA HPSA Database | Official shortage designations | 14,631 | Quarterly |
| CMS Provider Data | Medicare-enrolled providers | 2M+ | Monthly |
| Census ACS | Demographics, poverty rates | 3,143 counties | Annual |
| AHRF | Area Health Resource File | 6,000+ variables | Annual |
| FQHC Locations | Federally Qualified Health Centers | 1,400+ | Quarterly |
| Rural-Urban Codes | USDA rural classification | All counties | Decennial |

### Data Fields

```
HPSA Record:
├── hpsa_id (unique identifier)
├── hpsa_name
├── hpsa_type (primary_care, dental, mental_health)
├── designation_type (geographic, population, facility)
├── hpsa_score (0-26)
├── hpsa_status (designated, proposed, withdrawn)
├── state_fips
├── county_fips
├── population_served
├── provider_count
├── provider_ratio
├── poverty_rate
├── percent_below_fpl
├── rural_status
├── designation_date
└── last_update_date

County Health Profile:
├── fips_code
├── county_name
├── state
├── population
├── population_density
├── percent_rural
├── percent_65_plus
├── median_income
├── poverty_rate
├── uninsured_rate
├── pcp_per_100k
├── dentist_per_100k
├── mental_health_per_100k
├── hospital_count
├── fqhc_count
├── hpsa_primary_care (boolean)
├── hpsa_dental (boolean)
├── hpsa_mental_health (boolean)
└── overall_access_score
```

---

## Database Schema

### Tables

```sql
-- HPSA designations
CREATE TABLE hpsa_designations (
    id SERIAL PRIMARY KEY,
    hpsa_id VARCHAR(20) UNIQUE NOT NULL,
    hpsa_name VARCHAR(500),
    hpsa_type VARCHAR(20) NOT NULL,  -- primary_care, dental, mental_health
    designation_type VARCHAR(20),     -- geographic, population, facility
    hpsa_score INTEGER CHECK (hpsa_score BETWEEN 0 AND 26),
    hpsa_status VARCHAR(20),
    state_fips VARCHAR(2),
    county_fips VARCHAR(5),
    population_served BIGINT,
    provider_count INTEGER,
    provider_ratio FLOAT,
    poverty_rate FLOAT,
    rural_status VARCHAR(20),
    designation_date DATE,
    withdrawal_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_state (state_fips),
    INDEX idx_county (county_fips),
    INDEX idx_type (hpsa_type),
    INDEX idx_score (hpsa_score)
);

-- Counties
CREATE TABLE counties (
    id SERIAL PRIMARY KEY,
    fips_code VARCHAR(5) UNIQUE NOT NULL,
    county_name VARCHAR(100) NOT NULL,
    state_fips VARCHAR(2) NOT NULL,
    state_name VARCHAR(50),
    population INTEGER,
    population_density FLOAT,
    land_area_sq_miles FLOAT,
    percent_rural FLOAT,
    percent_urban FLOAT,
    percent_65_plus FLOAT,
    median_income INTEGER,
    poverty_rate FLOAT,
    uninsured_rate FLOAT,
    rural_urban_code INTEGER,  -- 1-9 USDA code
    metro_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Healthcare providers by county
CREATE TABLE county_providers (
    id SERIAL PRIMARY KEY,
    county_fips VARCHAR(5) REFERENCES counties(fips_code),
    year INTEGER,
    pcp_count INTEGER,
    pcp_per_100k FLOAT,
    specialist_count INTEGER,
    dentist_count INTEGER,
    dentist_per_100k FLOAT,
    mental_health_count INTEGER,
    mental_health_per_100k FLOAT,
    hospital_count INTEGER,
    hospital_beds INTEGER,
    fqhc_count INTEGER,
    urgent_care_count INTEGER,
    pharmacy_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(county_fips, year)
);

-- Healthcare facilities
CREATE TABLE healthcare_facilities (
    id SERIAL PRIMARY KEY,
    facility_id VARCHAR(20) UNIQUE,
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50),  -- hospital, fqhc, clinic, etc.
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    county_fips VARCHAR(5),
    latitude FLOAT,
    longitude FLOAT,
    beds INTEGER,
    is_critical_access BOOLEAN,
    is_rural BOOLEAN,
    accepts_medicaid BOOLEAN,
    accepts_medicare BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Access metrics (materialized view)
CREATE MATERIALIZED VIEW county_access_metrics AS
SELECT
    c.fips_code,
    c.county_name,
    c.state_name,
    c.population,
    c.poverty_rate,
    c.percent_rural,
    cp.pcp_per_100k,
    cp.dentist_per_100k,
    cp.mental_health_per_100k,
    COUNT(DISTINCT h_pc.id) AS hpsa_pc_count,
    COUNT(DISTINCT h_d.id) AS hpsa_dental_count,
    COUNT(DISTINCT h_mh.id) AS hpsa_mh_count,
    MAX(h_pc.hpsa_score) AS max_pc_shortage_score,
    -- Calculate overall access score (0-100, higher = better access)
    CASE
        WHEN cp.pcp_per_100k IS NULL THEN 0
        ELSE LEAST(100, cp.pcp_per_100k * 1.5)
    END * 0.4 +
    CASE
        WHEN COUNT(h_pc.id) > 0 THEN 0
        ELSE 30
    END +
    CASE
        WHEN c.percent_rural > 50 THEN 0
        ELSE 30 * (1 - c.percent_rural / 100)
    END AS access_score
FROM counties c
LEFT JOIN county_providers cp ON c.fips_code = cp.county_fips
LEFT JOIN hpsa_designations h_pc ON c.fips_code = h_pc.county_fips AND h_pc.hpsa_type = 'primary_care'
LEFT JOIN hpsa_designations h_d ON c.fips_code = h_d.county_fips AND h_d.hpsa_type = 'dental'
LEFT JOIN hpsa_designations h_mh ON c.fips_code = h_mh.county_fips AND h_mh.hpsa_type = 'mental_health'
GROUP BY c.fips_code, c.county_name, c.state_name, c.population, c.poverty_rate, c.percent_rural,
         cp.pcp_per_100k, cp.dentist_per_100k, cp.mental_health_per_100k;
```

---

## API Reference

### Endpoints

#### Get HPSA Designations

```http
GET /api/ruralaccess/hpsa
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| state | string | State abbreviation (e.g., "CA") |
| type | string | HPSA type: primary_care, dental, mental_health |
| min_score | integer | Minimum shortage score |
| rural_only | boolean | Only rural designations |
| limit | integer | Results per page |

**Response:**
```json
{
  "total": 14631,
  "hpsas": [
    {
      "hpsa_id": "1234567890",
      "hpsa_name": "Rural County Primary Care",
      "hpsa_type": "primary_care",
      "hpsa_score": 18,
      "severity": "high",
      "state": "KY",
      "county": "Pike County",
      "population_served": 45000,
      "provider_ratio": "3500:1",
      "poverty_rate": 28.5,
      "rural_status": "rural"
    }
  ]
}
```

#### Get County Profile

```http
GET /api/ruralaccess/counties/{fips}
```

**Response:**
```json
{
  "county": {
    "fips": "21195",
    "name": "Pike County",
    "state": "Kentucky",
    "population": 58883,
    "population_density": 79.2,
    "percent_rural": 100,
    "median_income": 32456,
    "poverty_rate": 28.5,
    "uninsured_rate": 8.2
  },
  "healthcare_access": {
    "pcp_count": 12,
    "pcp_per_100k": 20.4,
    "national_avg_pcp": 76.0,
    "pcp_shortage": true,
    "dentist_count": 8,
    "dentist_per_100k": 13.6,
    "mental_health_per_100k": 5.2,
    "hospital_count": 1,
    "fqhc_count": 2,
    "nearest_hospital_miles": 12
  },
  "hpsa_status": {
    "primary_care": {
      "designated": true,
      "score": 18,
      "severity": "high"
    },
    "dental": {
      "designated": true,
      "score": 15,
      "severity": "high"
    },
    "mental_health": {
      "designated": true,
      "score": 20,
      "severity": "severe"
    }
  },
  "access_score": 25,
  "access_grade": "F",
  "recommendations": [
    "Recruit 3+ primary care physicians",
    "Expand FQHC services",
    "Implement telehealth programs"
  ]
}
```

#### Find Nearby Providers

```http
GET /api/ruralaccess/providers/nearby
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| lat | float | Latitude |
| lon | float | Longitude |
| radius | integer | Search radius in miles |
| type | string | Provider type (pcp, dentist, mental_health) |
| limit | integer | Max results |

**Response:**
```json
{
  "location": {
    "lat": 37.4316,
    "lon": -82.5185
  },
  "providers": [
    {
      "name": "Pike County Health Department",
      "type": "fqhc",
      "address": "123 Main St, Pikeville, KY",
      "distance_miles": 8.2,
      "accepts_medicaid": true,
      "accepts_medicare": true,
      "phone": "(606) 555-1234"
    }
  ],
  "nearest_hospital": {
    "name": "Pikeville Medical Center",
    "distance_miles": 12.5,
    "beds": 150,
    "emergency": true
  }
}
```

#### Healthcare Desert Analysis

```http
GET /api/ruralaccess/deserts
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| state | string | State abbreviation |
| threshold | integer | Max access score to be "desert" |

**Response:**
```json
{
  "state": "Kentucky",
  "total_counties": 120,
  "desert_counties": 45,
  "desert_population": 890000,
  "deserts": [
    {
      "fips": "21195",
      "county": "Pike County",
      "access_score": 25,
      "population": 58883,
      "nearest_hospital_miles": 35,
      "pcp_shortage_severity": "severe",
      "interventions_needed": [
        "Mobile health clinic",
        "Telehealth expansion",
        "Provider loan forgiveness"
      ]
    }
  ],
  "map_data": {
    "geojson_url": "/api/ruralaccess/deserts/geojson?state=KY"
  }
}
```

#### State Summary

```http
GET /api/ruralaccess/states/{state}/summary
```

**Response:**
```json
{
  "state": "Kentucky",
  "state_fips": "21",
  "summary": {
    "total_counties": 120,
    "total_population": 4505836,
    "rural_population": 2100000,
    "percent_rural": 46.6
  },
  "hpsa_summary": {
    "primary_care": {
      "designated_areas": 85,
      "population_affected": 2400000,
      "avg_score": 14.2
    },
    "dental": {
      "designated_areas": 92,
      "population_affected": 2800000,
      "avg_score": 15.8
    },
    "mental_health": {
      "designated_areas": 78,
      "population_affected": 2100000,
      "avg_score": 16.5
    }
  },
  "provider_summary": {
    "total_pcp": 3200,
    "pcp_per_100k": 71.0,
    "national_avg": 76.0,
    "deficit": -225
  },
  "worst_counties": [
    {"fips": "21195", "name": "Pike", "access_score": 25},
    {"fips": "21133", "name": "Letcher", "access_score": 28}
  ]
}
```

---

## Data Statistics

### HPSA Overview

| Metric | Value |
|--------|-------|
| Total HPSA Designations | 14,631 |
| States/Territories Affected | 59 |
| Counties with Shortages | 2,833 |
| Population in HPSAs | 957M (designations) |
| Mean HPSA Score | 15.1 |
| Median HPSA Score | 16.0 |

### Top States by Shortage

| State | HPSA Count | % of National |
|-------|------------|---------------|
| New York | 1,820 | 12.4% |
| California | 1,246 | 8.5% |
| Ohio | 1,071 | 7.3% |
| Arizona | 700 | 4.8% |
| Texas | 692 | 4.7% |
| Illinois | 530 | 3.6% |
| Wisconsin | 506 | 3.5% |
| Minnesota | 483 | 3.3% |
| Tennessee | 480 | 3.3% |
| Kentucky | 368 | 2.5% |

### Rural vs Urban

| Classification | HPSAs | Percentage |
|----------------|-------|------------|
| Non-Rural | 7,953 | 54.4% |
| Rural | 5,322 | 36.4% |
| Partially Rural | 1,232 | 8.4% |
| Unknown | 122 | 0.8% |

### Correlation with Poverty

| Poverty Rate | Avg HPSA Score |
|--------------|----------------|
| <10% | 12.3 |
| 10-20% | 14.8 |
| 20-30% | 16.9 |
| >30% | 19.2 |

---

## Use Cases

### 1. Grant Application Support

```
Scenario: Rural hospital applying for HRSA funding
1. Query RuralAccess for county HPSA data
2. Export shortage metrics and severity scores
3. Document population affected
4. Compare to state/national averages
5. Include data in grant narrative
6. Quantify need with official metrics
```

### 2. Medical School Residency Placement

```
Scenario: Medical school placing residents in underserved areas
1. Query high-severity HPSAs by state
2. Filter for areas with FQHC sites
3. Identify counties with loan forgiveness eligibility
4. Match resident preferences to locations
5. Place 20 residents in high-need areas
```

### 3. Telehealth Expansion Planning

```
Scenario: Health system planning telehealth services
1. Map healthcare deserts in service area
2. Identify populations without PCP access
3. Calculate travel times to nearest provider
4. Prioritize telehealth rollout locations
5. Project impact on access scores
```

### 4. Policy Analysis

```
Scenario: State health department assessing shortage trends
1. Compare HPSA trends over 5 years
2. Correlate with provider graduation rates
3. Analyze impact of loan forgiveness programs
4. Identify counties improving/declining
5. Recommend policy interventions
```

---

## Access Score Calculation

### Formula

```python
def calculate_access_score(county):
    """
    Calculate healthcare access score (0-100).
    Higher score = better access.

    Components:
    - Provider availability (40%)
    - HPSA status (30%)
    - Geographic accessibility (20%)
    - Facility availability (10%)
    """
    # Provider component
    pcp_score = min(100, (county.pcp_per_100k / 76.0) * 100)  # 76 = national avg

    # HPSA component (penalize for shortages)
    hpsa_penalty = 0
    if county.hpsa_primary_care:
        hpsa_penalty += 15
    if county.hpsa_dental:
        hpsa_penalty += 10
    if county.hpsa_mental_health:
        hpsa_penalty += 5
    hpsa_score = max(0, 100 - hpsa_penalty)

    # Geographic component
    if county.percent_rural > 80:
        geo_score = 20
    elif county.percent_rural > 50:
        geo_score = 50
    else:
        geo_score = 80

    # Facility component
    facility_score = min(100, (county.hospital_count * 20) + (county.fqhc_count * 15))

    # Weighted average
    access_score = (
        0.40 * pcp_score +
        0.30 * hpsa_score +
        0.20 * geo_score +
        0.10 * facility_score
    )

    return round(access_score)

def get_access_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 80: return 'A'
    if score >= 60: return 'B'
    if score >= 40: return 'C'
    if score >= 20: return 'D'
    return 'F'
```

---

## Configuration

### Environment Variables

```bash
# Database
RURALACCESS_DB_HOST=localhost
RURALACCESS_DB_NAME=healthguard

# Data Sources
HRSA_HPSA_API_URL=https://data.hrsa.gov/api/...
CMS_PROVIDER_URL=https://data.cms.gov/...
CENSUS_API_KEY=your_census_api_key

# Refresh Settings
HPSA_REFRESH_DAYS=90
PROVIDER_REFRESH_DAYS=30
```

---

## File Structure

```
backend/ruralaccess/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── hpsa.py               # HPSA endpoints
│   ├── counties.py           # County profiles
│   ├── providers.py          # Provider search
│   └── deserts.py            # Desert analysis
├── models/
│   ├── __init__.py
│   ├── hpsa.py               # HPSA ORM model
│   ├── county.py             # County ORM model
│   ├── provider.py           # Provider counts
│   └── facility.py           # Facility ORM model
├── services/
│   ├── __init__.py
│   ├── hpsa_service.py       # HPSA data processing
│   ├── access_calculator.py  # Score calculations
│   └── geo_service.py        # Geographic queries
└── data/
    ├── __init__.py
    └── hrsa_loader.py        # HRSA data ingestion

data/
├── raw/ruralaccess/
│   ├── hpsa_designations.csv
│   ├── provider_counts.csv
│   └── fqhc_locations.csv
└── processed/ruralaccess/
    ├── county_access_metrics.parquet
    └── shortage_summary.parquet
```

---

## Future Enhancements

1. **Predictive Modeling:** Forecast future shortage areas
2. **Provider Retirement Tracking:** Anticipate workforce gaps
3. **Telehealth Impact:** Measure telehealth effect on access
4. **Social Determinants:** Integrate SDOH data
5. **Real-time Updates:** Live provider directory integration

---

*Documentation generated for HealthGuard RuralAccess Module*
